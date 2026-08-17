"""页面复用的小型 UI 组件。"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget,
)


class Card(QFrame):
    def __init__(self, parent=None, title: str = None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self._title = None
        if title:
            self._title = QLabel(title)
            self._title.setObjectName("Title")
            layout.addWidget(self._title)
        self.body = layout

    def add_widget(self, w) -> None:
        from PyQt5.QtWidgets import QLayout, QWidget
        if isinstance(w, QWidget):
            self.body.addWidget(w)
        elif isinstance(w, QLayout):
            self.body.addLayout(w)
        else:
            self.body.addWidget(w)


class HSeparator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("color: #3A3A3A;")


class LabeledSlider(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, text: str, suffix: str, minimum: int, maximum: int,
                 step: int, value: int, parent=None):
        super().__init__(parent)
        self.suffix = suffix
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.label = QLabel(text)
        self.value_label = QLabel(f"{value}{suffix}")
        self.value_label.setStyleSheet("color: #26C6DA; font-weight: bold;")
        row.addWidget(self.label)
        row.addStretch(1)
        row.addWidget(self.value_label)
        layout.addLayout(row)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setSingleStep(step)
        self.slider.setPageStep(step * 5)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider)

    def _on_slider(self, v: int) -> None:
        self.value_label.setText(f"{v}{self.suffix}")
        self.valueChanged.emit(v)

    def set_value(self, v: int, emit: bool = False) -> None:
        if not emit:
            self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.value_label.setText(f"{v}{self.suffix}")
        if not emit:
            self.slider.blockSignals(False)

    def set_enabled(self, ok: bool) -> None:
        self.slider.setEnabled(ok)


class PresetButton(QWidget):
    """预设按钮：可选中高亮，点击触发 clicked 信号。"""

    clicked = pyqtSignal()

    def __init__(self, name: str, key: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._selected = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn = QLabel(name)
        self.btn.setAlignment(Qt.AlignCenter)
        self.btn.setFixedHeight(34)
        self.btn.setStyleSheet(self._style(False))
        self.btn.setObjectName("Preset")
        layout.addWidget(self.btn)

    def _style(self, selected: bool) -> str:
        if selected:
            return ("background:#26C6DA; color:#10242A; border-radius:8px; "
                    "font-weight:bold; border:1px solid #26C6DA;")
        return ("background:#2E2E2E; color:#E0E0E0; border-radius:8px; "
                "border:1px solid #3A3A3A;")

    def set_selected(self, ok: bool) -> None:
        self._selected = ok
        self.btn.setStyleSheet(self._style(ok))

    def is_selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
