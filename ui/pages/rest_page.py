"""休息页面：番茄钟计时、设置与全屏休息提醒。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
    QWidget,
)

from core.config import config
from ui.widgets import Card


def format_hms(seconds: int) -> str:
    h, rem = divmod(max(0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class RestBreakWindow(QWidget):
    """全屏休息提醒覆盖窗口。"""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setStyleSheet("background: rgba(20,20,20,0.96); color: #E0E0E0;")
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        self.title = QLabel("该休息一下了")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 20pt; font-weight: bold; color:#26C6DA;")
        self.tip = QLabel("闭眼远眺 · 转动颈部 · 眨眼放松")
        self.tip.setAlignment(Qt.AlignCenter)
        self.tip.setStyleSheet("font-size: 12pt; color:#BDBDBD;")
        self.countdown = QLabel("00:00")
        self.countdown.setAlignment(Qt.AlignCenter)
        self.countdown.setStyleSheet("font-size: 40pt; font-weight: bold; color:#4CAF50;")
        layout.addWidget(self.title)
        layout.addWidget(self.tip)
        layout.addWidget(self.countdown)
        layout.addStretch(1)
        skip = QPushButton("立即结束休息")
        skip.setFixedWidth(160)
        skip.clicked.connect(self._skip)
        layout.addWidget(skip, alignment=Qt.AlignCenter)
        layout.addStretch(1)

    def show_for(self, minutes: int, is_long: bool) -> None:
        self.title.setText("长休息一下" if is_long else "该休息一下了")
        self.showFullScreen()

    def update_countdown(self, seconds: int) -> None:
        self.countdown.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

    def _skip(self) -> None:
        self.ctx.rest.reset()


class RestPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._break_win = RestBreakWindow(ctx)
        self._build_ui()
        self._connect()
        self._refresh_settings()
        self._update_timer(self.ctx.rest.remaining(), self.ctx.rest.total(),
                           self.ctx.rest.state)
        self._update_rest_count()

    def _build_ui(self) -> None:
        scroll = self._wrap_scroll()
        # 计时器卡片
        timer_card = Card(title="番茄钟")
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 44pt; font-weight: bold; color:#26C6DA;")
        timer_card.add_widget(self.timer_label)
        brow = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        for b in (self.start_btn, self.pause_btn, self.reset_btn):
            brow.addWidget(b)
        timer_card.add_widget(brow)
        scroll.addWidget(timer_card)

        self.start_btn.clicked.connect(self.ctx.rest.start)
        self.pause_btn.clicked.connect(self.ctx.rest.pause)
        self.reset_btn.clicked.connect(self.ctx.rest.reset)

        # 设置卡片
        set_card = Card(title="番茄钟设置")
        grid = QGridLayout()
        grid.setSpacing(10)
        self.work_spin = QSpinBox(); self.work_spin.setRange(5, 120)
        self.rest_spin = QSpinBox(); self.rest_spin.setRange(1, 30)
        self.long_spin = QSpinBox(); self.long_spin.setRange(5, 60)
        self.cycle_spin = QSpinBox(); self.cycle_spin.setRange(1, 12)
        grid.addWidget(QLabel("工作（分钟）"), 0, 0); grid.addWidget(self.work_spin, 0, 1)
        grid.addWidget(QLabel("休息（分钟）"), 1, 0); grid.addWidget(self.rest_spin, 1, 1)
        grid.addWidget(QLabel("长休息（分钟）"), 2, 0); grid.addWidget(self.long_spin, 2, 1)
        grid.addWidget(QLabel("长休息间隔（周期）"), 3, 0); grid.addWidget(self.cycle_spin, 3, 1)
        set_card.add_widget(grid)
        self.work_spin.valueChanged.connect(lambda v: self._save("work_minutes", v))
        self.rest_spin.valueChanged.connect(lambda v: self._save("rest_minutes", v))
        self.long_spin.valueChanged.connect(lambda v: self._save("long_break_minutes", v))
        self.cycle_spin.valueChanged.connect(lambda v: self._save("long_break_after_cycles", v))
        scroll.addWidget(set_card)

        # 统计卡片
        stat_card = Card(title="今日统计")
        self.rest_count_label = QLabel("今日休息次数: 0")
        self.screen_label = QLabel("今日屏幕时长: 0 分")
        stat_card.add_widget(self.rest_count_label)
        stat_card.add_widget(self.screen_label)
        scroll.addWidget(stat_card)
        scroll.addStretch(1)

    def _wrap_scroll(self):
        from PyQt5.QtWidgets import QScrollArea
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(14)
        sa.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(sa)
        return v

    def _refresh_settings(self) -> None:
        self.work_spin.setValue(config.get("rest", "work_minutes", default=45))
        self.rest_spin.setValue(config.get("rest", "rest_minutes", default=5))
        self.long_spin.setValue(config.get("rest", "long_break_minutes", default=15))
        self.cycle_spin.setValue(config.get("rest", "long_break_after_cycles", default=4))

    def _save(self, key, value) -> None:
        config.set("rest", key, value=value)
        config.save()

    def _connect(self) -> None:
        self.ctx.rest.tick.connect(self._update_timer)
        self.ctx.rest.state_changed.connect(self._on_state)
        self.ctx.rest.break_started.connect(self._on_break)
        self.ctx.rest.rest_count_changed.connect(lambda c: self._update_rest_count())
        self.ctx.screen.seconds_changed.connect(self._on_seconds)

    def _update_timer(self, remaining, total, state) -> None:
        self.timer_label.setText(format_hms(remaining))

    def _on_state(self, state, cycle) -> None:
        self._update_timer(self.ctx.rest.remaining(), self.ctx.rest.total(), state)
        if state in ("work", "idle"):
            if self._break_win.isVisible():
                self._break_win.hide()

    def _on_break(self, minutes, is_long) -> None:
        self._break_win.show_for(minutes, is_long)
        self._break_win.update_countdown(minutes * 60)

    def _update_rest_count(self) -> None:
        self.rest_count_label.setText(f"今日休息次数: {self.ctx.rest.rest_count_today()}")

    def _on_seconds(self, seconds, date) -> None:
        h, m = divmod(seconds, 3600)
        self.screen_label.setText(f"今日屏幕时长: {h} 小时 {m} 分" if h else
                                  f"今日屏幕时长: {m} 分")
