"""Polling, isolated port failures and diagnostics."""

import logging
import time
from collections import deque
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import IfmError, data_value
from .const import DEFAULT_INTERVAL, DOMAIN, MASTER_DIAGNOSTIC_PATHS, PORT_PROPERTIES, port_path
from .decoder import decode

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
        self.metadata = {}
        self.metadata_at = None
        self.condition_values = {}
        self.master_diagnostics = {}
        self.samples = {str(port): deque(maxlen=30) for port in range(1, identity["ports"] + 1)}

    async def _async_update_data(self):
        # time.monotonic()'s absolute value is arbitrary (e.g. time since boot on Linux), so it can
        # already be under 60 on a freshly booted host; metadata_at must start at None, not 0.
        refresh_metadata = self.metadata_at is None or time.monotonic() - self.metadata_at >= 60
        paths = list(MASTER_DIAGNOSTIC_PATHS)
        for port in range(1, self.identity["ports"] + 1):
            paths.extend(port_path(port, name) for name in ("pdin", "status"))
            paths.append(f"/iolinkmaster/port[{port}]/pin2in")
            # Gated on the device's own last-known mode too, not just the saved assignment: right
            # after a mode switch (or if a port was put into DO some other way) the assignment can
            # briefly lag the device, and skipping the read then would leave pdout stuck at None.
            assignment_mode = self.entry.options.get("ports", {}).get(str(port), {}).get("mode")
            known_mode = self.metadata.get(str(port), {}).get("mode")
            if 2 in (assignment_mode, known_mode) or refresh_metadata:
                paths.append(port_path(port, "pdout"))
            if refresh_metadata:
                paths.extend(port_path(port, name) for name in PORT_PROPERTIES if name != "status")
                paths.append(f"/iolinkmaster/port[{port}]/mode")
        try:
            response = await self.client.multi(paths)
        except IfmError as err:
            raise UpdateFailed(str(err)) from err
        self.master_diagnostics = self._diagnostics_from(response)
        now = dt_util.utcnow().isoformat()
        result = {}
        for port in range(1, self.identity["ports"] + 1):
            key = str(port)
            identity = self.metadata.setdefault(key, {})
            if refresh_metadata:
                identity.update(
                    {name: data_value(response, port_path(port, name)) for name in PORT_PROPERTIES if name != "status"}
                )
                identity["mode"] = data_value(response, f"/iolinkmaster/port[{port}]/mode")
            status = data_value(response, port_path(port, "status"))
            identity["status"] = status
            raw = data_value(response, port_path(port, "pdin"))
            assignment = self.entry.options.get("ports", {}).get(key, {})
            profile_id = assignment.get("profile", "unknown")
            profile = self.library.all.get(profile_id)
            values, error = {}, None
            connected = status == 2 and isinstance(raw, str) and bool(raw)
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
                "pin2": data_value(response, f"/iolinkmaster/port[{port}]/pin2in"),
                "mode": identity.get("mode"),
                "pdout": (
                    data_value(response, port_path(port, "pdout"))
                    if 2 in (assignment.get("mode"), identity.get("mode"))
                    else None
                ),
                "pin4": (
                    (raw not in (None, "00")) if 1 in (assignment.get("mode"), identity.get("mode")) else None
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

    @staticmethod
    def _diagnostics_from(response):
        """Master-level health values; ifm reports no direct power register, so it is derived from U x I."""
        temperature = data_value(response, "/processdatamaster/temperature")
        voltage_mv = data_value(response, "/processdatamaster/voltage")
        current_ma = data_value(response, "/processdatamaster/current")
        status = data_value(response, "/processdatamaster/supervisionstatus")
        voltage = voltage_mv / 1000 if isinstance(voltage_mv, (int, float)) else None
        current = current_ma / 1000 if isinstance(current_ma, (int, float)) else None
        power = voltage * current if voltage is not None and current is not None else None
        return {"temperature": temperature, "voltage": voltage, "current": current, "power": power, "status": status}

    def snapshot(self):
        return {
            "entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "identity": self.identity,
            "online": self.last_update_success,
            "interval": self.entry.options.get("interval", DEFAULT_INTERVAL),
            "ports": self.data or {},
            "diagnostics": self.master_diagnostics,
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
