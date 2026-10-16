"""Keep registry identities while suspending entities unused by a port mode."""

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

MARKER = "disabled_for_port_mode"


def sync_mode_entities(registry, entities, coordinator, requirements):
    """Only undo our own disables; unknown modes never change registry state.

    Options persist ownership across reloads. USER/DEVICE/CONFIG_ENTRY and
    unrelated INTEGRATION disables are deliberately left alone. HA handles
    removal and the debounced config-entry reload when re-enabling entities.
    """
    if not coordinator.last_update_success:
        return
    for entity in entities:
        requirement = requirements.get(entity.unique_id)
        if entity.platform != DOMAIN or requirement is None:
            continue
        port, required_mode = requirement
        mode = (coordinator.data or {}).get(str(port), {}).get("mode")
        if type(mode) is not int or mode not in (0, 1, 2, 3):
            continue
        options = dict(entity.options.get(DOMAIN, {}))
        owned = options.get(MARKER) is True
        if entity.disabled_by not in (None, "integration"):
            if owned:
                options.pop(MARKER)
                registry.async_update_entity_options(entity.entity_id, DOMAIN, options or None)
            continue
        if mode != required_mode and entity.disabled_by is None:
            options[MARKER] = True
            registry.async_update_entity_options(entity.entity_id, DOMAIN, options)
            registry.async_update_entity(entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        elif mode == required_mode and owned:
            # Enable first: a crash before clearing the marker is recoverable.
            if entity.disabled_by == "integration":
                registry.async_update_entity(entity.entity_id, disabled_by=None)
            options.pop(MARKER)
            registry.async_update_entity_options(entity.entity_id, DOMAIN, options or None)
