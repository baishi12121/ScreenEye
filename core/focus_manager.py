"""专注模块：番茄计时 + 色温联动（轻量化软专注｜方案A）。

设计原则：无侵入、不锁软件、不拦截窗口，只做计时 + 光线联动。

核心行为：
- 启动专注时快照保存当前各显示器色温/亮度（按设备），结束/重置自动还原
- 可选启动专注时自动切换到【办公】预设
- 可选专注期间暂停全局休息弹窗，避免打断思路
- 计时数据持久化（近 365 天按日记录，供专注页与统计页读取）
- 窗口最小化到托盘后计时后台持续运行；托盘右键可一键开始 25 分钟专注
"""
from __future__ import annotations

import datetime
from typing import Dict, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.config import config
from core import display_manager as dm


STATE_IDLE = "idle"
STATE_FOCUSING = "focusing"
STATE_RESTING = "resting"
STATE_PAUSED_FOCUS = "paused_focus"
STATE_PAUSED_REST = "paused_rest"

# 状态 -> 展示文字
STATE_TEXT = {
    STATE_IDLE: "等待开始",
    STATE_FOCUSING: "专注中",
    STATE_RESTING: "休息中",
    STATE_PAUSED_FOCUS: "已暂停（专注）",
    STATE_PAUSED_REST: "已暂停（休息）",
}


class FocusManager(QObject):
    # state_changed(state)
    state_changed = pyqtSignal(str)
    # tick(remaining_seconds, total_seconds, state)
    tick = pyqtSignal(int, int, str)
    # session_recorded()  —— 一次专注完成后刷新列表用
    session_recorded = pyqtSignal()
    # finished(message)   —— 一轮/一轮循环结束提示
    finished = pyqtSignal(str)

    def __init__(self, ctx=None):
        super().__init__()
        self._ctx = ctx

        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(1000)
        self._focus_timer.timeout.connect(self._on_focus_tick)

        self._rest_timer = QTimer(self)
        self._rest_timer.setInterval(1000)
        self._rest_timer.timeout.connect(self._on_rest_tick)

        self._state = STATE_IDLE
        self._focus_remaining = 0
        self._focus_total = 0
        self._rest_remaining = 0
        self._rest_total = 0
        # device_name -> {temperature, brightness, active_preset}
        self._origin: Dict[str, dict] = {}
        self._rest_paused_by_us = False

    # ---------- 配置 ----------
    def _cfg(self, key, default):
        return config.get("focus", key, default=default)

    @property
    def focus_minutes(self) -> int:
        return int(self._cfg("focus_duration", 25))

    @property
    def rest_minutes(self) -> int:
        return int(self._cfg("rest_duration", 5))

    @property
    def loop_enabled(self) -> bool:
        return bool(self._cfg("loop_enable", True))

    @property
    def auto_switch(self) -> bool:
        return bool(self._cfg("auto_switch_preset", True))

    @property
    def pause_rest(self) -> bool:
        return bool(self._cfg("pause_break_reminder", True))

    @property
    def preset_key(self) -> str:
        return str(self._cfg("preset_key", "office"))

    def set_config(self, **kw) -> None:
        for k, v in kw.items():
            config.set("focus", k, value=v)
        config.save()

    # ---------- 状态查询 ----------
    @property
    def state(self) -> str:
        return self._state

    def is_active(self) -> bool:
        return self._state in (STATE_FOCUSING, STATE_RESTING,
                               STATE_PAUSED_FOCUS, STATE_PAUSED_REST)

    def focus_remaining(self) -> int:
        return self._focus_remaining

    def rest_remaining(self) -> int:
        return self._rest_remaining

    # ---------- 快照 / 还原 ----------
    def _snapshot(self) -> None:
        self._origin = {}
        if self._ctx is None:
            return
        for dev in dm.display_manager.device_names():
            s = self._ctx.engine.get_settings(dev)
            self._origin[dev] = {
                "temperature": int(s.get("temperature", 6500)),
                "brightness": int(s.get("brightness", 100)),
                "active_preset": str(s.get("active_preset", "")),
            }

    def restore_screen(self) -> None:
        """把屏幕还原到启动专注瞬间保存的参数；还原后清空快照。"""
        if not self._origin or self._ctx is None:
            return
        for dev, s in self._origin.items():
            self._ctx.engine.set_temperature(dev, s["temperature"], apply=True)
            self._ctx.engine.set_brightness(dev, s["brightness"], apply=True)
            config.set("displays", dev, "active_preset", value=s["active_preset"])
        config.save()
        self._origin = {}

    def _pause_rest_if_needed(self) -> None:
        if not self.pause_rest or self._ctx is None:
            return
        if self._ctx.rest.is_running():
            self._ctx.rest.pause()
            self._rest_paused_by_us = True

    def _resume_rest_if_paused(self) -> None:
        if self._rest_paused_by_us and self._ctx is not None:
            self._ctx.rest.resume_timer()
            self._rest_paused_by_us = False

    # ---------- 控制 ----------
    def start(self) -> None:
        if self.is_active():
            return
        # 1. 快照当前屏幕参数
        self._snapshot()
        # 2. 自动切换办公色温
        if self.auto_switch and self._ctx is not None:
            self._ctx.engine.apply_preset_all(self.preset_key, 0)
        # 3. 暂停全局休息弹窗
        self._pause_rest_if_needed()
        # 4. 启动专注倒计时
        self._begin_focus_round()

    def _begin_focus_round(self) -> None:
        self._state = STATE_FOCUSING
        self._focus_total = max(1, self.focus_minutes * 60)
        self._focus_remaining = self._focus_total
        self._focus_timer.start()
        self.state_changed.emit(self._state)
        self.tick.emit(self._focus_remaining, self._focus_total, self._state)

    def _on_focus_tick(self) -> None:
        self._focus_remaining -= 1
        if self._focus_remaining > 0:
            self.tick.emit(self._focus_remaining, self._focus_total, self._state)
            return
        self._focus_timer.stop()
        self._on_focus_finish()

    def _on_focus_finish(self) -> None:
        # 记录本次完成的专注时长
        self._record_session(focus_seconds=self._focus_total, rest_seconds=0)

        if self.rest_minutes <= 0:
            self.finished.emit("本轮专注完成")
            self.reset_focus()
            return

        # 进入休息倒计时
        self._state = STATE_RESTING
        self._rest_total = max(1, self.rest_minutes * 60)
        self._rest_remaining = self._rest_total
        self._rest_timer.start()
        self.state_changed.emit(self._state)
        self.tick.emit(self._rest_remaining, self._rest_total, self._state)

    def _on_rest_tick(self) -> None:
        self._rest_remaining -= 1
        self.tick.emit(self._rest_remaining, self._rest_total, self._state)
        if self._rest_remaining > 0:
            return
        self._rest_timer.stop()
        if self.loop_enabled:
            # 循环模式：自动重启新一轮专注（不还原屏幕）
            self._begin_focus_round()
        else:
            self.finished.emit("休息结束，专注模式已退出")
            self.reset_focus()

    def pause_focus(self) -> None:
        if self._state == STATE_FOCUSING and self._focus_timer.isActive():
            self._focus_timer.stop()
            self._state = STATE_PAUSED_FOCUS
            self.state_changed.emit(self._state)
        elif self._state == STATE_RESTING and self._rest_timer.isActive():
            self._rest_timer.stop()
            self._state = STATE_PAUSED_REST
            self.state_changed.emit(self._state)

    def resume_focus(self) -> None:
        if self._state == STATE_PAUSED_FOCUS:
            self._state = STATE_FOCUSING
            self._focus_timer.start()
            self.state_changed.emit(self._state)
        elif self._state == STATE_PAUSED_REST:
            self._state = STATE_RESTING
            self._rest_timer.start()
            self.state_changed.emit(self._state)

    def toggle_pause(self) -> None:
        if self._state in (STATE_FOCUSING, STATE_RESTING):
            self.pause_focus()
        elif self._state in (STATE_PAUSED_FOCUS, STATE_PAUSED_REST):
            self.resume_focus()

    def reset_focus(self) -> None:
        """任意时刻重置：停止计时、还原屏幕、恢复休息弹窗、回到等待开始。"""
        self._focus_timer.stop()
        self._rest_timer.stop()
        self.restore_screen()
        self._resume_rest_if_paused()
        self._state = STATE_IDLE
        self._focus_remaining = self.focus_minutes * 60
        self._rest_remaining = self.rest_minutes * 60
        self.state_changed.emit(self._state)
        self.tick.emit(self._focus_remaining, self.focus_minutes * 60, self._state)

    # ---------- 持久化 ----------
    def _record_session(self, focus_seconds: int, rest_seconds: int) -> None:
        today = datetime.date.today().isoformat()
        hist = config.get("focus", "history", default={})
        if not isinstance(hist, dict):
            hist = {}
        records = hist.get(today, [])
        records.append({
            "start": datetime.datetime.now().strftime("%H:%M"),
            "focus_seconds": int(focus_seconds),
            "rest_seconds": int(rest_seconds),
        })
        hist[today] = records[-50:]  # 每天最多保留 50 条
        if len(hist) > 365:
            for k in sorted(hist.keys())[:-365]:
                hist.pop(k, None)
        config.set("focus", "history", value=hist)
        config.save()
        self.session_recorded.emit()

    def history(self) -> dict:
        h = config.get("focus", "history", default={})
        return h if isinstance(h, dict) else {}

    def recent_records(self, limit: int = 30) -> list:
        """返回最近的专注记录（新→旧）：[{date, start, focus_seconds}, ...]。"""
        out = []
        for date_str in sorted(self.history().keys(), reverse=True):
            for rec in self.history()[date_str]:
                out.append({
                    "date": date_str,
                    "start": rec.get("start", ""),
                    "focus_seconds": int(rec.get("focus_seconds", 0)),
                })
                if len(out) >= limit:
                    return out
        return out

    def today_focus_seconds(self) -> int:
        today = datetime.date.today().isoformat()
        return sum(int(r.get("focus_seconds", 0))
                   for r in self.history().get(today, []))
