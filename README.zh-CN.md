# Qingping Extended for Home Assistant

[English](README.md) | 简体中文

这是一个非官方 Home Assistant 自定义集成，通过无线 ADB 控制青萍空气检测仪 2 的屏幕。

## 功能

- `switch`：控制屏幕背光，并读取设备实际状态。
- `select`：选择汇总页、设置页、App 页或空气数据页。
- 支持 2–300 秒的本地轮询。
- 自动维护 ADB RSA 密钥，并在连接中断后重连。
- 写入后回读验证，不使用乐观状态。

屏幕开关直接读取和写入：

```text
/sys/class/backlight/backlight/bl_power
```

- `0`：屏幕开启
- `4`：屏幕关闭

展示页面从 `/data/etc/setting.ini` 的 `current_main_page_index` 读取：

| 页面 | 配置值 |
|---|---:|
| 汇总页 | `0` |
| 设置页 | `1` |
| App 页 | `2` |
| 空气数据页 | `3` |

切换页面时，集成会冻结 `QingSnow2App`、备份并修改配置、校验新值、执行 `sync`，最后使用 `KILL` 终止旧进程，避免旧实例在退出时写回旧配置。若任一步骤失败，集成会恢复备份并继续运行旧进程。

## 前提条件

1. 青萍设备已开启无线 ADB。
2. Home Assistant 能访问设备的 TCP 5555 端口。
3. ADB shell 能读写背光 sysfs 节点和 `/data/etc/setting.ini`。
4. ADB shell 能向 `QingSnow2App` 发送信号。
5. 建议为设备配置固定 IP 或 DHCP 地址保留。

## 使用 HACS 安装

[![在 Home Assistant 中打开此 HACS 仓库](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=orangeboyChen&repository=ha-qingping-extended&category=integration)

也可以手动添加自定义仓库：

1. 打开 Home Assistant 中的 HACS。
2. 进入“集成”。
3. 打开右上角菜单并选择“自定义存储库”。
4. 添加 `https://github.com/orangeboyChen/ha-qingping-extended`，类别选择“集成”。
5. 安装 **Qingping Screen** 并重启 Home Assistant。

## 手动安装

将 `custom_components/qingping_screen` 复制到 Home Assistant 配置目录下的 `custom_components`，然后重启 Home Assistant。

## 配置

进入 **设置 → 设备与服务 → 添加集成**，搜索 **Qingping Screen**，填写设备地址、ADB 端口、设备名称和轮询间隔。

首次连接时设备可能出现 RSA 授权提示。配置流程最多等待 30 秒，请在设备上允许连接。

## 免责声明

本项目是非官方社区集成，与青萍不存在关联，也未获得青萍认可或支持。集成依赖设备特定且未公开记录的文件和进程行为，这些行为可能随固件更新而改变。使用风险由用户自行承担。

## 许可证

MIT
