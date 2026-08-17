r"""开机自启：写入/读取 Windows 注册表 HKCU\...\Run。

仅操作当前用户（HKCU），无需管理员权限。
"""
from __future__ import annotations

import os
import sys

try:
    import winreg
except ImportError:  # 非 Windows
    winreg = None

from core.constants import APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _exe_path() -> str:
    """当前可执行文件路径；打包后(program).exe 即 sys.executable。"""
    return sys.executable


def set_autostart(enabled: bool) -> bool:
    """设置开机自启。成功返回 True。"""
    if winreg is None:
        return False
    exe = _exe_path()
    value = f'"{exe}" --minimized'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except OSError as exc:
        print(f"[Autostart] 写入注册表失败: {exc}")
        return False


def is_autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False
