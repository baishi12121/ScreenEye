"""屏幕使用时长统计：基于 GetLastInputInfo 的活动检测与每日累计。

持久化到 config["screen_time"]["history"]["YYYY-MM-DD"] = {seconds, idle_seconds}。
每日 00:00 自动重置；支持目标达成提醒与连续使用间隔提醒。
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import datetime
import os
from typing import Tuple

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.config import config

if hasattr(ctypes, "windll"):
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    # 设置精确原型，确保 64 位下句柄/指针不被截断
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
    ]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _kernel32.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    ]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD,
        wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
else:  # 非 Windows 兼容
    _user32 = None
    _kernel32 = None


# 常见进程名 -> 友好中文名（用于屏幕时长统计展示）
APP_NAME_MAP = {
    "chrome": "Google Chrome", "msedge": "Microsoft Edge", "firefox": "Firefox",
    "brave": "Brave", "opera": "Opera", "iexplore": "Internet Explorer",
    "explorer": "文件资源管理器", "devenv": "Visual Studio", "code": "Visual Studio Code",
    "notepad": "记事本", "notepad++": "Notepad++", "sublime_text": "Sublime Text",
    "pycharm64": "PyCharm", "idea64": "IntelliJ IDEA", "webstorm64": "WebStorm",
    "clion64": "CLion", "winword": "Word", "excel": "Excel",
    "powerpnt": "PowerPoint", "outlook": "Outlook", "onenote": "OneNote",
    "wechat": "微信", "weixin": "微信", "qq": "QQ", "tim": "QQ",
    "dingtalk": "钉钉", "feishu": "飞书", "wxwork": "企业微信",
    "slack": "Slack", "discord": "Discord", "steam": "Steam",
    "leagueclient": "英雄联盟", "photoshop": "Photoshop", "illustrator": "Illustrator",
    "premiere": "Premiere Pro", "afterfx": "After Effects", "lightroom": "Lightroom",
    "spotify": "Spotify", "cloudmusic": "网易云音乐", "kwmusic": "酷狗音乐",
    "qqmusic": "QQ音乐", "potplayer": "PotPlayer", "vlc": "VLC",
    "wmplayer": "Windows Media Player", "obs64": "OBS Studio",
    "zoom": "Zoom", "teams": "Microsoft Teams", "wemeet": "腾讯会议",
    "tencentdocs": "腾讯文档", "youdao": "有道词典", "typora": "Typora",
    "thunder": "迅雷", "qbittorrent": "qBittorrent", "todo": "Microsoft To Do",
    "applicationframehost": "系统应用", "shellexperiencehost": "系统界面",
    "textinputhost": "输入法", "searchui": "开始/搜索", "dwm": "桌面窗口管理器",
    "careueyes": "ScreenEye",
}


def get_foreground_app():
    """返回当前前台窗口对应的 (app_key, 显示名)；无法获取时返回 None。

    app_key 为去扩展名的进程名（小写），用于累计；显示名来自 APP_NAME_MAP，
    未知进程回退到进程名本身。
    """
    if _user32 is None or _kernel32 is None:
        return None
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        hproc = _kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not hproc:
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if not _kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size)):
                return None
            path = buf.value
        finally:
            _kernel32.CloseHandle(hproc)
        if not path:
            return None
        base = os.path.basename(path)
        key = base.lower()
        if key.endswith(".exe"):
            key = key[:-4]
        return key, APP_NAME_MAP.get(key, key)
    except Exception:
        return None


def get_idle_seconds() -> float:
    """返回系统闲置秒数；非 Windows 返回 0（视为持续活跃）。"""
    if _user32 is None:
        return 0.0
    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    millis = _kernel32.GetTickCount() - lii.dwTime
    return max(0.0, millis / 1000.0)


class ScreenTimeTracker(QObject):
    seconds_changed = pyqtSignal(int, str)      # (今日秒数, 日期)
    goal_reached = pyqtSignal(str)              # (日期)
    interval_reminder = pyqtSignal(int)         # (今日秒数)

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._tick_count = 0
        self._load_day()

    def _load_day(self) -> None:
        today = datetime.date.today().isoformat()
        self._date = today
        hist = config.get("screen_time", "history", default={})
        entry = hist.get(today, {"seconds": 0, "idle_seconds": 0, "apps": {}})
        self._seconds = int(entry.get("seconds", 0))
        self._idle_seconds = int(entry.get("idle_seconds", 0))
        self._app_seconds = {k: int(v) for k, v in (entry.get("apps") or {}).items()}
        self._continuous = 0
        self._last_interval_mult = 0
        self._goal_emitted = False

    def _reset_day(self) -> None:
        self._date = datetime.date.today().isoformat()
        self._seconds = 0
        self._idle_seconds = 0
        self._app_seconds = {}
        self._continuous = 0
        self._last_interval_mult = 0
        self._goal_emitted = False

    def enabled(self) -> bool:
        return bool(config.get("screen_time", "enabled", default=True))

    def start(self) -> None:
        if self.enabled():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._persist()

    def today_seconds(self) -> int:
        return self._seconds

    # ---------- 各软件使用时长 ----------
    def app_seconds(self) -> dict:
        """返回 {app_key: 今日秒数}（原始累计）。"""
        return dict(self._app_seconds)

    def apps_today(self) -> list:
        """返回 [(显示名, 今日秒数), ...]，按使用时长降序。"""
        items = [(APP_NAME_MAP.get(k, k), v) for k, v in self._app_seconds.items()]
        items.sort(key=lambda x: -x[1])
        return items

    def _persist(self) -> None:
        hist = config.get("screen_time", "history", default={})
        if not isinstance(hist, dict):
            hist = {}
        hist[self._date] = {
            "seconds": self._seconds,
            "idle_seconds": self._idle_seconds,
            "apps": dict(self._app_seconds),
        }
        # 仅保留最近 365 天
        if len(hist) > 365:
            sorted_keys = sorted(hist.keys())
            for old in sorted_keys[:-365]:
                hist.pop(old, None)
        config.set("screen_time", "history", value=hist)
        config.save()

    def _tick(self) -> None:
        # 跨日重置
        today = datetime.date.today().isoformat()
        if today != self._date:
            self._persist()
            self._reset_day()

        if not self.enabled():
            return

        threshold = int(config.get("screen_time", "idle_threshold_seconds", default=120))
        idle = get_idle_seconds()

        if idle <= threshold:
            self._seconds += 1
            self._continuous += 1
            # 按前台进程累计各软件使用时长
            app = get_foreground_app()
            if app:
                key = app[0]
                self._app_seconds[key] = self._app_seconds.get(key, 0) + 1
        else:
            self._idle_seconds += 1
            self._continuous = 0

        # 提醒
        self._check_reminders()

        self._tick_count += 1
        self.seconds_changed.emit(self._seconds, self._date)
        if self._tick_count % 10 == 0:
            self._persist()

    def _check_reminders(self) -> None:
        # 连续使用间隔提醒
        interval_min = int(config.get("screen_time", "remind_interval_minutes", default=60))
        if interval_min > 0:
            mult = self._continuous // (interval_min * 60)
            if mult > self._last_interval_mult and mult > 0:
                self._last_interval_mult = mult
                self.interval_reminder.emit(self._seconds)

        # 每日目标达成提醒
        goal_min = int(config.get("screen_time", "daily_goal_minutes", default=480))
        if config.get("screen_time", "remind_when_exceed_goal", default=True):
            if not self._goal_emitted and goal_min > 0 and self._seconds >= goal_min * 60:
                self._goal_emitted = True
                self.goal_reached.emit(self._date)

    # ---------- 统计查询 ----------
    def history(self) -> dict:
        return config.get("screen_time", "history", default={})

    def week_stats(self) -> list:
        """返回最近 7 天 (date, seconds) 列表。"""
        hist = self.history()
        out = []
        for i in range(6, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            out.append((d, int(hist.get(d, {}).get("seconds", 0))))
        return out

    def month_stats(self) -> list:
        """返回最近 30 天 (date, seconds) 列表。"""
        hist = self.history()
        out = []
        for i in range(29, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            out.append((d, int(hist.get(d, {}).get("seconds", 0))))
        return out

    def total_seconds(self) -> int:
        return sum(int(v.get("seconds", 0)) for v in self.history().values())

    def longest_streak_today(self) -> int:
        return self._continuous


def fmt_hm(seconds: int) -> Tuple[int, int]:
    return seconds // 3600, (seconds % 3600) // 60
