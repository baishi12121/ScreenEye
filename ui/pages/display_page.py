"""显示页面：显示器选择、预设、色温/亮度滑块、昼夜自动切换。"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QInputDialog, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from core import display_manager as dm, preset_manager
from core.config import config
from core.constants import BRIGHTNESS_MAX, BRIGHTNESS_MIN, BUILTIN_PRESETS, TEMP_MAX, TEMP_MIN
from ui import widgets
from ui.widgets import Card, HSeparator, LabeledSlider, PresetButton


class DisplayPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._device = None
        self._preset_buttons = {}
        self._build_ui()
        self._fill_displays()
        self._build_presets()
        self._connect()
        self.refresh()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(14)
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # 显示器
        disp_card = Card(title="显示器")
        drow = QHBoxLayout()
        self.disp_combo = QComboBox()
        self.disp_combo.setMinimumWidth(260)
        self.disp_combo.currentIndexChanged.connect(self._on_display_changed)
        drow.addWidget(self.disp_combo)
        drow.addStretch(1)
        self.sync_btn = QPushButton("同步所有显示器")
        self.sync_btn.clicked.connect(self._on_sync)
        drow.addWidget(self.sync_btn)
        disp_card.add_widget(drow)
        self._layout.addWidget(disp_card)

        # 预设
        self.preset_card = Card(title="快速预设")
        self.preset_grid = QGridLayout()
        self.preset_grid.setSpacing(8)
        self.preset_card.add_widget(self.preset_grid)
        self._layout.addWidget(self.preset_card)

        # 色温
        self.temp_card = Card(title="色温")
        self.temp_slider = LabeledSlider("色温", "K", TEMP_MIN, TEMP_MAX, 100, 6500)
        self.temp_slider.valueChanged.connect(self._on_temp)
        self.temp_card.add_widget(self.temp_slider)
        warm = QLabel("暖色 ◀")
        warm.setObjectName("Secondary")
        cool = QLabel("▶ 冷色")
        cool.setObjectName("Secondary")
        h = QHBoxLayout()
        h.addWidget(warm)
        h.addStretch(1)
        h.addWidget(cool)
        self.temp_card.add_widget(h)
        self._layout.addWidget(self.temp_card)

        # 亮度
        self.bright_card = Card(title="亮度")
        self.bright_slider = LabeledSlider("亮度", "%", BRIGHTNESS_MIN, BRIGHTNESS_MAX, 1, 100)
        self.bright_slider.valueChanged.connect(self._on_bright)
        self.bright_card.add_widget(self.bright_slider)
        self._layout.addWidget(self.bright_card)

        # 昼夜自动切换
        sched_card = Card(title="昼夜自动切换")
        srow = QHBoxLayout()
        self.sched_chk = QCheckBox("根据时间自动切换预设")
        self.sched_chk.toggled.connect(self._on_schedule_toggle)
        srow.addWidget(self.sched_chk)
        srow.addStretch(1)
        gear = QPushButton("⚙ 时间表")
        gear.clicked.connect(lambda: self.ctx.main_window.show_page("设置"))
        srow.addWidget(gear)
        sched_card.add_widget(srow)
        sched_card.add_widget(QLabel("开启后按设置中的时间段自动切换护眼预设。"))
        self._layout.addWidget(sched_card)

        # 屏幕时长
        st_card = Card(title="今日屏幕时长")
        self.st_label = QLabel("0 分")
        self.st_label.setObjectName("Title")
        st_card.add_widget(self.st_label)
        self._layout.addWidget(st_card)

        self._layout.addStretch(1)

    # ---------- 显示器 ----------
    def _fill_displays(self) -> None:
        self.disp_combo.blockSignals(True)
        self.disp_combo.clear()
        for m in dm.display_manager.monitors():
            self.disp_combo.addItem(m.label, m.device_name)
        self.disp_combo.blockSignals(False)
        # 默认选中主屏或 engine.current_device
        cur = self.ctx.engine.current_device
        idx = 0
        if cur:
            idx = self.disp_combo.findData(cur)
            if idx < 0:
                idx = 0
        self.disp_combo.setCurrentIndex(idx)
        self._device = self.disp_combo.currentData()

    def _on_display_changed(self, _=None) -> None:
        self._device = self.disp_combo.currentData()
        self.ctx.engine.select_device(self._device)
        self.refresh()

    # ---------- 预设 ----------
    def _build_presets(self) -> None:
        # 清空
        while self.preset_grid.count():
            item = self.preset_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._preset_buttons.clear()

        col = 0
        row = 0
        cols = 4
        for key, name, _, _, desc in BUILTIN_PRESETS:
            btn = PresetButton(name, key)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda k=key: self._apply_preset(k))
            self.preset_grid.addWidget(btn, row, col)
            self._preset_buttons[key] = btn
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # 自定义预设
        for i, p in enumerate(preset_manager.custom_presets()):
            key = preset_manager.custom_key(i)
            name = p.get("name", f"自定义 {i + 1}")
            btn = PresetButton(name, key)
            btn.clicked.connect(lambda k=key: self._apply_preset(k))
            self.preset_grid.addWidget(btn, row, col)
            self._preset_buttons[key] = btn
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # 添加按钮
        add_btn = PresetButton("＋ 自定义", "__add__")
        add_btn.clicked.connect(self._add_custom)
        self.preset_grid.addWidget(add_btn, row, col)

    def _apply_preset(self, key: str) -> None:
        if key == "__add__":
            return
        self.ctx.engine.apply_preset(self._device, key)

    def _add_custom(self) -> None:
        s = self.ctx.engine.get_settings(self._device)
        name, ok = QInputDialog.getText(self, "保存自定义预设",
                                         "预设名称：", text="我的预设")
        if ok and name.strip():
            key = preset_manager.add_custom(name.strip(),
                                            int(s["temperature"]), int(s["brightness"]))
            if key is None:
                QMessageBox.warning(self, "提示", "自定义预设已达上限（10 个）")
            else:
                self._build_presets()
                self.refresh()

    def _on_sync(self) -> None:
        self.ctx.engine.sync_all_to(self._device)
        self.ctx.toast("同步", "已将当前显示器设置同步到所有显示器")

    # ---------- 滑块 ----------
    def _on_temp(self, v: int) -> None:
        self.ctx.engine.set_temperature(self._device, v)

    def _on_bright(self, v: int) -> None:
        self.ctx.engine.set_brightness(self._device, v)

    def _on_schedule_toggle(self, checked: bool) -> None:
        config.set("general", "schedule_enabled", value=checked)
        config.save()
        self.ctx.scheduler.reload()

    # ---------- 刷新 ----------
    def refresh(self) -> None:
        if not self._device:
            self._fill_displays()
        s = self.ctx.engine.get_settings(self._device)
        temp = int(s["temperature"])
        bright = int(s["brightness"])
        active = s.get("active_preset", "")
        self.temp_slider.set_value(temp)
        self.bright_slider.set_value(bright)
        # 高亮激活预设
        for key, btn in self._preset_buttons.items():
            btn.set_selected(key == active)
        # 调度开关
        self.sched_chk.blockSignals(True)
        self.sched_chk.setChecked(config.get("general", "schedule_enabled", default=False))
        self.sched_chk.blockSignals(False)
        # 屏幕时长
        secs = self.ctx.screen.today_seconds()
        h, m = divmod(secs, 3600)
        self.st_label.setText(f"{h} 小时 {m} 分" if h else f"{m} 分")

    def _connect(self) -> None:
        self.ctx.engine.settings_changed.connect(self._on_ext_settings)
        self.ctx.engine.preset_applied.connect(self._on_ext_preset)
        self.ctx.screen.seconds_changed.connect(lambda s, d: self.refresh()
                                                 if self.isVisible() else None)

    def _on_ext_settings(self, *a) -> None:
        if self.isVisible():
            self.refresh()

    def _on_ext_preset(self, device: str, key: str) -> None:
        if self.isVisible():
            self.refresh()
