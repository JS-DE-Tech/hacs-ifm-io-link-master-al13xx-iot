"""Coordinator logic tests with a minimal HA scheduler boundary, not an HA startup test."""

import asyncio
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from custom_components.ifm_iolink.api import IfmError
from custom_components.ifm_iolink.const import port_path


@pytest.fixture
def coordinator_module(monkeypatch):
    for name in ("homeassistant", "homeassistant.helpers", "homeassistant.util"):
        module = ModuleType(name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    scheduler = ModuleType("homeassistant.helpers.update_coordinator")

    class Coordinator:
        def __init__(self, *args, **kwargs):
            self.data = None
            self.last_update_success = True

    class UpdateFailed(Exception):
        pass

    scheduler.DataUpdateCoordinator = Coordinator
    scheduler.UpdateFailed = UpdateFailed
    monkeypatch.setitem(sys.modules, scheduler.__name__, scheduler)
    dt = ModuleType("homeassistant.util.dt")
    dt.utcnow = lambda: datetime.now(timezone.utc)
    monkeypatch.setitem(sys.modules, dt.__name__, dt)
    sys.modules.pop("custom_components.ifm_iolink.coordinator", None)
    yield importlib.import_module("custom_components.ifm_iolink.coordinator")
    sys.modules.pop("custom_components.ifm_iolink.coordinator", None)


def instance(module, condition_value=0):
    profile = json.loads(
        (Path(__file__).parents[1] / "custom_components/ifm_iolink/profiles/pn7096.json").read_text(encoding="utf-8")
    )
    profile["conditions"] = [{"index": 64, "value": 0}]
    library = SimpleNamespace(all={"pn7096": profile}, suggest=lambda identity: ["pn7096"])
    entry = SimpleNamespace(
        entry_id="entry",
        title="PRIVATE LOCATION",
        options={"ports": {"1": {"profile": "pn7096"}, "2": {"profile": "pn7096"}}},
    )

    class Client:
        fail = False
        device = 602

        async def multi(self, paths):
            if self.fail:
                raise IfmError("network unavailable")
            result = {}
            for port in (1, 2):
                for name, value in {
                    "pdin": "08980101" if port == 1 else "BAD",
                    "status": 2,
                    "vendorid": 310,
                    "deviceid": self.device,
                    "serial": "PRIVATE SERIAL",
                    "applicationspecifictag": "PRIVATE TAG",
                }.items():
                    path = port_path(port, name)
                    if path in paths:
                        result[path] = {"code": 200, "data": value}
            return result

        async def request(self, path, data):
            return {"value": f"{condition_value:02X}"}

    client = Client()
    c = module.IfmCoordinator(None, entry, client, {"serial": "PRIVATE MASTER", "model": "AL1350", "ports": 2}, library)
    return c, client


def test_metadata_refreshes_after_boot_and_invalidation(coordinator_module, monkeypatch):
    """Adapted from 100prznt/dff25a6; cover restore invalidation as well."""
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: 5.0)
    c, client = instance(coordinator_module)
    result = asyncio.run(c._async_update_data())
    assert result["1"]["identity"]["vendorid"] == 310
    assert result["1"]["values"]["pd_1"] == 0.22
    client.device = 601
    c.metadata_at = None
    result = asyncio.run(c._async_update_data())
    assert result["1"]["identity"]["deviceid"] == 601
    assert result["1"]["error"]


@pytest.mark.parametrize("mode,raw,expected", [(1, "00", False), (1, None, None), (2, "01", True), (2, "02", None)])
def test_digital_polling_preserves_unknown_and_rechecks_mode(coordinator_module, mode, raw, expected):
    c, client = instance(coordinator_module)
    original = client.multi
    live = {"mode": mode}

    async def multi(paths):
        result = await original(paths)
        result["/iolinkmaster/port[1]/mode"] = {"code": 200, "data": live["mode"]}
        result["/iolinkmaster/port[1]/pin2in"] = {"code": 200, "data": 1}
        result[port_path(1, "pdout" if mode == 2 else "pdin")] = {"code": 200, "data": raw}
        result["/iolinkmaster/port[2]/pin2in"] = {"code": 500, "data": 0}
        return result

    client.multi = multi
    result = asyncio.run(c._async_update_data())
    assert result["1"]["pin4"] is expected
    assert result["1"]["pin2"] is True
    assert result["2"]["pin2"] is None
    assert result["1"]["values"] == {}
    live["mode"] = 0
    result = asyncio.run(c._async_update_data())
    assert result["1"]["mode"] == 0
    assert result["1"]["pin4"] is None


def test_one_bad_port_does_not_remove_other_measurement(coordinator_module):
    c, _ = instance(coordinator_module)
    result = asyncio.run(c._async_update_data())
    assert result["1"]["values"]["pd_1"] == 0.22
    assert result["2"]["error"]
    assert result["2"]["values"] == {}


def test_wrong_device_and_wrong_mode_are_unavailable(coordinator_module):
    c, client = instance(coordinator_module)
    client.device = 601
    assert asyncio.run(c._async_update_data())["1"]["error"]
    c, _ = instance(coordinator_module, condition_value=1)
    assert "Index 64" in asyncio.run(c._async_update_data())["1"]["error"]


def test_network_error_marks_update_failed(coordinator_module):
    c, client = instance(coordinator_module)
    client.fail = True
    with pytest.raises(coordinator_module.UpdateFailed):
        asyncio.run(c._async_update_data())


def test_diagnostics_redact_identity_and_bound_history(coordinator_module):
    c, _ = instance(coordinator_module)
    for _ in range(40):
        c.data = asyncio.run(c._async_update_data())
    result = c.diagnostic(1)
    assert len(result["ports"]["1"]["samples"]) == 30
    assert "PRIVATE" not in json.dumps(result)
