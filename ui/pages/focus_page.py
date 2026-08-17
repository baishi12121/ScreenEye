"""专注页面：番茄计时 + 色温联动。

UI 结构（对照产品方案）：
- 大号倒计时文本 + 状态文字
- 专注时长 / 休息时长（单选 + 自定义）
- 选项：循环周期 / 启动专注自动切换办公色温 / 专注期间暂停休息弹窗
- 按钮：开始专注 / 暂停 / 重置
- 近期专注记录列表（日期 | 专注时长）
"""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from core.config import config
from ui.widgets import Card


def format_hms(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class DurationSelector(QWidget):
    """专注/休息时长选择：预设单选 + 自定义微调框（关闭选项可选）。"""

    changed = pyqtSignal(int)  # 分钟，0 表示关闭

    def __init__(self, presets, allow_off: bool = False, parent=None):
        super().__init__(parent)
        self.presets = list(presets)
        self.allow_off = allow_off
        self._group = QButtonGroup(self)
        self._radios: list = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for p in self.presets:
            rb = QRadioButton(f"{p}")
            self._group.addButton(rb)
            layout.addWidget(rb)
            self._radios.append((p, rb))
            rb.toggled.connect(
                lambda checked, val=p: self._on_preset(checked, val))
        if allow_off:
            self._off_radio = QRadioButton("关闭")
            self._group.addButton(self._off_radio)
            layout.addWidget(self._off_radio)
            self._off_radio.toggled.connect(
                lambda checked: self._on_off(checked))
        self._custom_radio = QRadioButton("自定义")
        self._group.addButton(self._custom_radio)
        layout.addWidget(self._custom_radio)
        self._spin = QSpinBox()
        self._spin.setRange(1, 180)
        self._spin.setSuffix(" 分")
        self._spin.setEnabled(False)
        layout.addWidget(self._spin)
        layout.addStretch(1)
        self._custom_radio.toggled.connect(self._on_custom)
        self._spin.valueChanged.connect(self._on_spin)

    def _on_preset(self, checked: bool, val: int) -> None:
        if checked:
            self._spin.setEnabled(False)
            self.changed.emit(val)

    def _on_off(self, checked: bool) -> None:
        if checked:
            self._spin.setEnabled(False)
            self.changed.emit(0)

    def _on_custom(self, checked: bool) -> None:
        self._spin.setEnabled(checked)
        if checked:
            self.changed.emit(self._spin.value())

    def _on_spin(self, val: int) -> None:
        if self._custom_radio.isChecked():
            self.changed.emit(val)

    def set_value(self, minutes: int) -> None:
        if self.allow_off and minutes == 0:
            self._off_radio.setChecked(True)
            return
        for p, rb in self._radios:
            if p == minutes:
                rb.setChecked(True)
                return
        # 不在预设列表 -> 自定义
        self._custom_radio.setChecked(True)
        self._spin.setValue(min(180, max(1, int(minutes))))

    def value(self) -> int:
        if self._custom_radio.isChecked():
            return self._spin.value()
        if self.allow_off and self._off_radio.isChecked():
            return 0
        for p, rb in self._radios:
            if rb.isChecked():
                return p
        return self.presets[0]


class FocusPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._build_ui()
        self._connect()
        self.refresh()

    # ---------- 构建 UI ----------
    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(14)
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        # 计时卡片
        timer_card = Card(title="专注计时")
        self.label_countdown = QLabel("00:25:00")
        self.label_countdown.setAlignment(Qt.AlignCenter)
        self.label_countdown.setStyleSheet(
            "font-size: 52pt; font-weight: bold; color:#26C6DA;")
        timer_card.add_widget(self.label_countdown)
        self.label_status = QLabel("等待开始")
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.setStyleSheet("font-size: 13pt; color:#9E9E9E;")
        timer_card.add_widget(self.label_status)

        brow = QHBoxLayout()
        self.btn_start = QPushButton("开始专注")
        self.btn_start.setObjectName("Active")
        self.btn_pause = QPushButton("暂停")
        self.btn_reset = QPushButton("重置")
        self.btn_pause.setEnabled(False)
        self.btn_reset.setEnabled(False)
        for b in (self.btn_start, self.btn_pause, self.btn_reset):
            b.setFixedHeight(36)
            brow.addWidget(b)
        timer_card.add_widget(brow)
        v.addWidget(timer_card)

        self.btn_start.clicked.connect(self._on_start)
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_reset.clicked.connect(self._on_reset)

        # 设置卡片
        set_card = Card(title="专注设置")
        # 专注时长
        focus_row = QHBoxLayout()
        focus_row.addWidget(QLabel("专注时长"))
        focus_row.addStretch(1)
        set_card.add_widget(focus_row)
        self.focus_sel = DurationSelector([25, 40, 50, 60])
        self.focus_sel.changed.connect(self._on_focus_duration)
        set_card.add_widget(self.focus_sel)

        # 休息时长
        rest_row = QHBoxLayout()
        rest_row.addWidget(QLabel("休息时长"))
        rest_row.addStretch(1)
        set_card.add_widget(rest_row)
        self.rest_sel = DurationSelector([5, 10, 15], allow_off=True)
        self.rest_sel.changed.connect(self._on_rest_duration)
        set_card.add_widget(self.rest_sel)

        # 选项
        self.chk_loop = QCheckBox("循环周期（专注-休息自动循环）")
        self.chk_auto = QCheckBox("启动专注自动切换【办公】色温")
        self.chk_pause = QCheckBox("专注期间暂停休息弹窗")
        self.chk_loop.toggled.connect(lambda c: self._save("loop_enable", c))
        self.chk_auto.toggled.connect(lambda c: self._save("auto_switch_preset", c))
        self.chk_pause.toggled.connect(lambda c: self._save("pause_break_reminder", c))
        set_card.add_widget(self.chk_loop)
        set_card.add_widget(self.chk_auto)
        set_card.add_widget(self.chk_pause)
        v.addWidget(set_card)

        # 记录卡片
        rec_card = Card(title="近期专注记录")
        self.rec_list = QListWidget()
        self.rec_list.setMaximumHeight(220)
        rec_card.add_widget(self.rec_list)
        v.addWidget(rec_card)

        v.addStretch(1)

    # ---------- 信号连接 ----------
    def _connect(self) -> None:
        mgr = self.ctx.focus
        mgr.state_changed.connect(self._on_state)
        mgr.tick.connect(self._on_tick)
        mgr.session_recorded.connect(self._refresh_records)
        mgr.finished.connect(self._on_finished)

    # ---------- 行为 ----------
    def _on_start(self) -> None:
        self.ctx.focus.start()

    def _on_pause(self) -> None:
        self.ctx.focus.toggle_pause()

    def _on_reset(self) -> None:
        self.ctx.focus.reset_focus()

    def _on_focus_duration(self, minutes: int) -> None:
        self._save("focus_duration", minutes)
        if not self.ctx.focus.is_active():
            self.label_countdown.setText(format_hms(minutes * 60))

    def _on_rest_duration(self, minutes: int) -> None:
        self._save("rest_duration", minutes)

    def _save(self, key, value) -> None:
        config.set("focus", key, value=value)
        config.save()

    # ---------- 状态/计时刷新 ----------
    def _on_state(self, state: str) -> None:
        from core.focus_manager import STATE_TEXT
        self.label_status.setText(STATE_TEXT.get(state, "等待开始"))
        active = state in ("focusing", "resting", "paused_focus", "paused_rest")
        self.btn_start.setEnabled(not active)
        self.btn_pause.setEnabled(active)
        self.btn_reset.setEnabled(active)
        if state == "paused_focus" or state == "paused_rest":
            self.btn_pause.setText("继续")
        else:
            self.btn_pause.setText("暂停")
        if state == "idle":
            self.label_countdown.setText(format_hms(self.ctx.focus.focus_minutes * 60))

    def _on_tick(self, remaining: int, total: int, state: str) -> None:
        self.label_countdown.setText(format_hms(remaining))

    def _on_finished(self, message: str) -> None:
        self.ctx.toast("专注", message)

    # ---------- 记录列表 ----------
    def _refresh_records(self) -> None:
        self.rec_list.clear()
        records = self.ctx.focus.recent_records(30)
        if not records:
            item = QListWidgetItem("暂无专注记录")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.rec_list.addItem(item)
            return
        for rec in records:
            date_disp = rec["date"][5:]  # MM-DD
            mins = rec["focus_seconds"] // 60
            secs = rec["focus_seconds"] % 60
            dur = f"{mins} 分" + (f" {secs} 秒" if secs else "")
            text = f"{date_disp} {rec.get('start', '')}  ·  {dur}"
            self.rec_list.addItem(QListWidgetItem(text))

    # ---------- 对外刷新（切到本页时调用） ----------
    def refresh(self) -> None:
        mgr = self.ctx.focus
        self.focus_sel.set_value(mgr.focus_minutes)
        self.rest_sel.set_value(mgr.rest_minutes)
        self.chk_loop.setChecked(mgr.loop_enabled)
        self.chk_auto.setChecked(mgr.auto_switch)
        self.chk_pause.setChecked(mgr.pause_rest)
        self._on_state(mgr.state)
        self._refresh_records()
