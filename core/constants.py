"""CareUEyes 全局常量与预设定义。"""
from __future__ import annotations

import os

APP_NAME = "CareUEyes"  # 仅用于配置目录/注册表键名，保持不变以免丢失已有用户设置
APP_VERSION = "1.0.0"
APP_DISPLAY_NAME = "屏间护目"        # 中文显示名
APP_DISPLAY_NAME_EN = "ScreenEye"    # 英文显示名
UPDATE_URL = ""  # 留空：开源版本不检查更新


def app_display_name() -> str:
    """根据当前 UI 语言返回显示名：中文→屏间护目，英文→ScreenEye。"""
    try:
        from core.config import config
        lang = str(config.get("ui", "language", default="zh-CN")).lower()
    except Exception:
        lang = "zh-cn"
    return APP_DISPLAY_NAME_EN if lang.startswith("en") else APP_DISPLAY_NAME

# 配置目录：%APPDATA%\CareUEyes
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# 色温 / 亮度范围
TEMP_MIN = 1900
TEMP_MAX = 10000
TEMP_DEFAULT = 6500
TEMP_STEP = 100

BRIGHTNESS_MIN = 20
BRIGHTNESS_MAX = 100
BRIGHTNESS_DEFAULT = 100

# 内置预设（按 PRD 4.4 的 8 种顺序排列，自定义单独处理）
# (key, 中文名, 色温, 亮度, 设计思路/使用场景说明)
BUILTIN_PRESETS = [
    ("pause", "暂停", 6500, 100, "完全关闭滤镜，恢复原生屏幕。修图、色彩校对、游戏需要精准色彩时使用"),
    ("health", "健康", 4200, 82, "通用护眼均衡档位，日常长时间上网、聊天，中度减少蓝光"),
    ("game", "游戏", 5800, 88, "尽量保留色彩不发黄，轻微护眼；避免色温过黄影响游戏画面识别"),
    ("movie", "影视", 5000, 85, "兼顾观影色彩观感，柔和不刺眼，适合追剧视频"),
    ("office", "办公", 4800, 83, "Word/Excel、浏览网页文字办公，长时间看文本缓解疲劳"),
    ("edit", "编辑", 6500, 85, "设计、剪辑、调色工作；色温保持标准，只微调亮度，杜绝偏色"),
    ("read", "阅读", 3600, 75, "电子书、文档长时间阅读；更暖黄光，强力降低蓝光"),
    ("night", "夜间", 2800, 60, "关灯环境使用，极致暖黄；避免强光干扰褪黑素，不建议白天使用"),
]

DEFAULT_PRESET_KEY = "health"

# 主题
THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_SYSTEM = "system"

# 主题色（PRD 7.7）
COLOR_PRIMARY = "#4CAF50"      # 护眼绿 主色调
COLOR_ACCENT = "#26C6DA"       # 青色 强调色
COLOR_BG_DARK = "#1E1E1E"
COLOR_CARD_DARK = "#252525"
COLOR_TEXT_DARK = "#E0E0E0"
COLOR_TEXT_SECONDARY_DARK = "#9E9E9E"
COLOR_BORDER_DARK = "#3A3A3A"
COLOR_TEMP_WARM = "#FF8A65"     # 暖橙
COLOR_TEMP_COOL = "#E0F7FA"     # 冷白


def builtin_preset_dict() -> dict:
    """返回 {key: {temperature, brightness, name, description}} 形式的默认内置预设。"""
    return {
        key: {"temperature": temp, "brightness": bright, "name": name, "description": desc}
        for key, name, temp, bright, desc in BUILTIN_PRESETS
    }
