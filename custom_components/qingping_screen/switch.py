"""Switch platform for the Qingping Screen integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import QingpingScreenConfigEntry
from .api import QingpingScreenError
from .entity import QingpingScreenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QingpingScreenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the screen switch."""

    async_add_entities([QingpingScreenSwitch(entry)])


class QingpingScreenSwitch(QingpingScreenEntity, SwitchEntity):
    """Representation of the Qingping screen backlight."""

    _attr_translation_key = "screen"

    def __init__(self, entry: QingpingScreenConfigEntry) -> None:
        super().__init__(entry, "screen")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.screen_on

    async def async_turn_on(self, **kwargs: object) -> None:
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        try:
            await self.coordinator.async_set_screen_state(enabled)
        except QingpingScreenError as err:
            raise HomeAssistantError(
                "Failed to change the Qingping screen state"
            ) from err
