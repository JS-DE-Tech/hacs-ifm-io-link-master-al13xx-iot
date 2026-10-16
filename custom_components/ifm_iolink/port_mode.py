"""Explicit port-mode changes with fresh identity, locking and readback."""

from .api import data_value
from .const import DOMAIN, port_path
from .digital import digital_value, port_mode


async def change_mode(hass, coordinator, port, expected_mode, target_mode):
    """Do not modify assignments or retry writes whose outcome is uncertain."""
    if (type(port) is not int or not 1 <= port <= coordinator.identity["ports"]
            or port_mode(expected_mode) is None or port_mode(target_mode) is None):
        raise ValueError("Ungültiger Port/Modus")
    data = hass.data[DOMAIN]
    key = (coordinator.entry.entry_id, port)
    busy = data["parameter_backups"].busy

    def current():
        if (hass.data.get(DOMAIN) is not data
                or data["coordinators"].get(key[0]) is not coordinator
                or not coordinator.last_update_success):
            raise ValueError("Master nicht verfügbar oder neu geladen")

    current()
    if key in busy:
        raise ValueError("Aktion an diesem Port läuft bereits")
    busy.add(key)
    path = f"/iolinkmaster/port[{port}]/mode"
    output = port_path(port, "pdout")
    attempted = False
    try:
        identity = await coordinator.client.identify()
        current()
        if any(identity[k] != coordinator.identity[k] for k in ("serial", "model")):
            raise ValueError("Unter dieser Adresse antwortet ein anderer Master")
        response = await coordinator.client.multi([path])
        current()
        if port_mode(data_value(response, path)) != expected_mode:
            raise ValueError("Portmodus geändert oder unbekannt; Ansicht aktualisieren und erneut bestätigen")
        if expected_mode == target_mode:
            return
        attempted = True
        await coordinator.client.write_port_mode(port, target_mode)
        current()
        response = await coordinator.client.multi([path])
        current()
        if port_mode(data_value(response, path)) != target_mode:
            raise ValueError("Modusänderung nicht durch Rücklesen bestätigt")
        if target_mode == 2:
            await coordinator.client.write_port_output(port, False)
            current()
            response = await coordinator.client.multi([path, output])
            current()
            if port_mode(data_value(response, path)) != 2 or digital_value(data_value(response, output)) is not False:
                raise ValueError("DO wurde gewählt, aber AUS konnte nicht bestätigt werden; Ausgang prüfen")
    finally:
        if attempted:
            # Even failed requests may have changed hardware. Never publish a
            # cached old mode or confirmed output after a partial operation.
            item = (coordinator.data or {}).get(str(port))
            if item is not None:
                item.update(mode=None, pin4=None, connected=False, values={})
            coordinator.metadata_at = None
            coordinator.condition_values = {
                k: v for k, v in getattr(coordinator, "condition_values", {}).items() if k[0] != port
            }
        busy.discard(key)
