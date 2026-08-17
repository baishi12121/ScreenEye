"""生成 CareUEyes 应用图标 resources/app.ico。

用 Pillow 以 4x 超采样渲染后缩放，保证小尺寸下边缘平滑。
图标语义：圆角渐变底（护眼绿→青）+ 白色眼形 + 绿色虹膜 + 青色瞳孔 + 高光。

仅依赖 Pillow，可在任意平台运行：
    python tools/make_icon.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

# .ico 内嵌的多种分辨率（Windows 会按使用场景自动挑选）
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]

# 品牌色（与 core/constants.py 保持一致）
TOP = (33, 191, 115)      # #21BF73 护眼绿（顶部）
BOTTOM = (26, 150, 170)   # #1A96AA 青（底部）
EYE_WHITE = (245, 245, 245)
IRIS = (76, 175, 80)      # #4CAF50 主色
PUPIL = (38, 198, 218)    # #26C6DA 强调色
HILITE = (255, 255, 255)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render(size: int) -> Image.Image:
    """以 SS 倍超采样渲染单个尺寸的图标，返回 size×size 的 RGBA 图像。"""
    SS = 4
    s = size * SS
    # 渐变背景
    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    for y in range(s):
        t = y / (s - 1)
        bd.line([(0, y), (s, y)], fill=lerp(TOP, BOTTOM, t) + (255,))
    # 圆角遮罩
    radius = int(s * 0.22)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s, s], radius=radius, fill=255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(img)

    # 眼白（横向椭圆）
    ex0, ey0, ex1, ey1 = s * 0.12, s * 0.36, s * 0.88, s * 0.64
    d.ellipse([ex0, ey0, ex1, ey1], fill=EYE_WHITE + (255,))

    # 虹膜
    cx, cy = s * 0.5, s * 0.5
    ri = s * 0.15
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=IRIS + (255,))

    # 瞳孔
    rp = s * 0.07
    d.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=PUPIL + (255,))

    # 高光
    rh = s * 0.03
    hx, hy = cx + ri * 0.4, cy - ri * 0.4
    d.ellipse([hx - rh, hy - rh, hx + rh, hy + rh], fill=HILITE + (255,))

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(os.path.dirname(here), "resources")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "app.ico")

    # 基准图必须是最大尺寸：ICO 编码器对“大于基准图”的尺寸会直接跳过。
    # 这里传入每个尺寸各自超采样渲染的清晰版本（append_images），由编码器按尺寸挑选。
    imgs = {sz: render(sz) for sz in SIZES}
    base = imgs[max(SIZES)]  # 256
    others = [imgs[sz] for sz in SIZES if sz != max(SIZES)]
    base.save(
        out_path,
        format="ICO",
        sizes=[(sz, sz) for sz in SIZES],
        append_images=others,
    )
    print(f"wrote {out_path} ({os.path.getsize(out_path)} bytes), sizes={SIZES}")


if __name__ == "__main__":
    main()
