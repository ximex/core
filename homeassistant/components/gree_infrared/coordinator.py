"""Shared assumed AC state for the Gree Infrared integration."""

from dataclasses import asdict, dataclass, replace
from typing import Any

from infrared_protocols.commands.gree_ac import (
    GreeAcAir,
    GreeAcFanSpeed,
    GreeAcMode,
    GreeAcSinclairCommand,
)

from homeassistant.components.infrared import async_send_command
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Context, HomeAssistant, callback

from .const import CONF_INFRARED_ENTITY_ID

DEFAULT_TEMPERATURE = 24


@dataclass(frozen=True)
class GreeAcState:
    """Every field of a Gree frame, as last sent.

    Field names match the ``GreeAcSinclairCommand`` keyword arguments, so the
    whole state converts to a command in one step.
    """

    power: bool = False
    mode: GreeAcMode = GreeAcMode.AUTO
    temperature: int = DEFAULT_TEMPERATURE
    fan: GreeAcFanSpeed = GreeAcFanSpeed.AUTO
    swing_v: bool = False
    sleep: bool = False
    timer_hours: float | None = None
    humidity: bool = False
    light: bool = False
    anion: bool = False
    save: bool = False
    air: GreeAcAir = GreeAcAir.OFF

    def to_command(self) -> GreeAcSinclairCommand:
        """Build the IR command carrying this state."""
        return GreeAcSinclairCommand(**asdict(self))


class GreeAcDevice:
    """The assumed state of one AC, shared by every entity of a config entry.

    A Gree frame always carries the complete state, so changing one field means
    transmitting all of them. This holds the single copy every entity reads from
    and writes to.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the device state."""
        self.hass = hass
        self.entry = entry
        self.state = GreeAcState()
        self.emitter_entity_id: str = entry.data[CONF_INFRARED_ENTITY_ID]
        self._listeners: list[CALLBACK_TYPE] = []

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Subscribe an entity to state changes, returning an unsubscribe callback."""
        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def async_update_listeners(self) -> None:
        """Tell every entity to write its new state."""
        for update_callback in self._listeners:
            update_callback()

    @callback
    def async_restore(self, **changes: Any) -> None:
        """Apply restored fields without transmitting them."""
        self.state = replace(self.state, **changes)

    async def async_send(self, context: Context | None = None, **changes: Any) -> None:
        """Apply changes to the state and transmit the resulting frame."""
        self.state = replace(self.state, **changes)
        await async_send_command(
            self.hass, self.emitter_entity_id, self.state.to_command(), context=context
        )
        self.async_update_listeners()
