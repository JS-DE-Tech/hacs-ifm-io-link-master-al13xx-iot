"""Shared device and availability information."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .replacement import registry_serial


class IfmEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, port, field=None, *, kind="connection", name="Verbindung"):
        super().__init__(coordinator)
        self.port = str(port)
        self.field = field
        assignment = coordinator.entry.options.get("ports", {}).get(self.port, {})
        self.profile_id = assignment.get("profile", "unknown")
        profile = coordinator.library.all.get(self.profile_id, {})
        # Decorative DI/DO metadata never participates in entity unique IDs.
        if (coordinator.data or {}).get(self.port, {}).get("mode") in (1, 2):
            profile = coordinator.library.all.get(assignment.get("digital_profile"), {})
        serial = registry_serial(coordinator.entry)
        suffix = f"{self.profile_id}_{field['key']}" if field else kind
        self._attr_unique_id = f"{serial}_port_{port}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{serial}_port_{port}")},
            name=assignment.get("name") or (profile.get("name") if profile.get("kind") == "digital" else None)
            or f"{coordinator.entry.title} · Port {port}",
            manufacturer=profile.get("manufacturer") or "IO-Link",
            model=profile.get("model") or "Unbekannt",
            suggested_area=assignment.get("location") or None,
        )
        if "via_device_id" in DeviceInfo.__annotations__:
            self._attr_device_info["via_device_id"] = coordinator.master_device_id
        else:
            # HA 2025.7 supports only the identifier form in DeviceInfo.
            # Keep this compatibility branch off the current HA API path.
            self._attr_device_info["via_device"] = (DOMAIN, serial)
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
