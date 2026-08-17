"""系统托盘：图标状态、右键菜单、气泡通知、tooltip。"""
from __future__ import annotations

from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

from core import autostart, display_manager as dm, preset_manager
from core.constants import app_display_name, BUILTIN_PRESETS
from ui import icons


class TrayIcon(QSystemTrayIcon):
    def __init__(self, ctx):
        super().__init__(ctx.app)
        self.ctx = ctx
        self._state = "normal"
        self._preset_actions = {}
        self._build_menu()
        self.setIcon(icons.make_tray_icon("normal"))
        self.setToolTip(f"{app_display_name()} — 正在运行")
        self.activated.connect(self._on_activated)
        # 信号
        self.ctx.engine.preset_applied.connect(lambda d, k: self._refresh_preset_checks(k))
        self.ctx.engine.paused_changed.connect(self._on_paused)
        self.ctx.screen.seconds_changed.connect(self._on_seconds)
        self._on_seconds(0, "")

    # ---------- 菜单 ----------
    def _build_menu(self) -> None:
        menu = QMenu()

        # 模式预设
        preset_menu = QMenu("模式预设", menu)
        for key, name, _, _, _ in BUILTIN_PRESETS:
            act = QAction(name, preset_menu)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, k=key: self.ctx.engine.apply_preset_all(k, 0))
            preset_menu.addAction(act)
            self._preset_actions[key] = act
        preset_menu.addSeparator()
        save_act = QAction("保存当前为自定义预设...", preset_menu)
        save_act.triggered.connect(self.ctx.save_custom_preset)
        preset_menu.addAction(save_act)
        menu.addMenu(preset_menu)

        # 快速专注
        self.focus_quick_act = QAction("开始 25 分钟专注", menu)
        self.focus_quick_act.triggered.connect(self.ctx.quick_start_focus)
        menu.addAction(self.focus_quick_act)

        menu.addSeparator()

        # 暂停
        self.pause_act = QAction("暂停色温调节", menu)
        self.pause_act.setCheckable(True)
        self.pause_act.setShortcut("Ctrl+Alt+P")
        self.pause_act.triggered.connect(self._on_pause_toggle)
        menu.addAction(self.pause_act)

        menu.addSeparator()

        # 显示器
        disp_menu = QMenu("显示器", menu)
        self._disp_actions = []
        self._rebuild_display_menu(disp_menu)
        self._disp_menu = disp_menu
        menu.addMenu(disp_menu)

        menu.addSeparator()

        # 开机自启
        self.autostart_act = QAction("开机自启", menu)
        self.autostart_act.setCheckable(True)
        self.autostart_act.setChecked(autostart.is_autostart_enabled())
        self.autostart_act.triggered.connect(self._on_autostart)
        menu.addAction(self.autostart_act)

        # 设置
        settings_act = QAction("设置...", menu)
        settings_act.triggered.connect(lambda: self.ctx.main_window.show_page("设置"))
        menu.addAction(settings_act)

        menu.addSeparator()

        quit_act = QAction("退出", menu)
        quit_act.triggered.connect(self.ctx.quit_app)
        menu.addAction(quit_act)

        self.setContextMenu(menu)

    def _rebuild_display_menu(self, disp_menu: QMenu) -> None:
        disp_menu.clear()
        for m in dm.display_manager.monitors():
            act = QAction(m.label, disp_menu)
            act.triggered.connect(
                lambda checked, dev=m.device_name: self._on_select_display(dev))
            disp_menu.addAction(act)

    def _on_select_display(self, device_name: str) -> None:
        self.ctx.engine.select_device(device_name)
        self.ctx.main_window.show_page("显示")

    # ---------- 交互 ----------
    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:  # 左键单击：切换显示/隐藏
            if self.ctx.main_window.isVisible():
                self.ctx.main_window.hide()
            else:
                self.ctx.main_window.show_page("显示")
        elif reason == QSystemTrayIcon.DoubleClick:  # 双击：打开显示页
            self.ctx.main_window.show_page("显示")

    def _on_pause_toggle(self, checked: bool) -> None:
        if checked:
            self.ctx.engine.pause()
        else:
            self.ctx.engine.resume()

    def _on_paused(self, paused: bool) -> None:
        self.pause_act.setChecked(paused)
        self.set_state("paused" if paused else "normal")

    def _on_autostart(self, checked: bool) -> None:
        ok = autostart.set_autostart(checked)
        if not ok:
            self.ctx.toast("开机自启", "写入注册表失败，可能权限不足")
            self.autostart_act.setChecked(not checked)

    def _refresh_preset_checks(self, active_key: str) -> None:
        for key, act in self._preset_actions.items():
            act.setChecked(key == active_key)

    def _on_seconds(self, seconds: int, date: str) -> None:
        h, rem = divmod(seconds, 3600)
        m, _ = divmod(rem, 60)
        if h:
            tip = f"今日已使用 {h} 小时 {m} 分"
        else:
            tip = f"今日已使用 {m} 分"
        if self.ctx.engine.paused:
            tip += "（已暂停）"
        self.setToolTip(f"{app_display_name()} — {tip}")

    # ---------- 状态 ----------
    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.setIcon(icons.make_tray_icon(state))

    def show_message(self, title: str, msg: str, icon=QSystemTrayIcon.Information,
                     msecs: int = 3000) -> None:
        if self.ctx.config.get("ui", "toast_notifications", default=True):
            self.showMessage(title, msg, icon, msecs)
