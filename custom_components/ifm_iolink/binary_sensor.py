"""Port connection, process status flags and the master's own supervision status."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory

from .entity import IfmEntity, IfmMasterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = [IfmMasterStatus(coordinator)]
    for port in range(1, coordinator.identity["ports"] + 1):
        entities.append(IfmBinarySensor(coordinator, port))
        entities.append(IfmPin2Sensor(coordinator, port))
        assignment = entry.options.get("ports", {}).get(str(port), {})
        if assignment.get("mode") == 1:
            entities.append(IfmPin4DiSensor(coordinator, port))
        assigned = assignment.get("profile")
        profile = coordinator.library.all.get(assigned, {})
        entities.extend(
            IfmBinarySensor(coordinator, port, field) for field in profile.get("fields", []) if field["type"] == "bool"
        )
    async_add_entities(entities)


class IfmBinarySensor(IfmEntity, BinarySensorEntity):
    def __init__(self, coordinator, port, field=None):
        super().__init__(coordinator, port, field)
        self._attr_device_class = (field.get("device_class") or None) if field else "connectivity"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        if self.field is None:
            return self.port_data.get("connected", False)
        return self.port_data.get("values", {}).get(self.field["key"])


class IfmPin2Sensor(IfmEntity, BinarySensorEntity):
    """Pin 2 digital input; always active on the master regardless of port mode or assigned profile."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, port):
        super().__init__(coordinator, port, kind="pin2", name="Digitaleingang (Pin 2)")

    @property
    def is_on(self):
        value = self.port_data.get("pin2")
        return None if value is None else bool(value)


class IfmPin4DiSensor(IfmEntity, BinarySensorEntity):
    """Pin 4/C-Q digital input, once a port has been switched to digital-input mode."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, port):
        super().__init__(coordinator, port, kind="pin4_di", name="Digitaleingang (Pin 4)")

    @property
    def is_on(self):
        value = self.port_data.get("pin4")
        return None if value is None else bool(value)

    @property
    def available(self):
        return super().available and self.port_data.get("assignment", {}).get("mode") == 1


class IfmMasterStatus(IfmMasterEntity, BinarySensorEntity):
    """On when the master reports a non-zero supervision status (e.g. undervoltage, overload)."""

    _attr_device_class = "problem"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "status", "Status")

    @property
    def is_on(self):
        return bool(self.value)

    @property
    def extra_state_attributes(self):
        return {"supervisionstatus": self.value}
