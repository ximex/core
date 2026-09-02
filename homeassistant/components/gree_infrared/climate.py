"""Climate platform for Gree Infrared integration."""

from typing import Any, override

from infrared_protocols.commands.gree_ac import (
    MAX_TEMP,
    MIN_TEMP,
    GreeAcFanSpeed,
    GreeAcMode,
)

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_OFF,
    SWING_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import GreeIrConfigEntry
from .coordinator import GreeAcDevice
from .entity import GreeIrEntity

PARALLEL_UPDATES = 1

HVAC_MODE_TO_GREE: dict[HVACMode, GreeAcMode] = {
    HVACMode.AUTO: GreeAcMode.AUTO,
    HVACMode.COOL: GreeAcMode.COOL,
    HVACMode.DRY: GreeAcMode.DRY,
    HVACMode.FAN_ONLY: GreeAcMode.FAN_ONLY,
    HVACMode.HEAT: GreeAcMode.HEAT,
}

FAN_MODE_TO_GREE: dict[str, GreeAcFanSpeed] = {
    FAN_AUTO: GreeAcFanSpeed.AUTO,
    FAN_LOW: GreeAcFanSpeed.LOW,
    FAN_MEDIUM: GreeAcFanSpeed.MEDIUM,
    FAN_HIGH: GreeAcFanSpeed.HIGH,
}

GREE_TO_HVAC_MODE: dict[GreeAcMode, HVACMode] = {
    value: key for key, value in HVAC_MODE_TO_GREE.items()
}

GREE_TO_FAN_MODE: dict[GreeAcFanSpeed, str] = {
    value: key for key, value in FAN_MODE_TO_GREE.items()
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GreeIrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gree IR climate from config entry."""
    async_add_entities([GreeIrClimate(entry.runtime_data)])


class GreeIrClimate(GreeIrEntity, ClimateEntity, RestoreEntity):
    """Gree IR climate entity."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = float(MIN_TEMP)
    _attr_max_temp = float(MAX_TEMP)
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_swing_modes = [SWING_OFF, SWING_ON]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    def __init__(self, device: GreeAcDevice) -> None:
        """Initialize Gree IR climate."""
        super().__init__(device, unique_id_suffix="climate")

    @property
    @override
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        state = self.device.state
        return GREE_TO_HVAC_MODE[state.mode] if state.power else HVACMode.OFF

    @property
    @override
    def target_temperature(self) -> float:
        """Return the target temperature."""
        return float(self.device.state.temperature)

    @property
    @override
    def fan_mode(self) -> str:
        """Return the fan mode."""
        return GREE_TO_FAN_MODE[self.device.state.fan]

    @property
    @override
    def swing_mode(self) -> str:
        """Return the swing mode."""
        return SWING_ON if self.device.state.swing_v else SWING_OFF

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the assumed state, as infrared cannot read it back from the AC."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            return

        changes: dict[str, Any] = {}
        if last_state.state in self._attr_hvac_modes:
            hvac_mode = HVACMode(last_state.state)
            changes["power"] = hvac_mode is not HVACMode.OFF
            if hvac_mode is not HVACMode.OFF:
                changes["mode"] = HVAC_MODE_TO_GREE[hvac_mode]
        if (fan_mode := last_state.attributes.get(ATTR_FAN_MODE)) in FAN_MODE_TO_GREE:
            changes["fan"] = FAN_MODE_TO_GREE[fan_mode]
        if (
            swing_mode := last_state.attributes.get(ATTR_SWING_MODE)
        ) in self._attr_swing_modes:
            changes["swing_v"] = swing_mode == SWING_ON
        if (temperature := last_state.attributes.get(ATTR_TEMPERATURE)) is not None:
            changes["temperature"] = int(float(temperature))

        self.device.async_restore(**changes)

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode is HVACMode.OFF:
            await self.device.async_send(self._context, power=False)
            return
        await self.device.async_send(
            self._context, power=True, mode=HVAC_MODE_TO_GREE[hvac_mode]
        )

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        changes: dict[str, Any] = {}
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            changes["temperature"] = int(temperature)
        if (hvac_mode_str := kwargs.get(ATTR_HVAC_MODE)) is not None:
            hvac_mode = HVACMode(hvac_mode_str)
            changes["power"] = hvac_mode is not HVACMode.OFF
            if hvac_mode is not HVACMode.OFF:
                changes["mode"] = HVAC_MODE_TO_GREE[hvac_mode]
        await self.device.async_send(self._context, **changes)

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        await self.device.async_send(self._context, fan=FAN_MODE_TO_GREE[fan_mode])

    @override
    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode."""
        await self.device.async_send(self._context, swing_v=swing_mode == SWING_ON)

    @override
    async def async_turn_on(self) -> None:
        """Turn the AC on."""
        if self.hvac_mode is HVACMode.OFF:
            await self.device.async_send(
                self._context, power=True, mode=GreeAcMode.COOL
            )
            return
        await self.device.async_send(self._context, power=True)

    @override
    async def async_turn_off(self) -> None:
        """Turn the AC off."""
        await self.device.async_send(self._context, power=False)
