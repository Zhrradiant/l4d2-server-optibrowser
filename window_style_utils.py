import pywinstyles
import os


class WindowStyleUtils:
    def __init__(self):
        self.window_style = "light"  # 默认样式

    def apply_window_style(self, window, style=None):
        """应用窗口样式到指定窗口"""
        if style is None:
            style = self.window_style

        try:
            pywinstyles.apply_style(window, style)
            window.attributes("-alpha", 0.99)  # 轻微调整透明度（触发重绘）
            window.attributes("-alpha", 1.0)   # 恢复透明度
            return True
        except Exception as e:
            print(f"应用窗口样式失败: {e}")
            return False

    def set_global_style(self, style):
        """设置全局窗口样式"""
        self.window_style = style

    def get_global_style(self):
        """获取全局窗口样式"""
        return self.window_style


# 创建全局实例
window_style_utils = WindowStyleUtils()