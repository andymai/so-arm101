#!/usr/bin/env python3
"""Self-contained interactive MuJoCo viewer for the SO-101 — no ``mjpython`` needed.

The stock ``python -m mujoco.viewer`` requires the ``mjpython`` trampoline on macOS
(it frees the Cocoa main thread). On a uv/venv whose interpreter is *not* a framework
build, that trampoline relaunches into the system framework Python and crashes inside
``_Simulate`` with an opaque "Caught an unknown exception!". Direct GLFW windowing,
however, works fine from the venv. So this drives the GLFW render loop ourselves on the
main thread — orbit (left-drag), pan (right-drag / shift-left-drag), zoom (scroll).

    python sim/view.py                       # scene.xml, free physics (settles under gravity)
    python sim/view.py --sweep               # drive each joint through its range, one at a time
    python sim/view.py sim/SO101/so101_old_calib.xml --sweep

``--sweep`` is the visual calibration check: each joint swings center→max→center→min→center
so you can confirm the model's ranges (and zero pose) match the real arm. The active joint
is shown in the window title.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import glfw
import mujoco

DEFAULT = Path(__file__).resolve().parent / "SO101" / "scene.xml"
SECS_PER_JOINT = 3.0  # sweep dwell time per joint


def joint_sweep_targets(model: mujoco.MjModel):
    """Per-joint (name, qpos_adr, lo, hi) for the sweep, in model joint order.

    Continuous/unlimited joints (e.g. wrist_roll) have no MJCF range, so we sweep them
    ±180° about their zero — enough to see the full revolution without a hard stop.
    """
    targets = []
    for j in range(model.njnt):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) or f"joint{j}"
        adr = model.jnt_qposadr[j]
        if model.jnt_limited[j]:
            lo, hi = model.jnt_range[j]
        else:
            lo, hi = -math.pi, math.pi
        targets.append((name, int(adr), float(lo), float(hi)))
    return targets


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("model", nargs="?", default=str(DEFAULT),
                        help="path to MJCF (default: sim/SO101/scene.xml)")
    parser.add_argument("--sweep", action="store_true",
                        help="animate each joint through its range (visual calibration check)")
    args = parser.parse_args(argv[1:])

    path = Path(args.model)
    if not path.exists():
        print(f"model not found: {path}\n(run `python sim/fetch.py` first)", file=sys.stderr)
        return 1

    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    targets = joint_sweep_targets(model) if args.sweep else []

    if not glfw.init():
        print("glfw.init() failed — no display?", file=sys.stderr)
        return 1
    window = glfw.create_window(960, 720, f"SO-101 — {path.name}", None, None)
    if not window:
        glfw.terminate()
        print("glfw.create_window() failed — no window server access?", file=sys.stderr)
        return 1
    glfw.make_context_current(window)
    glfw.swap_interval(1)

    cam = mujoco.MjvCamera()
    opt = mujoco.MjvOption()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.distance *= 0.5  # default frames the whole floor; pull in to the arm
    scene = mujoco.MjvScene(model, maxgeom=10_000)
    ctx = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_150)

    # --- mouse state for orbit/pan/zoom ---
    state = {"lastx": 0.0, "lasty": 0.0, "left": False, "right": False}

    def on_mouse_button(win, button, act, mods):
        state["left"] = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
        state["right"] = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
        state["lastx"], state["lasty"] = glfw.get_cursor_pos(win)

    def on_cursor_move(win, xpos, ypos):
        dx, dy = xpos - state["lastx"], ypos - state["lasty"]
        state["lastx"], state["lasty"] = xpos, ypos
        if not (state["left"] or state["right"]):
            return
        width, height = glfw.get_window_size(win)
        shift = (
            glfw.get_key(win, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
            or glfw.get_key(win, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS
        )
        if state["right"] or (state["left"] and shift):
            action = mujoco.mjtMouse.mjMOUSE_MOVE_H if shift else mujoco.mjtMouse.mjMOUSE_MOVE_V
        else:
            action = mujoco.mjtMouse.mjMOUSE_ROTATE_V
        mujoco.mjv_moveCamera(model, action, dx / height, dy / height, scene, cam)

    def on_scroll(win, xoff, yoff):
        mujoco.mjv_moveCamera(model, mujoco.mjtMouse.mjMOUSE_ZOOM, 0.0, -0.05 * yoff, scene, cam)

    def on_key(win, key, scancode, act, mods):
        if act == glfw.PRESS and key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(win, True)
        if act == glfw.PRESS and key == glfw.KEY_BACKSPACE:
            mujoco.mj_resetData(model, data)  # reset pose

    glfw.set_mouse_button_callback(window, on_mouse_button)
    glfw.set_cursor_pos_callback(window, on_cursor_move)
    glfw.set_scroll_callback(window, on_scroll)
    glfw.set_key_callback(window, on_key)

    mode = "sweep" if args.sweep else "free physics"
    print(f"viewing {path.name} [{mode}] — left-drag orbit, right-drag/shift pan, "
          "scroll zoom, Backspace reset, Esc quit")

    active_label = None
    while not glfw.window_should_close(window):
        if args.sweep:
            # Kinematic playback: park every joint at the center of its range, then swing
            # the one active joint center→max→center→min→center. No physics (mj_forward,
            # not mj_step) so gravity doesn't drag the arm down mid-check.
            t = glfw.get_time()
            idx = int(t / SECS_PER_JOINT) % len(targets)
            phase = (t % SECS_PER_JOINT) / SECS_PER_JOINT
            for k, (_name, adr, lo, hi) in enumerate(targets):
                mid = 0.5 * (lo + hi)
                if k == idx:
                    data.qpos[adr] = mid + 0.5 * (hi - lo) * math.sin(2 * math.pi * phase)
                else:
                    data.qpos[adr] = mid
            mujoco.mj_forward(model, data)
            if targets[idx][0] != active_label:
                active_label = targets[idx][0]
                glfw.set_window_title(window, f"SO-101 — {path.name} — sweep: {active_label}")
        else:
            mujoco.mj_step(model, data)

        viewport = mujoco.MjrRect(0, 0, *glfw.get_framebuffer_size(window))
        mujoco.mjv_updateScene(
            model, data, opt, None, cam, mujoco.mjtCatBit.mjCAT_ALL, scene
        )
        mujoco.mjr_render(viewport, scene, ctx)
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
