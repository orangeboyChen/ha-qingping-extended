"""Tests for the Qingping screen ADB client."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable

import pytest

from custom_components.qingping_screen.api import (
    QingpingScreenCannotConnectError,
    QingpingScreenClient,
    QingpingScreenCommandError,
    QingpingScreenInvalidStateError,
)


class FakeAdbDevice:
    """In-memory ADB device used by the unit tests."""

    def __init__(
        self,
        responses: Iterable[str | Exception],
        *,
        connect_error: Exception | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.available = False
        self.responses = iter(responses)
        self.connect_error = connect_error
        self.close_error = close_error
        self.commands: list[str] = []
        self.connect_calls = 0
        self.close_calls = 0

    async def connect(self, **kwargs: object) -> bool:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error
        self.available = True
        return True

    async def shell(self, command: str, **kwargs: object) -> str:
        self.commands.append(command)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response

    async def close(self) -> None:
        self.close_calls += 1
        self.available = False
        if self.close_error is not None:
            raise self.close_error


def make_client(devices: list[FakeAdbDevice]) -> QingpingScreenClient:
    """Create a client backed only by fake devices."""

    device_iter = iter(devices)
    client = QingpingScreenClient(
        "192.0.2.1",
        5555,
        "/tmp/not-used-adbkey",
        device_factory=lambda host, port, timeout: next(device_iter),
    )
    client._signer = object()  # type: ignore[assignment]
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize(("response", "expected"), [("0\n", True), ("4\r\n", False)])
async def test_get_screen_state_uses_device_value(
    response: str,
    expected: bool,
) -> None:
    device = FakeAdbDevice([response])
    client = make_client([device])

    assert await client.async_get_screen_state() is expected
    assert device.commands == ["cat /sys/class/backlight/backlight/bl_power"]


@pytest.mark.asyncio
async def test_set_screen_state_reads_back_value() -> None:
    device = FakeAdbDevice(["0\n"])
    client = make_client([device])

    assert await client.async_set_screen_state(True) is True
    assert device.commands == [
        "printf '%s' '0' > /sys/class/backlight/backlight/bl_power"
        " && cat /sys/class/backlight/backlight/bl_power"
    ]


@pytest.mark.asyncio
async def test_unexpected_state_is_not_guessed() -> None:
    client = make_client([FakeAdbDevice(["2\n"])])

    with pytest.raises(QingpingScreenInvalidStateError):
        await client.async_get_screen_state()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("index", "option"),
    [("0", "summary"), ("1", "settings"), ("2", "app"), ("3", "air_data")],
)
async def test_get_display_page_uses_setting_value(index: str, option: str) -> None:
    device = FakeAdbDevice([f"{index}\n"])
    client = make_client([device])

    assert await client.async_get_display_page() == option
    assert device.commands == [
        "sed -n 's/^current_main_page_index=//p' /data/etc/setting.ini | head -n 1"
    ]


@pytest.mark.asyncio
async def test_set_display_page_uses_safe_restart_sequence() -> None:
    device = FakeAdbDevice(["__PAGE__:3\n"])
    client = make_client([device])

    assert await client.async_set_display_page("air_data") == "air_data"
    command = device.commands[0]
    assert "pidof QingSnow2App" in command
    assert 'kill -STOP "$PID"' in command
    assert 'cp -a "$INI" "$INI.bak"' in command
    assert "current_main_page_index=$INDEX" in command
    assert 'kill -KILL "$PID"' in command
    assert 'kill -CONT "$PID"' in command
    assert "trap 'exit 1' HUP INT TERM" in command


def test_display_page_script_has_valid_shell_syntax() -> None:
    command = QingpingScreenClient._display_page_command(3)

    result = subprocess.run(
        ["/bin/sh", "-n"],
        input=command,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_set_display_page_requires_success_marker() -> None:
    client = make_client([FakeAdbDevice(["__ERROR__:process_not_found\n"])])

    with pytest.raises(QingpingScreenCommandError, match="process_not_found"):
        await client.async_set_display_page("summary")


@pytest.mark.asyncio
async def test_connection_error_reconnects_once() -> None:
    first = FakeAdbDevice([BrokenPipeError()])
    second = FakeAdbDevice(["4\n"])
    client = make_client([first, second])

    assert await client.async_get_screen_state() is False
    assert first.close_calls == 1
    assert second.connect_calls == 1


@pytest.mark.asyncio
async def test_initial_connection_error_retries_once() -> None:
    first = FakeAdbDevice([], connect_error=OSError("unreachable"))
    second = FakeAdbDevice(["0\n"])
    client = make_client([first, second])

    assert await client.async_get_screen_state() is True
    assert first.connect_calls == 1
    assert first.close_calls == 1
    assert second.connect_calls == 1


@pytest.mark.asyncio
async def test_close_error_does_not_mask_connection_error() -> None:
    first = FakeAdbDevice(
        [],
        connect_error=OSError("unreachable"),
        close_error=OSError("close failed"),
    )
    second = FakeAdbDevice([], connect_error=OSError("still unreachable"))
    client = make_client([first, second])

    with pytest.raises(QingpingScreenCannotConnectError):
        await client.async_get_screen_state()


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    device = FakeAdbDevice(["0"])
    client = make_client([device])
    await client.async_get_screen_state()

    await client.async_close()
    await client.async_close()

    assert device.close_calls == 1
