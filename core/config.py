r"""配置管理：JSON 读写、默认值合并、损坏备份、迁移。

配置文件路径：%APPDATA%\CareUEyes\config.json
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import threading
from typing import Any

from core.constants import (
    APP_NAME,
    BRIGHTNESS_DEFAULT,
    CONFIG_PATH,
    TEMP_DEFAULT,
    builtin_preset_dict,
)


def default_config() -> dict:
    """返回一份全新的默认配置（与 PRD 4.9 结构一致）。"""
    return {
        "version": "1.0",
        "general": {
            "autostart": False,
            "minimize_to_tray": True,
            "hotkeys_enabled": True,
            "schedule_enabled": False,
            "fullscreen_dnd": True,
        },
        "displays": {
            "default": {
                "temperature": TEMP_DEFAULT,
                "brightness": BRIGHTNESS_DEFAULT,
                "active_preset": "health",
            }
        },
        "presets": {
            "builtin": builtin_preset_dict(),
            "custom": [],
        },
        "schedule": {
            "rules": [
                {"start": "06:00", "end": "18:00", "preset": "health"},
                {"start": "18:00", "end": "21:00", "preset": "office"},
                {"start": "21:00", "end": "23:00", "preset": "read"},
                {"start": "23:00", "end": "06:00", "preset": "read"},
            ],
            "transition_duration": 2,
            "use_sunrise_sunset": False,
            "latitude": None,
            "longitude": None,
        },
        "hotkeys": {
            "toggle_pause": "Ctrl+Alt+P",
            "preset_1": "Ctrl+Alt+1",
            "preset_2": "Ctrl+Alt+2",
            "preset_3": "Ctrl+Alt+3",
            "preset_4": "Ctrl+Alt+4",
            "temp_up": "Ctrl+Alt+Up",
            "temp_down": "Ctrl+Alt+Down",
            "focus_toggle": "Ctrl+Alt+F",
        },
        "ui": {
            "theme": "dark",
            "launch_minimized": True,
            "toast_notifications": True,
            "language": "zh-CN",
        },
        "rest": {
            "enabled": False,
            "work_minutes": 45,
            "rest_minutes": 5,
            "long_break_minutes": 15,
            "long_break_after_cycles": 4,
            "auto_start_timer": False,
            "play_sound": True,
        },
        "focus": {
            "focus_duration": 25,
            "rest_duration": 5,
            "loop_enable": True,
            "auto_switch_preset": True,
            "pause_break_reminder": True,
            "preset_key": "office",
            "history": {},
        },
        "screen_time": {
            "enabled": True,
            "idle_threshold_seconds": 120,
            "daily_goal_minutes": 480,
            "remind_interval_minutes": 60,
            "remind_when_exceed_goal": True,
            "history": {},
        },
    }


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并：以 base 为模板，用 override 中存在的键覆盖（不删除 base 多余键）。"""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Config:
    """线程安全的配置管理单例（模块内单例，按路径加载）。"""

    _instance: "Config | None" = None
    _lock = threading.Lock()

    def __new__(cls, path: str = CONFIG_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str = CONFIG_PATH):
        if getattr(self, "_initialized", False):
            return
        self.path = path
        self._data = default_config()
        self._save_lock = threading.Lock()
        self._initialized = True
        self.load()

    # ---------- 读写 ----------
    def load(self) -> None:
        if not os.path.exists(self.path):
            self._data = default_config()
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("配置文件根节点不是对象")
            self._data = _deep_merge(default_config(), raw)
        except Exception as exc:  # noqa: BLE001
            # 损坏文件：备份后使用默认配置
            backup = self.path + ".corrupt." + str(os.getpid())
            try:
                shutil.copyfile(self.path, backup)
            except OSError:
                backup = ""
            print(f"[Config] 配置文件损坏，已使用默认配置并备份至 {backup}: {exc}")
            self._data = default_config()
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with self._save_lock:
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            except OSError as exc:
                print(f"[Config] 保存配置失败: {exc}")
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass

    # ---------- 访问器 ----------
    def get(self, *keys, default: Any = None) -> Any:
        node: Any = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, *keys, value: Any) -> None:
        if not keys:
            return
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)


# 模块级便捷实例
config = Config()
