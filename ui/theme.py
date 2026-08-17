"""主题管理：暗黑 / 浅色 / 跟随系统 的 QSS 与应用。

主题色参见 PRD 7.7。跟随系统在 Windows 上读取注册表 AppsUseLightTheme。
"""
from __future__ import annotations

import sys

from core.constants import (
    COLOR_ACCENT,
    COLOR_BG_DARK,
    COLOR_BORDER_DARK,
    COLOR_CARD_DARK,
    COLOR_PRIMARY,
    COLOR_TEXT_DARK,
    COLOR_TEXT_SECONDARY_DARK,
)

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_SYSTEM = "system"


def _system_is_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return val == 0
    except Exception:
        return True


def resolve_theme(theme: str) -> str:
    if theme == THEME_SYSTEM:
        return THEME_DARK if _system_is_dark() else THEME_LIGHT
    return theme


def _dark_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_DARK};
        font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-size: 10pt;
    }}
    QFrame#Card {{
        background-color: {COLOR_CARD_DARK};
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 10px;
    }}
    QLabel#Title {{ font-size: 13pt; font-weight: bold; color: {COLOR_TEXT_DARK}; }}
    QLabel#Secondary {{ color: {COLOR_TEXT_SECONDARY_DARK}; }}
    QPushButton {{
        background-color: #2E2E2E;
        color: {COLOR_TEXT_DARK};
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 8px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{ background-color: #383838; border-color: {COLOR_ACCENT}; }}
    QPushButton:pressed {{ background-color: #303030; }}
    QPushButton:checked, QPushButton#Active {{
        background-color: {COLOR_ACCENT};
        color: #10242A;
        border: 1px solid {COLOR_ACCENT};
        font-weight: bold;
    }}
    QPushButton#Preset:hover {{ border-color: {COLOR_ACCENT}; }}
    QComboBox, QSpinBox, QLineEdit {{
        background-color: #2E2E2E;
        color: {COLOR_TEXT_DARK};
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLOR_CARD_DARK};
        color: {COLOR_TEXT_DARK};
        selection-background-color: {COLOR_ACCENT};
    }}
    QSlider::groove:horizontal {{
        height: 8px; border-radius: 4px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FF8A65, stop:1 #E0F7FA);
    }}
    QSlider::sub-page:horizontal {{ background: transparent; }}
    QSlider::handle:horizontal {{
        width: 18px; height: 18px; margin: -6px 0;
        border-radius: 9px; background: {COLOR_ACCENT};
        border: 2px solid #FFFFFF;
    }}
    QTabWidget::pane {{ border: 1px solid {COLOR_BORDER_DARK}; border-radius: 8px; }}
    QTabBar::tab {{
        background: #2A2A2A; color: {COLOR_TEXT_DARK};
        padding: 6px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{ background: {COLOR_ACCENT}; color: #10242A; font-weight: bold; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:checked {{ background: {COLOR_PRIMARY}; border-radius: 4px; }}
    NavButton:hover {{ background: rgba(255,255,255,0.04); }}
    NavButton QLabel {{ background: transparent; }}
    QScrollBar:vertical {{ width: 10px; background: {COLOR_CARD_DARK}; }}
    QScrollBar::handle:vertical {{ background: #444; border-radius: 5px; }}
    QToolTip {{
        background: {COLOR_CARD_DARK}; color: {COLOR_TEXT_DARK};
        border: 1px solid {COLOR_BORDER_DARK}; border-radius: 6px;
    }}
    """


def _light_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: #F5F5F5;
        color: #212121;
        font-family: "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-size: 10pt;
    }}
    QFrame#Card {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
    }}
    QLabel#Title {{ font-size: 13pt; font-weight: bold; color: #212121; }}
    QLabel#Secondary {{ color: #757575; }}
    QPushButton {{
        background-color: #FFFFFF; color: #212121;
        border: 1px solid #D0D0D0; border-radius: 8px; padding: 6px 12px;
    }}
    QPushButton:hover {{ border-color: {COLOR_ACCENT}; }}
    QPushButton:checked, QPushButton#Active {{
        background-color: {COLOR_ACCENT}; color: #10242A;
        border: 1px solid {COLOR_ACCENT}; font-weight: bold;
    }}
    QComboBox, QSpinBox, QLineEdit {{
        background-color: #FFFFFF; color: #212121;
        border: 1px solid #D0D0D0; border-radius: 6px; padding: 4px 8px;
    }}
    QComboBox QAbstractItemView {{ background: #FFFFFF; color: #212121; }}
    QSlider::groove:horizontal {{
        height: 8px; border-radius: 4px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #FF8A65, stop:1 #E0F7FA);
    }}
    QSlider::handle:horizontal {{
        width: 18px; height: 18px; margin: -6px 0;
        border-radius: 9px; background: {COLOR_ACCENT}; border: 2px solid #FFF;
    }}
    QTabWidget::pane {{ border: 1px solid #E0E0E0; border-radius: 8px; }}
    QTabBar::tab {{
        background: #ECECEC; color: #212121; padding: 6px 14px;
        border-top-left-radius: 6px; border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{ background: {COLOR_ACCENT}; color: #10242A; font-weight: bold; }}
    NavButton:hover {{ background: rgba(0,0,0,0.04); }}
    NavButton QLabel {{ background: transparent; }}
    QToolTip {{ background: #FFFFFF; color: #212121; border: 1px solid #D0D0D0; }}
    """


def stylesheet(theme: str) -> str:
    t = resolve_theme(theme)
    return _dark_stylesheet() if t == THEME_DARK else _light_stylesheet()


def apply_theme(app, theme: str) -> None:
    app.setStyleSheet(stylesheet(theme))


def current_palette_is_dark(theme: str) -> bool:
    return resolve_theme(theme) == THEME_DARK
