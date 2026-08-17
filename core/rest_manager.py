"""休息模块：番茄钟计时与休息提醒状态机。

状态：idle / work / rest / long_rest
通过 Qt 信号广播状态与倒计时，UI 据此渲染全屏休息提醒。
"""
from __future__ import annotations

from typing import Tuple

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.config import config

STATE_IDLE = "idle"
STATE_WORK = "work"
STATE_REST = "rest"
STATE_LONG_REST = "long_rest"


class RestManager(QObject):
    # state_changed(state, cycle_count)
    state_changed = pyqtSignal(str, int)
    # tick(remaining_seconds, total_seconds, state)
    tick = pyqtSignal(int, int, str)
    # break_started(minutes, is_long)
    break_started = pyqtSignal(int, bool)
    # work_started()
    work_started = pyqtSignal()
    # rest_count_changed(count)
    rest_count_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._state = STATE_IDLE
        self._remaining = 0
        self._total = 0
        self._cycle = 0
        self._rest_today = self._load_today()

    # ---------- 配置 ----------
    def _cfg(self, key, default):
        return config.get("rest", key, default=default)

    @property
    def work_seconds(self) -> int:
        return int(self._cfg("work_minutes", 45)) * 60

    @property
    def rest_seconds(self) -> int:
        return int(self._cfg("rest_minutes", 5)) * 60

    @property
    def long_rest_seconds(self) -> int:
        return int(self._cfg("long_break_minutes", 15)) * 60

    @property
    def long_every(self) -> int:
        return max(1, int(self._cfg("long_break_after_cycles", 4)))

    # ---------- 今日休息次数 ----------
    def _load_today(self) -> Tuple[str, int]:
        import datetime
        today = datetime.date.today().isoformat()
        hist = config.get("rest", "today", default={})
        if hist.get("date") != today:
            config.set("rest", "today", value={"date": today, "count": 0})
            config.save()
            return today, 0
        return today, int(hist.get("count", 0))

    def _bump_rest_count(self) -> None:
        today, count = self._load_today()
        count += 1
        config.set("rest", "today", value={"date": today, "count": count})
        config.save()
        self.rest_count_changed.emit(count)

    def rest_count_today(self) -> int:
        _, count = self._load_today()
        return count

    # ---------- 控制 ----------
    def start(self) -> None:
        if self._state in (STATE_WORK, STATE_REST, STATE_LONG_REST):
            return
        self._begin_work()

    def _begin_work(self) -> None:
        self._state = STATE_WORK
        self._total = self.work_seconds
        self._remaining = self._total
        self._timer.start()
        self.state_changed.emit(self._state, self._cycle)
        self.work_started.emit()
        self.tick.emit(self._remaining, self._total, self._state)

    def pause(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        # 保持状态，仅暂停计时

    def resume_timer(self) -> None:
        if self._state != STATE_IDLE and not self._timer.isActive():
            self._timer.start()

    def reset(self) -> None:
        self._timer.stop()
        self._state = STATE_IDLE
        self._remaining = 0
        self._total = 0
        self._cycle = 0
        self.state_changed.emit(self._state, self._cycle)

    def is_running(self) -> bool:
        return self._timer.isActive()

    @property
    def state(self) -> str:
        return self._state

    def remaining(self) -> int:
        return self._remaining

    def total(self) -> int:
        return self._total

    # ---------- 计时 ----------
    def _on_tick(self) -> None:
        self._remaining -= 1
        if self._remaining > 0:
            self.tick.emit(self._remaining, self._total, self._state)
            return
        # 当前阶段结束
        if self._state == STATE_WORK:
            self._cycle += 1
            is_long = (self._cycle % self.long_every) == 0
            self._state = STATE_LONG_REST if is_long else STATE_REST
            self._total = self.long_rest_seconds if is_long else self.rest_seconds
            self._remaining = self._total
            self._timer.start()
            self.state_changed.emit(self._state, self._cycle)
            self.break_started.emit(self._total // 60, is_long)
            self._bump_rest_count()
            self.tick.emit(self._remaining, self._total, self._state)
        else:
            # 休息结束 -> 回到工作
            self._begin_work()
