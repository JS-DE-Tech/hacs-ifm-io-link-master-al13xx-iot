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
from .parameters import ParameterBackups
from .profiles import ProfileLibrary
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
        module_url=f"{STATIC_URL}/panel.js?v={installed_version()}",
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
    try:
        identity = await client.identify()
    except IfmError as err:
        raise ConfigEntryNotReady(str(err)) from err
    if identity["serial"] != entry.unique_id:
        raise ConfigEntryNotReady("Unter dieser Adresse antwortet ein anderer Master (Seriennummer geändert)")
    coordinator = IfmCoordinator(hass, entry, client, identity, hass.data[DOMAIN]["library"])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, identity["serial"])},
        manufacturer="ifm electronic",
        model=identity["model"],
        name=entry.title,
        sw_version=identity.get("firmware"),
        serial_number=identity["serial"],
        configuration_url=client.url,
    )
    expected = {f"{identity['serial']}_master_{key}" for key in ("voltage", "power", "temperature", "status")}
    for port in range(1, identity["ports"] + 1):
        prefix = f"{identity['serial']}_port_{port}_"
        expected.add(prefix + "connection")
        expected.add(prefix + "pin2")
        assignment = entry.options.get("ports", {}).get(str(port), {})
        if assignment.get("mode") == 2:
            expected.add(prefix + "pin4_do")
        if assignment.get("mode") == 1:
            expected.add(prefix + "pin4_di")
        profile_id = assignment.get("profile", "unknown")
        profile = coordinator.library.all.get(profile_id, {})
        expected.update(prefix + profile_id + "_" + field["key"] for field in profile.get("fields", []))
        parameter_indices = {p["index"] for p in profile.get("parameters", [])}
        expected.update(
            f"{prefix}{profile_id}_param_{index}" for index in assignment.get("entities", []) if index in parameter_indices
        )
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform == DOMAIN and entity.unique_id not in expected:
            registry.async_remove(entity.entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
