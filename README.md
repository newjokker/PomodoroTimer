# 🍅 番茄时钟 — macOS 菜单栏 Pomodoro Timer

一款轻量、优雅的 macOS 菜单栏番茄工作法计时器，基于 Python 和 [rumps](https://github.com/jaredks/rumps) 构建。

![Python](https://img.shields.io/badge/Python-3.6%2B-blue) ![Platform](https://img.shields.io/badge/platform-macOS-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green) ![Arch](https://img.shields.io/badge/arch-arm64-brightgreen)


> **⬇️ [下载最新版 v1.3.0](https://github.com/newjokker/PomodoroTimer/releases)** — 原生 ARM64，支持 Apple Silicon

---

## 功能特性

### 核心计时
- **标准番茄工作法**：25 分钟专注 + 5 分钟短休息
- **长休息**：每完成 4 个番茄后自动进入 15 分钟长休息
- **倒计时显示**：菜单栏实时显示剩余时间，并有 🍅 / ☕ 图标区分工作/休息状态

### 操作控制
| 操作 | 说明 |
|------|------|
| ▶ 开始专注 | 启动一个工作番茄 |
| ⏸ 暂停 / ▶ 继续 | 随时暂停并恢复当前计时 |
| ↺ 重置 | 重置到初始状态 |
| ⏭ 跳过 | 跳过当前阶段（工作或休息） |

### 个性化设置
所有设置自动保存至 `~/.pomodoro_timer.json`，下次启动自动恢复：
- **工作时长**：15 / 20 / 25 / 30 / 35 / 40 / 45 / 50 / 60 分钟可选
- **短休息时长**：5 / 10 / 15 / 20 / 25 / 30 分钟可选
- **长休息时长**：10 / 15 / 20 / 25 / 30 分钟可选
- **自动开始休息**：番茄完成后是否自动进入休息倒计时
- **静音模式**：开启后仅保留通知，不播放提示音
- **完成时弹窗**：可关闭阻塞式弹窗，仅保留系统通知
- **休息后自动工作**：休息结束自动进入下一个番茄

### 数据统计
- 📅 **今日统计**：今日番茄数 + 专注时长
- 📆 **本周统计**：本周累计番茄数和时长
- 🏆 **累计统计**：总番茄数、总专注时长（小时）
- 所有数据持久化，重启不丢失

### 提醒通知
- 番茄完成 / 休息结束时弹出 macOS 原生通知
- 同时播放系统提示音（Ping）

---

## 快速开始

### 前置要求
- macOS 操作系统
- Python 3.6+
- [rumps](https://github.com/jaredks/rumps) 库

### 安装与运行

```bash
# 1. 安装依赖
pip3 install rumps

# 2. 直接运行（开发者模式）
chmod +x pomodoro_timer.py
python3 pomodoro_timer.py
```

番茄图标会出现在 macOS 菜单栏右上角，点击即可开始使用。

### 打包为 macOS App

```bash
# 安装打包工具
pip3 install py2app

# 打包
python3 setup.py py2app

# 从 dist/ 目录运行
open dist/番茄时钟.app
```

### 生成图标

```bash
python3 make_icon.py
```

会在项目根目录生成 `icon.icns` 应用图标。

---

## 项目结构

```
番茄时钟/
├── pomodoro_timer.py    # 主程序 — 菜单栏番茄计时器
├── setup.py             # py2app 打包配置
├── pyproject.toml       # 项目元数据 + py2app 配置
├── Makefile             # 构建自动化（一键 dmg / release）
├── make_icon.py         # 图标生成脚本（纯 Python，无需 PIL）
├── icon.icns            # 生成的 macOS 应用图标
├── BUILD.md             # 详细构建指南（含故障排查）
├── CHANGELOG.md         # 版本更新日志
├── releases/            # 历史版本 DMG（已 .gitignore）
├── .gitignore
└── README.md
```

### 核心模块

**`pomodoro_timer.py`** — 主程序入口，包含：
- `PomodoroTimer` 类：继承 `rumps.App`，管理所有状态和 UI
- 状态机：`IDLE` → `WORK` → `BREAK` → ... 循环
- 配置持久化：JSON 文件自动读写
- 系统通知：`rumps.notification` + `afplay` 音效

**`setup.py`** — py2app 配置，支持打包为独立的 `.app` 包：
- 无 Dock 图标（`LSUIElement: True`），仅菜单栏运行
- 国际化设置为中文

**`make_icon.py`** — 纯 Python 图标生成器，无需安装 PIL/Pillow：
- 使用原始 PNG 编码生成番茄图标
- 包含番茄主体、绿色叶蒂、高光反射

---

## 技术细节

### 配置持久化
- 文件位置：`~/.pomodoro_timer.json`
- 保存内容：工作时长、休息时长、自动休息开关、统计数据
- 写入时机：设置变更时（设置页面）、番茄完成时、退出应用时

### 状态机

```
                ┌──────────┐
                │   IDLE   │
                └────┬─────┘
                     │ ▶ 开始专注
                     ↓
           ┌─────────────────┐
    ┌──────│     WORK (🍅)    │──────┐
    │      └────────┬────────┘      │
    │ 暂停          │ 完成          │ 跳过
    ↓               ↓               ↓
┌─────────┐  ┌──────────┐     ┌──────────┐
│WORK_PAUSE│  │  BREAK   │     │  BREAK   │
│  ⏸ 暂停  │  │  ☕ 休息  │     │  ☕ 休息  │
└────┬────┘  └──────────┘     └──────────┘
     │ ▶ 继续         │ 完成 / 跳过
     ↓                 ↓
  ┌─────────┐     ┌──────────┐
  │  WORK   │     │  WORK    │  ← 回到工作
  └─────────┘     └──────────┘
```

---

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

| 版本 | 日期 | 说明 |
|------|------|------|
| [v1.3.0](https://github.com/newjokker/PomodoroTimer/releases/tag/v1.3.0) | 2026-06-08 | 弹窗开关、休息后自动工作 |
| [v1.1.0](https://github.com/newjokker/PomodoroTimer/releases/tag/v1.1.0) | 2026-06-08 | ARM64 原生、按日统计、静音模式 |

---

## 构建

从源码构建 `.app` / `.dmg`，详见 **[BUILD.md](BUILD.md)**。

```bash
make dmg        # 一键构建 DMG（自动检查架构、生成图标、打包）
make app        # 仅构建 .app
make release    # 打标签 + 构建 DMG
```

> ⚠️ **必须使用 ARM64 原生 Python**。Makefile 已内置架构检查，x86_64 Python 会被自动拦截。在 Apple Silicon Mac 上用 x86_64 Python 构建的 App 无法运行（除非安装 Rosetta 2）。

---

## 许可证

MIT License

---

## 作者

Created with 🍅 by [newjokker](https://github.com/newjokker)
