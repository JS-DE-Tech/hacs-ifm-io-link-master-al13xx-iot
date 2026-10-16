"""Explicit master replacement, preserving logical registry identifiers."""

import secrets
import time
from copy import deepcopy

from .api import IfmClient, data_value, normalize_url
from .const import DOMAIN, MODELS, port_path


def registry_serial(entry):
    """Immutable namespace of the original installation, not hardware identity."""
    return entry.data.get("registry_serial", entry.unique_id)


def replacement_entry(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError("Master nicht gefunden")
    return entry


def ensure_idle(hass, entry):
    if any(key[0] == entry.entry_id for key in hass.data[DOMAIN]["parameter_backups"].busy):
        raise ValueError("An diesem Master läuft noch eine Parameter- oder Schaltaktion")


def ensure_target_available(hass, entry, serial):
    """Check ownership without yielding before the final config-entry commit."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id != entry.entry_id and serial in (other.unique_id, registry_serial(other)):
            raise ValueError("Dieser Master gehört bereits zu einer anderen Integration")


def candidate_client(hass, entry, url):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    return IfmClient(async_get_clientsession(hass), url,
                     entry.data.get("username", ""), entry.data.get("password", ""),
                     entry.data.get("verify_ssl", True))


async def pause_replacement(hass, entry):
    """Save HA configuration before pausing; never write to the physical master."""
    from homeassistant.helpers.storage import Store

    ensure_idle(hass, entry)
    if entry.data.get("replacement_paused"):
        return
    from .replacement_network import capture

    # Reserve the same keys as all sensor/mode/output actions before yielding.
    # Otherwise an entire port write could run between the two idle checks.
    busy = hass.data[DOMAIN]["parameter_backups"].busy
    reserved = {(entry.entry_id, port) for port in range(1, entry.data["ports"] + 1)}
    busy.update(reserved)
    try:
        storage = Store(hass, 1, f"{DOMAIN}.replacement.{entry.entry_id}")
        previous = await storage.async_load()
        transfer = (previous or {}).get("transfer")
        if transfer and transfer.get("serial") != entry.unique_id:
            raise ValueError("Unvollständiger Austausch vorhanden; vorhandenen Ablauf zuerst fortsetzen")
        source, options = deepcopy(dict(entry.data)), deepcopy(dict(entry.options))
        hardware = await capture(hass, entry)
        if dict(entry.data) != source or dict(entry.options) != options:
            raise ValueError("Konfiguration geändert; Vorbereitung erneut starten")
        await storage.async_save({
            "entry_id": entry.entry_id, "unique_id": entry.unique_id,
            "title": entry.title, "data": source,
            "options": options,
            "hardware": hardware,
        })
    finally:
        busy.difference_update(reserved)
    # Synchronous re-check after disk I/O, before publishing the pause.
    ensure_idle(hass, entry)
    if dict(entry.data) != source or dict(entry.options) != options:
        raise ValueError("Konfiguration geändert; Vorbereitung erneut starten")
    hass.config_entries.async_update_entry(entry, data={**entry.data, "replacement_paused": True})


async def preview_replacement(hass, entry, url):
    if not entry.data.get("replacement_paused"):
        raise ValueError("Bitte zuerst Sicherung erstellen und Austausch vorbereiten")
    source = deepcopy(dict(entry.data))
    options = deepcopy(dict(entry.options))
    client = candidate_client(hass, entry, normalize_url(url))
    target = await client.identify()
    if target["model"] not in MODELS or target["ports"] < source["ports"]:
        raise ValueError("Ersatzmaster muss mindestens genauso viele Ports besitzen")
    ensure_target_available(hass, entry, target["serial"])
    paths = []
    for port in range(1, target["ports"] + 1):
        paths.extend([f"/iolinkmaster/port[{port}]/mode", port_path(port, "pdout"),
                      port_path(port, "vendorid"), port_path(port, "deviceid")])
    values = await client.multi(paths)
    rows = []
    for port in range(1, target["ports"] + 1):
        mode = data_value(values, f"/iolinkmaster/port[{port}]/mode")
        output = data_value(values, port_path(port, "pdout"))
        if type(mode) is not int or mode not in (0, 1, 2, 3):
            raise ValueError(f"Port {port}: Betriebsart nicht lesbar")
        if mode == 2 and output != "00":
            raise ValueError(f"Port {port}: Digitalausgang muss am Ersatzmaster bestätigt AUS sein")
        assignment = options.get("ports", {}).get(str(port), {})
        profile = hass.data[DOMAIN]["library"].all.get(assignment.get("profile"), {})
        matches = profile.get("match", [])
        matched = not matches or any(
            data_value(values, port_path(port, "vendorid")) == m["vendorid"]
            and data_value(values, port_path(port, "deviceid")) == m["deviceid"] for m in matches)
        rows.append({"port": port, "mode": mode, "name": assignment.get("name", ""),
                     "new": port > source["ports"], "profile_matches": matched})
    if dict(entry.data) != source or dict(entry.options) != options:
        raise ValueError("Konfiguration geändert; Vorschau erneut erstellen")
    token = secrets.token_urlsafe(24)
    # One bounded, short-lived preview per config entry. No credentials sent to UI.
    hass.data[DOMAIN].setdefault("replacement_previews", {})[entry.entry_id] = {
        "token": token, "expires": time.monotonic() + 300, "source": source,
        "options": options, "target": target, "url": client.url, "rows": rows,
    }
    return {"token": token, "target": target, "rows": rows,
            "old_model": source["model"], "old_serial": entry.unique_id}


async def confirm_replacement(hass, entry, token):
    from .replacement_network import check_adoption

    previews = hass.data[DOMAIN].setdefault("replacement_previews", {})
    preview = previews.get(entry.entry_id)
    if not preview or not secrets.compare_digest(preview["token"], token) or preview["expires"] < time.monotonic():
        raise ValueError("Vorschau abgelaufen; Ersatzgerät erneut prüfen")
    if dict(entry.data) != preview["source"] or dict(entry.options) != preview["options"]:
        raise ValueError("Konfiguration geändert; Ersatzgerät erneut prüfen")
    ensure_idle(hass, entry)
    await check_adoption(hass, entry, preview)
    # Re-read all target state and duplicate checks immediately before commit.
    fresh = await preview_replacement(hass, entry, preview["url"])
    if fresh["target"] != preview["target"] or fresh["rows"] != preview["rows"]:
        raise ValueError("Ersatzgerät oder Portzustand geändert; Vorschau erneut prüfen")
    if dict(entry.data) != preview["source"] or dict(entry.options) != preview["options"]:
        raise ValueError("Konfiguration geändert; Ersatzgerät erneut prüfen")
    ensure_idle(hass, entry)
    target = preview["target"]
    ensure_target_available(hass, entry, target["serial"])
    data = {**entry.data, **target, "url": preview["url"],
            "registry_serial": registry_serial(entry), "replacement_paused": False}
    # No registry entries are deleted/recreated. The same logical namespace is
    # used by master, ports and entities after reload, including repeated swaps.
    hass.config_entries.async_update_entry(entry, unique_id=target["serial"], data=data)
    previews.pop(entry.entry_id, None)
    return {"saved": True, "model": target["model"], "ports": target["ports"]}
