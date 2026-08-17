"""程序图标生成：用 QPainter 绘制护眼“眼睛”图标与侧边栏导航图标，避免外部资源文件。"""
from __future__ import annotations

from PyQt5.QtCore import QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from core.constants import COLOR_ACCENT, COLOR_PRIMARY


def _draw_eye(pixmap: QPixmap, color: str, bg: str = None) -> None:
    pixmap.fill(QColor(0, 0, 0, 0))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pixmap.width(), pixmap.height()
    if bg:
        p.setBrush(QColor(bg))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, w * 0.2, h * 0.2)
    # 眼形（杏仁）：用两段贝塞尔近似，这里用椭圆裁剪 + 横线
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    # 外眼白
    p.setBrush(QColor(245, 245, 245, 255))
    p.drawEllipse(int(w * 0.12), int(h * 0.34), int(w * 0.76), int(h * 0.32))
    # 虹膜（护眼绿）
    p.setBrush(QColor(COLOR_PRIMARY))
    cx, cy = w // 2, int(h * 0.5)
    r = int(h * 0.15)
    p.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
    # 瞳孔（青色高光）
    p.setBrush(QColor(COLOR_ACCENT))
    r2 = int(h * 0.07)
    p.drawEllipse(cx - r2, cy - r2, 2 * r2, 2 * r2)
    p.end()


def make_icon(state: str = "normal", size: int = 64) -> QIcon:
    """state: normal(彩色) / paused(灰) / night(青色月亮感)。"""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    if state == "paused":
        _draw_eye(pm, "#9E9E9E")
    elif state == "night":
        _draw_eye(pm, COLOR_ACCENT)
    else:
        _draw_eye(pm, COLOR_PRIMARY)
    return QIcon(pm)


def make_tray_icon(state: str = "normal") -> QIcon:
    return make_icon(state, size=32)


# ---------- 侧边栏导航图标 ----------

def _new_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    return pm


def _draw_display(pm: QPixmap, color: str) -> None:
    """显示器图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    pen_w = max(2, int(w * 0.08))
    p.setPen(QColor(color))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(color), pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    # 屏幕
    rect = QRectF(w * 0.15, h * 0.20, w * 0.70, h * 0.48)

    p.drawRoundedRect(rect, w * 0.04, h * 0.04)
    # 底座
    p.drawLine(int(w * 0.35), int(h * 0.72), int(w * 0.65), int(h * 0.72))
    p.drawLine(int(w * 0.50), int(h * 0.68), int(w * 0.50), int(h * 0.78))
    p.drawLine(int(w * 0.40), int(h * 0.80), int(w * 0.60), int(h * 0.80))
    p.end()


def _draw_rest(pm: QPixmap, color: str) -> None:
    """番茄钟/休息图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    pen_w = max(2, int(w * 0.08))
    p.setPen(QPen(QColor(color), pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    # 外圆
    p.drawEllipse(int(w * 0.18), int(h * 0.18), int(w * 0.64), int(h * 0.64))
    # 指针
    p.drawLine(int(w * 0.50), int(h * 0.32), int(w * 0.50), int(h * 0.52))
    p.drawLine(int(w * 0.50), int(h * 0.52), int(w * 0.62), int(h * 0.62))
    p.end()


def _draw_focus(pm: QPixmap, color: str) -> None:
    """专注/靶心图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    pen_w = max(2, int(w * 0.08))
    pen = QPen(QColor(color), pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    cx, cy = w // 2, h // 2
    p.drawEllipse(cx - int(w * 0.26), cy - int(h * 0.26), int(w * 0.52), int(h * 0.52))
    p.drawEllipse(cx - int(w * 0.14), cy - int(h * 0.14), int(w * 0.28), int(h * 0.28))
    p.drawPoint(cx, cy)
    p.drawLine(cx - int(w * 0.08), cy, cx + int(w * 0.08), cy)
    p.drawLine(cx, cy - int(h * 0.08), cx, cy + int(h * 0.08))
    p.end()


def _draw_stats(pm: QPixmap, color: str) -> None:
    """统计/柱状图图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    bar_w = w * 0.16
    gaps = (w - 4 * bar_w) / 5
    heights = [0.38, 0.58, 0.46, 0.70]
    for i, hei in enumerate(heights):
        x = gaps + i * (bar_w + gaps)
        y = h * (1 - hei) - h * 0.10
        p.drawRoundedRect(int(x), int(y), int(bar_w), int(h * hei), 2, 2)
    p.end()


def _draw_settings(pm: QPixmap, color: str) -> None:
    """设置/齿轮图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    pen_w = max(2, int(w * 0.08))
    p.setPen(QPen(QColor(color), pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    cx, cy = w // 2, h // 2
    outer_r = w * 0.26
    inner_r = w * 0.14
    teeth = 8
    from math import cos, sin, pi
    path = QPainterPath()
    for i in range(teeth * 2):
        angle = 2 * pi * i / (teeth * 2) - pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        x = cx + r * cos(angle)
        y = cy + r * sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    p.drawEllipse(cx - int(w * 0.08), cy - int(h * 0.08), int(w * 0.16), int(h * 0.16))
    p.end()


def _draw_about(pm: QPixmap, color: str) -> None:
    """关于/信息图标。"""
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    w, h = pm.width(), pm.height()
    pen_w = max(2, int(w * 0.08))
    p.setPen(QPen(QColor(color), pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(int(w * 0.18), int(h * 0.18), int(w * 0.64), int(h * 0.64))
    p.setBrush(QColor(color))
    p.drawEllipse(int(w * 0.46), int(h * 0.30), int(w * 0.08), int(h * 0.08))
    p.drawLine(int(w * 0.50), int(h * 0.44), int(w * 0.50), int(h * 0.72))
    p.end()


def make_nav_icon(name: str, size: int = 28, color: str = COLOR_ACCENT) -> QIcon:
    """生成侧边栏导航图标。

    name: display / rest / focus / stats / settings / about
    """
    pm = _new_pixmap(size)
    dispatch = {
        "display": _draw_display,
        "rest": _draw_rest,
        "focus": _draw_focus,
        "stats": _draw_stats,
        "settings": _draw_settings,
        "about": _draw_about,
    }
    fn = dispatch.get(name, _draw_display)
    fn(pm, color)
    return QIcon(pm)
