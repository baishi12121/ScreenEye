"""统计页面：今日屏幕总时长、各软件使用时长排行、近 7 天趋势。"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget,
)

from ui.widgets import Card

_BAR_STYLE = """
QProgressBar { background: #2E2E2E; border: 1px solid #3A3A3A; border-radius: 6px; }
QProgressBar::chunk { background: #26C6DA; border-radius: 6px; }
"""


def _fmt(secs: int) -> str:
    secs = int(secs)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h:
        return f"{h} 小时 {m} 分"
    if m:
        if s:
            return f"{m} 分 {s} 秒"
        return f"{m} 分"
    return f"{s} 秒"


class ScreenTimePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._build_ui()
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

        # 今日总览
        sum_card = Card(title="今日总览")
        self.total_label = QLabel("0 秒")
        self.total_label.setObjectName("Title")
        self.total_label.setStyleSheet("font-size: 22pt; color: #26C6DA; font-weight: bold;")
        sum_card.add_widget(self.total_label)
        self.apps_count_label = QLabel("共使用了 0 个软件")
        self.apps_count_label.setObjectName("Secondary")
        sum_card.add_widget(self.apps_count_label)
        self._layout.addWidget(sum_card)

        # 今日专注（与专注模块联动）
        focus_card = Card(title="今日专注")
        self.focus_label = QLabel("0 秒")
        self.focus_label.setObjectName("Title")
        self.focus_label.setStyleSheet("font-size: 22pt; color: #4CAF50; font-weight: bold;")
        focus_card.add_widget(self.focus_label)
        self._layout.addWidget(focus_card)

        # 各软件使用时长
        self.apps_card = Card(title="各软件使用时长")
        self.apps_body = QVBoxLayout()
        self.apps_body.setSpacing(8)
        self.apps_card.add_widget(self.apps_body)
        self._layout.addWidget(self.apps_card)

        # 近 7 天
        self.week_card = Card(title="近 7 天总时长")
        self.week_body = QVBoxLayout()
        self.week_body.setSpacing(8)
        self.week_card.add_widget(self.week_body)
        self._layout.addWidget(self.week_card)

        self._layout.addStretch(1)

    # ---------- 构建条形行 ----------
    def _make_bar_row(self, name: str, secs: int, maximum: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        name_lbl = QLabel(name)
        name_lbl.setFixedWidth(140)
        bar = QProgressBar()
        bar.setRange(0, max(1, maximum))
        bar.setValue(int(secs))
        bar.setTextVisible(False)
        bar.setStyleSheet(_BAR_STYLE)
        bar.setFixedHeight(16)
        time_lbl = QLabel(_fmt(secs))
        time_lbl.setFixedWidth(96)
        time_lbl.setObjectName("Secondary")
        row.addWidget(name_lbl)
        row.addWidget(bar, 1)
        row.addWidget(time_lbl)
        return row

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            else:
                # 嵌套布局
                lay = item.layout()
                if lay:
                    self._clear_layout(lay)

    def _fill_apps(self) -> None:
        self._clear_layout(self.apps_body)
        apps = self.ctx.screen.apps_today()
        if not apps:
            tip = QLabel("暂无可统计的软件使用时长。保持程序运行并在各软件间切换即可累计。")
            tip.setObjectName("Secondary")
            self.apps_body.addWidget(tip)
            return
        maximum = max(v for _, v in apps)
        for name, secs in apps:
            self.apps_body.addLayout(self._make_bar_row(name, secs, maximum))

    def _fill_week(self) -> None:
        self._clear_layout(self.week_body)
        week = self.ctx.screen.week_stats()
        maximum = max((s for _, s in week), default=1) or 1
        for date_str, secs in week:
            mmdd = date_str[5:]
            self.week_body.addLayout(self._make_bar_row(mmdd, secs, maximum))

    def refresh(self) -> None:
        secs = self.ctx.screen.today_seconds()
        self.total_label.setText(_fmt(secs))
        focus_secs = self.ctx.focus.today_focus_seconds()
        self.focus_label.setText(_fmt(focus_secs))
        apps = self.ctx.screen.apps_today()
        self.apps_count_label.setText(f"共使用了 {len(apps)} 个软件")
        self._fill_apps()
        self._fill_week()

    def _connect(self) -> None:
        self.ctx.screen.seconds_changed.connect(
            lambda s, d: self.refresh() if self.isVisible() else None)
