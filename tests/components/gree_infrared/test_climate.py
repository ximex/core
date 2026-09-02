"""Tests for the Gree Infrared climate platform."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from infrared_protocols.commands.gree_ac import GreeAcMode
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry, mock_restore_cache, snapshot_platform
from tests.components.common import assert_availability_follows_source_entity
from tests.components.infrared import EMITTER_ENTITY_ID
from tests.components.infrared.common import MockInfraredEmitterEntity

CLIMATE_ENTITY_ID = "climate.sinclair_ac"


@pytest.fixture
def platforms() -> list[Platform]:
    """Return platforms to set up."""
    return [Platform.CLIMATE]


@pytest.mark.usefixtures("init_integration")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the climate entity is created with correct attributes."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)

    device_entry = device_registry.async_get_device_by_identifier(
        ("gree_infrared", mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert device_entry
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    for entity_entry in entity_entries:
        assert entity_entry.device_id == device_entry.id


@pytest.mark.usefixtures("init_integration")
async def test_set_hvac_mode_cool(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test setting HVAC mode to cool sends IR command."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["power"] is True
    assert cmd["mode"] == 0x01  # GreeCommand.MODE_COOL


@pytest.mark.usefixtures("init_integration")
async def test_set_hvac_mode_off(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test setting HVAC mode to off sends IR command with power=False."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["power"] is False


@pytest.mark.parametrize(
    ("hvac_mode", "expected_power", "expected_mode"),
    [
        (HVACMode.COOL, True, 0x01),
        (HVACMode.HEAT, True, 0x04),
        (HVACMode.DRY, True, 0x02),
        (HVACMode.FAN_ONLY, True, 0x03),
        (HVACMode.AUTO, True, 0x00),
        (HVACMode.OFF, False, 0x01),  # mode preserved as last active (cool)
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_set_hvac_mode_all(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    hvac_mode: HVACMode,
    expected_power: bool,
    expected_mode: int,
) -> None:
    """Test all HVAC modes send correct IR parameters."""
    # First set to cool so we have a known starting mode
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    mock_infrared_emitter_entity.send_command_calls.clear()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: hvac_mode},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["power"] is expected_power
    assert cmd["mode"] == expected_mode


@pytest.mark.usefixtures("init_integration")
async def test_set_temperature(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test setting temperature sends IR command."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_TEMPERATURE: 26},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["temperature"] == 26


@pytest.mark.parametrize(
    ("fan_mode", "expected_fan_speed"),
    [
        ("auto", 0x00),
        ("low", 0x01),
        ("medium", 0x02),
        ("high", 0x03),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_set_fan_mode(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    fan_mode: str,
    expected_fan_speed: int,
) -> None:
    """Test setting fan mode sends IR command."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_FAN_MODE: fan_mode},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["fan"] == expected_fan_speed


@pytest.mark.parametrize(
    ("swing_mode", "expected_swing_vertical"),
    [
        ("on", True),
        ("off", False),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_set_swing_mode(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    swing_mode: str,
    expected_swing_vertical: bool,
) -> None:
    """Test setting swing mode sends IR command."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_SWING_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_SWING_MODE: swing_mode},
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["swing_v"] is expected_swing_vertical


@pytest.mark.usefixtures("init_integration")
async def test_set_temperature_with_hvac_mode(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test setting temperature with HVAC mode in same call."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: CLIMATE_ENTITY_ID,
            ATTR_TEMPERATURE: 22,
            ATTR_HVAC_MODE: HVACMode.HEAT,
        },
        blocking=True,
    )

    assert len(mock_infrared_emitter_entity.send_command_calls) == 1
    cmd = mock_infrared_emitter_entity.send_command_calls[0]
    assert cmd["temperature"] == 22
    assert cmd["mode"] == 0x04  # HEAT
    assert cmd["power"] is True


@pytest.mark.usefixtures("init_integration")
async def test_state_attributes_after_set(
    hass: HomeAssistant,
) -> None:
    """Test state attributes are updated after setting values."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_TEMPERATURE: 22},
        blocking=True,
    )
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_FAN_MODE: "high"},
        blocking=True,
    )

    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_TEMPERATURE] == 22
    assert state.attributes[ATTR_FAN_MODE] == "high"


@pytest.mark.usefixtures("init_integration")
async def test_climate_availability_follows_ir_entity(
    hass: HomeAssistant,
) -> None:
    """Test climate entity becomes unavailable when IR entity is unavailable."""
    await assert_availability_follows_source_entity(
        hass, CLIMATE_ENTITY_ID, EMITTER_ENTITY_ID
    )


@pytest.mark.usefixtures("init_integration")
async def test_turn_on_and_off(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test turning on defaults to cool and turning off keeps the last active mode."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID},
        blocking=True,
    )

    cmd = mock_infrared_emitter_entity.send_command_calls[-1]
    assert cmd["power"] is True
    assert cmd["mode"] == GreeAcMode.COOL
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.COOL

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID},
        blocking=True,
    )

    cmd = mock_infrared_emitter_entity.send_command_calls[-1]
    assert cmd["power"] is False
    # The AC needs a mode in the frame even when powering off.
    assert cmd["mode"] == GreeAcMode.COOL
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state is not None
    assert state.state == HVACMode.OFF


@pytest.mark.parametrize(
    ("restored_state", "restored_attributes", "expected"),
    [
        pytest.param(
            HVACMode.COOL,
            {
                ATTR_FAN_MODE: "high",
                ATTR_SWING_MODE: "on",
                ATTR_TEMPERATURE: 29.0,
            },
            (HVACMode.COOL, "high", "on", 29.0),
            id="full_state",
        ),
        pytest.param(
            STATE_UNAVAILABLE,
            {},
            (HVACMode.OFF, "auto", "off", 24.0),
            id="unavailable_falls_back_to_defaults",
        ),
        pytest.param(
            STATE_UNKNOWN,
            {},
            (HVACMode.OFF, "auto", "off", 24.0),
            id="unknown_falls_back_to_defaults",
        ),
        pytest.param(
            HVACMode.HEAT_COOL,
            {ATTR_FAN_MODE: "turbo", ATTR_SWING_MODE: "both"},
            (HVACMode.OFF, "auto", "off", 24.0),
            id="unsupported_values_are_ignored",
        ),
    ],
)
async def test_state_restored_on_restart(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    mock_gree_command: None,
    platforms: list[Platform],
    restored_state: str,
    restored_attributes: dict[str, Any],
    expected: tuple[HVACMode, str, str, float],
) -> None:
    """Test the assumed state is restored, since infrared cannot read it back."""
    mock_restore_cache(
        hass, [State(CLIMATE_ENTITY_ID, restored_state, restored_attributes)]
    )
    mock_config_entry.add_to_hass(hass)

    with patch("homeassistant.components.gree_infrared.PLATFORMS", platforms):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    expected_mode, expected_fan, expected_swing, expected_temperature = expected
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state is not None
    assert state.state == expected_mode
    assert state.attributes[ATTR_FAN_MODE] == expected_fan
    assert state.attributes[ATTR_SWING_MODE] == expected_swing
    assert state.attributes[ATTR_TEMPERATURE] == expected_temperature


async def test_restored_mode_is_reused_when_turning_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    mock_gree_command: None,
    platforms: list[Platform],
) -> None:
    """Test the restored HVAC mode is the one sent in a later power-off frame."""
    mock_restore_cache(hass, [State(CLIMATE_ENTITY_ID, HVACMode.HEAT, {})])
    mock_config_entry.add_to_hass(hass)

    with patch("homeassistant.components.gree_infrared.PLATFORMS", platforms):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID},
        blocking=True,
    )

    cmd = mock_infrared_emitter_entity.send_command_calls[-1]
    assert cmd["power"] is False
    assert cmd["mode"] == GreeAcMode.HEAT


@pytest.mark.usefixtures("init_integration")
async def test_turn_on_while_already_on_repeats_the_current_mode(
    hass: HomeAssistant,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
) -> None:
    """Test turning on an already running AC repeats its mode instead of cooling."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )
    mock_infrared_emitter_entity.send_command_calls.clear()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID},
        blocking=True,
    )

    cmd = mock_infrared_emitter_entity.send_command_calls[-1]
    assert cmd["power"] is True
    assert cmd["mode"] == GreeAcMode.HEAT
