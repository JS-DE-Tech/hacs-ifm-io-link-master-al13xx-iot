"""Strict digital states and coordinated, verified DO writes.

Based on 100prznt's digital-output feature; mode changes have a separate entry point.
"""

from .api import data_value
from .const import DOMAIN, port_path


def digital_value(value):
    """Accept only one-byte digital process data; errors are not OFF."""
    if value == "00":
        return False
    if value == "01":
        return True
    return None


def pin2_value(value):
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    return None


def port_mode(value):
    return value if type(value) is int and value in (0, 1, 2, 3) else None


async def set_output(hass, coordinator, port, on):
    """No retries or optimistic state. Share the existing restore/backup lock."""
    if type(port) is not int or not 1 <= port <= coordinator.identity["ports"] or type(on) is not bool:
        raise ValueError("Ungültiger Port/Ausgangswert")
    data = hass.data[DOMAIN]
    key = (coordinator.entry.entry_id, port)
    busy = data["parameter_backups"].busy

    def current():
        if (
            hass.data.get(DOMAIN) is not data
            or data["coordinators"].get(key[0]) is not coordinator
            or not coordinator.last_update_success
        ):
            raise ValueError("Master nicht verfügbar oder neu geladen")

    current()
    if coordinator.entry.data.get("replacement_paused"):
        raise ValueError("Masteraustausch vorbereitet")
    if key in busy:
        raise ValueError("Aktion an diesem Port läuft bereits")
    busy.add(key)
    mode_path = f"/iolinkmaster/port[{port}]/mode"
    output_path = port_path(port, "pdout")
    try:
        identity = await coordinator.client.identify()
        current()
        if identity["serial"] != coordinator.identity["serial"] or identity["model"] != coordinator.identity["model"]:
            raise ValueError("Unter dieser Adresse antwortet ein anderer Master")
        response = await coordinator.client.multi([mode_path])
        current()
        if port_mode(data_value(response, mode_path)) != 2:
            raise ValueError("Port ist nicht im Digitalausgangsmodus (DO)")
        await coordinator.client.write_port_output(port, on)
        current()
        response = await coordinator.client.multi([mode_path, output_path])
        current()
        if port_mode(data_value(response, mode_path)) != 2 or digital_value(data_value(response, output_path)) is not on:
            raise ValueError("Ausgang nicht bestätigt: Rücklesewert oder Portmodus abweichend/unbekannt")
    except BaseException:
        # A timeout/cancellation may follow an effective write: do not retain an
        # apparently confirmed old value, and never resend automatically.
        if coordinator.data and str(port) in coordinator.data:
            coordinator.data[str(port)]["pin4"] = None
        raise
    finally:
        busy.discard(key)
