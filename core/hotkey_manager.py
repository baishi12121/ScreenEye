"""全局快捷键：基于 Windows RegisterHotKey + QWidget.nativeEvent。

非 Windows 环境下不可用（所有注册静默失败），不影响其余功能。
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QWidget

try:
    import ctypes
    from ctypes import wintypes
    _user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
except ImportError:  # noqa: F401
    ctypes = None
    wintypes = None
    _user32 = None

MOD_ALT = 0x1
MOD_CONTROL = 0x2
MOD_SHIFT = 0x4
MOD_WIN = 0x8
WM_HOTKEY = 0x0312

# 特殊按键 -> VK
_SPECIAL_VK = {
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "SPACE": 0x20, "TAB": 0x09, "ENTER": 0x0D, "ESC": 0x1B,
    "INS": 0x2D, "DEL": 0x2E, "HOME": 0x24, "END": 0x23,
    "PGUP": 0x21, "PGDN": 0x22,
}


def _vk_for_key(token: str) -> Optional[int]:
    token = token.strip().upper()
    if token in _SPECIAL_VK:
        return _SPECIAL_VK[token]
    if token.startswith("F") and token[1:].isdigit() and 1 <= int(token[1:]) <= 12:
        return 0x70 + int(token[1:]) - 1
    if len(token) == 1 and token.isdigit():
        return 0x30 + int(token)
    if len(token) == 1 and token.isalpha():
        if _user32 is not None:
            vk = _user32.VkKeyScanW(ord(token.upper())) & 0xFF
            return vk
        return ord(token.upper())
    # 其他：尝试 VkKeyScanW
    if _user32 is not None:
        vk = _user32.VkKeyScanW(ord(token[0])) & 0xFF
        return vk
    return None


def parse_combo(combo: str) -> Optional[Tuple[int, int]]:
    """'Ctrl+Alt+P' -> (modifiers, vk)；解析失败返回 None。"""
    if _user32 is None:
        return None
    parts = [p.strip() for p in combo.replace(" ", "").split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    key_token = None
    for p in parts:
        pu = p.upper()
        if pu == "CTRL" or pu == "CONTROL":
            mods |= MOD_CONTROL
        elif pu == "ALT":
            mods |= MOD_ALT
        elif pu == "SHIFT":
            mods |= MOD_SHIFT
        elif pu in ("WIN", "META"):
            mods |= MOD_WIN
        else:
            key_token = p  # 取最后一个非修饰键
    if key_token is None:
        return None
    vk = _vk_for_key(key_token)
    if vk is None:
        return None
    return mods, vk


class _HotkeyWindow(QWidget):
    def __init__(self, manager: "HotkeyManager"):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.Window | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_NativeWindow, True)

    def nativeEvent(self, eventType, message):  # noqa: N802
        if _user32 is not None and eventType == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self.manager._dispatch(msg.wParam)
            except Exception:  # noqa: BLE001
                pass
        return super().nativeEvent(eventType, message)


class HotkeyManager(QObject):
    def __init__(self):
        super().__init__()
        self._window = _HotkeyWindow(self) if _user32 is not None else None
        self._hwnd = int(self._window.winId()) if self._window is not None else None
        self._next_id = 1
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._registrations: List[Tuple[str, int]] = []  # (combo, id)

        if _user32 is not None:
            _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int,
                                               wintypes.UINT, wintypes.UINT]
            _user32.RegisterHotKey.restype = ctypes.c_bool
            _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            _user32.UnregisterHotKey.restype = ctypes.c_bool

    def available(self) -> bool:
        return _user32 is not None and self._hwnd is not None

    def register(self, combo: str, callback: Callable[[], None]) -> bool:
        """注册一个快捷键；成功返回 True。冲突时返回 False。"""
        if not self.available():
            return False
        parsed = parse_combo(combo)
        if parsed is None:
            return False
        mods, vk = parsed
        hid = self._next_id
        self._next_id += 1
        ok = _user32.RegisterHotKey(self._hwnd, hid, mods, vk)
        if not ok:
            return False
        self._callbacks[hid] = callback
        self._registrations.append((combo, hid))
        return True

    def unregister_all(self) -> None:
        if not self.available():
            return
        for _, hid in self._registrations:
            _user32.UnregisterHotKey(self._hwnd, hid)
            self._callbacks.pop(hid, None)
        self._registrations.clear()

    def reregister(self, combos: Dict[str, Callable[[], None]]) -> List[str]:
        """批量注册，返回注册失败的 combo 列表。"""
        self.unregister_all()
        failed = []
        for combo, cb in combos.items():
            if not self.register(combo, cb):
                failed.append(combo)
        return failed

    def _dispatch(self, hid: int) -> None:
        cb = self._callbacks.get(int(hid))
        if cb is not None:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                print(f"[Hotkey] 回调异常: {exc}")
