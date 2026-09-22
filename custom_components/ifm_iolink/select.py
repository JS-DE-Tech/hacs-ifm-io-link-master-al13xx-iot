"""Writable manufacturer parameters with a fixed set of accepted values, opted into per port in the panel."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory

from .decoder import parameter_entity_kind, select_values
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
            IfmParameterSelect(coordinator, port, parameters[index])
            for index in selected
            if index in parameters and parameter_entity_kind(parameters[index]) == "select"
        )
    async_add_entities(entities)


def _label(value, unit):
    text = f"{value:g}"
    return f"{text} {unit}" if unit else text


class IfmParameterSelect(IfmParameterEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, port, parameter):
        super().__init__(coordinator, port, parameter)
        field = parameter["decoder"]["fields"][0]
        unit = field.get("unit", "")
        self._values = select_values(field)
        self._attr_options = [_label(value, unit) for value in self._values]
        self._unit = unit

    @property
    def current_option(self):
        return None if self._value is None else _label(self._value, self._unit)

    async def async_select_option(self, option):
        await self.write_value(self._values[self._attr_options.index(option)])
