"""Writable manufacturer parameters with a continuous range, opted into per port in the panel."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory

from .decoder import numeric_range, parameter_entity_kind
from .entity import IfmParameterEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = []
    for port in range(1, coordinator.identity["ports"] + 1):
        assigned = entry.options.get("ports", {}).get(str(port), {}).get("profile")
        profile = coordinator.library.all.get(assigned, {})
        parameters = {p["index"]: p for p in profile.get("parameters", [])}
        selected = entry.options.get("ports", {}).get(str(port), {}).get("entities", [])
        entities.extend(
            IfmParameterNumber(coordinator, port, parameters[index])
            for index in selected
            if index in parameters and parameter_entity_kind(parameters[index]) == "number"
        )
    async_add_entities(entities)


class IfmParameterNumber(IfmParameterEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, port, parameter):
        super().__init__(coordinator, port, parameter)
        field = parameter["decoder"]["fields"][0]
        self._attr_native_unit_of_measurement = field.get("unit") or None
        self._attr_native_step = abs(field.get("scale", 1)) or 1
        self._attr_native_min_value, self._attr_native_max_value = numeric_range(field)

    @property
    def native_value(self):
        return self._value

    async def async_set_native_value(self, value):
        await self.write_value(value)
