"""伽马表控制：色温→RGB 增益、伽马表生成、平滑过渡插值。

纯计算模块，不依赖显示器/Windows 句柄。最终的 SetDeviceGammaRamp 调用
由 display_manager 持有 HDC 后执行。
"""
from __future__ import annotations

import math
from typing import List, Tuple

# 类型别名：单条伽马表 = 256 级 * (r, g, b)，值域 0~65535
GammaRamp = List[Tuple[int, int, int]]

# 标准伽马表（身份映射，屏幕恢复原始色彩）
IDENTITY_GAMMA: GammaRamp = [(i * 257, i * 257, i * 257) for i in range(256)]


def temperature_to_rgb(temperature_k: float) -> Tuple[float, float, float]:
    """Tanner Helland 色温→RGB 算法。

    返回归一化到 0.0~1.0 的 R/G/B 增益。
    """
    temp = temperature_k / 100.0
    r: float
    g: float
    b: float

    if temp <= 66:
        r = 255.0
        # 绿色通道
        if temp <= 0:
            g = 0.0
        else:
            g = 99.4708025861 * math.log(temp) - 161.1195681661
            g = max(0.0, min(255.0, g))
        # 蓝色通道
        if temp <= 19:
            b = 0.0
        else:
            b = 138.5177312231 * math.log(temp - 10) - 305.0447927307
            b = max(0.0, min(255.0, b))
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        r = max(0.0, min(255.0, r))
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        g = max(0.0, min(255.0, g))
        b = 255.0

    return r / 255.0, g / 255.0, b / 255.0


def build_gamma_ramp(temperature_k: float, brightness: float) -> GammaRamp:
    """根据色温与亮度生成 256 级伽马表。

    ramp[i] = clamp(i * 65535/255 * brightness * gain, 0, 65535)
    brightness 取值范围 0.0~1.0（调用方负责把百分比转成 0~1）。
    """
    r_gain, g_gain, b_gain = temperature_to_rgb(temperature_k)
    scale = 65535.0 / 255.0
    ramp: GammaRamp = []
    for i in range(256):
        r_val = int(min(65535, i * scale * brightness * r_gain))
        g_val = int(min(65535, i * scale * brightness * g_gain))
        b_val = int(min(65535, i * scale * brightness * b_gain))
        ramp.append((r_val, g_val, b_val))
    return ramp


def interpolate_ramp(from_ramp: GammaRamp, to_ramp: GammaRamp, t: float) -> GammaRamp:
    """在两条伽马表之间线性插值，t∈[0,1]。用于平滑过渡。"""
    t = max(0.0, min(1.0, t))
    return [
        (
            int(from_ramp[i][0] + (to_ramp[i][0] - from_ramp[i][0]) * t),
            int(from_ramp[i][1] + (to_ramp[i][1] - from_ramp[i][1]) * t),
            int(from_ramp[i][2] + (to_ramp[i][2] - from_ramp[i][2]) * t),
        )
        for i in range(256)
    ]
