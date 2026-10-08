"""Qingping Screen integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import STORAGE_DIR

from .api import QingpingDeviceInfo, QingpingScreenClient, QingpingScreenError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import QingpingScreenCoordinator


@dataclass(slots=True)
class QingpingScreenData:
    """Runtime data for a Qingping Screen config entry."""

    client: QingpingScreenClient
    coordinator: QingpingScreenCoordinator
    device_info: QingpingDeviceInfo


type QingpingScreenConfigEntry = ConfigEntry[QingpingScreenData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QingpingScreenConfigEntry,
) -> bool:
    """Set up Qingping Screen from a config entry."""

    client = QingpingScreenClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        hass.config.path(STORAGE_DIR, f"{DOMAIN}_adbkey"),
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    coordinator = QingpingScreenCoordinator(hass, client, scan_interval)

    try:
        await coordinator.async_config_entry_first_refresh()
        device_info = await client.async_get_device_info()
    except QingpingScreenError as err:
        await client.async_close()
        raise ConfigEntryNotReady(str(err)) from err
    except Exception:
        await client.async_close()
        raise

    entry.runtime_data = QingpingScreenData(
        client=client,
        coordinator=coordinator,
        device_info=device_info,
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: QingpingScreenConfigEntry,
) -> bool:
    """Unload a Qingping Screen config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.async_close()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant,
    entry: QingpingScreenConfigEntry,
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
