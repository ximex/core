"""Common fixtures for the Gree Infrared tests."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from homeassistant.components.gree_infrared import PLATFORMS
from homeassistant.components.gree_infrared.const import (
    CONF_INFRARED_ENTITY_ID,
    DOMAIN,
    GreeDeviceModel,
)
from homeassistant.const import CONF_MODEL, Platform
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry
from tests.components.infrared import EMITTER_ENTITY_ID as MOCK_INFRARED_ENTITY_ID
from tests.components.infrared.common import MockInfraredEmitterEntity


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="01JTEST0000000000000000000",
        title="Sinclair AC via Test IR emitter",
        data={
            CONF_MODEL: GreeDeviceModel.SINCLAIR,
            CONF_INFRARED_ENTITY_ID: MOCK_INFRARED_ENTITY_ID,
        },
        unique_id=f"gree_ir_sinclair_{MOCK_INFRARED_ENTITY_ID}",
    )


@pytest.fixture
def platforms() -> list[Platform]:
    """Return platforms to set up."""
    return PLATFORMS


@pytest.fixture
def mock_gree_command() -> Generator[None]:
    """Patch GreeAcSinclairCommand to return its kwargs dict for assertion.

    This allows tests to assert on the high-level parameters
    rather than the raw IR timings.
    """
    with patch(
        "homeassistant.components.gree_infrared.coordinator.GreeAcSinclairCommand",
        side_effect=lambda **kwargs: kwargs,
    ):
        yield


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_infrared_emitter_entity: MockInfraredEmitterEntity,
    mock_gree_command: None,
    platforms: list[Platform],
) -> MockConfigEntry:
    """Set up the Gree Infrared integration for testing."""
    mock_config_entry.add_to_hass(hass)

    with patch("homeassistant.components.gree_infrared.PLATFORMS", platforms):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry
