"""Select platform for the Qingping Screen integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import QingpingScreenConfigEntry
from .api import QingpingScreenError
from .const import DISPLAY_PAGE_OPTIONS
from .entity import QingpingScreenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QingpingScreenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the display page select."""

    async_add_entities([QingpingDisplayPageSelect(entry)])


class QingpingDisplayPageSelect(QingpingScreenEntity, SelectEntity):
    """Select the page shown by QingSnow2App."""

    _attr_translation_key = "display_page"
    _attr_options = DISPLAY_PAGE_OPTIONS

    def __init__(self, entry: QingpingScreenConfigEntry) -> None:
        super().__init__(entry, "display_page")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.display_page

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(f"Unsupported display page: {option}")
        if option == self.current_option:
            return
        try:
            await self.coordinator.async_set_display_page(option)
        except QingpingScreenError as err:
            raise HomeAssistantError(
                "Failed to change the Qingping display page"
            ) from err
