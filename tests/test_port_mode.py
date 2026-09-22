"""Port-mode switch checks and failure semantics without writing to real hardware."""

import asyncio
from types import SimpleNamespace

import pytest

from custom_components.ifm_iolink.port_mode import execute_mode_change, prepare_mode_change


def setup(mode=3, connected=True):
    state = {"mode": mode}
    writes, output_writes = [], []

    async def write_port_mode(port, target):
        writes.append((port, target))
        state["mode"] = target

    async def write_port_output(port, on):
        output_writes.append((port, on))

    async def multi(paths):
        return {p: {"code": 200, "data": state["mode"]} for p in paths}

    c = SimpleNamespace(
        client=SimpleNamespace(write_port_mode=write_port_mode, write_port_output=write_port_output, multi=multi),
        condition_values={(1, "prof", 64): 0, (2, "prof", 64): 0},
        metadata_at=1,
    )
    c.data = {
        "1": {
            "mode": state["mode"],
            "connected": connected,
            "assignment": {"name": "Drucksensor"},
            "profile": "prof",
        }
    }
    return c, state, writes, output_writes


def test_preview_reports_current_state_and_rejects_noop():
    c, *_ = setup(mode=3, connected=True)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))
    assert plan == {
        "port": 1,
        "current_mode": 3,
        "target_mode": 2,
        "device_connected": True,
        "assignment_name": "Drucksensor",
        "profile_id": "prof",
    }
    with pytest.raises(ValueError):
        asyncio.run(prepare_mode_change(c, 1, 3))  # already IO-Link


@pytest.mark.parametrize("target", [4, -1, 99])
def test_out_of_range_targets_are_rejected(target):
    c, *_ = setup()
    with pytest.raises(ValueError):
        asyncio.run(prepare_mode_change(c, 1, target))


@pytest.mark.parametrize("target", [0, 1])
def test_disabled_and_di_are_switchable_targets(target):
    c, *_ = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, target))
    assert plan["target_mode"] == target


def test_unknown_port_or_unread_mode_cannot_be_previewed():
    c, *_ = setup()
    with pytest.raises(ValueError):
        asyncio.run(prepare_mode_change(c, 5, 2))
    c.data["1"]["mode"] = None
    with pytest.raises(ValueError):
        asyncio.run(prepare_mode_change(c, 1, 2))


def test_execute_writes_reads_back_and_clears_port_conditions():
    c, state, writes, output_writes = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))
    result = asyncio.run(execute_mode_change(c, 1, plan))
    assert writes == [(1, 2)]
    assert result == {"port": 1, "mode": 2}
    assert c.condition_values == {(2, "prof", 64): 0}
    assert c.metadata_at is None


def test_switching_to_do_initializes_pdout_to_off():
    c, *_, output_writes = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))
    asyncio.run(execute_mode_change(c, 1, plan))
    assert output_writes == [(1, False)]  # pdout has no defined value until the first write


def test_switching_to_iolink_does_not_touch_pdout():
    c, *_, output_writes = setup(mode=2)
    plan = asyncio.run(prepare_mode_change(c, 1, 3))
    asyncio.run(execute_mode_change(c, 1, plan))
    assert output_writes == []


def test_stale_current_mode_aborts_before_write():
    c, state, writes, _ = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))
    c.data["1"]["mode"] = 1  # changed behind our back since the preview
    with pytest.raises(ValueError):
        asyncio.run(execute_mode_change(c, 1, plan))
    assert not writes


def test_reloaded_coordinator_aborts_before_write():
    c, *_ = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))
    with pytest.raises(ValueError):
        asyncio.run(execute_mode_change(c, 1, plan, still_current=lambda: False))


def test_readback_mismatch_after_write_is_reported():
    c, state, writes, _ = setup(mode=3)
    plan = asyncio.run(prepare_mode_change(c, 1, 2))

    async def write_port_mode(port, target):
        writes.append((port, target))
        state["mode"] = 1  # device rejected the requested mode and picked another one

    c.client.write_port_mode = write_port_mode

    with pytest.raises(ValueError):
        asyncio.run(execute_mode_change(c, 1, plan))
    assert writes == [(1, 2)]
