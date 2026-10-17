"""ifm AL1350/AL1352 IO-Link masters with local IoT interface."""

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IfmClient, IfmError
from .const import DOMAIN, PLATFORMS, STATIC_URL
from .coordinator import IfmCoordinator
from .mode_entities import sync_mode_entities
from .parameters import ParameterBackups
from .profiles import ProfileLibrary
from .replacement import registry_serial
from .version import installed_version


async def async_setup(hass, config):
    library = ProfileLibrary(hass)
    await library.load()
    backups = ParameterBackups(hass)
    await backups.load()
    hass.data[DOMAIN] = {"library": library, "coordinators": {}, "parameter_backups": backups}
    from .websocket import register_commands

    register_commands(hass)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=DOMAIN,
        webcomponent_name="ifm-iolink-panel",
        sidebar_title="ifm IO-Link",
        sidebar_icon="mdi:lan-connect",
        module_url=f"{STATIC_URL}/panel.js?v={installed_version()}&ui=wiring-help-20261017",
        require_admin=True,
    )
    return True


async def async_setup_entry(hass, entry):
    client = IfmClient(
        async_get_clientsession(hass),
        entry.data["url"],
        entry.data.get("username", ""),
        entry.data.get("password", ""),
        entry.data.get("verify_ssl", True),
    )
    stored_identity = {key: entry.data[key] for key in ("serial", "model", "ports") if key in entry.data}
    paused = entry.data.get("replacement_paused", False)
    mismatch = None
    try:
        identity = stored_identity if paused else await client.identify()
        if (identity["serial"] != entry.unique_id
                or identity["model"] != stored_identity.get("model", identity["model"])):
            if not all(key in stored_identity for key in ("serial", "model", "ports")):
                raise ConfigEntryNotReady("Unter dieser Adresse antwortet ein anderer Master")
            mismatch, identity = identity, stored_identity
    except IfmError as err:
        if not all(key in stored_identity for key in ("serial", "model", "ports")):
            raise ConfigEntryNotReady(str(err)) from err
        identity = stored_identity
        paused = True  # Keep management available while the old master is offline.
    coordinator = IfmCoordinator(hass, entry, client, identity, hass.data[DOMAIN]["library"])
    coordinator.replacement_detected = mismatch
    if paused or mismatch:
        coordinator.async_set_updated_data({})
        coordinator.last_update_success = False
    else:
        try:
            await coordinator.async_config_entry_first_refresh()
        except ConfigEntryNotReady:
            if not all(key in stored_identity for key in ("serial", "model", "ports")):
                raise
            # Identification may succeed just before the old master disconnects.
            # Existing installations must still expose the replacement manager.
            coordinator.async_set_updated_data({})
            coordinator.last_update_success = False
    entry.runtime_data = coordinator
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator
    master_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, registry_serial(entry))},
        manufacturer="ifm electronic",
        model=identity["model"],
        name=entry.title,
        sw_version=identity.get("firmware"),
        serial_number=identity["serial"],
        configuration_url=client.url,
    )
    # Use the device returned for this config entry, including after HA registry
    # migrations. Platforms must never resolve a master globally by serial alone.
    coordinator.master_device_id = master_device.id
    expected = set()
    requirements = {}
    for port in range(1, identity["ports"] + 1):
        prefix = f"{registry_serial(entry)}_port_{port}_"
        requirements[prefix + "connection"] = (port, 3)
        requirements[prefix + "pin4_do"] = (port, 2)
        requirements[prefix + "pin4_di"] = (port, 1)
        expected.add(prefix + "connection")
        expected.add(prefix + "pin4_do")
        expected.add(prefix + "pin4_di")
        expected.add(prefix + "pin2_di")
        profile_id = entry.options.get("ports", {}).get(str(port), {}).get("profile", "unknown")
        profile = coordinator.library.all.get(profile_id, {})
        expected.update(prefix + profile_id + "_" + field["key"] for field in profile.get("fields", []))
        requirements.update({prefix + profile_id + "_" + field["key"]: (port, 3) for field in profile.get("fields", [])})
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform == DOMAIN and entity.unique_id not in expected:
            registry.async_remove(entity.entity_id)
    def sync_entities():
        sync_mode_entities(
            registry, er.async_entries_for_config_entry(registry, entry.entry_id),
            coordinator, requirements,
        )

    # Reconcile existing entries before loading platforms, then newly registered
    # entities. This listener stays active even when every entity is disabled.
    sync_entities()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(sync_entities))
    entry.async_on_unload(entry.add_update_listener(_update_options))
    return True


async def _update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)
    return unloaded


async def async_remove_entry(hass, entry):
    await hass.data[DOMAIN]["parameter_backups"].remove(entry.entry_id)
