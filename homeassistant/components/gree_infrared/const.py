"""Constants for the Gree Infrared integration."""

from enum import StrEnum

DOMAIN = "gree_infrared"
CONF_INFRARED_ENTITY_ID = "infrared_entity_id"


class GreeDeviceModel(StrEnum):
    """Gree device model variants."""

    SINCLAIR = "sinclair"
