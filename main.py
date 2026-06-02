import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import TkinterDnD
from server_checker_app import ServerCheckerApp
import os
import sys
import argparse
import win32gui
import win32con
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def activate_existing_window():
    """激活已运行的应用程序窗口"""
    target_hwnd = None

    def enum_windows_callback(hwnd, _):
        nonlocal target_hwnd
        window_text = win32gui.GetWindowText(hwnd)
        if "L4D2 Server OptiBrowser" in window_text:
            target_hwnd = hwnd
            return False  # 找到目标窗口，停止枚举
        return True

    # 查找窗口（不检查可见性，因为托盘状态窗口不可见）
    win32gui.EnumWindows(enum_windows_callback, None)

    if target_hwnd:
        try:
            # 检查窗口是否最小化或隐藏
            if win32gui.IsIconic(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

            # 如果窗口不可见（可能在托盘），显示它
            if not win32gui.IsWindowVisible(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)

            # 激活窗口
            win32gui.SetForegroundWindow(target_hwnd)
            win32gui.BringWindowToTop(target_hwnd)
            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False

    return False


if __name__ == "__main__":
    # 检查是否已有实例运行
    if activate_existing_window():
        print("应用程序已在运行中，激活现有窗口...")
        sys.exit(0)

    # 原有的启动代码保持不变...
    parser = argparse.ArgumentParser()
    parser.add_argument('--minimized', action='store_true', help='Start minimized to tray')
    args = parser.parse_args()

    root = TkinterDnD.Tk()

    if args.minimized:
        root.withdraw()
        time.sleep(8)

    root.geometry("1200x600")
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    root.geometry(f"+{x}+{y}")

    app = ServerCheckerApp(root)

    try:
        root.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
    except Exception as e:
        print(f"图标加载错误: {str(e)}")

    root.mainloop()