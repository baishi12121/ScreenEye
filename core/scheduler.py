"""定时切换：按时间段规则自动切换预设，并支持平滑过渡。

可选「日出日落」模式（基于经纬度）暂以规则模式回退实现，预留扩展点。
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from PyQt5.QtCore import QObject, QTimer

from core import engine
from core.config import config


def _parse_hhmm(s: str) -> int:
    """'HH:MM' -> 当天分钟数；解析失败返回 -1。"""
    try:
        h, m = s.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return -1


def match_rule(now_min: int, rules: List[dict]) -> Optional[str]:
    """返回当前时间命中的预设 key；无命中返回 None（含跨午夜规则）。"""
    for r in rules:
        s = _parse_hhmm(r.get("start", ""))
        e = _parse_hhmm(r.get("end", ""))
        preset = r.get("preset")
        if s < 0 or e < 0 or not preset:
            continue
        if s <= e:
            if s <= now_min < e:
                return preset
        else:  # 跨午夜，例如 23:00 - 06:00
            if now_min >= s or now_min < e:
                return preset
    return None


class Scheduler(QObject):
    def __init__(self, eng: engine.Engine):
        super().__init__()
        self.engine = eng
        self._last_preset: Optional[str] = None
        self._timer = QTimer(self)
        self._timer.setInterval(30 * 1000)  # 30 秒检查一次
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        if config.get("general", "schedule_enabled", default=False):
            self._last_preset = None
            self._tick()
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def reload(self) -> None:
        """设置变更后调用：按开关状态启停。"""
        if config.get("general", "schedule_enabled", default=False):
            if not self._timer.isActive():
                self.start()
        else:
            self.stop()

    def _tick(self) -> None:
        if not config.get("general", "schedule_enabled", default=False):
            return
        rules = config.get("schedule", "rules", default=[])
        now = datetime.datetime.now()
        now_min = now.hour * 60 + now.minute
        # 日出日落模式（预留）：目前直接复用规则
        if config.get("schedule", "use_sunrise_sunset", default=False):
            # TODO: 基于 latitude/longitude 计算日出日落，替换 rules 选择
            pass
        preset = match_rule(now_min, rules)
        if preset and preset != self._last_preset:
            duration = config.get("schedule", "transition_duration", default=2)
            self.engine.apply_preset_all(preset, transition=float(duration))
            self._last_preset = preset
