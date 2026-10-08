# Qingping Extended for Home Assistant

English | [简体中文](README.zh-CN.md)

An unofficial Home Assistant custom integration that controls the screen of a
Qingping Air Monitor 2 over wireless ADB.

## Features

- A screen switch backed by the device's actual backlight state.
- A display-page selector for the summary, settings, app, and air-data pages.
- Configurable local polling from 2 to 300 seconds.
- Automatic ADB reconnect and RSA key management.
- Verified writes instead of optimistic state updates.

The screen switch reads and writes:

```text
/sys/class/backlight/backlight/bl_power
```

The integration treats `0` as on and `4` as off. Any other value is reported
as an invalid device state.

The display-page selector reads `current_main_page_index` from
`/data/etc/setting.ini`:

| Page | Value |
|---|---:|
| Summary | `0` |
| Settings | `1` |
| App | `2` |
| Air data | `3` |

When changing the page, the integration freezes `QingSnow2App`, backs up and
updates the configuration, verifies and syncs the new value, and kills the old
process without allowing it to write stale settings during shutdown. If any
step fails, it restores the backup and resumes the old process.

## Requirements

- Wireless ADB is enabled on the Qingping device.
- Home Assistant can reach TCP port 5555 on the device.
- The ADB shell can read and write the backlight sysfs node and
  `/data/etc/setting.ini`.
- The ADB shell can signal the `QingSnow2App` process.

## Installation with HACS

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=orangeboyChen&repository=ha-qingping-extended&category=integration)

Alternatively, add the repository manually:

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add `https://github.com/orangeboyChen/ha-qingping-extended` as an
   **Integration** repository.
5. Install **Qingping Screen** and restart Home Assistant.

## Manual installation

Copy `custom_components/qingping_screen` to the `custom_components` directory
inside your Home Assistant configuration directory, then restart Home
Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Qingping Screen**, and enter the device address, ADB port, device name, and
polling interval.

The first connection may show an RSA authorization prompt on the device. The
setup flow waits up to 30 seconds for approval.

## Disclaimer

This project is an unofficial community integration and is not affiliated
with, endorsed by, or supported by Qingping. It relies on device-specific,
undocumented files and process behavior that may change with firmware updates.
Use it at your own risk.

## License

MIT
