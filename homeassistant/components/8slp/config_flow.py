"""Config flow for EightSleep2 integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .eightslp_api import EightSleepAPI

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    data = None

    # def __init__(self, host: str) -> None:
    #     """Initialize."""
    #     self.host = host

    async def authenticate(
        self, username: str, password: str, hass: HomeAssistant
    ) -> bool:
        """Test if we can authenticate with the host."""
        res = await hass.async_add_executor_job(EightSleepAPI.login, username, password)
        if res.user_id is not None:
            self.data = res
            _LOGGER.info("setting auth data var")
            return True
        else:
            return False


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:

    hub = PlaceholderHub()

    if not await hub.authenticate(data["username"], data["password"], hass):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {
        "user_id": hub.data.user_id,
        "access_token": hub.data.access_token,
        "refresh_token": hub.data.refresh_token,
        "expires_at": datetime.now() + timedelta(0, hub.data.expires_in),
        "username": data["username"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EightSleep2."""

    VERSION = 1
    data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.data["AUTH"] = info
                await self.async_set_unique_id(info["user_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"EightSleepAccount: {info['username']}", data=info
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
