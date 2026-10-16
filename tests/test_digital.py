"""DO safety invariants with simulated I/O, no physical outputs are switched."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ifm_iolink.api import IfmError
from custom_components.ifm_iolink.digital import digital_value, pin2_value, port_mode, set_output


def fixture():
    state = {"mode": 2, "output": "00"}
    writes = []
    identity = {"serial": "MASTER", "model": "AL1350", "ports": 4}

    async def multi(paths):
        return {path: {"code": 200, "data": state["mode" if path.endswith("/mode") else "output"]} for path in paths}

    async def write(port, on):
        writes.append((port, on))
        state["output"] = "01" if on else "00"

    coordinator = SimpleNamespace(
        identity=identity, entry=SimpleNamespace(entry_id="entry"), last_update_success=True,
        data={"1": {"mode": 2, "pin4": False}},
        client=SimpleNamespace(identify=AsyncMock(return_value=dict(identity)), multi=multi, write_port_output=write),
    )
    busy = set()
    hass = SimpleNamespace(data={"ifm_iolink": {
        "coordinators": {"entry": coordinator}, "parameter_backups": SimpleNamespace(busy=busy),
    }})
    return hass, coordinator, state, writes, busy


@pytest.mark.parametrize("value", [None, "", "02", "0001", "ff", 1, True, {}, []])
def test_unknown_process_data_is_not_off(value):
    assert digital_value(value) is None


def test_digital_encodings():
    assert digital_value("00") is False
    assert digital_value("01") is True
    for value in (1, True):
        assert pin2_value(value) is True
    for value in (0, False):
        assert pin2_value(value) is False
    for value in (None, 2, "0", "false", {}, 1.0):
        assert pin2_value(value) is None
    assert port_mode(True) is None
    assert port_mode("2") is None


@pytest.mark.parametrize("on", [True, False])
def test_write_and_verify(on):
    hass, c, state, writes, busy = fixture()
    asyncio.run(set_output(hass, c, 1, on))
    assert writes == [(1, on)]
    assert state["output"] == ("01" if on else "00")
    assert not busy


@pytest.mark.parametrize("mode", [None, 0, 1, 3, "2", True])
def test_live_mode_blocks_stale_cached_do(mode):
    hass, c, state, writes, busy = fixture()
    state["mode"] = mode
    with pytest.raises(ValueError, match="DO"):
        asyncio.run(set_output(hass, c, 1, True))
    assert not writes
    assert not busy


def test_backup_restore_busy_blocks_output():
    hass, c, _, writes, busy = fixture()
    busy.add(("entry", 1))
    with pytest.raises(ValueError, match="läuft bereits"):
        asyncio.run(set_output(hass, c, 1, True))
    assert not writes
    assert busy == {("entry", 1)}


@pytest.mark.parametrize("failure", ["mismatch", "unknown", "mode", "timeout", "cancel"])
def test_unconfirmed_write_never_retries_and_clears_state(failure):
    hass, c, state, writes, busy = fixture()

    async def write(port, on):
        writes.append((port, on))
        if failure == "unknown":
            state["output"] = None
        if failure == "mode":
            state["mode"] = 3
        if failure == "timeout":
            raise IfmError("Timeout after possible write")
        if failure == "cancel":
            raise asyncio.CancelledError

    c.client.write_port_output = write
    with pytest.raises((ValueError, IfmError, asyncio.CancelledError)):
        asyncio.run(set_output(hass, c, 1, True))
    assert writes == [(1, True)]
    assert c.data["1"]["pin4"] is None
    assert not busy


@pytest.mark.parametrize("failure", ["identity", "offline", "reload"])
def test_changed_target_is_rejected(failure):
    hass, c, _, writes, busy = fixture()
    if failure == "identity":
        c.client.identify.return_value["serial"] = "OTHER"
    elif failure == "offline":
        c.last_update_success = False
    else:
        async def identify():
            hass.data["ifm_iolink"]["coordinators"]["entry"] = object()
            return c.identity
        c.client.identify = identify
    with pytest.raises(ValueError):
        asyncio.run(set_output(hass, c, 1, True))
    assert not writes
    assert not busy


def test_two_clients_cannot_interleave_writes():
    async def run():
        hass, c, _, writes, busy = fixture()
        entered, release = asyncio.Event(), asyncio.Event()
        original = c.client.identify

        async def identify():
            entered.set()
            await release.wait()
            return await original()

        c.client.identify = identify
        task = asyncio.create_task(set_output(hass, c, 1, True))
        await entered.wait()
        with pytest.raises(ValueError, match="läuft bereits"):
            await set_output(hass, c, 1, False)
        assert busy == {("entry", 1)}
        release.set()
        await task
        assert writes == [(1, True)]
        assert not busy

    asyncio.run(run())


@pytest.mark.parametrize("port,on", [(0, True), (5, True), (True, True), (1, 1)])
def test_invalid_requests_do_not_write(port, on):
    hass, c, _, writes, _ = fixture()
    with pytest.raises(ValueError):
        asyncio.run(set_output(hass, c, port, on))
    assert not writes
