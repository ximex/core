"""Common entity for Gree Infrared integration."""

from typing import override

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.const import CONF_MODEL
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, GreeDeviceModel
from .coordinator import GreeAcDevice

MODEL_MANUFACTURERS: dict[GreeDeviceModel, str] = {
    GreeDeviceModel.SINCLAIR: "Sinclair",
}

MODEL_DEVICE_NAMES: dict[GreeDeviceModel, str] = {
    GreeDeviceModel.SINCLAIR: "Sinclair AC",
}


class GreeIrEntity(InfraredEmitterConsumerEntity):
    """Gree IR base entity.

    Tracks availability of the underlying infrared emitter and keeps the entity
    in sync with the shared assumed AC state.
    """

    _attr_has_entity_name = True
    _attr_assumed_state = True

    def __init__(self, device: GreeAcDevice, unique_id_suffix: str) -> None:
        """Initialize Gree IR entity."""
        self.device = device
        self._infrared_emitter_entity_id = device.emitter_entity_id
        self._attr_unique_id = f"{device.entry.entry_id}_{unique_id_suffix}"
        model = GreeDeviceModel(device.entry.data[CONF_MODEL])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.entry.entry_id)},
            name=MODEL_DEVICE_NAMES[model],
            manufacturer=MODEL_MANUFACTURERS[model],
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Subscribe to shared state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(self.device.async_add_listener(self._handle_device_update))

    @callback
    def _handle_device_update(self) -> None:
        """Write the state after the shared state changed."""
        self.async_write_ha_state()
