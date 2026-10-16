import asyncio

import pytest
from test_digital import fixture

from custom_components.ifm_iolink.port_mode import change_mode


@pytest.mark.parametrize("target", [0, 1, 2, 3])
@pytest.mark.parametrize("ports", [4, 8])
def test_mode_change_readback_and_no_assignment_changes(target, ports):
    hass, c, state, writes, busy = fixture()
    c.identity["ports"] = ports
    state["mode"] = 3 if target != 3 else 1
    original = state["mode"]

    async def write_mode(port, mode):
        writes.append(("mode", port, mode))
        state["mode"] = mode

    c.client.write_port_mode = write_mode
    asyncio.run(change_mode(hass, c, ports, original, target))
    assert state["mode"] == target
    assert writes[0] == ("mode", ports, target)
    assert not busy
    if target == 2:
        assert writes[-1] == (ports, False)
        assert state["output"] == "00"


@pytest.mark.parametrize("failure", ["busy", "stale", "identity", "reload", "invalid", "unknown"])
def test_mode_guard_never_writes(failure):
    hass, c, state, writes, busy = fixture()

    async def write_mode(*args):
        writes.append(args)

    c.client.write_port_mode = write_mode
    expected = 2
    if failure == "busy":
        busy.add(("entry", 1))
    if failure == "stale":
        expected = 3
    if failure == "identity":
        c.identity["serial"] = "OTHER"
    if failure == "reload":
        hass.data["ifm_iolink"]["coordinators"].clear()
    if failure == "invalid":
        expected = True
    if failure == "unknown":
        state["mode"] = None
    with pytest.raises(ValueError):
        asyncio.run(change_mode(hass, c, 1, expected, 1))
    assert not writes


@pytest.mark.parametrize("failure", ["mode_readback", "off_write", "off_readback"])
def test_partial_change_is_unknown_no_retry(failure):
    hass, c, state, writes, busy = fixture()
    state["mode"] = 3

    async def write_mode(port, mode):
        writes.append(("mode", port, mode))
        if failure != "mode_readback":
            state["mode"] = mode

    async def write_output(port, on):
        writes.append(("output", port, on))
        if failure == "off_write":
            raise ValueError("failure")
        state["output"] = "01"

    c.client.write_port_mode = write_mode
    c.client.write_port_output = write_output
    with pytest.raises(ValueError):
        asyncio.run(change_mode(hass, c, 1, 3, 2))
    assert len(writes) == (1 if failure == "mode_readback" else 2)
    assert c.data["1"]["mode"] is None
    assert c.data["1"]["pin4"] is None
    assert not busy


def test_noop_preserves_output():
    hass, c, state, writes, busy = fixture()
    state["output"] = "01"
    asyncio.run(change_mode(hass, c, 1, 2, 2))
    assert state["output"] == "01"
    assert not writes
