"""Config-flow identity guards at an isolated HA boundary."""

import asyncio
import importlib
import sys
from types import ModuleType
from types import SimpleNamespace as NS

import pytest


@pytest.fixture
def flow_module(monkeypatch):
    def module(name, **attrs):
        result = ModuleType(name)
        result.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, result)
        return result

    for name in ("homeassistant", "homeassistant.components", "homeassistant.helpers"):
        module(name, __path__=[])

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass
        def async_abort(self, reason):
            return {"type": "abort", "reason": reason}
        async def async_set_unique_id(self, serial):
            self.selected_serial = serial
        def _abort_if_unique_id_configured(self):
            assert not any(entry.unique_id == self.selected_serial for entry in self.entries)
        def async_create_entry(self, **kwargs):
            return {"type": "create", **kwargs}
        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    module("homeassistant.config_entries", ConfigFlow=ConfigFlow, OptionsFlow=object)
    module("homeassistant.components.network")
    module("homeassistant.core", callback=lambda callback: callback)
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.helpers.selector", SelectSelector=object, SelectSelectorConfig=object)
    name = "custom_components.ifm_iolink.config_flow"
    monkeypatch.delitem(sys.modules, name, raising=False)
    mod = importlib.import_module(name)
    state = {"serial": "ORIGINAL"}

    class Client:
        def __init__(self, session, url, *args):
            self.url = url
        async def identify(self):
            return {"serial": state["serial"], "model": "AL1350", "ports": 4}

    monkeypatch.setattr(mod, "IfmClient", Client)
    flow = mod.IfmConfigFlow()
    flow.context = {}
    flow.entries = [NS(unique_id="REPLACEMENT", data={"registry_serial": "ORIGINAL"})]
    flow.hass = NS(config_entries=NS(async_entries=lambda domain: flow.entries))
    yield flow, state
    sys.modules.pop(name, None)


@pytest.mark.parametrize("source", ["manual", "dhcp"])
def test_original_hardware_cannot_reuse_preserved_namespace(flow_module, source):
    flow, state = flow_module
    async def run():
        if source == "manual":
            return await flow.async_step_manual({"url": "http://original"})
        return await flow.async_step_dhcp(NS(ip="10.0.0.10"))
    assert asyncio.run(run()) == {"type": "abort", "reason": "already_configured"}
    assert not hasattr(flow, "selected_serial")


def test_independent_new_master_can_still_be_added(flow_module):
    flow, state = flow_module
    state["serial"] = "INDEPENDENT"
    result = asyncio.run(flow.async_step_manual({"url": "http://new"}))
    assert result["type"] == "create"
    assert result["data"]["serial"] == "INDEPENDENT"
    assert flow.selected_serial == "INDEPENDENT"
