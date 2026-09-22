"""Preview-bound port-mode switch (IO-Link <-> digital output), mirroring restore.py's flow."""

from .api import data_value

MODE_NAMES = {0: "Deaktiviert", 1: "Digitaleingang (DI)", 2: "Digitalausgang (DO)", 3: "IO-Link"}
SWITCHABLE_MODES = (0, 1, 2, 3)


async def prepare_mode_change(coordinator, port, target_mode):
    if target_mode not in SWITCHABLE_MODES:
        raise ValueError("Ungültiger Zielmodus")
    item = (coordinator.data or {}).get(str(port))
    if item is None:
        raise ValueError("Port nicht gefunden; Master lädt noch")
    current_mode = item.get("mode")
    if current_mode is None:
        raise ValueError("Aktueller Portmodus konnte nicht gelesen werden")
    if current_mode == target_mode:
        raise ValueError("Port ist bereits in diesem Modus")
    return {
        "port": port,
        "current_mode": current_mode,
        "target_mode": target_mode,
        "device_connected": bool(item.get("connected")),
        "assignment_name": item.get("assignment", {}).get("name", ""),
        "profile_id": item.get("profile"),
    }


async def execute_mode_change(coordinator, port, plan, still_current=lambda: True):
    path = f"/iolinkmaster/port[{port}]/mode"
    item = (coordinator.data or {}).get(str(port))
    if not still_current() or item is None or item.get("mode") != plan["current_mode"]:
        raise ValueError("Portmodus hat sich seit der Vorschau geändert; neue Vorschau erstellen")
    await coordinator.client.write_port_mode(port, plan["target_mode"])
    if not still_current():
        raise ValueError("Master wurde seit der Vorschau neu geladen oder entfernt")
    response = await coordinator.client.multi([path])
    actual = data_value(response, path)
    if actual != plan["target_mode"]:
        raise ValueError("Rücklesewert stimmt nicht mit dem Zielmodus überein")
    if actual == 2:
        # pdout has no defined value until the first write; default it to off rather than
        # leaving it in the error state the device reports for an unwritten DO output.
        await coordinator.client.write_port_output(port, False)
    coordinator.condition_values = {key: value for key, value in coordinator.condition_values.items() if key[0] != port}
    coordinator.metadata_at = None
    return {"port": port, "mode": actual}
