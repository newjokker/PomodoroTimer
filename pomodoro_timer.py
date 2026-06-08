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
    - 统计数据追踪（每日/每周/累计）
    - 静音模式
    - 完成时弹窗开关（可关闭阻塞式弹窗）
    - 休息结束自动开始工作
    - 设置持久化（重启后保留）
"""

# ── 版本信息 ──
__version__ = "1.3.0"
__app_name__ = "🍅 番茄时钟"
__repo_url__ = "https://github.com/newjokker/PomodoroTimer"

import rumps
import subprocess
import json
import os
import datetime
import tempfile

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
        self.mute = config.get("mute", False)
        self.show_alert = config.get("show_alert", True)
        self.auto_resume = config.get("auto_resume", False)
        self._daily_stats = config.get("daily", {})

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
        """将当前配置原子写入 JSON 文件（先写临时文件再 rename，防止崩溃损坏）"""
        config = {
            "work_minutes": self.work_minutes,
            "short_break_minutes": self.short_break_minutes,
            "long_break_minutes": self.long_break_minutes,
            "auto_break": self.auto_break,
            "mute": self.mute,
            "show_alert": self.show_alert,
            "auto_resume": self.auto_resume,
            "completed_pomodoros": self.completed_pomodoros,
            "total_focus_minutes": self.total_focus_minutes,
            "daily": self._daily_stats,
        }
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".json",
                dir=CONFIG_DIR, delete=False,
            )
            try:
                json.dump(config, tmp, indent=2, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
            finally:
                tmp.close()
            os.replace(tmp.name, CONFIG_FILE)  # 原子 rename
        except OSError:
            pass

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
            self.work_submenu, self.work_minutes, "work_minutes",
            [15, 20, 25, 30, 35, 40, 45, 50, 60],
        )

        # 短休息时长
        self.short_break_submenu = rumps.MenuItem("☕ 短休息时长")
        self.setup_duration_submenu(
            self.short_break_submenu, self.short_break_minutes, "short_break_minutes",
            [5, 10, 15, 20, 25, 30],
        )

        # 长休息时长
        self.long_break_submenu = rumps.MenuItem("🌿 长休息时长")
        self.setup_duration_submenu(
            self.long_break_submenu, self.long_break_minutes, "long_break_minutes",
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
        self.mute_item = rumps.MenuItem(
            f"🔇 静音模式 {'✓' if self.mute else '✗'}",
            callback=self.toggle_mute,
        )
        self.settings_menu.add(self.mute_item)
        self.alert_item = rumps.MenuItem(
            f"🎯 完成时弹窗 {'✓' if self.show_alert else '✗'}",
            callback=self.toggle_alert,
        )
        self.settings_menu.add(self.alert_item)
        self.auto_resume_item = rumps.MenuItem(
            f"🔁 休息后自动工作 {'✓' if self.auto_resume else '✗'}",
            callback=self.toggle_auto_resume,
        )
        self.settings_menu.add(self.auto_resume_item)

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

    def setup_duration_submenu(self, parent, current_value, attr_name, values):
        """为子菜单添加时长选项列表"""
        for v in values:
            item = rumps.MenuItem(f"{v} 分钟", callback=self._on_set_duration)
            item.state = (v == current_value)
            item._setting_attr = attr_name
            item._setting_submenu = parent
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
            # 按实际完成时间累加，而非总是加满 work_minutes（修复跳过时统计虚高）
            elapsed_seconds = self.work_minutes * 60 - self.seconds_left
            actual_minutes = max(0, round(elapsed_seconds / 60))
            self.total_focus_minutes += actual_minutes
            # 每日统计
            today = datetime.date.today().isoformat()
            daily = self._daily_stats.setdefault(today, {"pomodoros": 0, "minutes": 0})
            daily["pomodoros"] += 1
            daily["minutes"] += actual_minutes
            self._notify("🎉 番茄完成！", f"已完成 {self.completed_pomodoros} 个番茄")
            # ── 弹窗提醒（可关闭） ──
            is_long = self.completed_pomodoros % POMODOROS_UNTIL_LONG_BREAK == 0
            break_min = self.long_break_minutes if is_long else self.short_break_minutes
            if self.show_alert:
                rumps.alert(
                    title="🎉 番茄完成！",
                    message=(
                        f"已完成 {self.completed_pomodoros} 个番茄，专注 {actual_minutes} 分钟\n"
                        f"即将开始 {break_min} 分钟休息，好好放松一下！"
                    ),
                )
            self._save_config()
            self._start_break()
        else:
            self._notify("☕ 休息结束", "准备开始新的番茄吧！")
            # ── 弹窗提醒（可关闭） ──
            if self.show_alert:
                rumps.alert(
                    title="☕ 休息结束",
                    message="休息结束，准备开始新的番茄吧！\n点击「好」开始专注工作",
                )
            if self.auto_resume:
                self._start_work()
            else:
                self.state = "IDLE"
                self.seconds_left = self.work_minutes * 60
                self.start_item.title = "▶ 开始专注"
                self._update_title()

    def _notify(self, title, subtitle):
        """发送系统通知（静音模式下跳过音效）"""
        rumps.notification(title=title, subtitle=subtitle, message="", sound=not self.mute)
        if not self.mute:
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

    def _on_set_duration(self, sender):
        """设置时长（通用回调，通过 MenuItem 自定义属性识别是哪个设置项）"""
        submenu = sender._setting_submenu
        attr = sender._setting_attr
        for item in submenu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = False
        sender.state = True
        value = int(sender.title.split()[0])
        setattr(self, attr, value)
        # 修改工作时长且处于空闲状态 → 立即刷新倒计时显示
        if attr == "work_minutes" and self.state == "IDLE":
            self.seconds_left = self.work_minutes * 60
            self._update_title()
        self._save_config()

    def toggle_auto_break(self, sender):
        """切换自动开始休息"""
        self.auto_break = not self.auto_break
        sender.title = f"⏰ 自动开始休息 {'✓' if self.auto_break else '✗'}"
        self._save_config()

    def toggle_mute(self, sender):
        """切换静音模式"""
        self.mute = not self.mute
        sender.title = f"🔇 静音模式 {'✓' if self.mute else '✗'}"
        self._save_config()

    def toggle_alert(self, sender):
        """切换完成时弹窗"""
        self.show_alert = not self.show_alert
        sender.title = f"🎯 完成时弹窗 {'✓' if self.show_alert else '✗'}"
        self._save_config()

    def toggle_auto_resume(self, sender):
        """切换休息后自动开始工作"""
        self.auto_resume = not self.auto_resume
        sender.title = f"🔁 休息后自动工作 {'✓' if self.auto_resume else '✗'}"
        self._save_config()

    def _get_week_stats(self):
        """计算本周（周一至周日）的统计数据"""
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        week_pomos = 0
        week_minutes = 0
        for d in range(7):
            day = (monday + datetime.timedelta(days=d)).isoformat()
            if day in self._daily_stats:
                week_pomos += self._daily_stats[day]["pomodoros"]
                week_minutes += self._daily_stats[day]["minutes"]
        return week_pomos, week_minutes

    def show_stats(self, _):
        """显示统计数据（今日 / 本周 / 累计）"""
        today = datetime.date.today().isoformat()
        today_stats = self._daily_stats.get(today, {"pomodoros": 0, "minutes": 0})
        week_pomos, week_minutes = self._get_week_stats()
        total_hours = self.total_focus_minutes / 60

        rumps.alert(
            title="📊 番茄统计",
            message=(
                f"📅 今日\n"
                f"   番茄: {today_stats['pomodoros']} 个   "
                f"专注: {today_stats['minutes']} 分钟\n\n"
                f"📆 本周\n"
                f"   番茄: {week_pomos} 个   "
                f"专注: {week_minutes} 分钟\n\n"
                f"🏆 累计\n"
                f"   番茄: {self.completed_pomodoros} 个   "
                f"专注: {self.total_focus_minutes} 分钟"
                f" ({total_hours:.1f} 小时)"
            ),
        )

    def show_about(self, _):
        """关于信息"""
        rumps.alert(
            title=f"🍅 番茄时钟 v{__version__}",
            message=(
                "macOS 菜单栏番茄工作法计时器\n\n"
                f"标准: {DEFAULT_WORK}min 工作 — {DEFAULT_SHORT_BREAK}min 休息\n"
                f"长休: 每 {POMODOROS_UNTIL_LONG_BREAK} 个番茄后 {DEFAULT_LONG_BREAK}min\n\n"
                "基于 Python rumps 构建\n"
                "设置自动保存至 ~/.pomodoro_timer.json\n\n"
                f"版本: v{__version__}"
            ),
        )

    def quit_app(self, _):
        """退出应用前保存配置"""
        self._save_config()
        rumps.quit_application()


if __name__ == "__main__":
    PomodoroTimer().run()
