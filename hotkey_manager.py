import time
import threading

try:
    import keyboard
    import pyperclip

    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class HotkeyManager:
    def __init__(self, main_app):
        self.main_app = main_app
        self.current_hotkey = ""
        self.is_listening = False
        self.hotkey_thread = None

    def setup_hotkey(self, hotkey_str):
        """设置工坊快捷键"""
        if not KEYBOARD_AVAILABLE:
            print("keyboard库未安装，无法设置快捷键")
            return False

        try:
            # 移除之前的快捷键绑定
            if self.current_hotkey:
                try:
                    keyboard.remove_hotkey(self.current_hotkey)
                except:
                    pass

            # 清除当前快捷键
            self.current_hotkey = ""

            # 如果新快捷键为空，则不设置
            if not hotkey_str or not hotkey_str.strip():
                return True

            # 绑定新的快捷键
            keyboard.add_hotkey(hotkey_str, self.on_hotkey_triggered)
            self.current_hotkey = hotkey_str
            print(f"工坊快捷键已设置: {hotkey_str}")
            return True

        except Exception as e:
            print(f"设置快捷键失败: {e}")
            return False

    def on_hotkey_triggered(self):
        """工坊快捷键触发时的处理"""
        if not KEYBOARD_AVAILABLE:
            return

        try:
            hotkey = self.current_hotkey

            if not hotkey:
                return

            # 模拟复制操作
            keyboard.release(hotkey)
            time.sleep(0.1)
            keyboard.press_and_release('ctrl+c')
            time.sleep(0.2)  # 等待剪贴板更新

            # 获取剪贴板内容
            clipboard_content = pyperclip.paste().strip()

            # 检查是否是工坊链接
            if self.is_workshop_url(clipboard_content):
                # 在主线程中执行解析
                if hasattr(self.main_app, 'root'):
                    self.main_app.root.after(0, lambda: self.process_workshop_url(clipboard_content))

        except Exception as e:
            print(f"工坊快捷键处理失败: {e}")

    def is_workshop_url(self, text):
        """检查文本是否是Steam工坊链接"""
        workshop_patterns = [
            'steamcommunity.com/sharedfiles/filedetails',
            'steamcommunity.com/workshop/filedetails'
        ]
        return any(pattern in text.lower() for pattern in workshop_patterns)

    def process_workshop_url(self, url):
        """处理工坊链接"""
        try:
            # 获取主应用的workshop_utils实例
            workshop_utils = self.main_app.workshop_utils

            # 显示工坊解析窗口
            workshop_win = workshop_utils.show_workshop_parser()

            # 设置URL并开始解析
            workshop_utils.workshop_url_var.set(url)

            # 延迟执行解析，确保窗口已完全加载
            workshop_win.after(500, lambda: workshop_utils.start_workshop_parse(workshop_win))

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("错误", f"处理工坊链接失败: {str(e)}")

    def stop(self):
        """停止快捷键监听"""
        if self.current_hotkey and KEYBOARD_AVAILABLE:
            try:
                keyboard.remove_hotkey(self.current_hotkey)
            except:
                pass
        self.current_hotkey = ""