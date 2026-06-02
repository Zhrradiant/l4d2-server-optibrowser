import json
import os
import tkinter as tk
import ttkbootstrap as ttk

CONFIG_FILE = "server_checker_config.json"


def get_app_font():
    """从配置文件获取应用的字体设置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'font' in config:  # 只有当font字段存在时才返回
                    return config['font']
    except:
        pass
    return '微软雅黑'  # 其他所有情况都返回微软雅黑


def apply_font_to_styled_widgets(style, font_name):
    """
    为无法直接使用font属性的控件设置字体样式

    参数:
        style: ttk.Style对象
        font_name: 字体名称
    """
    if not font_name:
        return

    # 为各种ttk控件配置字体
    styled_widgets = [
        'TButton', 'TCheckbutton', 'TCombobox', 'TEntry',
        'TFrame', 'TLabel', 'TLabelframe', 'TLabelframe.Label',
        'TNotebook', 'TNotebook.Tab', 'TPanedwindow', 'TProgressbar',
        'TRadiobutton', 'TScale', 'TScrollbar', 'TSeparator',
        'TSpinbox', 'Treeview', 'Treeview.Heading'
    ]

    for widget in styled_widgets:
        try:
            style.configure(widget, font=(font_name, 10))
        except:
            # 忽略配置失败的控件
            pass


# 字体占位符常量
APP_FONT = get_app_font()