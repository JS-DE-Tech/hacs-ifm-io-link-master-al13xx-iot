"""Exercise real setup/platform code with versioned HA registry boundaries.

These are lifecycle regression tests, not a running Home Assistant instance.
The old/new DeviceInfo contracts follow HA 2025.7.0 and 2026.9.4.
"""

import asyncio
import importlib
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TypedDict

import pytest

from custom_components.ifm_iolink.const import DOMAIN


@pytest.fixture(params=[False, True], ids=["HA-2025.7", "HA-2026.9"])
def lifecycle(request, monkeypatch):
    modern = request.param

    def module(name, **attrs):
        mod = ModuleType(name)
        mod.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod

    for name in ("homeassistant", "homeassistant.components", "homeassistant.helpers"):
        module(name, __path__=[])
    info = TypedDict("DeviceInfo", {"via_device_id": str} if modern else {"via_device": tuple[str, str]})
    devices, entities, calls = {}, {}, []

    class Registry:
        def async_get_or_create(self, *, config_entry_id, identifiers, **kwargs):
            if modern:
                assert "via_device" not in kwargs, "Deprecated API used on current HA"
            else:
                assert "via_device_id" not in kwargs, "Unsupported keyword on HA 2025.7"
            key = (config_entry_id, frozenset(identifiers))
            parent = kwargs.get("via_device_id")
            if "via_device" in kwargs:
                parent = devices[(config_entry_id, frozenset({kwargs["via_device"]}))].id
            if parent is not None:
                assert isinstance(parent, str)
                assert any(d.id == parent and d.config_entry_id == config_entry_id for d in devices.values())
            if key not in devices:
                devices[key] = SimpleNamespace(
                    id=f"registry-{len(devices)}",
                    config_entry_id=config_entry_id,
                    name_by_user=None,
                    area_id=None,
                    disabled_by=None,
                )
            device = devices[key]
            device.via_device_id = parent
            calls.append((config_entry_id, identifiers, kwargs))
            return device

    registry = Registry()
    module("homeassistant.helpers.device_registry", DeviceInfo=info, async_get=lambda hass: registry)
    module(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: None,
        async_entries_for_config_entry=lambda reg, entry_id: [],
    )
    module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    module("homeassistant.components.panel_custom")
    module("homeassistant.components.http", StaticPathConfig=object)
    module("homeassistant.exceptions", ConfigEntryNotReady=RuntimeError, HomeAssistantError=RuntimeError)
    module("homeassistant.components.switch", SwitchEntity=type("SwitchEntity", (), {}))
    module("homeassistant.components.sensor", SensorEntity=type("SensorEntity", (), {}))
    module("homeassistant.components.binary_sensor", BinarySensorEntity=type("BinarySensorEntity", (), {}))
    module("homeassistant.const", EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"))

    class CoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    module("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity)

    class Coordinator:
        last_update_success = False

        def async_add_listener(self, callback):
            return lambda: None

        def __init__(self, hass, entry, client, identity, library):
            self.entry, self.identity, self.library = entry, identity, library

        async def async_config_entry_first_refresh(self):
            pass

    module("custom_components.ifm_iolink.coordinator", IfmCoordinator=Coordinator)
    module("custom_components.ifm_iolink.profiles", ProfileLibrary=object)
    for name in ("entity", "sensor", "binary_sensor", "switch"):
        monkeypatch.delitem(sys.modules, f"custom_components.ifm_iolink.{name}", raising=False)
    platforms = [
        importlib.import_module(f"custom_components.ifm_iolink.{name}")
        for name in ("sensor", "binary_sensor", "switch")
    ]
    path = Path(__file__).parents[1] / "custom_components/ifm_iolink/__init__.py"
    spec = importlib.util.spec_from_file_location(
        "custom_components.ifm_iolink._setup_test", path, submodule_search_locations=None
    )
    setup = importlib.util.module_from_spec(spec)
    setup.__package__ = "custom_components.ifm_iolink"
    spec.loader.exec_module(setup)

    class Client:
        def __init__(self, session, url, *args):
            self.url = url

        async def identify(self):
            return {"serial": "MASTER", "model": "AL1350", "ports": 4}

    setup.IfmClient = Client
    library = SimpleNamespace(
        all={
            "pressure": {
                "fields": [
                    {"key": "pressure", "type": "int", "name": "Pressure"},
                    {"key": "out1", "type": "bool", "name": "OUT1"},
                ]
            }
        }
    )
    backups = {"saved": "unchanged"}
    hass = SimpleNamespace(data={DOMAIN: {"library": library, "coordinators": {}, "parameter_backups": backups}})

    async def forward(entry, names):
        assert entry.runtime_data.master_device_id in {d.id for d in devices.values()}

        def add(items):
            for item in items:
                device = registry.async_get_or_create(config_entry_id=entry.entry_id, **item._attr_device_info)
                key = (entry.entry_id, item._attr_unique_id)
                entities.setdefault(key, {"entity_id": f"sensor.saved_{len(entities)}", "device_id": device.id})
                assert entities[key]["device_id"] == device.id

        for platform in platforms:
            await platform.async_setup_entry(hass, entry, add)

    async def unload(entry, platforms):
        return True

    hass.config_entries = SimpleNamespace(async_forward_entry_setups=forward, async_unload_platforms=unload)

    def entry(entry_id="entry-a"):
        return SimpleNamespace(
            entry_id=entry_id,
            title="My master",
            unique_id="MASTER",
            data={"url": "http://master"},
            options={"ports": {"1": {"profile": "pressure", "name": "Filter", "location": "Pool"}}},
            async_on_unload=lambda callback: None,
            add_update_listener=lambda callback: None,
        )

    yield SimpleNamespace(
        setup=setup,
        hass=hass,
        entry=entry,
        devices=devices,
        entities=entities,
        registry=registry,
        calls=calls,
        backups=backups,
    )
    for name in ("entity", "sensor", "binary_sensor", "switch"):
        sys.modules.pop(f"custom_components.ifm_iolink.{name}", None)


@pytest.mark.parametrize("existing", [False, True], ids=["first-install", "existing-install"])
def test_device_identity_survives_setup_and_reload(lifecycle, existing):
    ctx = lifecycle
    entry = ctx.entry()
    options = deepcopy(entry.options)
    if existing:
        master = ctx.registry.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "MASTER")})
        master.id = "existing-master-id"
        port = ctx.registry.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "MASTER_port_1")})
        port.id = "existing-port-id"
        port.via_device_id = master.id
        port.name_by_user, port.area_id, port.disabled_by = "User name", "user-area", "user"
        ctx.entities[(entry.entry_id, "MASTER_port_1_pressure_pressure")] = {
            "entity_id": "sensor.my_existing_pressure",
            "device_id": port.id,
        }
    asyncio.run(ctx.setup.async_setup_entry(ctx.hass, entry))
    assert len(ctx.devices) == 5
    assert len(ctx.entities) == 18
    assert (entry.entry_id, "MASTER_port_1_pin2_di") in ctx.entities
    assert (entry.entry_id, "MASTER_port_1_pin4_di") in ctx.entities
    assert (entry.entry_id, "MASTER_port_1_pin4_do") in ctx.entities
    assert (entry.entry_id, "MASTER_port_1_pressure_out1") in ctx.entities
    assert (entry.entry_id, "MASTER_port_4_connection") in ctx.entities
    before_devices, before_entities = deepcopy(ctx.devices), deepcopy(ctx.entities)
    asyncio.run(ctx.setup.async_unload_entry(ctx.hass, entry))
    assert entry.entry_id not in ctx.hass.data[DOMAIN]["coordinators"]
    asyncio.run(ctx.setup.async_setup_entry(ctx.hass, entry))
    assert ctx.devices == before_devices
    assert ctx.entities == before_entities
    assert entry.options == options
    assert ctx.backups == {"saved": "unchanged"}
    if existing:
        assert entry.runtime_data.master_device_id == "existing-master-id"
        assert port.name_by_user == "User name"
        assert port.area_id == "user-area"
        assert port.disabled_by == "user"
        assert (
            ctx.entities[(entry.entry_id, "MASTER_port_1_pressure_pressure")]["entity_id"]
            == "sensor.my_existing_pressure"
        )


def test_master_id_is_scoped_to_config_entry(lifecycle):
    """Even matching identifiers must use the entry-specific returned device."""
    ctx = lifecycle
    first, second = ctx.entry("entry-a"), ctx.entry("entry-b")
    asyncio.run(ctx.setup.async_setup_entry(ctx.hass, first))
    asyncio.run(ctx.setup.async_setup_entry(ctx.hass, second))
    assert first.runtime_data.master_device_id != second.runtime_data.master_device_id
    for (entry_id, identifiers), device in ctx.devices.items():
        if identifiers == frozenset({(DOMAIN, "MASTER")}):
            continue
        entry = first if entry_id == first.entry_id else second
        assert device.via_device_id == entry.runtime_data.master_device_id


def test_wrong_master_is_rejected_before_registry_changes(lifecycle):
    ctx = lifecycle
    entry = ctx.entry()
    entry.unique_id = "OTHER-MASTER"
    with pytest.raises(RuntimeError, match="anderer Master"):
        asyncio.run(ctx.setup.async_setup_entry(ctx.hass, entry))
    assert not ctx.devices
    assert not ctx.entities


@pytest.mark.parametrize(
    "mode,value,expected", [(1, True, True), (1, False, False), (1, None, None), (2, True, None), (3, True, None)]
)
def test_di_entity_tracks_readback_and_mode(lifecycle, monkeypatch, mode, value, expected):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    monkeypatch.setattr(CoordinatorEntity, "available", property(lambda self: True), raising=False)
    entry = lifecycle.entry()
    asyncio.run(lifecycle.setup.async_setup_entry(lifecycle.hass, entry))
    from custom_components.ifm_iolink.binary_sensor import IfmDigitalInput

    c = entry.runtime_data
    c.data = {"4": {"mode": mode, "pin4": value}}
    entity = IfmDigitalInput(c, 4)
    assert entity.is_on is expected
    assert entity.available is (mode == 1)
    assert entity._attr_unique_id == "MASTER_port_4_pin4_di"


@pytest.mark.parametrize("mode", [0, 1, 2, 3, None])
@pytest.mark.parametrize("value", [True, False, None])
def test_di2_is_independent_of_pin4_mode(lifecycle, monkeypatch, mode, value):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    monkeypatch.setattr(CoordinatorEntity, "available", property(lambda self: True), raising=False)
    entry = lifecycle.entry()
    asyncio.run(lifecycle.setup.async_setup_entry(lifecycle.hass, entry))
    from custom_components.ifm_iolink.binary_sensor import IfmDigitalInput

    c = entry.runtime_data
    c.data = {"4": {"mode": mode, "pin2": value, "pin4": not value}}
    entity = IfmDigitalInput(c, 4, pin=2)
    assert entity.available
    assert entity.is_on is value
    assert entity._attr_unique_id == "MASTER_port_4_pin2_di"
    monkeypatch.setattr(CoordinatorEntity, "available", property(lambda self: False))
    assert not entity.available
    assert entity.is_on is None
