"""The DO output state on Pin 4/C-Q, once a port has been switched to digital-output mode."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .api import IfmError
from .entity import IfmEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities(
        IfmPin4Switch(coordinator, port)
        for port in range(1, coordinator.identity["ports"] + 1)
        if entry.options.get("ports", {}).get(str(port), {}).get("mode") == 2
    )


class IfmPin4Switch(IfmEntity, SwitchEntity):
    def __init__(self, coordinator, port):
        super().__init__(coordinator, port, kind="pin4_do", name="Digitalausgang (Pin 4)")

    @property
    def is_on(self):
        # pdout reads as an error until the first write after a mode switch; treat that as "off".
        return self.port_data.get("pdout") not in (None, "00")

    @property
    def available(self):
        return super().available and self.port_data.get("assignment", {}).get("mode") == 2

    async def async_turn_on(self, **kwargs):
        await self._write(True)

    async def async_turn_off(self, **kwargs):
        await self._write(False)

    async def _write(self, on):
        try:
            await self.coordinator.client.write_port_output(int(self.port), on)
        except (ValueError, IfmError) as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
