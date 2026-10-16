"""Independent safety expectations; failures block adoption, not expected xfails."""
import asyncio

import pytest
from test_coordinator import coordinator_module, instance  # noqa: F401
from test_port_mode import setup

from custom_components.ifm_iolink.decoder import encode_parameter
from custom_components.ifm_iolink.port_mode import execute_mode_change, prepare_mode_change


def test_reject_invalid_sentinel_write():
    parameter = {"access": "rw", "decoder": {"fields": [
        {"type": "uint", "length": 1, "invalid_values": [255]},
    ]}}
    with pytest.raises(ValueError):
        encode_parameter(parameter, 255)


def test_reject_changed_live_port_mode():
    coordinator, live, writes, _ = setup()
    plan = asyncio.run(prepare_mode_change(coordinator, 1, 2))
    live["mode"] = 1
    try:
        asyncio.run(execute_mode_change(coordinator, 1, plan))
    except ValueError:
        pass
    assert writes == []


def test_missing_di_data_is_unknown(coordinator_module):
    coordinator, client = instance(coordinator_module)
    client.mode = 1
    client.pdin1 = None
    assert asyncio.run(coordinator._async_update_data())["1"]["pin4"] is None


def test_system_command_not_numeric_parameter():
    parameter = {"index": 2, "access": "rw", "decoder": {"fields": [{"type": "uint", "length": 1}]}}
    with pytest.raises(ValueError):
        encode_parameter(parameter, 130)
