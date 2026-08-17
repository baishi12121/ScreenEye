"""设置页面：常规、计时器、显示、快捷键、规则 五个标签。"""
from __future__ import annotations

from PyQt5.QtCore import QTime, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QInputDialog, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QRadioButton, QScrollArea, QSpinBox, QTabWidget, QTimeEdit,
    QVBoxLayout, QWidget,
)

from core import preset_manager
from core.config import config
from core.constants import BUILTIN_PRESETS
from ui.widgets import Card


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self._root = QVBoxLayout(inner)
        self._root.setContentsMargins(16, 16, 16, 16)
        self._root.setSpacing(14)
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self.tabs = QTabWidget()
        self.tab_general = QWidget()
        self.tab_timer = QWidget()
        self.tab_display = QWidget()
        self.tab_hotkey = QWidget()
        self.tab_rules = QWidget()
        self.tabs.addTab(self.tab_general, "常规")
        self.tabs.addTab(self.tab_timer, "计时器")
        self.tabs.addTab(self.tab_display, "显示")
        self.tabs.addTab(self.tab_hotkey, "快捷键")
        self.tabs.addTab(self.tab_rules, "规则")
        self._root.addWidget(self.tabs)
        self._root.addStretch(1)

        self._build_general()
        self._build_timer()
        self._build_display()
        self._build_hotkey()
        self._build_rules()

    # ---------- 常规 ----------
    def _build_general(self) -> None:
        v = QVBoxLayout(self.tab_general)
        v.setSpacing(14)
        card = Card(title="常规")
        form = QFormLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["简体中文", "English"])
        self.lang_combo.setCurrentText("简体中文")
        form.addRow("语言", self.lang_combo)

        self.autostart_chk = QCheckBox("随系统自启动")
        self.minimize_chk = QCheckBox("最小化到托盘")
        self.dnd_chk = QCheckBox("全屏免打扰（全屏时静默）")
        self.toast_chk = QCheckBox("气泡通知")
        for c in (self.autostart_chk, self.minimize_chk, self.dnd_chk, self.toast_chk):
            c.toggled.connect(self._on_general_toggle)
        form.addRow(self.autostart_chk)
        form.addRow(self.minimize_chk)
        form.addRow(self.dnd_chk)
        form.addRow(self.toast_chk)
        card.add_widget(form)
        v.addWidget(card)

        theme_card = Card(title="应用程序外观")
        self.theme_group = QButtonGroup(theme_card)
        self.theme_group.setExclusive(True)
        self.rb_system = QRadioButton("跟随系统")
        self.rb_light = QRadioButton("浅色")
        self.rb_dark = QRadioButton("暗黑")
        for rb in (self.rb_system, self.rb_light, self.rb_dark):
            self.theme_group.addButton(rb)
            rb.toggled.connect(self._on_theme)
        trow = QHBoxLayout()
        trow.addWidget(self.rb_system)
        trow.addWidget(self.rb_light)
        trow.addWidget(self.rb_dark)
        theme_card.add_widget(trow)
        v.addWidget(theme_card)
        v.addStretch(1)

    def _on_general_toggle(self) -> None:
        config.set("general", "autostart", value=self.autostart_chk.isChecked())
        config.set("general", "minimize_to_tray", value=self.minimize_chk.isChecked())
        config.set("general", "fullscreen_dnd", value=self.dnd_chk.isChecked())
        config.set("ui", "toast_notifications", value=self.toast_chk.isChecked())
        config.save()
        # 同步注册表自启
        from core import autostart
        autostart.set_autostart(self.autostart_chk.isChecked())

    def _on_theme(self, checked: bool) -> None:
        if not checked:
            return
        theme = ("system" if self.rb_system.isChecked() else
                 "light" if self.rb_light.isChecked() else "dark")
        config.set("ui", "theme", value=theme)
        config.save()
        self.ctx.reload_theme()

    # ---------- 计时器 ----------
    def _build_timer(self) -> None:
        v = QVBoxLayout(self.tab_timer)
        v.setSpacing(14)
        rest_card = Card(title="番茄钟")
        grid = QFormLayout()
        self.t_work = QSpinBox(); self.t_work.setRange(5, 120)
        self.t_rest = QSpinBox(); self.t_rest.setRange(1, 30)
        self.t_long = QSpinBox(); self.t_long.setRange(5, 60)
        self.t_cycle = QSpinBox(); self.t_cycle.setRange(1, 12)
        grid.addRow("工作（分钟）", self.t_work)
        grid.addRow("休息（分钟）", self.t_rest)
        grid.addRow("长休息（分钟）", self.t_long)
        grid.addRow("长休息间隔（周期）", self.t_cycle)
        rest_card.add_widget(grid)
        for w, key in ((self.t_work, "work_minutes"), (self.t_rest, "rest_minutes"),
                      (self.t_long, "long_break_minutes"), (self.t_cycle, "long_break_after_cycles")):
            w.valueChanged.connect(lambda val, k=key: (config.set("rest", k, value=val), config.save()))
        v.addWidget(rest_card)

        st_card = Card(title="屏幕使用时长")
        sg = QFormLayout()
        self.st_enable = QCheckBox("启用屏幕时长统计")
        self.st_goal = QSpinBox(); self.st_goal.setRange(60, 1440)
        self.st_idle = QSpinBox(); self.st_idle.setRange(10, 600)
        self.st_interval = QSpinBox(); self.st_interval.setRange(0, 240)
        sg.addRow(self.st_enable)
        sg.addRow("每日目标（分钟）", self.st_goal)
        sg.addRow("闲置阈值（秒）", self.st_idle)
        sg.addRow("连续使用提醒间隔（分钟，0=关）", self.st_interval)
        st_card.add_widget(sg)
        self.st_enable.toggled.connect(lambda c: (config.set("screen_time", "enabled", value=c), config.save()))
        self.st_goal.valueChanged.connect(lambda val: (config.set("screen_time", "daily_goal_minutes", value=val), config.save()))
        self.st_idle.valueChanged.connect(lambda val: (config.set("screen_time", "idle_threshold_seconds", value=val), config.save()))
        self.st_interval.valueChanged.connect(lambda val: (config.set("screen_time", "remind_interval_minutes", value=val), config.save()))
        v.addWidget(st_card)
        v.addStretch(1)

    # ---------- 显示（自定义预设管理） ----------
    def _build_display(self) -> None:
        v = QVBoxLayout(self.tab_display)
        v.setSpacing(14)
        card = Card(title="自定义预设管理")
        self.preset_list = QListWidget()
        card.add_widget(self.preset_list)
        brow = QHBoxLayout()
        self.rename_btn = QPushButton("重命名")
        self.del_btn = QPushButton("删除")
        brow.addWidget(self.rename_btn)
        brow.addWidget(self.del_btn)
        card.add_widget(brow)
        self.rename_btn.clicked.connect(self._rename_custom)
        self.del_btn.clicked.connect(self._delete_custom)
        v.addWidget(card)

        reset_card = Card(title="重置")
        rb = QPushButton("将所有显示器恢复为默认设置")
        rb.clicked.connect(self._reset_displays)
        reset_card.add_widget(rb)
        v.addWidget(reset_card)
        v.addStretch(1)
        self._fill_custom()

    def _fill_custom(self) -> None:
        self.preset_list.clear()
        for i, p in enumerate(preset_manager.custom_presets()):
            item = QListWidgetItem(f"{p.get('name', '自定义')}  ({p.get('temperature')}K / {p.get('brightness')}%)")
            item.setData(Qt.UserRole, i)
            self.preset_list.addItem(item)

    def _rename_custom(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return
        idx = item.data(Qt.UserRole)
        name, ok = QInputDialog.getText(self, "重命名预设", "名称：",
                                        text=preset_manager.custom_presets()[idx].get("name", ""))
        if ok and name.strip():
            preset_manager.rename_custom(idx, name.strip())
            self._fill_custom()

    def _delete_custom(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return
        idx = item.data(Qt.UserRole)
        preset_manager.delete_custom(idx)
        self._fill_custom()

    def _reset_displays(self) -> None:
        displays = config.get("displays", default={})
        displays.pop("default", None)
        for k in list(displays.keys()):
            displays.pop(k, None)
        config.set("displays", value={"default": {"temperature": 6500, "brightness": 100, "active_preset": "health"}})
        config.save()

    # ---------- 快捷键 ----------
    def _build_hotkey(self) -> None:
        v = QVBoxLayout(self.tab_hotkey)
        v.setSpacing(14)
        card = Card(title="全局快捷键")
        from PyQt5.QtWidgets import QKeySequenceEdit
        self.hk_edits = {}
        rows = [
            ("toggle_pause", "暂停/恢复色温"),
            ("preset_1", "切换到日间模式"),
            ("preset_2", "切换到办公模式"),
            ("preset_3", "切换到暖光模式"),
            ("preset_4", "切换到夜间模式"),
            ("temp_up", "色温 +100K"),
            ("temp_down", "色温 -100K"),
            ("focus_toggle", "专注模式开关"),
        ]
        form = QFormLayout()
        for key, label in rows:
            edit = QKeySequenceEdit()
            edit.editingFinished.connect(lambda k=key, e=edit: self._on_hotkey(k, e))
            self.hk_edits[key] = edit
            form.addRow(label, edit)
        card.add_widget(form)
        v.addWidget(card)
        v.addStretch(1)

    def _on_hotkey(self, key: str, edit) -> None:
        seq = edit.keySequence()
        if seq.isEmpty():
            return
        text = seq.toString()
        config.set("hotkeys", key, value=text)
        config.save()
        failed = self.ctx.reregister_hotkeys()
        if failed:
            self.ctx.toast("快捷键", f"以下快捷键注册失败（可能冲突）：{', '.join(failed)}")

    # ---------- 规则 ----------
    def _build_rules(self) -> None:
        v = QVBoxLayout(self.tab_rules)
        v.setSpacing(14)
        card = Card(title="定时切换时间表")
        self.rule_enable = QCheckBox("启用定时切换")
        self.rule_enable.toggled.connect(self._on_rule_enable)
        card.add_widget(self.rule_enable)
        self.rule_trans = QSpinBox()
        self.rule_trans.setRange(0, 10)
        self.rule_trans.setSuffix(" 秒")
        self.rule_trans.valueChanged.connect(lambda val: (config.set("schedule", "transition_duration", value=val), config.save()))
        rrow = QHBoxLayout()
        rrow.addWidget(QLabel("过渡时长"))
        rrow.addWidget(self.rule_trans)
        rrow.addStretch(1)
        card.add_widget(rrow)

        self.rule_list = QVBoxLayout()
        card.add_widget(self.rule_list)
        add_btn = QPushButton("添加规则")
        add_btn.clicked.connect(self._add_rule)
        card.add_widget(add_btn)
        v.addWidget(card)
        v.addStretch(1)
        self._fill_rules()

    def _preset_combo(self) -> QComboBox:
        cb = QComboBox()
        for key, name, _, _, _ in BUILTIN_PRESETS:
            cb.addItem(name, key)
        for i, p in enumerate(preset_manager.custom_presets()):
            cb.addItem(p.get("name", f"自定义{i+1}"), preset_manager.custom_key(i))
        return cb

    def _fill_rules(self) -> None:
        # 清空
        while self.rule_list.count():
            item = self.rule_list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        rules = config.get("schedule", "rules", default=[])
        for i, r in enumerate(rules):
            self._add_rule_row(i, r)

    def _add_rule_row(self, index: int, r: dict) -> None:
        row = QHBoxLayout()
        start = QTimeEdit()
        end = QTimeEdit()
        try:
            sh, sm = r.get("start", "06:00").split(":")
            eh, em = r.get("end", "18:00").split(":")
            start.setTime(QTime(int(sh), int(sm)))
            end.setTime(QTime(int(eh), int(em)))
        except Exception:
            pass
        preset = self._preset_combo()
        preset_key = r.get("preset", "health")
        idx = preset.findData(preset_key)
        if idx >= 0:
            preset.setCurrentIndex(idx)

        def _save():
            rules = config.get("schedule", "rules", default=[])
            rules[index] = {
                "start": start.time().toString("HH:mm"),
                "end": end.time().toString("HH:mm"),
                "preset": preset.currentData(),
            }
            config.set("schedule", "rules", value=rules)
            config.save()
            self.ctx.scheduler.reload()
        start.timeChanged.connect(lambda: _save())
        end.timeChanged.connect(lambda: _save())
        preset.currentIndexChanged.connect(lambda: _save())

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda: self._delete_rule(index))
        row.addWidget(start)
        row.addWidget(QLabel("→"))
        row.addWidget(end)
        row.addWidget(preset)
        row.addWidget(del_btn)
        self.rule_list.addLayout(row)

    def _add_rule(self) -> None:
        rules = config.get("schedule", "rules", default=[])
        rules.append({"start": "12:00", "end": "13:00", "preset": "health"})
        config.set("schedule", "rules", value=rules)
        config.save()
        self._fill_rules()

    def _delete_rule(self, index: int) -> None:
        rules = config.get("schedule", "rules", default=[])
        if 0 <= index < len(rules):
            rules.pop(index)
            config.set("schedule", "rules", value=rules)
            config.save()
        self._fill_rules()

    def _on_rule_enable(self, checked: bool) -> None:
        config.set("general", "schedule_enabled", value=checked)
        config.save()
        self.ctx.scheduler.reload()

    # ---------- 加载 ----------
    def _load(self) -> None:
        self.lang_combo.setCurrentText(config.get("ui", "language", default="zh-CN"))
        self.autostart_chk.setChecked(config.get("general", "autostart", default=False))
        self.minimize_chk.setChecked(config.get("general", "minimize_to_tray", default=False))
        self.dnd_chk.setChecked(config.get("general", "fullscreen_dnd", default=True))
        self.toast_chk.setChecked(config.get("ui", "toast_notifications", default=True))
        theme = config.get("ui", "theme", default="dark")
        (self.rb_system if theme == "system" else
         self.rb_light if theme == "light" else self.rb_dark).setChecked(True)

        self.t_work.setValue(config.get("rest", "work_minutes", default=45))
        self.t_rest.setValue(config.get("rest", "rest_minutes", default=5))
        self.t_long.setValue(config.get("rest", "long_break_minutes", default=15))
        self.t_cycle.setValue(config.get("rest", "long_break_after_cycles", default=4))
        self.st_enable.setChecked(config.get("screen_time", "enabled", default=True))
        self.st_goal.setValue(config.get("screen_time", "daily_goal_minutes", default=480))
        self.st_idle.setValue(config.get("screen_time", "idle_threshold_seconds", default=120))
        self.st_interval.setValue(config.get("screen_time", "remind_interval_minutes", default=60))

        for key, edit in self.hk_edits.items():
            val = config.get("hotkeys", key, default="")
            if val:
                edit.setKeySequence(QKeySequence(val))

        self.rule_enable.setChecked(config.get("general", "schedule_enabled", default=False))
        self.rule_trans.setValue(config.get("schedule", "transition_duration", default=2))
