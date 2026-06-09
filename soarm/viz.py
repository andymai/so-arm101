"""Rerun-based visualization for the SO-101.

LeRobot's whole viz stack is Rerun, so we are too. rerun-sdk is pinned <0.27 (lerobot's
cap), which predates Rerun's Python URDF API — so we parse the URDF and do forward
kinematics with yourdfpy ourselves, log each link mesh once, and stream a per-link
Transform3D each frame. No MuJoCo, no GLFW, no mjpython.

Three commands, registered onto the main Typer app by register():
  soarm view             offline: the model at neutral, or a joint sweep
  soarm twin  --live     digital twin: mirror the real arm(s); overlay leader on follower
  soarm replay DATASET   play a recorded LeRobot episode (joints + camera frames)
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import rerun as rr
import typer
import yourdfpy

from .bus import CONTINUOUS, MOTORS, REG
from .console import console

ASSETS = Path(__file__).resolve().parent.parent / "sim" / "SO101"
DEFAULT_URDF = ASSETS / "so101_new_calib.urdf"

# leader ghost tint (RGBA, 0-255); follower keeps its original mesh colors
GHOST = (90, 170, 255, 120)


def _require_urdf(urdf: Path) -> Path:
    if not urdf.exists():
        raise SystemExit(f"URDF not found: {urdf}\nrun `soarm fetch` first to download the assets.")
    return urdf


class Robot:
    """A URDF robot mirrored into Rerun: log link meshes once, then push FK transforms.

    Meshes are logged in their local frame at an entity path per scene-graph node; each
    frame we recompute the node->world transform with yourdfpy and log it at the same
    path, so Rerun animates the kinematic chain.
    """

    def __init__(self, urdf_path: Path, root: str, *, tint: tuple | None = None):
        self.urdf = yourdfpy.URDF.load(str(urdf_path), load_meshes=True, build_scene_graph=True)
        self.root = root
        self.tint = tint
        self.joint_names = list(self.urdf.actuated_joint_names)
        self._nodes = list(self.urdf.scene.graph.nodes_geometry)

    def log_meshes(self) -> None:
        """Log every link mesh once as static geometry (local frame)."""
        scene = self.urdf.scene
        albedo = (np.array(self.tint[:3]) / 255.0) if self.tint else None
        for node in self._nodes:
            _, geom_name = scene.graph.get(node)
            mesh = scene.geometry[geom_name]
            rr.log(
                f"{self.root}/{node}",
                rr.Mesh3D(
                    vertex_positions=np.asarray(mesh.vertices, dtype=np.float32),
                    triangle_indices=np.asarray(mesh.faces, dtype=np.uint32),
                    albedo_factor=albedo,
                ),
                static=True,
            )

    def set_joints(self, angles: dict[str, float]) -> None:
        """Apply joint angles (radians) and stream each link's world transform."""
        cfg = {n: float(angles.get(n, 0.0)) for n in self.joint_names}
        self.urdf.update_cfg(cfg)
        scene = self.urdf.scene
        for node in self._nodes:
            t, _ = scene.graph.get(node)
            rr.log(f"{self.root}/{node}",
                   rr.Transform3D(translation=t[:3, 3], mat3x3=t[:3, :3]))


def normalized_to_radians(pos: dict[str, float], urdf: yourdfpy.URDF) -> dict[str, float]:
    """Map LeRobot normalized joints (degrees; gripper 0-100) to URDF joint radians."""
    out: dict[str, float] = {}
    for name in urdf.actuated_joint_names:
        v = pos.get(name)
        if v is None:
            continue
        if name == "gripper":
            joint = urdf.joint_map[name]
            lo, hi = joint.limit.lower, joint.limit.upper
            out[name] = lo + (v / 100.0) * (hi - lo)
        else:
            out[name] = math.radians(v)
    return out


def _init(name: str, save: Optional[Path]) -> None:
    """Start a Rerun recording — spawn the viewer, or write a shareable .rrd."""
    rr.init(f"soarm:{name}", spawn=save is None)
    if save is not None:
        rr.save(str(save))
        console.print(f"recording to [cyan]{save}[/] (open with: rerun {save})")


# --------------------------------------------------------------------------- commands


def view(
    sweep: Annotated[bool, typer.Option(help="sweep each joint through its range")] = False,
    urdf: Annotated[Path, typer.Option(help="URDF to load")] = DEFAULT_URDF,
    save: Annotated[Optional[Path], typer.Option(help="write a .rrd instead of opening the viewer")] = None,
    seconds: Annotated[float, typer.Option(help="sweep duration when --sweep/--save")] = 12.0,
) -> None:
    """Offline viewer: the SO-101 at its neutral (range-middle) pose, or a joint sweep."""
    _require_urdf(urdf)
    _init("view", save)
    robot = Robot(urdf, "robot")
    robot.log_meshes()

    if not sweep:
        robot.set_joints({})  # neutral
        if save is None:
            console.print("viewing neutral pose in Rerun. Ctrl-C to quit.")
            _idle()
        return

    # sweep one joint at a time, center -> max -> center -> min -> center
    names = [n for n in robot.joint_names]
    per = max(seconds / max(len(names), 1), 0.5)
    steps = 40
    t0 = 0.0
    for name in names:
        joint = robot.urdf.joint_map[name]
        lo, hi = joint.limit.lower, joint.limit.upper
        mid = 0.5 * (lo + hi)
        for k in range(steps):
            phase = k / steps
            rr.set_time_seconds("sweep", t0 + phase * per)
            robot.set_joints({name: mid + 0.5 * (hi - lo) * math.sin(2 * math.pi * phase)})
        t0 += per


def twin(
    live: Annotated[bool, typer.Option(help="mirror the real arm(s) over serial")] = False,
    tol: Annotated[float, typer.Option(help="leader/follower divergence threshold (deg)")] = 8.0,
    hz: Annotated[float, typer.Option(help="update rate when --live")] = 30.0,
    urdf: Annotated[Path, typer.Option(help="URDF to load")] = DEFAULT_URDF,
    save: Annotated[Optional[Path], typer.Option(help="write a .rrd instead of opening the viewer")] = None,
) -> None:
    """Digital twin: overlay the leader (ghost) on the follower (solid) and plot sync."""
    _require_urdf(urdf)
    _init("twin", save)
    follower_robot = Robot(urdf, "follower")
    leader_robot = Robot(urdf, "leader", tint=GHOST)
    follower_robot.log_meshes()
    leader_robot.log_meshes()

    if not live:
        follower_robot.set_joints({})
        leader_robot.set_joints({})
        console.print("offline twin: both arms at neutral. Run with [cyan]--live[/] to mirror "
                      "hardware. Ctrl-C to quit.")
        if save is None:
            _idle()
        return

    _twin_live(follower_robot, leader_robot, tol=tol, hz=hz, has_viewer=save is None)


def _twin_live(follower_robot: Robot, leader_robot: Robot, *, tol: float, hz: float,
               has_viewer: bool) -> None:
    from .devices import follower, follower_positions, leader, leader_positions

    period = 1.0 / max(hz, 1.0)
    console.print(f"live twin @ {hz:.0f} Hz — move the leader; ghost tracks follower. Ctrl-C to quit.")
    with follower() as f, leader() as lead:
        try:
            while True:
                fpos = follower_positions(f)
                lpos = leader_positions(lead)
                rr.set_time_seconds("wall", time.monotonic())

                follower_robot.set_joints(normalized_to_radians(fpos, follower_robot.urdf))
                leader_robot.set_joints(normalized_to_radians(lpos, leader_robot.urdf))

                worst = 0.0
                for name in MOTORS.values():
                    if name in fpos and name in lpos:
                        d = lpos[name] - fpos[name]
                        rr.log(f"sync/{name}", rr.Scalars(d))
                        if name not in CONTINUOUS:
                            worst = max(worst, abs(d))
                rr.log("sync/worst_abs", rr.Scalars(worst))
                _stream_health("follower", f)
                if worst > tol:
                    rr.log("sync/status", rr.TextLog(f"OUT OF SYNC: {worst:.1f} deg > {tol}",
                                                     level=rr.TextLogLevel.WARN))
                if not has_viewer:
                    return  # one frame is enough to validate a .rrd
                time.sleep(period)
        except KeyboardInterrupt:
            console.print("\nstopped.")


def _stream_health(arm: str, device) -> None:
    """Best-effort: stream voltage/temp per motor onto the timeline, reusing the device's
    already-open bus (no second serial connection). Silently skips if unavailable."""
    try:
        ph = device.bus.packet_handler
        po = device.bus.port_handler
    except Exception:  # noqa: BLE001 — health is a bonus, never break the twin
        return
    v_addr = REG["Present_Voltage"][0]
    t_addr = REG["Present_Temperature"][0]
    for mid, name in MOTORS.items():
        try:
            v, comm, _ = ph.read1ByteTxRx(po, mid, v_addr)
            if comm == 0:
                rr.log(f"health/{arm}/{name}/voltage", rr.Scalars(v / 10))
            t, comm, _ = ph.read1ByteTxRx(po, mid, t_addr)
            if comm == 0:
                rr.log(f"health/{arm}/{name}/temp", rr.Scalars(float(t)))
        except Exception:  # noqa: BLE001
            continue


def replay(
    dataset: Annotated[str, typer.Argument(help="LeRobot dataset: local path or hub repo id")],
    episode: Annotated[int, typer.Option(help="episode index to replay")] = 0,
    urdf: Annotated[Path, typer.Option(help="URDF to load")] = DEFAULT_URDF,
    save: Annotated[Optional[Path], typer.Option(help="write a .rrd instead of opening the viewer")] = None,
) -> None:
    """Replay a recorded LeRobot episode in Rerun (joint poses + camera frames)."""
    _require_urdf(urdf)
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    root = dataset if Path(dataset).exists() else None
    repo_id = Path(dataset).name if root else dataset
    console.print(f"loading {'local ' if root else 'hub '}dataset [cyan]{dataset}[/] episode {episode} ...")
    ds = LeRobotDataset(repo_id, root=root)

    if episode >= ds.num_episodes:
        raise SystemExit(f"episode {episode} out of range (dataset has {ds.num_episodes})")
    frm = int(ds.episode_data_index["from"][episode])
    to = int(ds.episode_data_index["to"][episode])

    _init("replay", save)
    robot = Robot(urdf, "robot")
    robot.log_meshes()
    joints = list(MOTORS.values())

    for i in range(frm, to):
        item = ds[i]
        rr.set_time_sequence("frame", i - frm)
        state = item.get("observation.state")
        if state is not None:
            pos = {name: float(state[j]) for j, name in enumerate(joints) if j < len(state)}
            robot.set_joints(normalized_to_radians(pos, robot.urdf))
        for key, val in item.items():
            if key.startswith("observation.images"):
                img = np.asarray(val)
                if img.ndim == 3 and img.shape[0] in (1, 3):  # CHW -> HWC
                    img = np.transpose(img, (1, 2, 0))
                if img.dtype != np.uint8:
                    img = (img * 255).clip(0, 255).astype(np.uint8)
                rr.log(key.replace("observation.images.", "camera/"), rr.Image(img))
    console.print(f"replayed {to - frm} frames.")


def _idle() -> None:
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        console.print("\nstopped.")


def fetch() -> None:
    """Download the SO-101 URDF + meshes used by the visualization tools."""
    from . import fetch as _fetch

    _fetch.run()


def register(app: typer.Typer) -> None:
    """Attach the viz subcommands to the main soarm Typer app."""
    app.command()(view)
    app.command()(twin)
    app.command()(replay)
    app.command()(fetch)
