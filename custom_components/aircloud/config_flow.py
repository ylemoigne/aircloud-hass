"""Config flow for Hitachi Air Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import aircloudy.api
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hitachi Air Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()

                await aircloudy.api.perform_login(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )
            except aircloudy.ConnectionFailed:
                errors["base"] = "connection_failed"
            except aircloudy.AuthenticationFailedException:
                errors["base"] = "authentication_failed"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )
