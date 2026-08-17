"""主窗口：左侧导航 + 右侧内容区，承载各功能页面。"""
from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSpacerItem, QStackedWidget, QSizePolicy, QVBoxLayout, QWidget,
)

from ui import icons
from core.constants import app_display_name
from ui.pages import (
    about_page, display_page, focus_page, rest_page, screen_time_page, settings_page,
)

NAV_ITEMS = [
    ("display", "显示"),
    ("rest", "休息"),
    ("focus", "专注"),
    ("stats", "统计"),
    ("settings", "设置"),
    ("about", "关于"),
]


class NavButton(QWidget):
    """左侧导航按钮：图标在上、文字在下，选中时左侧显示强调色指示条。"""

    def __init__(self, key: str, text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.text = text
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(QSize(76, 68))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(QSize(28, 28))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setPixmap(icons.make_nav_icon(key, 28, self._icon_color()).pixmap(28, 28))
        layout.addWidget(self.icon_lbl, alignment=Qt.AlignCenter)

        self.text_lbl = QLabel(text)
        self.text_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_lbl)

        self._update_style()

    def _icon_color(self) -> str:
        return "#FFFFFF" if self._selected else "#9E9E9E"

    def _update_style(self) -> None:
        selected = self._selected
        bg = "rgba(38, 198, 218, 0.12)" if selected else "transparent"
        text_color = "#26C6DA" if selected else "#BDBDBD"
        self.setStyleSheet(f"""
            NavButton {{
                background: {bg};
                border-radius: 10px;
                border-left: 3px solid {'#26C6DA' if selected else 'transparent'};
            }}
            QLabel {{
                color: {text_color};
                font-size: 10pt;
                background: transparent;
            }}
        """)
        self.icon_lbl.setPixmap(icons.make_nav_icon(self.key, 28, self._icon_color()).pixmap(28, 28))

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    clicked = pyqtSignal()


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(app_display_name())
        # 隐藏系统原生标题栏/边框，改用自定义标题栏（避免双层标题栏）
        # 同时保留 Qt.Window 以确保任务栏图标不丢失
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(880, 600)
        self.resize(960, 640)
        self._nav_buttons: list[NavButton] = []
        self._top_h = 40
        self._drag_pos = None
        self._build_ui()
        self._connect()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部栏
        top = QFrame()
        top.setFixedHeight(40)
        top.setObjectName("Card")
        top.setStyleSheet("QFrame#Card { border-radius: 0; border-bottom: 1px solid #3A3A3A; }")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(12, 0, 8, 0)
        title = QLabel(app_display_name())
        title.setObjectName("Title")
        top_layout.addWidget(title)
        top_layout.addStretch(1)
        self.btn_min = QPushButton("—")
        self.btn_min.setObjectName("WinMin")
        self.btn_min.setFixedSize(34, 28)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max = QPushButton("□")
        self.btn_max.setObjectName("WinMax")
        self.btn_max.setFixedSize(34, 28)
        self.btn_max.setCursor(Qt.PointingHandCursor)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("WinClose")
        self.btn_close.setFixedSize(34, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)
        top_layout.addWidget(self.btn_min)
        top_layout.addWidget(self.btn_max)
        top_layout.addWidget(self.btn_close)
        # 自定义标题栏按钮样式（hover 反馈，关闭按钮变红）
        top.setStyleSheet(top.styleSheet() + """
            QPushButton#WinMin, QPushButton#WinMax, QPushButton#WinClose {
                background: transparent; border: none; color: #BDBDBD;
                font-size: 13pt; border-radius: 6px;
            }
            QPushButton#WinMin:hover, QPushButton#WinMax:hover { background: #383838; }
            QPushButton#WinClose:hover { background: #E53935; color: #FFFFFF; }
        """)
        root.addWidget(top)

        # 主体：左导航 + 右内容
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        nav = QFrame()
        nav.setFixedWidth(96)
        nav.setObjectName("Card")
        nav.setStyleSheet("QFrame#Card { border-radius: 0; border-right: 1px solid #3A3A3A; }")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 14, 10, 14)
        nav_layout.setSpacing(8)
        nav_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        for key, text in NAV_ITEMS:
            btn = NavButton(key, text)
            btn.clicked.connect(lambda k=key: self._select_nav(k))
            nav_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self._nav_buttons.append(btn)

        nav_layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 内容区
        self.stack = QStackedWidget()
        self.pages = {}
        self.pages["display"] = display_page.DisplayPage(self.ctx)
        self.pages["rest"] = rest_page.RestPage(self.ctx)
        self.pages["focus"] = focus_page.FocusPage(self.ctx)
        self.pages["stats"] = screen_time_page.ScreenTimePage(self.ctx)
        self.pages["settings"] = settings_page.SettingsPage(self.ctx)
        self.pages["about"] = about_page.AboutPage(self.ctx)
        for key, _ in NAV_ITEMS:
            self.stack.addWidget(self.pages[key])

        body.addWidget(nav)
        body.addWidget(self.stack, 1)
        root.addLayout(body)

        self._select_nav("display")

    def _connect(self) -> None:
        # 引擎设置变更时刷新当前页面（如托盘/快捷键改了色温）
        self.ctx.engine.settings_changed.connect(self._on_settings_changed)
        self.ctx.engine.paused_changed.connect(self._on_paused_changed)

    def _select_nav(self, key: str) -> None:
        for i, (k, _) in enumerate(NAV_ITEMS):
            btn = self._nav_buttons[i]
            btn.set_selected(k == key)
            if k == key:
                self.stack.setCurrentIndex(i)
        # 切到某页时刷新该页数据（如专注页读取最新配置/状态）
        cur = self.stack.currentWidget()
        if hasattr(cur, "refresh"):
            cur.refresh()

    def show_page(self, name: str) -> None:
        """兼容旧的中文名调用，同时支持 key。"""
        mapping = {text: key for key, text in NAV_ITEMS}
        key = mapping.get(name, name)
        self._select_nav(key)
        self.show()
        self.raise_()

    def _on_settings_changed(self, *args) -> None:
        # 当前是显示页时刷新
        cur = self.stack.currentWidget()
        if hasattr(cur, "refresh"):
            cur.refresh()

    def _on_paused_changed(self, paused: bool) -> None:
        self.ctx.tray.set_state("paused" if paused else "normal")
        cur = self.stack.currentWidget()
        if hasattr(cur, "refresh"):
            cur.refresh()

    def closeEvent(self, event):
        # 关闭 -> 最小化到托盘，而非退出
        event.ignore()
        self.hide()

    # ---------- 无边框窗口：自行实现拖动 / 最大化 / 还原 ----------
    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("▢")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() <= self._top_h:
            child = self.childAt(event.pos())
            if not isinstance(child, QPushButton):
                if self.isMaximized():
                    self.showNormal()
                self._drag_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and (event.buttons() & Qt.LeftButton):
            delta = event.globalPos() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.y() <= self._top_h and not isinstance(self.childAt(event.pos()), QPushButton):
            self._toggle_maximize()
        super().mouseDoubleClickEvent(event)

    def set_icon(self, state: str) -> None:
        self.setWindowIcon(icons.make_icon(state))
