"""Config flow for the Qingping Screen integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import STORAGE_DIR

from .api import (
    QingpingScreenCannotConnectError,
    QingpingScreenClient,
    QingpingScreenInvalidStateError,
)
from .const import (
    CONF_DEVICE_NAME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class QingpingScreenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Qingping Screen config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure a Qingping screen over ADB."""

        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})

            client = QingpingScreenClient(
                host,
                port,
                self.hass.config.path(STORAGE_DIR, f"{DOMAIN}_adbkey"),
            )
            try:
                await client.async_get_screen_state()
                info = await client.async_get_device_info()
            except QingpingScreenInvalidStateError:
                errors["base"] = "unsupported_state"
            except QingpingScreenCannotConnectError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception(
                    "Unexpected error connecting to Qingping device at %s:%s",
                    host,
                    port,
                )
                errors["base"] = "unknown"
            else:
                unique_id = info.serial or f"{host.lower()}:{port}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME].strip() or DEFAULT_NAME,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME].strip()
                        or DEFAULT_NAME,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )
            finally:
                await client.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_NAME): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> QingpingScreenOptionsFlow:
        """Return the options flow handler."""

        return QingpingScreenOptionsFlow()


class QingpingScreenOptionsFlow(OptionsFlow):
    """Handle Qingping Screen options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Change polling options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
