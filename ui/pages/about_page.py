"""关于页面：版本、开源信息与免责声明。"""
from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.constants import app_display_name, APP_VERSION
from ui.widgets import Card


class AboutPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(14)

        card = Card(title=app_display_name())
        card.add_widget(QLabel(f"版本：{APP_VERSION}"))
        card.add_widget(QLabel(
            "一款轻量级 Windows 护眼工具，通过调节屏幕色温与亮度减轻眼部疲劳。\n"
            "核心原理：利用 Windows SetDeviceGammaRamp API 修改显卡伽马查找表，"
            "即时生效、零性能损耗。"))
        card.add_widget(QLabel(
            "功能：托盘常驻、色温/亮度调节、8 种预设、多显示器独立控制、"
            "番茄钟休息提醒、阅读/聚光专注遮罩、屏幕使用时长统计。"))
        card.add_widget(QLabel(
            "开源协议：MIT。本程序不收集任何用户数据，无网络请求。"))
        v.addWidget(card)

        note = Card(title="兼容性说明")
        note.add_widget(QLabel(
            "• 远程桌面 (RDP) 环境不支持伽马表调节。\n"
            "• 部分 HDR 模式下系统会覆盖伽马表，建议关闭 HDR 或使用 Windows 夜间模式。\n"
            "• 退出程序会自动恢复原始屏幕色彩。"))
        v.addWidget(note)
        v.addStretch(1)
