"""Polling, isolated port failures and diagnostics."""

import logging
import time
from collections import deque
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import IfmError, data_value
from .const import DEFAULT_INTERVAL, DOMAIN, PORT_PROPERTIES, port_path
from .decoder import decode
from .digital import digital_value, pin2_value, port_mode

_LOGGER = logging.getLogger(__name__)


class IfmCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client, identity, library):
        super().__init__(
            hass,
            _LOGGER,
            name=f"ifm {identity['serial']}",
            config_entry=entry,
            update_interval=timedelta(seconds=entry.options.get("interval", DEFAULT_INTERVAL)),
        )
        self.entry, self.client, self.identity, self.library = entry, client, identity, library
        self.replacement_detected = None
        self.metadata = {}
        self.metadata_at = None
        self.condition_values = {}
        self.samples = {str(port): deque(maxlen=30) for port in range(1, identity["ports"] + 1)}

    async def _async_update_data(self):
        refresh_metadata = self.metadata_at is None or time.monotonic() - self.metadata_at >= 60
        if self.entry.data.get("replacement_paused"):
            raise UpdateFailed("Masteraustausch vorbereitet; Verarbeitung pausiert")
        paths = ["/deviceinfo/productcode", "/deviceinfo/serialnumber"]
        for port in range(1, self.identity["ports"] + 1):
            paths.extend(port_path(port, name) for name in ("pdin", "status"))
            paths.extend((f"/iolinkmaster/port[{port}]/mode", f"/iolinkmaster/port[{port}]/pin2in"))
            paths.append(port_path(port, "pdout"))
            if refresh_metadata:
                paths.extend(port_path(port, name) for name in PORT_PROPERTIES if name != "status")
        try:
            response = await self.client.multi(paths)
        except IfmError as err:
            raise UpdateFailed(str(err)) from err
        model = data_value(response, "/deviceinfo/productcode")
        serial = data_value(response, "/deviceinfo/serialnumber")
        if not model or not serial:
            raise UpdateFailed("Master-Identität nicht lesbar")
        if model != self.identity["model"] or serial != self.identity["serial"]:
            self.replacement_detected = {"model": model, "serial": serial}
            raise UpdateFailed("Anderer Master erkannt – Austausch bestätigen")
        self.replacement_detected = None
        now = dt_util.utcnow().isoformat()
        result = {}
        for port in range(1, self.identity["ports"] + 1):
            key = str(port)
            identity = self.metadata.setdefault(key, {})
            if refresh_metadata:
                identity.update(
                    {name: data_value(response, port_path(port, name)) for name in PORT_PROPERTIES if name != "status"}
                )
            status = data_value(response, port_path(port, "status"))
            identity["status"] = status
            raw = data_value(response, port_path(port, "pdin"))
            mode = port_mode(data_value(response, f"/iolinkmaster/port[{port}]/mode"))
            assignment = self.entry.options.get("ports", {}).get(key, {})
            profile_id = assignment.get("profile", "unknown")
            profile = self.library.all.get(profile_id)
            values, error = {}, None
            connected = status == 2 and isinstance(raw, str) and bool(raw) and mode in (None, 3)
            if profile and connected:
                try:
                    matches = profile.get("match", [])
                    if matches and all(
                        identity.get("vendorid") != match["vendorid"] or identity.get("deviceid") != match["deviceid"]
                        for match in matches
                    ):
                        raise ValueError("Gerätekennung passt nicht zum ausgewählten Profil")
                    for condition in profile.get("conditions", []):
                        condition_key = (port, profile_id, condition["index"])
                        if refresh_metadata or condition_key not in self.condition_values:
                            value = await self.client.request(
                                port_path(port, "iolreadacyclic"), {"index": condition["index"], "subindex": 0}
                            )
                            self.condition_values[condition_key] = int(value["value"], 16)
                        if self.condition_values[condition_key] != condition["value"]:
                            raise ValueError(
                                f"Gerätemodus/Einheit passt nicht: Index {condition['index']} erwartet {condition['value']}"
                            )
                    values = decode(profile, raw)
                except (ValueError, IfmError, KeyError, TypeError) as err:
                    error = str(err)
                    for condition in profile.get("conditions", []):
                        self.condition_values.pop((port, profile_id, condition["index"]), None)
            elif profile_id != "unknown" and not profile:
                error = "Zugewiesenes Profil fehlt"
            item = {
                "port": port,
                "identity": dict(identity),
                "raw": raw,
                "mode": mode,
                "pin2": pin2_value(data_value(response, f"/iolinkmaster/port[{port}]/pin2in")),
                "pin4": digital_value(raw) if mode == 1 else (
                    digital_value(data_value(response, port_path(port, "pdout"))) if mode == 2 else None
                ),
                "connected": connected,
                "profile": profile_id,
                "assignment": assignment,
                "values": values,
                "error": error,
                "suggested": self.library.suggest(identity),
                "updated": now,
            }
            result[key] = item
            self.samples[key].append(
                {
                    "time": now,
                    "pdin": raw,
                    "status": status,
                    "pdin_code": response.get(port_path(port, "pdin"), {}).get("code"),
                }
            )
        if refresh_metadata:
            self.metadata_at = time.monotonic()
        return result

    def snapshot(self):
        return {
            "entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "url": self.client.url,
            "replacement_paused": self.entry.data.get("replacement_paused", False),
            "replacement_detected": self.replacement_detected,
            "identity": self.identity,
            "online": self.last_update_success,
            "interval": self.entry.options.get("interval", DEFAULT_INTERVAL),
            "ports": self.data or {},
        }

    def diagnostic(self, port=None):
        ports = [str(port)] if port is not None else list(self.samples)
        profile_ids = {(self.data or {}).get(key, {}).get("profile") for key in ports}
        profiles = {
            key: {
                field: value
                for field, value in self.library.all[key].items()
                if field not in ("image", "purpose", "description", "notes")
            }
            for key in profile_ids
            if key in self.library.all
        }
        return {
            "schema_version": 1,
            "integration": DOMAIN,
            "generated_at": dt_util.utcnow().isoformat(),
            "master": {
                "model": self.identity["model"],
                "firmware": self.identity.get("firmware"),
                "serial": "REDACTED",
            },
            "ports": {
                key: {
                    "identity": {
                        name: value
                        for name, value in (self.data or {}).get(key, {}).get("identity", {}).items()
                        if name not in ("serial", "applicationspecifictag")
                    },
                    "samples": list(self.samples[key]),
                }
                for key in ports
            },
            "profiles": profiles,
            "instructions": "Erstelle ein JSON-Geräteprofil für ifm_iolink nach docs/device-profiles.md. Verwende IODD/Herstellerdokumentation für Bytepositionen, Vorzeichen, Einheiten und Skalierungen. Rohdaten allein beweisen keine Einheit. Keine ausführbaren Skripte. Prüfe mindestens zwei Werte gegen Display/Referenz. Profil-ID beginnt mit custom_.",
        }
