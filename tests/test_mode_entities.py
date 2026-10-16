"""Registry lifecycle checks without a running Home Assistant instance."""
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace as NS

import pytest

from custom_components.ifm_iolink.const import DOMAIN

sync_mode_entities = None
MARKER = "disabled_for_port_mode"

@pytest.fixture(autouse=True)
def boundary(monkeypatch):
    helpers = ModuleType("homeassistant.helpers")
    helpers.entity_registry = NS(RegistryEntryDisabler=NS(INTEGRATION="integration"))
    monkeypatch.setitem(sys.modules, "homeassistant", ModuleType("homeassistant"))
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    spec = importlib.util.spec_from_file_location(
        "custom_components.ifm_iolink.mode_entities_test",
        Path(__file__).parents[1] / "custom_components/ifm_iolink/mode_entities.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setitem(globals(), "sync_mode_entities", mod.sync_mode_entities)



class Registry:
    def __init__(self):
        self.entries = {key: NS(entity_id=key, unique_id=key, platform=DOMAIN,
                               disabled_by=None, options={"sensor": {"precision": 2}},
                               name="My name", device_id="original-device")
                        for key in ("do", "di", "di2", "value", "connection")}
        self.writes = []

    def async_update_entity(self, entity_id, **changes):
        self.writes.append((entity_id, changes))
        for key, value in changes.items():
            setattr(self.entries[entity_id], key, value)

    def async_update_entity_options(self, entity_id, domain, options):
        self.writes.append((entity_id, domain, options))
        if options is None:
            self.entries[entity_id].options.pop(domain, None)
        else:
            self.entries[entity_id].options[domain] = options


def sync(reg, mode, success=True):
    sync_mode_entities(reg, list(reg.entries.values()),
                       NS(last_update_success=success, data={"4": {"mode": mode}}),
                       {"do": (4, 2), "di": (4, 1), "value": (4, 3), "connection": (4, 3)})


@pytest.mark.parametrize("mode,enabled", [(0, {"di2"}), (1, {"di", "di2"}),
                                          (2, {"do", "di2"}), (3, {"value", "connection", "di2"})])
def test_new_existing_reload_and_mode_cycle(mode, enabled):
    reg = Registry()
    sync(reg, mode)
    assert {key for key, e in reg.entries.items() if e.disabled_by is None} == enabled
    writes = len(reg.writes)
    sync(reg, mode)
    assert len(reg.writes) == writes  # No polling/reload loop.
    reg.entries = deepcopy(reg.entries)  # Persisted registry, new entity objects.
    for next_mode in (2, 1, 0, 3, mode):
        sync(reg, next_mode)
    assert {key for key, e in reg.entries.items() if e.disabled_by is None} == enabled
    for key, e in reg.entries.items():
        assert e.entity_id == e.unique_id == key
        assert e.name == "My name" and e.device_id == "original-device"
        assert e.options["sensor"] == {"precision": 2}


@pytest.mark.parametrize("reason", ["user", "device", "config_entry", "hass", "integration"])
def test_never_enable_unowned_disables(reason):
    reg = Registry()
    reg.entries["do"].disabled_by = reason
    sync(reg, 1)
    sync(reg, 2)
    assert reg.entries["do"].disabled_by == reason


def test_manual_disable_overrides_owned_disable():
    reg = Registry()
    sync(reg, 1)
    reg.entries["do"].disabled_by = "user"
    sync(reg, 2)
    assert reg.entries["do"].disabled_by == "user"
    assert not reg.entries["do"].options.get(DOMAIN, {}).get(MARKER)


@pytest.mark.parametrize("mode,success", [(None, True), (8, True), (True, True), ("2", True), (2, False)])
def test_unknown_or_failed_poll_changes_nothing(mode, success):
    reg = Registry()
    sync(reg, 0)
    before = deepcopy(reg.writes)
    sync(reg, mode, success)
    assert reg.writes == before


def test_other_platform_and_unmanaged_entity_are_untouched():
    reg = Registry()
    reg.entries["do"].platform = "other"
    sync(reg, 0)
    assert reg.entries["do"].disabled_by is None
    assert reg.entries["di2"].disabled_by is None
