"""Config flow for Gree Infrared integration."""

from typing import Any, override

import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_MODEL
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_INFRARED_ENTITY_ID, DOMAIN, GreeDeviceModel

MODEL_NAMES: dict[GreeDeviceModel, str] = {
    GreeDeviceModel.SINCLAIR: "Sinclair",
}


def _unique_id(user_input: dict[str, Any]) -> str:
    """Build the entry unique id from the selected model and emitter."""
    return f"gree_ir_{user_input[CONF_MODEL]}_{user_input[CONF_INFRARED_ENTITY_ID]}"


class GreeIrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Gree IR."""

    VERSION = 1

    @callback
    def _schema(self) -> vol.Schema:
        """Build the selection schema for the model and emitter."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_MODEL): SelectSelector(
                SelectSelectorConfig(
                    options=[model.value for model in GreeDeviceModel],
                    translation_key=CONF_MODEL,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                EntitySelectorConfig(
                    domain=INFRARED_DOMAIN,
                    include_entities=async_get_emitters(self.hass),
                )
            ),
        }
        return vol.Schema(schema_dict)

    def _title(self, user_input: dict[str, Any]) -> str:
        """Name the entry after the model and the emitter it transmits through."""
        entity_id = user_input[CONF_INFRARED_ENTITY_ID]
        ent_reg = er.async_get(self.hass)
        registry_entry = ent_reg.async_get(entity_id)
        entity_name = (
            registry_entry.name or registry_entry.original_name or entity_id
            if registry_entry
            else entity_id
        )
        model_name = MODEL_NAMES[GreeDeviceModel(user_input[CONF_MODEL])]
        return f"{model_name} AC via {entity_name}"

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_emitters")

        if user_input is not None:
            await self.async_set_unique_id(_unique_id(user_input))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._title(user_input), data=user_input
            )

        return self.async_show_form(step_id="user", data_schema=self._schema())

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the selected model and emitter."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_emitters")

        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_MODEL: user_input[CONF_MODEL],
                    CONF_INFRARED_ENTITY_ID: user_input[CONF_INFRARED_ENTITY_ID],
                }
            )
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                unique_id=_unique_id(user_input),
                title=self._title(user_input),
                data=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                self._schema(), self._get_reconfigure_entry().data
            ),
        )
