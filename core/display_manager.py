"""显示器管理：枚举、友好名称、每显示器 HDC、伽马表应用、热插拔检测。

通过 ctypes 调用 user32/gdi32（Windows 专属）。非 Windows 环境下导入不会崩溃，
但运行时功能不可用（构造时记录不可用状态）。
"""
from __future__ import annotations

import ctypes
import threading
from typing import Dict, List, Optional, Tuple

from core import gamma_controller
from core.gamma_controller import GammaRamp

# ---------- ctypes 结构 ----------
if hasattr(ctypes, "windll"):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
else:  # 非 Windows（仅用于导入/语法兼容）
    user32 = None
    gdi32 = None


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
        ("szDevice", ctypes.c_wchar * 32),
    ]


class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", ctypes.c_ulong),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p
)

_MONITORINFOF_PRIMARY = 0x1


class DisplayInfo:
    def __init__(self, device_name: str, friendly_name: str, is_primary: bool,
                 rect: Tuple[int, int, int, int]):
        self.device_name = device_name
        self.friendly_name = friendly_name
        self.is_primary = is_primary
        self.rect = rect

    @property
    def label(self) -> str:
        base = self.friendly_name or self.device_name
        if self.is_primary:
            base += " (主屏)"
        return base

    def __repr__(self):
        return f"Display({self.device_name}, {self.friendly_name}, primary={self.is_primary})"


class DisplayManager:
    def __init__(self):
        self._available = user32 is not None and gdi32 is not None
        self._lock = threading.Lock()
        self._monitors: List[DisplayInfo] = []
        self._original_ramps: Dict[str, GammaRamp] = {}

    # ---------- 枚举 ----------
    def refresh(self) -> List[DisplayInfo]:
        """重新枚举显示器，返回 DisplayInfo 列表。"""
        if not self._available:
            return self._monitors
        monitors: List[DisplayInfo] = []

        def callback(hmonitor, hdc, rect, lparam):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                device_name = info.szDevice
                is_primary = bool(info.dwFlags & _MONITORINFOF_PRIMARY)
                friendly = self._friendly_name(device_name)
                monitors.append(
                    DisplayInfo(
                        device_name,
                        friendly,
                        is_primary,
                        (info.rcMonitor.left, info.rcMonitor.top,
                         info.rcMonitor.right, info.rcMonitor.bottom),
                    )
                )
            return True

        proc = MONITORENUMPROC(callback)
        user32.EnumDisplayMonitors(0, None, proc, 0)
        with self._lock:
            self._monitors = monitors
        return monitors

    def _friendly_name(self, device_name: str) -> str:
        dev = DISPLAY_DEVICE()
        dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
        if user32.EnumDisplayDevicesW(device_name, 0, ctypes.byref(dev), 0):
            name = dev.DeviceString.strip()
            if name:
                return name
        return ""

    def monitors(self) -> List[DisplayInfo]:
        with self._lock:
            return list(self._monitors)

    def get_by_device(self, device_name: str) -> Optional[DisplayInfo]:
        with self._lock:
            for m in self._monitors:
                if m.device_name == device_name:
                    return m
        return None

    def primary(self) -> Optional[DisplayInfo]:
        with self._lock:
            for m in self._monitors:
                if m.is_primary:
                    return m
        return self._monitors[0] if self._monitors else None

    def device_names(self) -> List[str]:
        return [m.device_name for m in self.monitors()]

    # ---------- 伽马表应用 ----------
    @staticmethod
    def _ramp_to_buffer(ramp: GammaRamp) -> "ctypes.Array":
        buf = (ctypes.c_uint16 * 768)()
        for i in range(256):
            buf[i] = ramp[i][0]
            buf[256 + i] = ramp[i][1]
            buf[512 + i] = ramp[i][2]
        return buf

    def _create_dc(self, device_name: str) -> Optional[int]:
        if not self._available:
            return None
        # CreateDCW("DISPLAY", device_name, NULL, NULL)
        hdc = gdi32.CreateDCW("DISPLAY", device_name, None, None)
        if not hdc or hdc == 0:
            return None
        return int(hdc)

    def apply_ramp(self, device_name: str, ramp: GammaRamp) -> bool:
        """将伽马表应用到指定显示器。成功返回 True。"""
        if not self._available:
            return False
        hdc = self._create_dc(device_name)
        if hdc is None:
            return False
        try:
            buf = self._ramp_to_buffer(ramp)
            ok = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(buf))
            return bool(ok)
        finally:
            gdi32.DeleteDC(hdc)

    def apply_all(self, ramp: GammaRamp) -> None:
        for dev in self.monitors():
            self.apply_ramp(dev.device_name, ramp)

    def get_current_ramp(self, device_name: str) -> Optional[GammaRamp]:
        """读取当前伽马表（用于启动捕获/恢复）。不支持时返回 None。"""
        if not self._available:
            return None
        hdc = self._create_dc(device_name)
        if hdc is None:
            return None
        try:
            buf = (ctypes.c_uint16 * 768)()
            ok = gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(buf))
            if not ok:
                return None
            ramp: GammaRamp = []
            for i in range(256):
                ramp.append((buf[i], buf[256 + i], buf[512 + i]))
            return ramp
        finally:
            gdi32.DeleteDC(hdc)

    # ---------- 原始状态捕获 / 恢复 ----------
    def capture_original(self) -> None:
        """启动时捕获每块显示器的原始伽马表。"""
        self._original_ramps.clear()
        for dev in self.monitors():
            ramp = self.get_current_ramp(dev.device_name)
            if ramp is not None:
                self._original_ramps[dev.device_name] = ramp

    def restore_original(self) -> None:
        """恢复启动时的原始伽马表；未捕获的显示器恢复为身份表。"""
        if not self._available:
            return
        for dev in self.monitors():
            ramp = self._original_ramps.get(dev.device_name, gamma_controller.IDENTITY_GAMMA)
            self.apply_ramp(dev.device_name, ramp)

    def restore_all_identity(self) -> None:
        for dev in self.monitors():
            self.apply_ramp(dev.device_name, gamma_controller.IDENTITY_GAMMA)

    def is_available(self) -> bool:
        return self._available

    # ---------- 热插拔 ----------
    def detect_changes(self) -> Tuple[List[str], List[str]]:
        """与上次枚举对比，返回 (新增设备名, 移除设备名)。"""
        previous = set(self.device_names())
        current = self.refresh()
        current_set = set(m.device_name for m in current)
        added = [d for d in current_set if d not in previous]
        removed = [d for d in previous if d not in current_set]
        return added, removed


# 模块级单例
display_manager = DisplayManager()
