@echo off
REM 紧急恢复：将屏幕色彩重置为默认（进程被强杀后色彩未恢复时使用）
"%~dp0ScreenEye.exe" --reset-gamma
