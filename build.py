"""打包 ScreenEye 为单文件 exe（PyInstaller）。

用法（在 Windows 上，已安装依赖的 Python 环境）：
    python build.py

产物：dist/ScreenEye.exe （单文件，无外部依赖，可直接复制分发）
图标：resources/app.ico（同时作为 exe 文件图标，并由程序在运行时加载为窗口图标）

说明：
- --windowed：无控制台窗口（GUI 程序）
- --onefile：打包为单个可执行文件
- --add-data 把 app.ico 一并打入，运行时通过 sys._MEIPASS 取出（见 main.resource_path）
- hidden-imports 确保 PyQt5 子模块被收集
"""
from __future__ import annotations

import os
import sys

from PyInstaller.__main__ import run

HERE = os.path.dirname(os.path.abspath(__file__))
ICO = os.path.join(HERE, "resources", "app.ico")
DIST = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "build")

# Windows 专用：数据文件分隔符为 ";"
SEP = ";" if sys.platform.startswith("win") else ":"


def main() -> None:
    args = [
        os.path.join(HERE, "main.py"),
        "--name", "ScreenEye",
        "--onefile",
        "--windowed",
        "--icon", ICO,
        "--add-data", f"{ICO}{SEP}resources",
        "--hidden-import", "PyQt5.QtCore",
        "--hidden-import", "PyQt5.QtGui",
        "--hidden-import", "PyQt5.QtWidgets",
        "--hidden-import", "PyQt5.sip",
        "--noconfirm",
        "--clean",
        "--distpath", DIST,
        "--workpath", BUILD,
    ]
    print("[build] PyInstaller:", " ".join(args))
    run(args)
    exe = os.path.join(DIST, "ScreenEye.exe")
    if os.path.exists(exe):
        print(f"[build] OK -> {exe} ({os.path.getsize(exe)} bytes)")
    else:
        print("[build] FAILED: dist/ScreenEye.exe not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
