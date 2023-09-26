"""Stateless api commands and data structures sent to eightsleep backend."""

from enum import Enum
import json
import logging
from typing import NamedTuple, Optional

import requests

CLIENT_ID = "0894c7f33bb94800a03f1f4df13a4f38"
CLIENT_SECRET = "f0954a3ed5763ba3d06834c73731a32f15f168f47d4f164751275def86db0c76"
AUTH_URI = "https://auth-api.8slp.net/v1/tokens"
API_BASE_URI = "https://client-api.8slp.net/v1"
APP_BASE_URI = "https://app-api.8slp.net/v1"


class BedPowerStatus(Enum):
    """Represents the power state of a bed side."""

    On = 1
    Off = 0


class BedSide(Enum):
    """Enum to represent the sides of a bed."""

    Left = "left"
    Right = "right"
    Both = "both"


class LoginResponse(NamedTuple):
    """Response after logging in."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user_id: Optional[str]


class GetDeviceResponse(NamedTuple):
    """Response showing bed status."""

    left_status: BedPowerStatus
    left_target: int
    left_current: int
    left_duration: int
    right_status: BedPowerStatus
    right_target: int
    right_current: int
    right_duration: int


class GetUserResponse(NamedTuple):
    """Response showing user info."""

    device_ids: list[str]
    current_device: str
    current_side: BedSide


_LOGGER = logging.getLogger(__name__)


class EightSleepAPI:
    """Stateless api commands sent to eightsleep backend."""

    @staticmethod
    def _send_request(
        url: str,
        method: str,
        payload: object | None = None,
        auth_header: str | None = None,
    ) -> dict:
        headers = {"Content-Type": "application/json"}
        if auth_header is not None:
            headers["Authorization"] = "Bearer " + auth_header
        if object is None:
            response = requests.request(method, url, headers=headers, timeout=60)
        else:
            response = requests.request(
                method, url, headers=headers, data=json.dumps(payload), timeout=60
            )
        _LOGGER.debug(response.content)
        return json.loads(response.content)

    @staticmethod
    def login(username: str, password: str) -> LoginResponse:
        """Log into the service."""
        res = EightSleepAPI._send_request(
            AUTH_URI,
            "POST",
            {
                "username": username,
                "password": password,
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        return LoginResponse(
            res["access_token"],
            res["token_type"],
            res["expires_in"],
            res["refresh_token"],
            res["userId"],
        )

    @staticmethod
    def set_temperature(
        user_id: str, temperature: int, auth_token: str, power_on: bool = False
    ) -> None:
        """Set the temperature."""

        if power_on:
            payload = {
                "currentLevel": int(temperature * 10),
                "currentState": {"type": "smart"},
            }
        else:
            payload = {"currentLevel": int(temperature * 10)}

        EightSleepAPI._send_request(
            APP_BASE_URI + f"/users/{user_id}/temperature", "PUT", payload, auth_token
        )

    @staticmethod
    def turn_off(user_id: str, auth_token: str) -> None:
        """Turn off a bed side."""
        EightSleepAPI._send_request(
            API_BASE_URI + f"/users/{user_id}/temperature",
            "PUT",
            {"currentState": {"type": "off"}},
            auth_token,
        )

    @staticmethod
    def turn_on(user_id: str, auth_token: str) -> None:
        """Turn on a bed side."""
        EightSleepAPI._send_request(
            APP_BASE_URI + f"/users/{user_id}/temperature",
            "PUT",
            {"currentState": {"type": "smart"}},
            auth_token,
        )

    @staticmethod
    def get_user(user_id: str, auth_token: str) -> GetUserResponse:
        """Get user info."""
        res = EightSleepAPI._send_request(
            API_BASE_URI + f"/users/{user_id}", "GET", auth_header=auth_token
        )
        side = BedSide(res["user"]["currentDevice"]["side"])
        return GetUserResponse(
            res["user"]["devices"], res["user"]["currentDevice"]["id"], side
        )

    @staticmethod
    def get_device(device_id: str, auth_token: str) -> GetDeviceResponse:
        """Get device info."""
        res = EightSleepAPI._send_request(
            API_BASE_URI + f"/devices/{device_id}", "GET", auth_header=auth_token
        )
        dev = res["result"]
        left_status = BedPowerStatus.On if dev["leftNowHeating"] else BedPowerStatus.Off
        right_status = (
            BedPowerStatus.On if dev["rightNowHeating"] else BedPowerStatus.Off
        )
        return GetDeviceResponse(
            left_status,
            round(dev["leftTargetHeatingLevel"], -1) / 10,
            round(dev["leftHeatingLevel"], -1) / 10,
            dev["leftHeatingDuration"],
            right_status,
            round(dev["rightTargetHeatingLevel"], -1) / 10,
            round(dev["rightHeatingLevel"], -1) / 10,
            dev["rightHeatingDuration"],
        )

    @staticmethod
    def refresh(refresh_token: str) -> LoginResponse:
        """Pull latest data off server."""
        res = EightSleepAPI._send_request(
            AUTH_URI,
            "POST",
            {
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        return LoginResponse(
            res["access_token"],
            res["token_type"],
            res["expires_in"],
            res["refresh_token"],
            None,
        )

    @staticmethod
    def get_device_names(user_id: str, auth_token: str) -> dict[str, str]:
        """Get device names."""
        res = EightSleepAPI._send_request(
            APP_BASE_URI + f"/household/users/{user_id}/devices",
            "GET",
            auth_header=auth_token,
        )
        devs = res["devices"]
        output = dict[str, str]()
        for dev in devs:
            output[dev["deviceId"]] = dev["friendlyName"]
        return output
