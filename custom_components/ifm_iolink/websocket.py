"""Authenticated panel commands; all configuration actions require admin."""

import asyncio
import base64
import binascii
import secrets
import time
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import voluptuous as vol
from homeassistant.components import websocket_api

from .api import IfmError
from .const import DOMAIN
from .decoder import decode, validate_profile
from .digital import set_output
from .iodd import import_iodd
from .parameters import collect_parameters, read_parameter_value
from .port_mode import change_mode
from .restore import execute_restore, prepare_restore
from .version import installed_version


def register_commands(hass):
    for command in (
        snapshot,
        set_digital_output,
        set_port_mode,
        assign,
        save_profile,
        delete_profile,
        debug,
        test_profile,
        import_profile,
        read_parameter,
        read_parameters,
        get_parameter_backup,
        rename_master,
        delete_master,
        preview_restore,
        restore_parameters,
        get_restore_report,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "ifm_iolink/set_digital_output",
    vol.Required("entry_id"): str, vol.Required("port"): int, vol.Required("on"): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
async def set_digital_output(hass, connection, message):
    try:
        coordinator = coordinator_for(hass, message)
        await set_output(hass, coordinator, message["port"], message["on"])
        await coordinator.async_request_refresh()
        connection.send_result(message["id"], {"verified": True})
    except (ValueError, IfmError) as err:
        connection.send_error(message["id"], "output_failed", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): "ifm_iolink/set_port_mode",
    vol.Required("entry_id"): str, vol.Required("port"): int,
    vol.Required("expected_mode"): int, vol.Required("target_mode"): int,
    vol.Required("confirm"): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
async def set_port_mode(hass, connection, message):
    try:
        if message["confirm"] is not True:
            raise ValueError("Modusänderung muss bestätigt werden")
        coordinator = coordinator_for(hass, message)
        try:
            await change_mode(hass, coordinator, message["port"], message["expected_mode"], message["target_mode"])
        finally:
            await coordinator.async_request_refresh()
        connection.send_result(message["id"], {"verified": True})
    except (ValueError, IfmError) as err:
        connection.send_error(message["id"], "mode_failed", str(err))


def coordinator_for(hass, message):
    coordinator = hass.data[DOMAIN]["coordinators"].get(message["entry_id"])
    if coordinator is None:
        raise ValueError("Master wird geladen oder ist nicht erreichbar")
    if "port" in message and not 1 <= message["port"] <= coordinator.identity["ports"]:
        raise ValueError("Port existiert an diesem Master nicht")
    return coordinator


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/snapshot", vol.Optional("include_profiles", default=True): bool}
)
@websocket_api.require_admin
@websocket_api.async_response
async def snapshot(hass, connection, message):
    data = hass.data[DOMAIN]
    result = {
        "masters": [item.snapshot() for item in data["coordinators"].values()],
        "profile_revision": data["library"].revision,
        "version": installed_version(),
    }
    if message["include_profiles"]:
        result["profiles"] = list(data["library"].all.values())
    connection.send_result(message["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ifm_iolink/assign",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
        vol.Required("profile"): str,
        vol.Optional("name", default=""): str,
        vol.Optional("location", default=""): str,
        vol.Optional("purpose", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def assign(hass, connection, message):
    try:
        coordinator = coordinator_for(hass, message)
        if (message["entry_id"], message["port"]) in hass.data[DOMAIN]["parameter_backups"].busy:
            raise ValueError("Parameteraktion läuft; Portzuweisung danach ändern")
        if message["profile"] != "unknown" and message["profile"] not in coordinator.library.all:
            raise ValueError("Profil nicht gefunden")
        for name in ("name", "location", "purpose"):
            if len(message[name]) > 500:
                raise ValueError("Metadaten dürfen höchstens 500 Zeichen enthalten")
        ports = {
            **coordinator.entry.options.get("ports", {}),
            str(message["port"]): {key: message[key].strip() for key in ("profile", "name", "location", "purpose")},
        }
        hass.config_entries.async_update_entry(coordinator.entry, options={**coordinator.entry.options, "ports": ports})
        connection.send_result(message["id"], {"saved": True})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command({vol.Required("type"): "ifm_iolink/save_profile", vol.Required("profile"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def save_profile(hass, connection, message):
    try:
        profile = message["profile"]
        await hass.data[DOMAIN]["library"].save(profile)
        # Reload users of an edited profile so entity metadata and keys match it.
        for entry in hass.config_entries.async_entries(DOMAIN):
            if any(port.get("profile") == profile["id"] for port in entry.options.get("ports", {}).values()):
                await hass.config_entries.async_reload(entry.entry_id)
        connection.send_result(message["id"], {"saved": True})
    except (ValueError, TypeError) as err:
        connection.send_error(message["id"], "invalid_profile", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/import_iodd", vol.Required("content"): str, vol.Required("filename"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def import_profile(hass, connection, message):
    try:
        if len(message["content"]) > 11_000_000:
            raise ValueError("IODD-Datei zu groß")
        raw = base64.b64decode(message["content"], validate=True)
        candidates = await hass.async_add_executor_job(import_iodd, raw, message["filename"])
        connection.send_result(message["id"], candidates)
    except (ValueError, TypeError, KeyError, ParseError, BadZipFile, binascii.Error) as err:
        connection.send_error(message["id"], "invalid_iodd", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ifm_iolink/read_parameter",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
        vol.Required("index"): int,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def read_parameter(hass, connection, message):
    try:
        coordinator = coordinator_for(hass, message)
        port = coordinator.data[str(message["port"])]
        if not port["connected"]:
            raise ValueError("Port nicht verbunden")
        profile = coordinator.library.all.get(port["profile"], {})
        parameter = next((item for item in profile.get("parameters", []) if item["index"] == message["index"]), None)
        if not parameter:
            raise ValueError("Parameter nicht im zugewiesenen Profil")
        result = await read_parameter_value(coordinator, message["port"], parameter)
        connection.send_result(message["id"], result)
    except (ValueError, IfmError) as err:
        connection.send_error(message["id"], "read_failed", str(err))


@websocket_api.websocket_command({vol.Required("type"): "ifm_iolink/delete_profile", vol.Required("profile_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def delete_profile(hass, connection, message):
    try:
        if any(
            port.get("profile") == message["profile_id"]
            for entry in hass.config_entries.async_entries(DOMAIN)
            for port in entry.options.get("ports", {}).values()
        ):
            raise ValueError("Profil ist noch einem Port zugewiesen")
        await hass.data[DOMAIN]["library"].delete(message["profile_id"])
        connection.send_result(message["id"], {"deleted": True})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/debug", vol.Required("entry_id"): str, vol.Required("port"): int}
)
@websocket_api.require_admin
@websocket_api.async_response
async def debug(hass, connection, message):
    try:
        coordinator = coordinator_for(hass, message)
        result = coordinator.diagnostic(message["port"])
        result["profile_template"] = {
            "id": "custom_mein_sensor",
            "name": "Mein Sensor",
            "manufacturer": "",
            "model": "",
            "description": "",
            "purpose": "",
            "image": "",
            "notes": "IODD ergänzen und Skalierung prüfen",
            "length": max(1, len((coordinator.data or {}).get(str(message["port"]), {}).get("raw") or "") // 2),
            "fields": [{"key": "raw_value", "name": "Rohwert (unskaliert)", "type": "uint", "offset": 0, "length": 1}],
        }
        connection.send_result(message["id"], result)
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/test_profile", vol.Required("profile"): dict, vol.Required("raw"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def test_profile(hass, connection, message):
    try:
        profile = validate_profile(message["profile"])
        connection.send_result(message["id"], decode(profile, message["raw"]))
    except (ValueError, TypeError) as err:
        connection.send_error(message["id"], "invalid_profile", str(err))


def entry_for(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError("IO-Link-Master nicht gefunden")
    return entry


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/rename_master", vol.Required("entry_id"): str, vol.Required("name"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def rename_master(hass, connection, message):
    from homeassistant.helpers import device_registry as dr

    try:
        entry = entry_for(hass, message["entry_id"])
        name = message["name"].strip()
        if not name or len(name) > 120:
            raise ValueError("Mastername muss 1 bis 120 Zeichen enthalten")
        registry = dr.async_get(hass)
        device = registry.async_get_device(identifiers={(DOMAIN, entry.unique_id)})
        if device:
            registry.async_update_device(device.id, name=name, name_by_user=name)
        hass.config_entries.async_update_entry(entry, title=name)
        connection.send_result(message["id"], {"saved": True})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/delete_master", vol.Required("entry_id"): str, vol.Required("confirm_name"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def delete_master(hass, connection, message):
    try:
        entry = entry_for(hass, message["entry_id"])
        if message["confirm_name"] != entry.title:
            raise ValueError("Zur Bestätigung den aktuellen Masternamen eingeben")
        result = await hass.config_entries.async_remove(entry.entry_id)
        # If unloading failed, the removed entry must still disappear from the panel.
        hass.data[DOMAIN]["coordinators"].pop(entry.entry_id, None)
        connection.send_result(message["id"], {"deleted": True, **result})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ifm_iolink/read_parameters",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
        vol.Optional("save", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def read_parameters(hass, connection, message):
    backups = hass.data[DOMAIN]["parameter_backups"]
    key = (message["entry_id"], message["port"])
    if key in backups.busy:
        connection.send_error(message["id"], "busy", "Parameterabfrage an diesem Port läuft bereits")
        return
    backups.busy.add(key)
    try:
        coordinator = coordinator_for(hass, message)
        result = await collect_parameters(coordinator, message["port"])
        if hass.data[DOMAIN]["coordinators"].get(message["entry_id"]) is not coordinator:
            raise ValueError("Master wurde neu geladen oder entfernt; bitte erneut lesen")
        result["saved"] = False
        if message["save"] and result["complete"]:
            await backups.save(message["entry_id"], message["port"], result)
            result["saved"] = True
        connection.send_result(message["id"], result)
    except (ValueError, IfmError) as err:
        connection.send_error(message["id"], "read_failed", str(err))
    finally:
        backups.busy.discard(key)


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/get_parameter_backup", vol.Required("entry_id"): str, vol.Required("port"): int}
)
@websocket_api.require_admin
@websocket_api.async_response
async def get_parameter_backup(hass, connection, message):
    try:
        entry_for(hass, message["entry_id"])
        if not 1 <= message["port"] <= 8:
            raise ValueError("Ungültiger Port")
        backup = hass.data[DOMAIN]["parameter_backups"].get(message["entry_id"], message["port"])
        connection.send_result(message["id"], {"backup": backup})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ifm_iolink/preview_restore",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
        vol.Optional("backup"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def preview_restore(hass, connection, message):
    backups = hass.data[DOMAIN]["parameter_backups"]
    key = (message["entry_id"], message["port"])
    if key in backups.busy:
        connection.send_error(message["id"], "busy", "Parameteraktion an diesem Port läuft bereits")
        return
    backups.busy.add(key)
    try:
        coordinator = coordinator_for(hass, message)
        backup = message["backup"] if "backup" in message else backups.get(*key)
        async with asyncio.timeout(45):
            plan = await prepare_restore(coordinator, message["port"], backup)
        backups.plans = {token: value for token, value in backups.plans.items() if value["expires"] > time.monotonic()}
        if len(backups.plans) >= 16:
            raise ValueError("Zu viele offene Vorschauen; später erneut versuchen")
        token = secrets.token_urlsafe(24)
        backups.plans[token] = {
            "expires": time.monotonic() + 300,
            "user": connection.user.id,
            "key": key,
            "coordinator": coordinator,
            "plan": plan,
        }
        connection.send_result(
            message["id"],
            {
                "token": token,
                "expires_in": 300,
                "target": plan["target"],
                "port": plan["port"],
                "source_created_at": plan["source_created_at"],
                "source_device": plan["source_device"],
                "rows": plan["rows"],
                "skipped": plan["skipped"],
            },
        )
    except (ValueError, IfmError, TimeoutError) as err:
        connection.send_error(
            message["id"], "restore_preview_failed", str(err) or "Zeitlimit bei der Vorschau erreicht"
        )
    finally:
        backups.busy.discard(key)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ifm_iolink/restore_parameters",
        vol.Required("entry_id"): str,
        vol.Required("port"): int,
        vol.Required("token"): str,
        vol.Required("confirm"): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def restore_parameters(hass, connection, message):
    backups = hass.data[DOMAIN]["parameter_backups"]
    key = (message["entry_id"], message["port"])
    if key in backups.busy:
        connection.send_error(message["id"], "busy", "Parameteraktion an diesem Port läuft bereits")
        return
    backups.busy.add(key)
    try:
        saved = backups.plans.get(message["token"])
        if (
            not message["confirm"]
            or not saved
            or saved["expires"] <= time.monotonic()
            or saved["user"] != connection.user.id
            or saved["key"] != key
        ):
            raise ValueError("Bestätigung fehlt oder Vorschau ist abgelaufen; neue Vorschau erstellen")
        coordinator = coordinator_for(hass, message)
        if coordinator is not saved["coordinator"]:
            raise ValueError("Master wurde seit der Vorschau neu geladen")
        backups.plans.pop(message["token"])

        async def record(report):
            await backups.record_restore(*key, report)

        report = await execute_restore(
            coordinator,
            message["port"],
            saved["plan"],
            record,
            still_current=lambda: hass.data[DOMAIN]["coordinators"].get(key[0]) is coordinator,
        )
        connection.send_result(message["id"], report)
    except (ValueError, IfmError) as err:
        connection.send_error(message["id"], "restore_failed", str(err))
    finally:
        backups.busy.discard(key)


@websocket_api.websocket_command(
    {vol.Required("type"): "ifm_iolink/get_restore_report", vol.Required("entry_id"): str, vol.Required("port"): int}
)
@websocket_api.require_admin
@websocket_api.async_response
async def get_restore_report(hass, connection, message):
    try:
        entry_for(hass, message["entry_id"])
        report = hass.data[DOMAIN]["parameter_backups"].reports.get(message["entry_id"], {}).get(str(message["port"]))
        connection.send_result(message["id"], {"report": report})
    except ValueError as err:
        connection.send_error(message["id"], "invalid_input", str(err))
