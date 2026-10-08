"""Constants for the Qingping Screen integration."""

from homeassistant.const import Platform

DOMAIN = "qingping_screen"

DEFAULT_NAME = "Qingping Air Monitor 2"
DEFAULT_PORT = 5555
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 2
MAX_SCAN_INTERVAL = 300

CONF_DEVICE_NAME = "device_name"

BACKLIGHT_POWER_PATH = "/sys/class/backlight/backlight/bl_power"
BACKLIGHT_ON = "0"
BACKLIGHT_OFF = "4"

APPLICATION_PROCESS = "QingSnow2App"
SETTINGS_PATH = "/data/etc/setting.ini"
DISPLAY_PAGE_KEY = "current_main_page_index"
DISPLAY_PAGE_INDEXES = {
    "summary": 0,
    "settings": 1,
    "app": 2,
    "air_data": 3,
}
DISPLAY_PAGE_OPTIONS = list(DISPLAY_PAGE_INDEXES)
DISPLAY_PAGE_BY_INDEX = {
    index: option for option, index in DISPLAY_PAGE_INDEXES.items()
}

ADB_CONNECT_TIMEOUT = 10.0
ADB_AUTH_TIMEOUT = 30.0
ADB_COMMAND_TIMEOUT = 10.0

PLATFORMS = [Platform.SELECT, Platform.SWITCH]
