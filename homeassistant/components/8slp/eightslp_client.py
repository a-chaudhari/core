from datetime import datetime, timedelta
import logging

from .eightslp_api import BedSide, BedPowerStatus, EightSleepAPI

_LOGGER = logging.getLogger(__name__)


class BedStatus:
    _side: BedSide
    status: BedPowerStatus
    temperature: int
    _user_id: str

    def __init__(
        self,
        side: BedSide,
        status: BedPowerStatus,
        temperature: int,
        user_id: str,
        target: int,
    ):
        self.status = status
        self.temperature = temperature
        self.target = target
        self._side = side
        self._user_id = user_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def side(self) -> BedSide:
        return self._side


class Client:
    _access_token: str
    _refresh_token: str
    _account_user_id: str
    _expires_at: datetime
    _bed_name: str

    sides = dict[BedSide, BedStatus]()

    def __init__(self, refresh_token: str, user_id: str):
        if refresh_token is not None and user_id is None:
            raise Exception("user_id is required with refresh_token")

        self._refresh_token = refresh_token
        self._access_token = None
        self._expires_at = datetime.now() - timedelta(0, 100)
        self._account_user_id = user_id

    def initialize(self):
        user = EightSleepAPI.get_user(self._account_user_id, self._token())
        device = EightSleepAPI.get_device(user.current_device, self._token())
        guest_side = (
            BedSide.Left if user.current_side == BedSide.Right else BedSide.Right
        )
        guest_user_id = f"guest-{user.current_device}-{guest_side.value}"
        names = EightSleepAPI.get_device_names(self._account_user_id, self._token())
        self._bed_name = names[user.current_device]
        if user.current_side == BedSide.Left:
            self.sides[BedSide.Left] = BedStatus(
                BedSide.Left,
                device.left_status,
                device.left_current,
                self._account_user_id,
                device.left_target,
            )
            self.sides[BedSide.Right] = BedStatus(
                BedSide.Right,
                device.right_status,
                device.right_current,
                guest_user_id,
                device.right_target,
            )
        else:
            self.sides[BedSide.Left] = BedStatus(
                BedSide.Left,
                device.left_status,
                device.left_current,
                guest_user_id,
                device.left_target,
            )
            self.sides[BedSide.right] = BedStatus(
                BedSide.Right,
                device.right_status,
                device.right_current,
                self._account_user_id,
                device.right_target,
            )

    def refresh_state(self) -> None:
        user = EightSleepAPI.get_user(self._account_user_id, self._token())
        device = EightSleepAPI.get_device(user.current_device, self._token())
        self.sides[BedSide.Right].status = device.right_status
        self.sides[BedSide.Right].temperature = device.right_current
        self.sides[BedSide.Right].target = device.right_target
        self.sides[BedSide.Left].status = device.left_status
        self.sides[BedSide.Left].temperature = device.left_current
        self.sides[BedSide.Left].target = device.left_target

    def set_temp(self, side: BedSide, temperature: int) -> None:
        state = self.sides[side]
        send_power_on = True if state.status == BedPowerStatus.Off else False
        EightSleepAPI.set_temperature(
            state.user_id, temperature, self._token(), send_power_on
        )

    def _token(self) -> str:
        if datetime.now() > self._expires_at:
            res = EightSleepAPI.refresh(self._refresh_token)
            self._access_token = res.access_token
            self._expires_at = datetime.now() + timedelta(0, res.expires_in - 100)
        return self._access_token

    def set_power(self, side: BedSide, target_state: BedPowerStatus) -> None:
        state = self.sides[side]
        _LOGGER.info("changing power")
        if target_state == BedPowerStatus.Off:
            EightSleepAPI.turn_off(state.user_id, self._token())
        else:
            EightSleepAPI.turn_on(state.user_id, self._token())

    @property
    def bed_name(self) -> str:
        return self._bed_name
