from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_PASSWORD,
    CONF_PROVIDER,
    CONF_USERNAME,
    DOMAIN,
    PROVIDER_GOUSTO,
    PROVIDERS,
)
from .providers.gousto import GoustoProvider
from .providers.green_chef import GreenChefProvider

_LOGGER = logging.getLogger(__name__)

_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROVIDER): vol.In(PROVIDERS),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class FoodBoxConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            provider_id: str = user_input[CONF_PROVIDER]
            username: str = user_input[CONF_USERNAME]
            password: str = user_input[CONF_PASSWORD]

            provider = (
                GoustoProvider(session, username, password)
                if provider_id == PROVIDER_GOUSTO
                else GreenChefProvider(session, username, password)
            )

            try:
                authenticated = await provider.authenticate()
                if not authenticated:
                    errors["base"] = "invalid_auth"
                else:
                    await self.async_set_unique_id(f"{provider_id}_{username}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"{PROVIDERS[provider_id]} ({username})",
                        data=user_input,
                    )
            except Exception:
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=_SCHEMA,
            errors=errors,
        )
