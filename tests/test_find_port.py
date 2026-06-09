"""Tests for the pure logic in soarm.find_port (classification + config rewrite)."""

from soarm.find_port import classify_arm, normalize_port, update_config_ports


def test_normalize_port_cu_to_tty():
    assert normalize_port("/dev/cu.usbmodem5B41") == "/dev/tty.usbmodem5B41"
    assert normalize_port("/dev/tty.usbmodem5B41") == "/dev/tty.usbmodem5B41"  # idempotent
    assert normalize_port("/dev/ttyACM0") == "/dev/ttyACM0"  # Linux untouched


def test_classify_arm():
    assert classify_arm(12.0) == "follower"
    assert classify_arm(11.9) == "follower"
    assert classify_arm(4.9) == "leader"
    assert classify_arm(5.0) == "leader"
    assert classify_arm(8.0) == "follower"  # split is inclusive on the follower side


def test_update_config_ports_replaces_per_section():
    cfg = (
        "# header comment\n"
        "[follower]\n"
        'port = "/dev/old-follower"\n'
        'id = "my_follower"\n'
        "\n"
        "[leader]\n"
        'port = "/dev/old-leader"\n'
        'id = "my_leader"\n'
    )
    out = update_config_ports(cfg, {"follower": "/dev/new-f", "leader": "/dev/new-l"})
    assert 'port = "/dev/new-f"' in out
    assert 'port = "/dev/new-l"' in out
    assert "/dev/old-follower" not in out and "/dev/old-leader" not in out
    # comments and non-port lines preserved
    assert "# header comment" in out
    assert 'id = "my_follower"' in out and 'id = "my_leader"' in out


def test_update_config_ports_only_touches_known_sections():
    cfg = "[other]\nport = \"/dev/keep\"\n[follower]\nport = \"/dev/old\"\n"
    out = update_config_ports(cfg, {"follower": "/dev/new"})
    assert 'port = "/dev/keep"' in out   # [other] section untouched
    assert 'port = "/dev/new"' in out
