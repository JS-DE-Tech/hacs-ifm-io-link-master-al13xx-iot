"""Coordinator logic tests with a minimal HA scheduler boundary, not an HA startup test."""

import asyncio
import importlib
import json
import sys
import time
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
        master = {}
        mode = 3
        pdout = "01"
        pdin1 = "08980101"

        async def multi(self, paths):
            if self.fail:
                raise IfmError("network unavailable")
            result = {}
            for port in (1, 2):
                for name, value in {
                    "pdin": self.pdin1 if port == 1 else "BAD",
                    "status": 2,
                    "vendorid": 310,
                    "deviceid": self.device,
                    "serial": "PRIVATE SERIAL",
                    "applicationspecifictag": "PRIVATE TAG",
                    "pdout": self.pdout,
                }.items():
                    path = port_path(port, name)
                    if path in paths:
                        result[path] = {"code": 200, "data": value}
                mode_path = f"/iolinkmaster/port[{port}]/mode"
                if mode_path in paths:
                    result[mode_path] = {"code": 200, "data": self.mode}
            for name, value in self.master.items():
                path = f"/processdatamaster/{name}"
                if path in paths:
                    result[path] = {"code": 200, "data": value}
            return result

        async def request(self, path, data):
            return {"value": f"{condition_value:02X}"}

    client = Client()
    c = module.IfmCoordinator(None, entry, client, {"serial": "PRIVATE MASTER", "model": "AL1350", "ports": 2}, library)
    return c, client


def test_one_bad_port_does_not_remove_other_measurement(coordinator_module):
    c, _ = instance(coordinator_module)
    result = asyncio.run(c._async_update_data())
    assert result["1"]["values"]["pd_1"] == 0.22
    assert result["2"]["error"]


def test_metadata_refreshes_on_first_update_even_with_a_low_monotonic_clock(coordinator_module, monkeypatch):
    # time.monotonic()'s absolute value is arbitrary (e.g. time since boot on Linux) and can
    # already be under 60 right after the host starts - metadata_at must not treat that as "recent".
    monkeypatch.setattr(coordinator_module.time, "monotonic", lambda: 5.0)
    c, _ = instance(coordinator_module)
    result = asyncio.run(c._async_update_data())
    assert result["1"]["values"]["pd_1"] == 0.22
    assert result["1"]["identity"]["vendorid"] == 310
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


def test_master_diagnostics_are_converted_from_mv_and_ma(coordinator_module):
    c, client = instance(coordinator_module)
    client.master = {"temperature": 35, "voltage": 23878, "current": 123, "supervisionstatus": 0}
    asyncio.run(c._async_update_data())
    assert c.master_diagnostics["temperature"] == 35
    assert c.master_diagnostics["voltage"] == pytest.approx(23.878)
    assert c.master_diagnostics["current"] == pytest.approx(0.123)
    assert c.master_diagnostics["power"] == pytest.approx(23.878 * 0.123)
    assert c.master_diagnostics["status"] == 0


def test_port_mode_is_read_once_and_persists_between_metadata_refreshes(coordinator_module):
    c, client = instance(coordinator_module)
    client.mode = 2
    result = asyncio.run(c._async_update_data())
    assert result["1"]["mode"] == 2
    client.mode = 3  # a later poll cycle skips the metadata read; the stale value must survive
    c.metadata_at = time.monotonic()
    result = asyncio.run(c._async_update_data())
    assert result["1"]["mode"] == 2


def test_pdout_is_only_read_and_exposed_for_ports_switched_to_do(coordinator_module):
    c, client = instance(coordinator_module)
    c.entry.options["ports"]["1"]["mode"] = 2
    client.pdout = "01"
    result = asyncio.run(c._async_update_data())
    assert result["1"]["pdout"] == "01"
    assert result["2"]["pdout"] is None  # port 2 was never switched to DO


def test_pdout_is_read_when_device_reports_do_even_if_assignment_is_stale(coordinator_module):
    # The saved assignment (options) can lag behind the device's own reported mode - e.g. right
    # after a mode switch, or if the port was put into DO some other way. The panel badge colors
    # a port based on the device's own reported mode (item["mode"]), so pdout must be fetched
    # whenever the device says DO, not only when the saved assignment already agrees - otherwise
    # the badge shows "DO" but never colors it, because pdout stays None.
    c, client = instance(coordinator_module)
    client.mode = 2
    client.pdout = "01"
    result = asyncio.run(c._async_update_data())
    assert result["1"]["mode"] == 2
    assert result["1"]["pdout"] == "01"


def test_pin4_di_value_is_only_exposed_for_ports_switched_to_di(coordinator_module):
    c, client = instance(coordinator_module)
    c.entry.options["ports"]["1"]["mode"] = 1
    client.pdin1 = "01"
    result = asyncio.run(c._async_update_data())
    assert result["1"]["pin4"] is True
    assert result["2"]["pin4"] is None  # port 2 was never switched to DI


def test_pin4_di_value_reads_rest_state_as_off(coordinator_module):
    c, client = instance(coordinator_module)
    c.entry.options["ports"]["1"]["mode"] = 1
    client.pdin1 = "00"
    result = asyncio.run(c._async_update_data())
    assert result["1"]["pin4"] is False


def test_pin4_di_value_is_read_when_device_reports_di_even_if_assignment_is_stale(coordinator_module):
    c, client = instance(coordinator_module)
    client.mode = 1
    client.pdin1 = "01"
    result = asyncio.run(c._async_update_data())
    assert result["1"]["mode"] == 1
    assert result["1"]["pin4"] is True


def test_master_diagnostics_missing_paths_stay_none(coordinator_module):
    c, _ = instance(coordinator_module)  # fake client does not serve /processdatamaster/*
    asyncio.run(c._async_update_data())
    assert c.master_diagnostics == {"temperature": None, "voltage": None, "current": None, "power": None, "status": None}


def test_snapshot_exposes_master_diagnostics(coordinator_module):
    c, client = instance(coordinator_module)
    client.master = {"temperature": 22, "voltage": 24000, "current": 100, "supervisionstatus": 4}
    asyncio.run(c._async_update_data())
    assert c.snapshot()["diagnostics"] == c.master_diagnostics
    assert c.snapshot()["diagnostics"]["status"] == 4
