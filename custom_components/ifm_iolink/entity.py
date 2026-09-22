"""Shared device and availability information."""

from datetime import timedelta

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import IfmError
from .const import DOMAIN
from .decoder import encode_parameter
from .parameters import read_parameter_value

PARAMETER_SCAN_INTERVAL = timedelta(hours=1)


def _device_info(coordinator, port, assignment, profile):
    serial = coordinator.identity["serial"]
    return DeviceInfo(
        identifiers={(DOMAIN, f"{serial}_port_{port}")},
        via_device=(DOMAIN, serial),
        name=assignment.get("name") or f"{coordinator.entry.title} · Port {port}",
        manufacturer=profile.get("manufacturer") or "IO-Link",
        model=profile.get("model") or "Unbekannt",
        suggested_area=assignment.get("location") or None,
    )


class IfmEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, port, field=None, kind="connection", name="Verbindung"):
        super().__init__(coordinator)
        self.port = str(port)
        self.field = field
        assignment = coordinator.entry.options.get("ports", {}).get(self.port, {})
        self.profile_id = assignment.get("profile", "unknown")
        profile = coordinator.library.all.get(self.profile_id, {})
        serial = coordinator.identity["serial"]
        suffix = f"{self.profile_id}_{field['key']}" if field else kind
        self._attr_unique_id = f"{serial}_port_{port}_{suffix}"
        self._attr_device_info = _device_info(coordinator, port, assignment, profile)
        self._attr_name = field.get("name", field["key"]) if field else name

    @property
    def port_data(self):
        return (self.coordinator.data or {}).get(self.port, {})

    @property
    def available(self):
        return super().available and (
            self.field is None
            or (
                self.port_data.get("connected", False)
                and not self.port_data.get("error")
                and self.port_data.get("values", {}).get(self.field["key"]) is not None
            )
        )

    @property
    def extra_state_attributes(self):
        assignment = self.port_data.get("assignment", {})
        return {
            "port": int(self.port),
            "profile": self.profile_id,
            "location": assignment.get("location", ""),
            "purpose": assignment.get("purpose", ""),
            "decode_error": self.port_data.get("error"),
        }


class IfmMasterEntity(CoordinatorEntity):
    """A master-level diagnostic value (voltage, current, power, temperature, status)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self.key = key
        serial = coordinator.identity["serial"]
        self._attr_unique_id = f"{serial}_master_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})
        self._attr_name = name

    @property
    def value(self):
        return self.coordinator.master_diagnostics.get(self.key)

    @property
    def available(self):
        return super().available and self.value is not None


class IfmParameterEntity(CoordinatorEntity):
    """A manufacturer parameter, opted into per port in the panel's parameter list.

    Read acyclically on its own schedule (independent of the fast PDIN poll), on
    startup, and after every write, since acyclic reads are comparatively slow and
    values change rarely.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, port, parameter):
        super().__init__(coordinator)
        self.port = str(port)
        self.parameter = parameter
        assignment = coordinator.entry.options.get("ports", {}).get(self.port, {})
        profile_id = assignment.get("profile", "unknown")
        profile = coordinator.library.all.get(profile_id, {})
        serial = coordinator.identity["serial"]
        self._attr_unique_id = f"{serial}_port_{port}_{profile_id}_param_{parameter['index']}"
        self._attr_device_info = _device_info(coordinator, port, assignment, profile)
        self._attr_name = parameter["name"]
        self._value = None
        self._parameter_available = False
        self._unsub_interval = None

    @property
    def port_data(self):
        return (self.coordinator.data or {}).get(self.port, {})

    @property
    def available(self):
        return super().available and self.port_data.get("connected", False) and self._parameter_available

    @property
    def extra_state_attributes(self):
        return {
            "port": int(self.port),
            "index": self.parameter["index"],
            "description": self.parameter.get("description", ""),
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsub_interval = async_track_time_interval(self.hass, self._scheduled_refresh, PARAMETER_SCAN_INTERVAL)
        await self.async_update_ha_state(force_refresh=True)

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None

    async def _scheduled_refresh(self, now):
        await self.async_update_ha_state(force_refresh=True)

    async def async_update(self):
        if not self.port_data.get("connected"):
            self._parameter_available = False
            return
        try:
            result = await read_parameter_value(self.coordinator, int(self.port), self.parameter)
        except (ValueError, IfmError):
            self._parameter_available = False
            return
        self._value = result["value"]
        self._parameter_available = True

    async def write_value(self, value):
        """Write a new value, then re-read to confirm what the device actually accepted."""
        try:
            raw = encode_parameter(self.parameter, value)
            await self.coordinator.client.write_parameter(int(self.port), self.parameter["index"], raw)
        except (ValueError, IfmError) as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_update_ha_state(force_refresh=True)
