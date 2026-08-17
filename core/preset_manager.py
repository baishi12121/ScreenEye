"""预设管理：内置预设（只读）与自定义预设的增删改查。

内置预设定义在 core.constants.BUILTIN_PRESETS。
自定义预设持久化在 config["presets"]["custom"]，结构为
[{name, temperature, brightness}, ...]。
"""
from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from core.config import config
from core.constants import BUILTIN_PRESETS

MAX_CUSTOM = 10

# key -> (temperature, brightness, name)
BuiltinMap = Dict[str, Dict[str, object]]


def builtin_presets() -> Dict[str, Dict[str, object]]:
    """返回内置预设字典（来自常量）。"""
    result: Dict[str, Dict[str, object]] = {}
    for key, name, temp, bright, desc in BUILTIN_PRESETS:
        result[key] = {
            "temperature": temp,
            "brightness": bright,
            "name": name,
            "description": desc,
        }
    return result


def custom_presets() -> List[Dict[str, object]]:
    raw = config.get("presets", "custom", default=[])
    if not isinstance(raw, list):
        return []
    return [dict(p) for p in raw]


def custom_key(index: int) -> str:
    return f"custom_{index}"


def get_preset(key: str) -> Optional[Dict[str, object]]:
    """按 key 返回 {temperature, brightness, name}；找不到返回 None。

    内置 key 直接查表；custom_N 查自定义列表第 N 项。
    """
    builtin = builtin_presets()
    if key in builtin:
        return dict(builtin[key])  # type: ignore[arg-type]
    if key.startswith("custom_"):
        try:
            idx = int(key.split("_", 1)[1])
        except ValueError:
            return None
        customs = custom_presets()
        if 0 <= idx < len(customs):
            p = dict(customs[idx])
            p["name"] = p.get("name", f"自定义 {idx + 1}")
            return p
    return None


def add_custom(name: str, temperature: int, brightness: int) -> Optional[str]:
    """新增自定义预设，返回其 key；达到上限返回 None。"""
    customs = custom_presets()
    if len(customs) >= MAX_CUSTOM:
        return None
    customs.append({"name": name, "temperature": int(temperature), "brightness": int(brightness)})
    config.set("presets", "custom", value=customs)
    config.save()
    return custom_key(len(customs) - 1)


def update_custom(index: int, name: Optional[str] = None,
                  temperature: Optional[int] = None,
                  brightness: Optional[int] = None) -> bool:
    customs = custom_presets()
    if not (0 <= index < len(customs)):
        return False
    if name is not None:
        customs[index]["name"] = name
    if temperature is not None:
        customs[index]["temperature"] = int(temperature)
    if brightness is not None:
        customs[index]["brightness"] = int(brightness)
    config.set("presets", "custom", value=customs)
    config.save()
    return True


def delete_custom(index: int) -> bool:
    customs = custom_presets()
    if not (0 <= index < len(customs)):
        return False
    customs.pop(index)
    config.set("presets", "custom", value=customs)
    config.save()
    return True


def rename_custom(index: int, name: str) -> bool:
    return update_custom(index, name=name)


def reorder_custom(order: List[int]) -> bool:
    """按新的索引顺序重排自定义预设。"""
    customs = custom_presets()
    if sorted(order) != list(range(len(customs))):
        return False
    new_list = [copy.deepcopy(customs[i]) for i in order]
    config.set("presets", "custom", value=new_list)
    config.save()
    return True
