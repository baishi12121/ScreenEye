"""ScreenEye 入口：单例锁、应用初始化、管理器装配、托盘启动、退出恢复。

用法：
    python main.py            # 正常启动（默认显示主窗口）
    python main.py --minimized # 静默启动，直接最小化到托盘
    python main.py --reset-gamma # 紧急复位屏幕色彩
"""
from __future__ import annotations

import atexit
import os
import sys
import types

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from core import display_manager as dm, engine, hotkey_manager
from core.config import config
from core.constants import CONFIG_PATH, app_display_name
from core import preset_manager, rest_manager, focus_manager, screen_time_tracker, scheduler
from ui import icons, theme
from ui.main_window import MainWindow
from ui.tray import TrayIcon


def resource_path(rel: str) -> str:
    """解析资源路径：冻结后位于 sys._MEIPASS，源码运行位于脚本目录。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ---------- 单例（Windows Mutex） ----------
def ensure_single_instance() -> object:
    """创建命名 Mutex；若已存在则返回 None（表示已有实例在运行）。"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, "ScreenEye_SingleInstance_Mutex")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return None
        return handle
    except Exception:
        return object()  # 非 Windows：不强制单例


# ---------- 应用上下文 ----------
class AppContext:
    def __init__(self, app: QApplication):
        self.app = app
        self.config = config
        self.engine = engine.Engine()
        self.rest = rest_manager.RestManager()
        self.focus = focus_manager.FocusManager(self)
        self.screen = screen_time_tracker.ScreenTimeTracker()
        self.scheduler = scheduler.Scheduler(self.engine)
        self.hotkey = hotkey_manager.HotkeyManager()
        self.tray: TrayIcon = None
        self.main_window: MainWindow = None

    # 便捷方法
    def toast(self, title: str, msg: str) -> None:
        if self.tray is not None:
            self.tray.show_message(title, msg)

    def reload_theme(self) -> None:
        theme.apply_theme(self.app, self.config.get("ui", "theme", default="dark"))

    def reregister_hotkeys(self) -> list:
        combos = {
            self.config.get("hotkeys", "toggle_pause", default="Ctrl+Alt+P"):
                self.engine.toggle_pause,
            self.config.get("hotkeys", "preset_1", default="Ctrl+Alt+1"):
                lambda: self.engine.apply_preset_all("health"),
            self.config.get("hotkeys", "preset_2", default="Ctrl+Alt+2"):
                lambda: self.engine.apply_preset_all("office"),
            self.config.get("hotkeys", "preset_3", default="Ctrl+Alt+3"):
                lambda: self.engine.apply_preset_all("read"),
            self.config.get("hotkeys", "preset_4", default="Ctrl+Alt+4"):
                lambda: self.engine.apply_preset_all("night"),
            self.config.get("hotkeys", "temp_up", default="Ctrl+Alt+Up"):
                lambda: self.engine.set_temperature_all(
                    int(self.engine.get_settings(
                        self.engine.current_device or "default")["temperature"]) + 100),
            self.config.get("hotkeys", "temp_down", default="Ctrl+Alt+Down"):
                lambda: self.engine.set_temperature_all(
                    int(self.engine.get_settings(
                        self.engine.current_device or "default")["temperature"]) - 100),
            self.config.get("hotkeys", "focus_toggle", default="Ctrl+Alt+F"):
                self._toggle_focus,
        }
        return self.hotkey.reregister(combos)

    def _toggle_focus(self) -> None:
        """专注快捷键：未开始则开始，进行中则暂停/继续。"""
        if self.focus.is_active():
            self.focus.toggle_pause()
            state = "暂停" if self.focus.state.startswith("paused") else "继续"
            self.toast("专注", f"专注已{state}")
        else:
            self.focus.start()
            self.toast("专注", "专注已开始")

    def quick_start_focus(self) -> None:
        """托盘「开始 25 分钟专注」：用 25/5/循环 配置直接启动。"""
        if self.focus.is_active():
            self.main_window.show_page("专注")
            return
        self.focus.set_config(focus_duration=25, rest_duration=5, loop_enable=True)
        self.main_window.show_page("专注")
        self.focus.start()

    def save_custom_preset(self) -> None:
        if self.main_window is not None:
            self.main_window.show_page("显示")
            page = self.main_window.pages["显示"]
            page._add_custom()

    def quit_app(self) -> None:
        """严格退出流程（对照用户的退出顺序方案）：

        1) 恢复屏幕原生色彩（关键第一步，必须在进程结束前同步执行，
           因为 NVIDIA/AMD 独显不会在进程销毁时自动恢复伽马表）
        2) 停止所有后台定时器（时长统计、自动切换、专注遮罩、休息、过渡）
        3) 保存本地配置文件
        4) 注销全局快捷键
        5) 退出应用
        """
        # 1. 恢复屏幕原生色彩
        try:
            self.engine.reset_color()
        except Exception:
            pass
        # 2. 停止所有后台定时器，防止退出后依然执行
        try:
            self.scheduler.stop()
        except Exception:
            pass
        try:
            self.screen.stop()
        except Exception:
            pass
        # 若正处于专注模式，先还原屏幕色温/亮度，再退出
        try:
            if self.focus.is_active():
                self.focus.restore_screen()
        except Exception:
            pass
        try:
            self.rest.reset()
        except Exception:
            pass
        try:
            self.engine.stop_transition()
        except Exception:
            pass
        # 3. 保存本地配置文件（标记本次为正常退出，供下次启动识别是否非正常退出）
        try:
            self.config.set("runtime", "running", value=False)
            self.config.save()
        except Exception:
            pass
        # 4. 注销全局快捷键
        try:
            self.hotkey.unregister_all()
        except Exception:
            pass
        # 5. 退出应用
        self.app.quit()


def boot(ctx: AppContext, selftest: bool = False) -> None:
    """装配所有管理器并应用已保存设置（main 与 --selftest 共用）。"""
    # 显示器枚举 + 捕获原始伽马表（用于退出恢复）
    # 场景 B 兜底：若上次非正常退出（强杀/崩溃），启动时先复位一次修复残留滤镜
    crashed_last = ctx.config.get("runtime", "running", default=False)
    dm.display_manager.refresh()
    dm.display_manager.restore_all_identity()
    dm.display_manager.capture_original()
    if not dm.display_manager.is_available() and not selftest:
        QMessageBox.warning(
            None, "提示",
            "当前环境不支持伽马表调节（可能为远程桌面或非 Windows）。\n"
            "程序仍可运行，但显示调节功能不可用。")

    # 主题
    ctx.reload_theme()

    # 主窗口 + 托盘
    ctx.main_window = MainWindow(ctx)
    ctx.tray = TrayIcon(ctx)
    if not selftest:
        ctx.tray.show()

    # 启动应用已保存的显示设置
    ctx.engine.apply_all()

    # 快捷键
    if ctx.config.get("general", "hotkeys_enabled", default=True):
        failed = ctx.reregister_hotkeys()
        if failed:
            ctx.toast("快捷键", f"部分快捷键注册失败：{', '.join(failed)}")

    # 调度 + 统计
    ctx.scheduler.reload()
    ctx.screen.start()

    # 信号连接（提醒类）
    ctx.screen.goal_reached.connect(
        lambda d: ctx.toast("屏幕时长", "今日使用时长已达目标，请注意休息"))
    ctx.screen.interval_reminder.connect(
        lambda s: ctx.toast("休息提醒", "已连续使用一段时间，建议闭眼远眺一下"))
    ctx.rest.break_started.connect(
        lambda minutes, is_long: ctx.toast(
            "休息提醒", f"工作结束，{'长' if is_long else ''}休息 {minutes} 分钟"))
    ctx.engine.preset_applied.connect(
        lambda d, k: ctx.toast("预设", f"已切换到 {preset_manager.get_preset(k).get('name', k)}"))

    # 标记本次为“正在运行”，便于下次启动识别是否非正常退出（场景 B）
    try:
        ctx.config.set("runtime", "running", value=True)
        ctx.config.save()
    except Exception:
        pass
    if crashed_last and not selftest:
        ctx.toast("ScreenEye", "检测到上次异常退出，已自动恢复屏幕色彩")


def _reset_gamma_and_exit() -> None:
    """诊断/恢复：将所有显示器伽马表重置为默认（身份表）后退出。

    用于进程被强制结束后屏幕色彩未恢复的紧急恢复。无需单例锁、无需完整启动。
    """
    try:
        dm.display_manager.refresh()
        # 未捕获原始表时 restore_original 会回退到身份表，正好用于“恢复默认”
        dm.display_manager.restore_original()
        print("[ScreenEye] 已将所有显示器恢复为默认伽马表。")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"[ScreenEye] 重置伽马表失败：{e}")
        sys.exit(1)


def main() -> None:
    # 紧急复位：无需单例、无需完整启动，直接恢复默认色彩后退出
    if "--reset-gamma" in sys.argv:
        _reset_gamma_and_exit()
        return

    selftest = "--selftest" in sys.argv
    if selftest:
        # 无头自检：强制 offscreen，避免需要真实显示器
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    QCoreApplication.setApplicationName("ScreenEye")
    QCoreApplication.setOrganizationName("ScreenEye")

    # 单例检测（--selftest 为诊断模式，跳过互斥锁以避免与正在运行的实例冲突）
    mutex = None if selftest else ensure_single_instance()
    if mutex is None and not selftest:
        print("[ScreenEye] 已有实例在运行，退出。")
        sys.exit(0)

    app = QApplication(sys.argv)
    # 真实应用图标（exe 内嵌 + 窗口/任务栏），托盘仍用绘制图标以表达状态
    app.setWindowIcon(QIcon(resource_path("resources/app.ico")))

    # 首次启动检测
    first_run = not os.path.exists(CONFIG_PATH)
    config.load()

    ctx = AppContext(app)
    boot(ctx, selftest)

    # 退出时恢复
    atexit.register(_cleanup, ctx)
    app.aboutToQuit.connect(lambda: _cleanup(ctx))

    if selftest:
        # 无头自检：装配完成即视为通过，清理后退出
        print("[ScreenEye] selftest OK")
        ctx.quit_app()
        sys.exit(0)

    # 显示策略：默认打开主窗口；用户可在设置里勾选“最小化到托盘”改为静默启动
    minimized = "--minimized" in sys.argv or ctx.config.get("general", "minimize_to_tray", default=False)
    if minimized:
        ctx.tray.show_message(app_display_name(), "已最小化到托盘，右键托盘图标打开主界面")
    else:
        ctx.main_window.show_page("显示")

    sys.exit(app.exec_())


def _cleanup(ctx: AppContext) -> None:
    try:
        ctx.scheduler.stop()
    except Exception:
        pass
    # 若正处于专注模式，先还原屏幕色温/亮度
    try:
        if ctx.focus.is_active():
            ctx.focus.restore_screen()
    except Exception:
        pass
    try:
        ctx.rest.reset()
    except Exception:
        pass
    try:
        ctx.screen.stop()
    except Exception:
        pass
    try:
        ctx.engine.restore_original()
    except Exception:
        pass
    try:
        ctx.config.set("runtime", "running", value=False)
        ctx.config.save()
    except Exception:
        pass
    try:
        ctx.hotkey.unregister_all()
    except Exception:
        pass


if __name__ == "__main__":
    main()
