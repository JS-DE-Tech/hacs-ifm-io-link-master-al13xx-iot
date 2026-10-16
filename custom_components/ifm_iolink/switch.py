"""Pin 4 outputs, usable only on ports already configured as DO at the master."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .api import IfmError
from .digital import set_output
from .entity import IfmEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(IfmPin4Switch(entry.runtime_data, port)
                       for port in range(1, entry.runtime_data.identity["ports"] + 1))


class IfmPin4Switch(IfmEntity, SwitchEntity):
    def __init__(self, coordinator, port):
        super().__init__(coordinator, port, kind="pin4_do", name="Digitalausgang (Pin 4)")

    @property
    def available(self):
        return super().available and self.port_data.get("mode") == 2

    @property
    def is_on(self):
        return self.port_data.get("pin4") if self.available else None

    async def async_turn_on(self, **kwargs):
        await self._write(True)

    async def async_turn_off(self, **kwargs):
        await self._write(False)

    async def _write(self, on):
        try:
            await set_output(self.hass, self.coordinator, int(self.port), on)
        except (ValueError, IfmError) as err:
            self.async_write_ha_state()
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
