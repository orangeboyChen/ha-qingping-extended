"""ADB client for a Qingping screen."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from adb_shell import exceptions as adb_exceptions
from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

from .const import (
    ADB_AUTH_TIMEOUT,
    ADB_COMMAND_TIMEOUT,
    ADB_CONNECT_TIMEOUT,
    APPLICATION_PROCESS,
    BACKLIGHT_OFF,
    BACKLIGHT_ON,
    BACKLIGHT_POWER_PATH,
    DISPLAY_PAGE_BY_INDEX,
    DISPLAY_PAGE_INDEXES,
    DISPLAY_PAGE_KEY,
    SETTINGS_PATH,
)

_LOGGER = logging.getLogger(__name__)


class QingpingScreenError(Exception):
    """Base error for the Qingping screen client."""


class QingpingScreenCannotConnectError(QingpingScreenError):
    """Raised when the ADB connection or command fails."""


class QingpingScreenInvalidStateError(QingpingScreenError):
    """Raised when the device returns an unexpected backlight state."""


class QingpingScreenCommandError(QingpingScreenError):
    """Raised when a command ran but did not complete successfully."""


class _AdbDevice(Protocol):
    """Subset of adb-shell used by the integration."""

    @property
    def available(self) -> bool: ...

    async def connect(self, **kwargs: object) -> bool: ...

    async def shell(self, command: str, **kwargs: object) -> str: ...

    async def close(self) -> None: ...


type DeviceFactory = Callable[[str, int, float], _AdbDevice]


@dataclass(frozen=True, slots=True)
class QingpingDeviceInfo:
    """Device metadata returned over ADB."""

    serial: str | None
    model: str | None


def _default_device_factory(host: str, port: int, timeout: float) -> _AdbDevice:
    return AdbDeviceTcpAsync(
        host,
        port,
        default_transport_timeout_s=timeout,
    )


def _load_or_create_signer(key_path: Path) -> PythonRSASigner:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.is_file() or not Path(f"{key_path}.pub").is_file():
        keygen(str(key_path))
    return PythonRSASigner.FromRSAKeyPath(str(key_path))


class QingpingScreenClient:
    """Manage an ADB connection and control the screen backlight."""

    def __init__(
        self,
        host: str,
        port: int,
        key_path: str,
        *,
        device_factory: DeviceFactory = _default_device_factory,
    ) -> None:
        self.host = host
        self.port = port
        self._key_path = Path(key_path)
        self._device_factory = device_factory
        self._device: _AdbDevice | None = None
        self._signer: PythonRSASigner | None = None
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        """Connect to the device, waiting for ADB authorization if needed."""

        async with self._lock:
            await self._async_connect_locked()

    async def async_close(self) -> None:
        """Close the current ADB connection."""

        async with self._lock:
            await self._async_close_locked()

    async def async_get_screen_state(self) -> bool:
        """Return the actual screen state reported by the backlight driver."""

        response = await self._async_shell(f"cat {BACKLIGHT_POWER_PATH}")
        return self._parse_screen_state(response)

    async def async_set_screen_state(self, enabled: bool) -> bool:
        """Set the backlight state and return the value read back from the device."""

        value = BACKLIGHT_ON if enabled else BACKLIGHT_OFF
        response = await self._async_shell(
            f"printf '%s' '{value}' > {BACKLIGHT_POWER_PATH}"
            f" && cat {BACKLIGHT_POWER_PATH}"
        )
        actual_state = self._parse_screen_state(response)
        if actual_state is not enabled:
            raise QingpingScreenInvalidStateError(
                "Backlight state did not match the requested state"
            )
        return actual_state

    async def async_get_display_page(self) -> str:
        """Return the display page selected in the application settings."""

        response = await self._async_shell(
            f"sed -n 's/^{DISPLAY_PAGE_KEY}=//p' {SETTINGS_PATH} | head -n 1"
        )
        return self._parse_display_page(response)

    async def async_set_display_page(self, option: str) -> str:
        """Persist a display page and restart the application without write-back."""

        try:
            index = DISPLAY_PAGE_INDEXES[option]
        except KeyError as err:
            raise QingpingScreenInvalidStateError(
                f"Unsupported display page: {option!r}"
            ) from err

        response = await self._async_shell(self._display_page_command(index))
        success_marker = f"__PAGE__:{index}"
        if success_marker not in response.splitlines():
            detail = response.strip() or "no response"
            raise QingpingScreenCommandError(f"Failed to change display page: {detail}")
        return option

    async def async_get_device_info(self) -> QingpingDeviceInfo:
        """Read stable device metadata when available."""

        serial = self._clean_property(await self._async_shell("getprop ro.serialno"))
        model = self._clean_property(
            await self._async_shell("getprop ro.product.model")
        )
        return QingpingDeviceInfo(serial=serial, model=model)

    async def _async_shell(self, command: str) -> str:
        async with self._lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    await self._async_connect_locked()
                    assert self._device is not None
                    return await self._device.shell(
                        command,
                        read_timeout_s=ADB_COMMAND_TIMEOUT,
                        timeout_s=ADB_COMMAND_TIMEOUT,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as err:  # adb-shell exposes several transport errors
                    last_error = err
                    await self._async_close_locked()
                    if attempt == 1 or not self._is_connection_error(err):
                        break

            raise QingpingScreenCannotConnectError(
                f"ADB command failed for {self.host}:{self.port}"
            ) from last_error

    async def _async_connect_locked(self) -> None:
        if self._device is not None and self._device.available:
            return

        if self._signer is None:
            self._signer = await asyncio.to_thread(
                _load_or_create_signer,
                self._key_path,
            )

        device = self._device_factory(self.host, self.port, ADB_CONNECT_TIMEOUT)
        try:
            connected = await device.connect(
                rsa_keys=[self._signer],
                transport_timeout_s=ADB_CONNECT_TIMEOUT,
                auth_timeout_s=ADB_AUTH_TIMEOUT,
                read_timeout_s=ADB_CONNECT_TIMEOUT,
            )
        except asyncio.CancelledError:
            await self._async_close_device(device)
            raise
        except Exception as err:
            await self._async_close_device(device)
            raise QingpingScreenCannotConnectError(
                f"Could not connect to {self.host}:{self.port}"
            ) from err

        if not connected:
            await self._async_close_device(device)
            raise QingpingScreenCannotConnectError(
                f"Could not connect to {self.host}:{self.port}"
            )
        self._device = device

    async def _async_close_locked(self) -> None:
        device, self._device = self._device, None
        if device is not None:
            await self._async_close_device(device)

    async def _async_close_device(self, device: _AdbDevice) -> None:
        try:
            await device.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.debug(
                "Error closing ADB connection to %s:%s",
                self.host,
                self.port,
                exc_info=True,
            )

    @staticmethod
    def _parse_screen_state(response: str) -> bool:
        value = response.strip()
        if value == BACKLIGHT_ON:
            return True
        if value == BACKLIGHT_OFF:
            return False
        raise QingpingScreenInvalidStateError(
            f"Unexpected value from {BACKLIGHT_POWER_PATH}: {value!r}"
        )

    @staticmethod
    def _parse_display_page(response: str) -> str:
        value = response.strip()
        try:
            index = int(value)
            return DISPLAY_PAGE_BY_INDEX[index]
        except (KeyError, ValueError) as err:
            raise QingpingScreenInvalidStateError(
                f"Unexpected value for {DISPLAY_PAGE_KEY}: {value!r}"
            ) from err

    @staticmethod
    def _display_page_command(index: int) -> str:
        return f"""PID=$(pidof {APPLICATION_PROCESS} | awk '{{print $1}}')
INI={SETTINGS_PATH}
INDEX={index}
DONE=0
BACKED_UP=0
rollback() {{
    if [ "$DONE" != 1 ]; then
        if [ "$BACKED_UP" = 1 ]; then
            cp -a "$INI.bak" "$INI" 2>/dev/null
            sync
        fi
        if [ -n "$PID" ]; then
            kill -CONT "$PID" 2>/dev/null
        fi
    fi
}}
fail() {{
    printf '__ERROR__:%s\\n' "$1"
    exit 1
}}
trap rollback EXIT
trap 'exit 1' HUP INT TERM
[ -n "$PID" ] || fail process_not_found
kill -STOP "$PID" || fail freeze_failed
cp -a "$INI" "$INI.bak" || fail backup_failed
BACKED_UP=1
if grep -q '^{DISPLAY_PAGE_KEY}=' "$INI"; then
    if ! sed -i "s/^{DISPLAY_PAGE_KEY}=.*/{DISPLAY_PAGE_KEY}=$INDEX/" "$INI"; then
        fail update_failed
    fi
else
    if ! sed -i "/^\\[application\\]$/a {DISPLAY_PAGE_KEY}=$INDEX" "$INI"; then
        fail insert_failed
    fi
fi
ACTUAL=$(sed -n 's/^{DISPLAY_PAGE_KEY}=//p' "$INI" | head -n 1)
[ "$ACTUAL" = "$INDEX" ] || fail verify_failed
sync || fail sync_failed
kill -KILL "$PID" || fail restart_failed
DONE=1
trap - EXIT HUP INT TERM
printf '__PAGE__:%s\\n' "$ACTUAL"
"""

    @staticmethod
    def _clean_property(response: str) -> str | None:
        value = response.strip()
        if not value or value.lower() in {"unknown", "null"}:
            return None
        return value

    @staticmethod
    def _is_connection_error(err: Exception) -> bool:
        return isinstance(
            err,
            (
                adb_exceptions.AdbConnectionError,
                adb_exceptions.AdbTimeoutError,
                adb_exceptions.TcpTimeoutException,
                QingpingScreenCannotConnectError,
                BrokenPipeError,
                ConnectionError,
                OSError,
                RuntimeError,
            ),
        )
