"""Data coordinator for the Qingping Screen integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    QingpingScreenClient,
    QingpingScreenError,
    QingpingScreenInvalidStateError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QingpingScreenState:
    """State read from the Qingping device."""

    screen_on: bool
    display_page: str | None


class QingpingScreenCoordinator(DataUpdateCoordinator[QingpingScreenState]):
    """Poll the actual screen and display-page state."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: QingpingScreenClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> QingpingScreenState:
        try:
            screen_on = await self.client.async_get_screen_state()
            try:
                display_page = await self.client.async_get_display_page()
            except QingpingScreenInvalidStateError as err:
                _LOGGER.debug("Unable to read the configured display page: %s", err)
                display_page = None
            return QingpingScreenState(
                screen_on=screen_on,
                display_page=display_page,
            )
        except QingpingScreenError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_screen_state(self, enabled: bool) -> None:
        """Set and immediately publish the verified device state."""

        actual_state = await self.client.async_set_screen_state(enabled)
        self.async_set_updated_data(replace(self.data, screen_on=actual_state))

    async def async_set_display_page(self, option: str) -> None:
        """Set and immediately publish the verified display page."""

        actual_page = await self.client.async_set_display_page(option)
        self.async_set_updated_data(replace(self.data, display_page=actual_page))
