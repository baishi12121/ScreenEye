"""核心引擎：把 配置 / 伽马表 / 显示器 / 预设 串起来，对外提供高层 API。

- 每块显示器在 config["displays"][device_name] 中独立保存 色温/亮度/激活预设。
- 所有变更通过 Qt 信号广播，UI 与托盘据此刷新。
- 支持平滑过渡（用于定时切换/预设切换）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core import gamma_controller
from core.config import config
from core import display_manager as dm
from core import preset_manager
from core.constants import BRIGHTNESS_MAX, BRIGHTNESS_MIN, TEMP_MAX, TEMP_MIN

# 信号参数使用字符串描述，避免复杂类型导出问题
# settings_changed(device_name, temperature, brightness, preset_key)
# paused_changed(paused: bool)
# preset_applied(device_name: str, preset_key: str)
# display_list_changed()


class Engine(QObject):
    settings_changed = pyqtSignal(str, int, int, str)
    paused_changed = pyqtSignal(bool)
    preset_applied = pyqtSignal(str, str)
    display_list_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._paused = False
        self._current_device: Optional[str] = None
        self._last_ramp: Dict[str, gamma_controller.GammaRamp] = {}
        self._transition_timer: Optional[QTimer] = None
        self._transition_state = None

    # ---------- 显示器 ----------
    def ensure_display(self, device_name: str) -> None:
        displays = config.get("displays", default={})
        if device_name not in displays:
            default = config.get("displays", "default", default={
                "temperature": 6500,
                "brightness": 100,
                "active_preset": "health",
            })
            config.set("displays", device_name, value=dict(default))
            config.save()

    def get_settings(self, device_name: str) -> Dict[str, object]:
        """获取某显示器的有效设置（缺字段时回退 default）。"""
        displays = config.get("displays", default={})
        base = dict(displays.get("default", {}))
        dev = displays.get(device_name, {})
        base.update(dev)
        base.setdefault("temperature", 6500)
        base.setdefault("brightness", 100)
        base.setdefault("active_preset", "health")
        return base

    def select_device(self, device_name: Optional[str]) -> None:
        self._current_device = device_name

    @property
    def current_device(self) -> Optional[str]:
        return self._current_device

    # ---------- 应用 ----------
    def _clamp_temp(self, t: int) -> int:
        return max(TEMP_MIN, min(TEMP_MAX, int(t)))

    def _clamp_bright(self, b: int) -> int:
        return max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, int(b)))

    def _build_and_apply(self, device_name: str, temperature: int, brightness: int) -> None:
        ramp = gamma_controller.build_gamma_ramp(temperature, brightness / 100.0)
        ok = dm.display_manager.apply_ramp(device_name, ramp)
        if ok:
            self._last_ramp[device_name] = ramp

    def apply_device(self, device_name: str, transition: float = 0.0) -> None:
        """将 config 中该显示器的当前设置应用到屏幕。"""
        s = self.get_settings(device_name)
        self._apply_values([device_name], s["temperature"], s["brightness"], transition)

    def apply_all(self, transition: float = 0.0) -> None:
        devices = dm.display_manager.device_names()
        for dev in devices:
            s = self.get_settings(dev)
            self._apply_values([dev], s["temperature"], s["brightness"], transition)
        # 广播（主显示器为代表）
        if devices:
            s = self.get_settings(devices[0])
            self.settings_changed.emit(devices[0], int(s["temperature"]),
                                       int(s["brightness"]), str(s["active_preset"]))

    def _apply_values(self, devices: List[str], temp_to: int, bright_to: int,
                      transition: float) -> None:
        if self._paused:
            return
        if transition and transition > 0:
            self._start_transition(devices, temp_to, bright_to, transition)
        else:
            for dev in devices:
                self._build_and_apply(dev, temp_to, bright_to)

    # ---------- 设置写入 ----------
    def set_temperature(self, device_name: str, temperature: int,
                       apply: bool = True, transition: float = 0.0) -> None:
        temperature = self._clamp_temp(temperature)
        self.ensure_display(device_name)
        config.set("displays", device_name, "temperature", value=temperature)
        config.set("displays", device_name, "active_preset", value="")
        config.save()
        if apply and not self._paused:
            self._apply_values([device_name], temperature,
                               int(self.get_settings(device_name)["brightness"]), transition)
        s = self.get_settings(device_name)
        self.settings_changed.emit(device_name, temperature, int(s["brightness"]), "")

    def set_brightness(self, device_name: str, brightness: int,
                       apply: bool = True, transition: float = 0.0) -> None:
        brightness = self._clamp_bright(brightness)
        self.ensure_display(device_name)
        config.set("displays", device_name, "brightness", value=brightness)
        config.set("displays", device_name, "active_preset", value="")
        config.save()
        if apply and not self._paused:
            self._apply_values([device_name],
                               int(self.get_settings(device_name)["temperature"]), brightness, transition)
        s = self.get_settings(device_name)
        self.settings_changed.emit(device_name, int(s["temperature"]), brightness, "")

    def set_temperature_all(self, temperature: int, transition: float = 0.0) -> None:
        temperature = self._clamp_temp(temperature)
        for dev in dm.display_manager.device_names():
            self.ensure_display(dev)
            config.set("displays", dev, "temperature", value=temperature)
            config.set("displays", dev, "active_preset", value="")
        config.save()
        if not self._paused:
            self._apply_values(dm.display_manager.device_names(), temperature,
                               self._avg_brightness(), transition)
        primary = dm.display_manager.primary()
        if primary:
            self.settings_changed.emit(primary.device_name, temperature,
                                       self._avg_brightness(), "")

    def _avg_brightness(self) -> int:
        devices = dm.display_manager.device_names()
        if not devices:
            return 100
        total = sum(int(self.get_settings(d)["brightness"]) for d in devices)
        return total // len(devices)

    def set_brightness_all(self, brightness: int, transition: float = 0.0) -> None:
        brightness = self._clamp_bright(brightness)
        for dev in dm.display_manager.device_names():
            self.ensure_display(dev)
            config.set("displays", dev, "brightness", value=brightness)
            config.set("displays", dev, "active_preset", value="")
        config.save()
        if not self._paused:
            self._apply_values(dm.display_manager.device_names(),
                               self._avg_temperature(), brightness, transition)
        primary = dm.display_manager.primary()
        if primary:
            self.settings_changed.emit(primary.device_name, self._avg_temperature(),
                                       brightness, "")

    def _avg_temperature(self) -> int:
        devices = dm.display_manager.device_names()
        if not devices:
            return 6500
        total = sum(int(self.get_settings(d)["temperature"]) for d in devices)
        return total // len(devices)

    # ---------- 预设 ----------
    def apply_preset(self, device_name: str, preset_key: str, transition: float = 0.0) -> None:
        preset = preset_manager.get_preset(preset_key)
        if preset is None:
            return
        temp = int(preset["temperature"])
        bright = int(preset["brightness"])
        self.ensure_display(device_name)
        config.set("displays", device_name, "temperature", value=temp)
        config.set("displays", device_name, "brightness", value=bright)
        config.set("displays", device_name, "active_preset", value=preset_key)
        config.save()
        if not self._paused:
            self._apply_values([device_name], temp, bright, transition)
        self.preset_applied.emit(device_name, preset_key)
        self.settings_changed.emit(device_name, temp, bright, preset_key)

    def apply_preset_all(self, preset_key: str, transition: float = 0.0) -> None:
        preset = preset_manager.get_preset(preset_key)
        if preset is None:
            return
        temp = int(preset["temperature"])
        bright = int(preset["brightness"])
        for dev in dm.display_manager.device_names():
            self.ensure_display(dev)
            config.set("displays", dev, "temperature", value=temp)
            config.set("displays", dev, "brightness", value=bright)
            config.set("displays", dev, "active_preset", value=preset_key)
        config.save()
        if not self._paused:
            self._apply_values(dm.display_manager.device_names(), temp, bright, transition)
        primary = dm.display_manager.primary()
        if primary:
            self.preset_applied.emit(primary.device_name, preset_key)
            self.settings_changed.emit(primary.device_name, temp, bright, preset_key)

    # ---------- 同步 ----------
    def sync_all_to(self, source_device: Optional[str] = None) -> None:
        """把源显示器（默认主屏）的设置复制到所有显示器并应用。"""
        src = source_device or (dm.display_manager.primary().device_name
                                 if dm.display_manager.primary() else None)
        if not src:
            return
        s = self.get_settings(src)
        for dev in dm.display_manager.device_names():
            if dev == src:
                continue
            config.set("displays", dev, "temperature", value=int(s["temperature"]))
            config.set("displays", dev, "brightness", value=int(s["brightness"]))
            config.set("displays", dev, "active_preset", value=str(s["active_preset"]))
        config.save()
        self.apply_all()

    # ---------- 暂停 / 恢复 ----------
    def pause(self) -> None:
        if self._paused:
            return
        self._paused = True
        self._stop_transition()
        dm.display_manager.restore_original()
        self.paused_changed.emit(True)

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        self.apply_all()
        self.paused_changed.emit(False)

    @property
    def paused(self) -> bool:
        return self._paused

    def toggle_pause(self) -> None:
        if self._paused:
            self.resume()
        else:
            self.pause()

    def reset_color(self) -> None:
        """恢复屏幕原生色彩（退出 / 暂停的核心复位动作）。

        依赖启动时已用 identity 表捕获的原始伽马表；即使未捕获，
        display_manager.restore_original 也会回退到 identity，仍等于恢复默认。
        必须在进程结束前同步调用——NVIDIA/AMD 独显不会在进程销毁时自动恢复。
        """
        dm.display_manager.restore_original()

    def stop_transition(self) -> None:
        """停止可能正在进行的平滑过渡定时器。"""
        self._stop_transition()

    # ---------- 平滑过渡 ----------
    def _stop_transition(self) -> None:
        if self._transition_timer is not None:
            self._transition_timer.stop()
            self._transition_timer = None
        self._transition_state = None

    def _start_transition(self, devices: List[str], temp_to: int, bright_to: int,
                          duration: float) -> None:
        self._stop_transition()
        # 起始值：取 devices 中第一块显示器的当前设置
        start_dev = devices[0] if devices else None
        if start_dev is None:
            return
        s0 = self.get_settings(start_dev)
        temp_from = int(s0["temperature"])
        bright_from = int(s0["brightness"])
        fps = 30
        frames = max(1, int(duration * fps))
        interval = max(1, int(duration * 1000 / frames))
        state = {
            "devices": devices,
            "temp_from": temp_from, "temp_to": temp_to,
            "bright_from": bright_from, "bright_to": bright_to,
            "frame": 0, "frames": frames,
        }
        self._transition_state = state
        timer = QTimer(self)
        timer.setInterval(interval)

        def tick():
            st = self._transition_state
            if st is None:
                timer.stop()
                return
            st["frame"] += 1
            t = st["frame"] / st["frames"]
            if t >= 1.0:
                temp = st["temp_to"]
                bright = st["bright_to"]
                for dev in st["devices"]:
                    self._build_and_apply(dev, temp, bright)
                timer.stop()
                self._transition_timer = None
                self._transition_state = None
                return
            temp = int(st["temp_from"] + (st["temp_to"] - st["temp_from"]) * t)
            bright = int(st["bright_from"] + (st["bright_to"] - st["bright_from"]) * t)
            for dev in st["devices"]:
                self._build_and_apply(dev, temp, bright)

        timer.timeout.connect(tick)
        self._transition_timer = timer
        timer.start()
