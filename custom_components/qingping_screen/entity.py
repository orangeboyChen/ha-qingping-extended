"""Base entity for the Qingping Screen integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import QingpingScreenConfigEntry
from .const import CONF_DEVICE_NAME, DOMAIN
from .coordinator import QingpingScreenCoordinator


class QingpingScreenEntity(CoordinatorEntity[QingpingScreenCoordinator]):
    """Base class shared by Qingping device entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: QingpingScreenConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        info = entry.runtime_data.device_info
        identifier = (
            entry.unique_id
            or info.serial
            or f"{entry.data['host']}:{entry.data['port']}"
        )
        self._attr_unique_id = f"{identifier}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=entry.data[CONF_DEVICE_NAME],
            manufacturer="Qingping",
            model=info.model or "Air Monitor 2",
        )
