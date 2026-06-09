"""Tests for the pure logic in soarm.record (camera-spec building)."""

import pytest

from soarm.record import _cameras_arg


def test_cameras_arg_single():
    out = _cameras_arg(["front=0"], 640, 480, 30)
    assert out == "{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}"


def test_cameras_arg_multiple():
    out = _cameras_arg(["front=0", "wrist=2"], 320, 240, 15)
    assert out.startswith("{front: ") and ", wrist: " in out
    assert "index_or_path: 2" in out and "width: 320" in out


def test_cameras_arg_path_index():
    # index_or_path may be a device path, not just an integer
    out = _cameras_arg(["front=/dev/video0"], 640, 480, 30)
    assert "index_or_path: /dev/video0" in out


@pytest.mark.parametrize("bad", ["=0", "front=", "front cam=0", "fr:ont=0", "noequals"])
def test_cameras_arg_rejects_malformed(bad):
    with pytest.raises(SystemExit):
        _cameras_arg([bad], 640, 480, 30)
