"""Platform for sensor integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .eightslp_client import Client, BedStatus, BedPowerStatus

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    client = hass.data[DOMAIN][config_entry.entry_id]
    beds = []
    for status in client.sides.values():
        beds.append(
            EightSleepClimate(client, status, hass.config.units.temperature_unit, hass)
        )
    async_add_entities(beds, update_before_add=True)


class EightSleepClimate(ClimateEntity):
    # static attributes
    _attr_max_temp = 10
    _attr_min_temp = -10
    _attr_target_temperature_step = 1
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_precision = 1.0

    # fixed attributes
    _attr_name = ""
    _attr_unique_id = ""
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT

    # dynamic attributes
    _attr_target_temperature = 0
    _attr_current_temperature = 0
    _attr_hvac_mode = HVACMode.OFF
    _attr_hvac_action = HVACAction.OFF

    def __init__(
        self,
        client: Client,
        status: BedStatus,
        temp_units: UnitOfTemperature,
        hass: HomeAssistant,
    ):
        self._attr_name = f"{client.bed_name} - {status.side.name}"
        self._attr_unique_id = f"{client.bed_name} - {status.user_id}"
        self._attr_temperature_unit = temp_units

        self._client = client
        self._side = status.side
        self._hass = hass

        self._update_status(self._client.sides[self._side])

    async def async_update(self) -> None:
        await self._hass.async_add_executor_job(self._client.refresh_state)
        self._update_status(self._client.sides[self._side])

    def _update_status(self, status: BedStatus) -> None:
        self._attr_target_temperature = status.target
        self._attr_current_temperature = status.temperature
        self._attr_hvac_mode = (
            HVACMode.HEAT_COOL if status.status == BedPowerStatus.On else HVACMode.OFF
        )
        if self._attr_hvac_mode == HVACMode.HEAT_COOL:
            if status.target == status.temperature:
                self._attr_hvac_action = HVACAction.IDLE
            elif status.target > status.temperature:
                self._attr_hvac_action = HVACAction.HEATING
            else:
                self._attr_hvac_action = HVACAction.COOLING
        else:
            self._attr_hvac_action = HVACAction.OFF

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        _LOGGER.info(f"set hvac mode: {hvac_mode}")
        target_state = (
            BedPowerStatus.On if hvac_mode == HVACMode.HEAT_COOL else BedPowerStatus.Off
        )
        await self._hass.async_add_executor_job(
            self._client.set_power, self._side, target_state
        )
        self._update_status(self._client.sides[self._side])

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE in kwargs:
            _LOGGER.info(f"set temp to {kwargs[ATTR_TEMPERATURE]}")
            await self._hass.async_add_executor_job(
                self._client.set_temp, self._side, kwargs[ATTR_TEMPERATURE]
            )
            self._update_status(self._client.sides[self._side])
