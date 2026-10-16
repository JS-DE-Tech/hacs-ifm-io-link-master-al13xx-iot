"""Bounded replacement network transfer with durable, non-replayed writes."""

import asyncio
import ipaddress
import time
from urllib.parse import urlsplit, urlunsplit

from .api import IfmError, data_value
from .const import DOMAIN
from .replacement import candidate_client, registry_serial

NETWORK_KEYS = ("dhcp", "ipaddress", "subnetmask", "ipdefaultgateway")
SETTINGS = ("/devicetag/applicationtag", "/iotsetup/smobip", "/iotsetup/smobport", "/iotsetup/smobinterval")


def validate_setting(path, value):
    if path == SETTINGS[0] and isinstance(value, str) and len(value.encode("utf-8")) <= 31:
        return
    if path == SETTINGS[1] and isinstance(value, str):
        ipaddress.IPv4Address(value)
        return
    if path == SETTINGS[2] and type(value) is int and 0 <= value <= 65535:
        return
    if path == SETTINGS[3] and type(value) is int and (value == 0 or 500 <= value <= 2147483647):
        return
    raise ValueError("Nicht unterstützter Masterparameter oder ungültiger Wert")


def store(hass, entry):
    from homeassistant.helpers.storage import Store

    return Store(hass, 1, f"{DOMAIN}.replacement.{entry.entry_id}")


def validate_network(values):
    if set(values) != set(NETWORK_KEYS) or type(values["dhcp"]) is not int or values["dhcp"] != 0:
        raise ValueError("Automatische IP-Übernahme benötigt eine vollständige statische IPv4-Konfiguration")
    address = ipaddress.IPv4Address(values["ipaddress"])
    network = ipaddress.IPv4Network(f"{address}/{values['subnetmask']}", strict=False)
    gateway = ipaddress.IPv4Address(values["ipdefaultgateway"])
    if (not address.is_private or address.is_loopback or address.is_link_local
            or address in (network.network_address, network.broadcast_address)
            or (int(gateway) != 0 and (gateway not in network or gateway in
                                     (network.network_address, network.broadcast_address)))):
        raise ValueError("Ungültige statische Netzwerkwerte")
    return {**values, "ipaddress": str(address), "subnetmask": str(network.netmask),
            "ipdefaultgateway": str(gateway)}


async def capture(hass, entry):
    """Read only. An unavailable old master does not prevent manual replacement."""
    client = candidate_client(hass, entry, entry.data["url"])
    try:
        identity = await client.identify()
        if identity["serial"] != entry.unique_id:
            return {"error": "Bisheriger Master antwortet nicht; keine Hardwarewerte gesichert"}
        paths = [f"/iotsetup/network/{key}" for key in NETWORK_KEYS]
        paths += [f"/iolinkmaster/port[{port}]/mode" for port in range(1, entry.data["ports"] + 1)]
        paths += list(SETTINGS)
        values = await client.multi(paths)
        network = {key: data_value(values, f"/iotsetup/network/{key}") for key in NETWORK_KEYS}
        modes = {str(port): data_value(values, f"/iolinkmaster/port[{port}]/mode")
                 for port in range(1, entry.data["ports"] + 1)}
        if any(type(mode) is not int or mode not in (0, 1, 2, 3) for mode in modes.values()):
            raise ValueError("Portmodi nicht vollständig lesbar")
        # DHCP is retained in the backup, but cannot be cloned to a predictable IP.
        settings, skipped = {}, []
        for path in SETTINGS:
            value = data_value(values, path)
            try:
                validate_setting(path, value)
            except ValueError:
                skipped.append(path)
            else:
                settings[path] = value
        return {"network": network, "modes": modes, "settings": settings, "skipped": skipped}
    except (IfmError, ValueError) as err:
        return {"error": str(err)}


async def saved(hass, entry):
    backup = await store(hass, entry).async_load()
    if not backup or not entry.data.get("replacement_paused"):
        raise ValueError("Zuerst Austausch vorbereiten")
    assert_source(hass, entry, backup)
    return backup


def assert_source(hass, entry, backup):
    """Bind the durable operation to its original, still-paused configuration."""
    if (hass.config_entries.async_get_entry(entry.entry_id) is not entry
            or backup.get("entry_id") != entry.entry_id or backup.get("unique_id") != entry.unique_id
            or not isinstance(backup.get("data"), dict)
            or {**backup["data"], "replacement_paused": True} != dict(entry.data)
            or backup.get("options") != dict(entry.options)):
        raise ValueError("Gesicherte und aktuelle Integrationskonfiguration unterscheiden sich; Austausch gestoppt")


def validate_restore_plan(backup, entry):
    """Reject incomplete source configuration before changing any network state."""
    hardware = backup.get("hardware", {})
    modes, settings = hardware.get("modes", {}), hardware.get("settings", {})
    if (not isinstance(modes, dict)
            or set(modes) != {str(p) for p in range(1, entry.data["ports"] + 1)}
            or any(type(mode) is not int or mode not in (0, 1, 2, 3) for mode in modes.values())):
        raise ValueError("Keine vollständige Sicherung der Portmodi vorhanden")
    if not isinstance(settings, dict):
        raise ValueError("Ungültige Sicherung der Masterparameter")
    for path, value in settings.items():
        validate_setting(path, value)


async def ensure_target_available(hass, entry, serial):
    """Caller serializes replacement jobs globally across config entries."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == entry.entry_id:
            continue
        if serial in (other.unique_id, registry_serial(other)):
            raise ValueError("Dieser Ersatzmaster gehört bereits zu einer anderen Integration")
        if other.data.get("replacement_paused"):
            other_backup = await store(hass, other).async_load()
            if other_backup and (other_backup.get("transfer") or {}).get("serial") == serial:
                raise ValueError("Dieser Ersatzmaster ist bereits für einen anderen Austausch reserviert")


def assert_target_unassigned(hass, entry, serial):
    """No await between the final registry check and initiating a write."""
    if any(other.entry_id != entry.entry_id and serial in (other.unique_id, registry_serial(other))
           for other in hass.config_entries.async_entries(DOMAIN)):
        raise ValueError("Dieser Ersatzmaster gehört bereits zu einer anderen Integration")


async def network_status(hass, entry):
    backup = await saved(hass, entry)
    return {"hardware": backup.get("hardware", {}), "transfer": backup.get("transfer")}


async def check_adoption(hass, entry, preview):
    backup = await saved(hass, entry)
    transfer = backup.get("transfer")
    if not transfer:
        return
    if transfer["serial"] != preview["target"]["serial"] or transfer["url"] != preview["url"]:
        raise ValueError("Übernahme muss den ausgewählten Ersatzmaster an der bestätigten Ziel-IP verwenden")
    if not (await verify_network(hass, entry))["verified"]:
        raise ValueError("Netzwerkübernahme noch nicht bestätigt")
    if not transfer.get("restore_complete"):
        raise ValueError("Konfigurationsübertragung unvollständig; Protokoll prüfen und Wiederherstellung klären")
    validate_restore_plan(backup, entry)
    client = candidate_client(hass, entry, transfer["url"])
    identity = await client.identify()
    if any(identity[key] != transfer[key] for key in ("serial", "model")):
        raise ValueError("Ersatzmaster vor Übernahme geändert")
    expected = {f"/iolinkmaster/port[{port}]/mode": 0 if mode == 2 else mode
                for port, mode in backup["hardware"]["modes"].items()}
    expected.update(backup["hardware"].get("settings", {}))
    actual = await client.multi(list(expected))
    if any(data_value(actual, path) != value for path, value in expected.items()):
        raise ValueError("Zurückgesicherte Konfiguration vor Übernahme geändert; Werte am Ersatzmaster prüfen")
    assert_source(hass, entry, backup)


async def address_in_use(url):
    parts = urlsplit(url)
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)), 2)
    except (OSError, TimeoutError):
        return False
    writer.close()
    await writer.wait_closed()
    return True


async def transfer_network(hass, entry, token):
    """Write once, journal before I/O; continue interrupted operations by readback."""
    from .replacement import preview_replacement

    backup = await saved(hass, entry)
    if backup.get("transfer"):
        await resume_reboot(hass, entry)
        return await verify_network(hass, entry)
    preview = hass.data[DOMAIN].get("replacement_previews", {}).get(entry.entry_id)
    if (not preview or preview["token"] != token or preview["expires"] < time.monotonic()
            or preview["source"] != dict(entry.data) or preview["options"] != dict(entry.options)):
        raise ValueError("Ersatzmaster erneut prüfen")
    network = validate_network(backup.get("hardware", {}).get("network", {}))
    validate_restore_plan(backup, entry)
    target = preview["target"]
    if target["serial"] == entry.unique_id:
        raise ValueError("Netzwerkübernahme ist nur auf einen anderen Ersatzmaster erlaubt")
    fresh = await preview_replacement(hass, entry, preview["url"])
    if fresh["target"] != target or fresh["rows"] != preview["rows"]:
        raise ValueError("Ersatzmaster geändert; erneut prüfen")
    parts = urlsplit(preview["url"])
    target_url = urlunsplit((parts.scheme, network["ipaddress"] + (f":{parts.port}" if parts.port else ""), "/", "", ""))
    client = candidate_client(hass, entry, preview["url"])
    destination = candidate_client(hass, entry, target_url)
    if client.url != destination.url:
        # Any open IoT TCP port blocks takeover, including non-ifm devices.
        # Lack of response is not proof of a free IP: UI also requires disconnection.
        if await address_in_use(target_url):
            raise ValueError("Ziel-IP antwortet bereits; bisherigen Master trennen und IP-Belegung prüfen")
    if (await client.identify())["serial"] != target["serial"]:
        raise ValueError("Ersatzmaster geändert")
    await ensure_target_available(hass, entry, target["serial"])
    assert_source(hass, entry, backup)
    transfer = {"serial": target["serial"], "model": target["model"], "url": target_url,
                "source_url": client.url, "network": network, "stage": "write_attempted"}
    backup["transfer"] = transfer
    await store(hass, entry).async_save(backup)
    assert_source(hass, entry, backup)
    assert_target_unassigned(hass, entry, target["serial"])
    try:
        code = await client.write_network(network)
        transfer["network_code"] = code
        transfer["stage"] = "reboot_pending" if code == 230 else "network_accepted"
        await store(hass, entry).async_save(backup)
        await resume_reboot(hass, entry)
        # 233 reloads networking itself. Never reboot an unverified IP afterwards.
    except IfmError:
        pass  # Outcome uncertain: only readback is permitted, never replay.
    await asyncio.sleep(1.1)
    return await verify_network(hass, entry)


async def resume_reboot(hass, entry):
    """Resume only a positively acknowledged 230; never replay an attempted reboot."""
    backup = await saved(hass, entry)
    transfer = backup.get("transfer", {})
    if (transfer.get("network_code") != 230 or transfer.get("reboot_attempted")
            or transfer.get("stage") == "verified"):
        return
    source_url = transfer.get("source_url")
    # A confirmed different address proves networking already moved, for example
    # after an external reboot while HA was stopped. Do not contact the old IP.
    # At the same address, configured values alone do not prove a reboot happened.
    if source_url != transfer.get("url"):
        if (await verify_network(hass, entry))["verified"]:
            return
    if not source_url:
        raise ValueError("Ursprüngliche Ersatzmaster-Adresse fehlt; Neustart am Gerät prüfen")
    client = candidate_client(hass, entry, source_url)
    try:
        identity = await client.identify()
    except IfmError:
        return  # Device may be rebooting already; bounded target readback follows.
    if any(identity[key] != transfer[key] for key in ("serial", "model")):
        raise ValueError("Identität vor Neustart geändert")
    await ensure_target_available(hass, entry, transfer["serial"])
    assert_source(hass, entry, backup)
    transfer["stage"] = "reboot_attempted"
    transfer["reboot_attempted"] = True
    await store(hass, entry).async_save(backup)
    assert_source(hass, entry, backup)
    assert_target_unassigned(hass, entry, transfer["serial"])
    try:
        await client.reboot()
    except IfmError:
        return  # Possibly accepted: only reconnect/readback may follow.
    transfer["reboot_acknowledged"] = True
    await store(hass, entry).async_save(backup)


async def verify_network(hass, entry):
    backup = await saved(hass, entry)
    transfer = backup.get("transfer")
    if not transfer:
        raise ValueError("Keine Netzwerkübertragung vorhanden")
    client = candidate_client(hass, entry, transfer["url"])
    try:
        identity = await client.identify()
        if any(identity[key] != transfer[key] for key in ("serial", "model")):
            raise ValueError("An der Ziel-IP antwortet nicht der ausgewählte Ersatzmaster")
        paths = [f"/iotsetup/network/{key}" for key in NETWORK_KEYS]
        values = await client.multi(paths)
        actual = {key: data_value(values, path) for key, path in zip(NETWORK_KEYS, paths, strict=True)}
        if any(value is None for value in actual.values()):
            return {"verified": False, "url": transfer["url"],
                    "message": "Ersatzmaster antwortet; Netzwerkwerte sind noch nicht vollständig lesbar. Erneut prüfen."}
        if actual != transfer["network"]:
            raise ValueError("Netzwerkwerte sind noch nicht durch Rücklesen bestätigt")
    except IfmError:
        return {"verified": False, "url": transfer["url"],
                "message": ("Ersatzmaster noch nicht an der Ziel-IP erreichbar. Verbindung und Neustart "
                            f"am Gerät prüfen (bisherige Adresse: {transfer.get('source_url', 'unbekannt')}). "
                            "Erneut prüfen setzt durch Rücklesen fort; unbestätigte Schreibvorgänge werden nicht wiederholt.")}
    assert_source(hass, entry, backup)
    transfer["stage"] = "verified"
    await store(hass, entry).async_save(backup)
    return {"verified": True, "url": transfer["url"], "serial": transfer["serial"]}


async def wait_for_network(hass, entry, *, attempts=30, interval=2):
    """Bounded reconnect polling; this never sends hardware write/reboot requests."""
    if type(attempts) is not int or not 1 <= attempts <= 60 or not 0 <= interval <= 5:
        raise ValueError("Ungültige Wartezeit für Netzwerkprüfung")
    result = {"verified": False, "message": "Wartezeit abgelaufen; Verbindung prüfen und Austausch fortsetzen."}
    try:
        async with asyncio.timeout(90):
            for attempt in range(attempts):
                result = await verify_network(hass, entry)
                if result["verified"]:
                    return result
                if attempt + 1 < attempts:
                    await asyncio.sleep(interval)
    except TimeoutError:
        pass
    return result


async def restore_modes(hass, entry):
    """Restore supported port configuration only after verified network transfer.

    Output modes require deliberate subsequent activation; never restore ON or
    transiently enable an output while restoring configuration.
    """
    result = await verify_network(hass, entry)
    if not result["verified"]:
        raise ValueError(result["message"])
    backup = await saved(hass, entry)
    transfer = backup["transfer"]
    validate_restore_plan(backup, entry)
    modes = backup["hardware"]["modes"]
    transfer["restore_attempted"] = True
    transfer["restore_complete"] = False
    transfer.setdefault("ports", [])
    transfer.setdefault("settings", [])
    await store(hass, entry).async_save(backup)
    client = candidate_client(hass, entry, transfer["url"])
    for port, mode in modes.items():
        if type(mode) is not int or mode not in (0, 1, 2, 3):
            raise ValueError("Ungültiger gesicherter Portmodus")
        identity = await client.identify()
        if any(identity[key] != transfer[key] for key in ("serial", "model")):
            raise ValueError("Ersatzmaster während Portübertragung geändert")
        assert_source(hass, entry, backup)
        target_mode = 0 if mode == 2 else mode
        row = next((r for r in transfer["ports"] if r["port"] == int(port)), None)
        if row is None:
            row = {"port": int(port), "saved_mode": mode, "target_mode": target_mode, "state": "attempted"}
            transfer["ports"].append(row)
            await store(hass, entry).async_save(backup)
            assert_source(hass, entry, backup)
            assert_target_unassigned(hass, entry, transfer["serial"])
            await client.write_port_mode(int(port), target_mode)
        path = f"/iolinkmaster/port[{port}]/mode"
        if data_value(await client.multi([path]), path) != target_mode:
            raise ValueError(f"Port {port}: Rücklesen fehlgeschlagen; gespeicherten Zielmodus am Gerät prüfen. "
                             "Ein unbestätigter Schreibvorgang wird nicht wiederholt.")
        assert_source(hass, entry, backup)
        row["state"] = "verified"
        await store(hass, entry).async_save(backup)
    for path, value in backup.get("hardware", {}).get("settings", {}).items():
        validate_setting(path, value)
        identity = await client.identify()
        if any(identity[key] != transfer[key] for key in ("serial", "model")):
            raise ValueError("Ersatzmaster während Konfigurationsübertragung geändert")
        assert_source(hass, entry, backup)
        row = next((r for r in transfer["settings"] if r["path"] == path), None)
        if row is None:
            row = {"path": path, "state": "attempted"}
            transfer["settings"].append(row)
            await store(hass, entry).async_save(backup)
            assert_source(hass, entry, backup)
            assert_target_unassigned(hass, entry, transfer["serial"])
            await client.write_master_setting(path, value)
        if data_value(await client.multi([path]), path) != value:
            raise ValueError(f"{path}: Rücklesen fehlgeschlagen; gesicherten Wert am Gerät prüfen. "
                             "Ein unbestätigter Schreibvorgang wird nicht wiederholt.")
        assert_source(hass, entry, backup)
        row["state"] = "verified"
        await store(hass, entry).async_save(backup)
    transfer["restore_complete"] = True
    await store(hass, entry).async_save(backup)
    return {"ports": transfer["ports"], "settings": transfer["settings"]}
