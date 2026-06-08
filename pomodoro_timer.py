#!/usr/bin/env python3
"""
🍅 番茄时钟 - macOS 菜单栏 Pomodoro Timer
基于 rumps 实现的标准番茄工作法计时器

用法:
    chmod +x pomodoro_timer.py
    python3 pomodoro_timer.py

功能:
    - 标准番茄: 25min 工作 + 5min 休息
    - 长休息: 每4个番茄后 15min
    - 可自定义工作/短休息/长休息时间
    - 暂停/继续/跳过
    - 完成时系统通知 + 提示音
    - 统计数据追踪
    - 设置持久化（重启后保留）
"""

import rumps
import subprocess
import json
import os

# ═══════════════════════════════════════
#  默认配置
# ═══════════════════════════════════════
DEFAULT_WORK = 25
DEFAULT_SHORT_BREAK = 5
DEFAULT_LONG_BREAK = 15
POMODOROS_UNTIL_LONG_BREAK = 4

# 配置文件路径
CONFIG_DIR = os.path.expanduser("~")
CONFIG_FILE = os.path.join(CONFIG_DIR, ".pomodoro_timer.json")


class PomodoroTimer(rumps.App):
    """菜单栏番茄时钟"""

    def __init__(self):
        super().__init__("🍅 25:00", quit_button=None)

        # ── 从文件加载配置 ──
        config = self._load_config()

        # ── 状态 ──
        self.timer = rumps.Timer(self.on_tick, 1)
        self.state = "IDLE"  # IDLE | WORK | WORK_PAUSE | BREAK | BREAK_PAUSE
        self.work_minutes = config.get("work_minutes", DEFAULT_WORK)
        self.short_break_minutes = config.get("short_break_minutes", DEFAULT_SHORT_BREAK)
        self.long_break_minutes = config.get("long_break_minutes", DEFAULT_LONG_BREAK)
        self.seconds_left = self.work_minutes * 60
        self.completed_pomodoros = config.get("completed_pomodoros", 0)
        self.total_focus_minutes = config.get("total_focus_minutes", 0)
        self.auto_break = config.get("auto_break", True)

        # ── 更新菜单栏标题（反映加载后的配置值） ──
        self.title = f"🍅 {self._fmt()}"

        # ── 构建菜单 ──
        self._build_menu()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  配置持久化
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_config(self):
        """从 JSON 文件加载配置，文件不存在时返回空字典"""
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_config(self):
        """将当前配置写入 JSON 文件"""
        config = {
            "work_minutes": self.work_minutes,
            "short_break_minutes": self.short_break_minutes,
            "long_break_minutes": self.long_break_minutes,
            "auto_break": self.auto_break,
            "completed_pomodoros": self.completed_pomodoros,
            "total_focus_minutes": self.total_focus_minutes,
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # 静默处理写入失败

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  菜单构建
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_menu(self):
        """组装菜单结构"""
        self.start_item = rumps.MenuItem("▶ 开始专注", callback=self.toggle)
        self.reset_item = rumps.MenuItem("↺ 重置", callback=self.reset)
        self.skip_item = rumps.MenuItem("⏭ 跳过", callback=self.skip)

        # ── 设置子菜单 ──
        self.settings_menu = rumps.MenuItem("⚙ 设置")

        # 工作时长
        self.work_submenu = rumps.MenuItem("📝 工作时长")
        self.setup_duration_submenu(
            self.work_submenu,
            self.work_minutes,
            self._on_set_work,
            [15, 20, 25, 30, 35, 40, 45, 50, 60],
        )

        # 短休息时长
        self.short_break_submenu = rumps.MenuItem("☕ 短休息时长")
        self.setup_duration_submenu(
            self.short_break_submenu,
            self.short_break_minutes,
            self._on_set_short_break,
            [5, 10, 15, 20, 25, 30],
        )

        # 长休息时长
        self.long_break_submenu = rumps.MenuItem("🌿 长休息时长")
        self.setup_duration_submenu(
            self.long_break_submenu,
            self.long_break_minutes,
            self._on_set_long_break,
            [10, 15, 20, 25, 30],
        )

        self.settings_menu.add(self.work_submenu)
        self.settings_menu.add(self.short_break_submenu)
        self.settings_menu.add(self.long_break_submenu)
        self.auto_break_item = rumps.MenuItem(
            f"⏰ 自动开始休息 {'✓' if self.auto_break else '✗'}",
            callback=self.toggle_auto_break,
        )
        self.settings_menu.add(self.auto_break_item)

        # ── 组装主菜单 ──
        self.menu = [
            self.start_item,
            self.reset_item,
            self.skip_item,
            None,
            self.settings_menu,
            None,
            rumps.MenuItem("📊 统计", callback=self.show_stats),
            rumps.MenuItem("❓ 关于", callback=self.show_about),
            None,
            rumps.MenuItem("🚪 退出", callback=self.quit_app),
        ]

    def setup_duration_submenu(self, parent, current_value, callback, values):
        """为子菜单添加时长选项列表"""
        for v in values:
            item = rumps.MenuItem(f"{v} 分钟", callback=callback)
            item.state = (v == current_value)
            parent.add(item)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  界面更新
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _fmt(self):
        """格式化为 MM:SS"""
        m, s = divmod(self.seconds_left, 60)
        return f"{m:02d}:{s:02d}"

    def _update_title(self):
        """刷新菜单栏标题"""
        prefix = "⏸ " if "PAUSE" in self.state else ""
        icon = "☕" if self.state.startswith("BREAK") else "🍅"
        if self.state == "IDLE":
            self.title = f"🍅 {self._fmt()}"
        else:
            self.title = f"{icon} {prefix}{self._fmt()}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  计时器核心
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def on_tick(self, _):
        """每秒触发一次"""
        if self.seconds_left > 0:
            self.seconds_left -= 1
            self._update_title()
        else:
            self.timer.stop()
            self._on_complete()

    def _start_session(self, state, minutes):
        """开始一个会话段"""
        self.state = state
        self.seconds_left = minutes * 60
        self.start_item.title = "⏸ 暂停"
        self._update_title()
        self.timer.start()

    def _on_complete(self):
        """当前段结束时触发"""
        if self.state in ("WORK", "WORK_PAUSE"):
            self.completed_pomodoros += 1
            self.total_focus_minutes += self.work_minutes
            self._notify("🎉 番茄完成！", f"已完成 {self.completed_pomodoros} 个番茄")
            self._save_config()  # 完成一个番茄后保存统计
            self._start_break()
        else:
            self._notify("☕ 休息结束", "准备开始新的番茄吧！")
            self._start_work()

    def _notify(self, title, subtitle):
        """发送系统通知 + 音效"""
        rumps.notification(title=title, subtitle=subtitle, message="", sound=True)
        subprocess.run(
            ["afplay", "/System/Library/Sounds/Ping.aiff"],
            capture_output=True,
        )

    def _start_work(self):
        """开始工作时段"""
        self._start_session("WORK", self.work_minutes)

    def _start_break(self):
        """开始休息时段（自动判断短休/长休）"""
        is_long = self.completed_pomodoros % POMODOROS_UNTIL_LONG_BREAK == 0
        minutes = self.long_break_minutes if is_long else self.short_break_minutes
        if is_long:
            self._notify("🌿 长时间休息", f"{minutes} 分钟，好好放松一下")
        if self.auto_break:
            self._start_session("BREAK", minutes)
        else:
            self.state = "BREAK"
            self.seconds_left = minutes * 60
            self._update_title()
            self.start_item.title = "▶ 开始休息"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  菜单回调
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def toggle(self, _):
        """开始 / 暂停 / 继续"""
        if self.state == "IDLE":
            self._start_work()
        elif self.state == "WORK":
            self.timer.stop()
            self.state = "WORK_PAUSE"
            self.start_item.title = "▶ 继续"
            self._update_title()
        elif self.state == "WORK_PAUSE":
            self.state = "WORK"
            self.start_item.title = "⏸ 暂停"
            self.timer.start()
        elif self.state == "BREAK":
            self.timer.stop()
            self.state = "BREAK_PAUSE"
            self.start_item.title = "▶ 继续休息"
            self._update_title()
        elif self.state == "BREAK_PAUSE":
            self.state = "BREAK"
            self.start_item.title = "⏸ 暂停"
            self.timer.start()

    def reset(self, _):
        """重置到初始状态"""
        self.timer.stop()
        self.state = "IDLE"
        self.seconds_left = self.work_minutes * 60
        self.start_item.title = "▶ 开始专注"
        self._update_title()

    def skip(self, _):
        """跳过当前阶段"""
        self.timer.stop()
        self._on_complete()

    def _on_set_work(self, sender):
        """设置工作时长"""
        for item in self.work_submenu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = False
        sender.state = True
        self.work_minutes = int(sender.title.split()[0])
        # 空闲状态时立即刷新倒计时显示；运行中只保存值，不影响当前计时
        if self.state == "IDLE":
            self.seconds_left = self.work_minutes * 60
        self._update_title()
        self._save_config()

    def _on_set_short_break(self, sender):
        """设置短休息时长"""
        for item in self.short_break_submenu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = False
        sender.state = True
        self.short_break_minutes = int(sender.title.split()[0])
        self._save_config()

    def _on_set_long_break(self, sender):
        """设置长休息时长"""
        for item in self.long_break_submenu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = False
        sender.state = True
        self.long_break_minutes = int(sender.title.split()[0])
        self._save_config()

    def toggle_auto_break(self, sender):
        """切换自动开始休息"""
        self.auto_break = not self.auto_break
        sender.title = f"⏰ 自动开始休息 {'✓' if self.auto_break else '✗'}"
        self._save_config()

    def show_stats(self, _):
        """显示统计数据"""
        hours = self.total_focus_minutes / 60
        rumps.alert(
            title="📊 番茄统计",
            message=(
                f"🍅 完成番茄数: {self.completed_pomodoros}\n"
                f"⏱ 累计专注: {self.total_focus_minutes} 分钟"
                f" ({hours:.1f} 小时)"
            ),
        )

    def show_about(self, _):
        """关于信息"""
        rumps.alert(
            title="🍅 番茄时钟 v1.1",
            message=(
                "macOS 菜单栏番茄工作法计时器\n\n"
                f"标准: {DEFAULT_WORK}min 工作 — {DEFAULT_SHORT_BREAK}min 休息\n"
                f"长休: 每 {POMODOROS_UNTIL_LONG_BREAK} 个番茄后 {DEFAULT_LONG_BREAK}min\n\n"
                "基于 Python rumps 构建\n"
                "设置自动保存至 ~/.pomodoro_timer.json"
            ),
        )

    def quit_app(self, _):
        """退出应用前保存配置"""
        self._save_config()
        rumps.quit_application()


if __name__ == "__main__":
    PomodoroTimer().run()
