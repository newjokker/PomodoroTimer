# 更新日志

## [1.0.0] — 2026-06-08

### ✨ 首发

第一个可用版本，打包为 macOS 独立 App + DMG 安装包。

**功能：**
- 标准番茄工作法：25min 专注 + 5min 短休息
- 长休息：每 4 个番茄后 15min
- 可自定义工作/短休息/长休息时长（菜单栏设置）
- 暂停、继续、跳过、重置
- 番茄完成时系统通知 + 提示音
- 统计追踪（完成番茄数 + 累计专注时间）
- 设置持久化（~/.pomodoro_timer.json）

**技术栈：**
- Python rumps（macOS 菜单栏框架）
- py2app 打包为独立 App
- hdiutil 创建 DMG 安装包

**已修复的问题：**
- 修复 `libffi.8.dylib` 缺失导致的 Launch Error（setup.py 添加 `frameworks`）
