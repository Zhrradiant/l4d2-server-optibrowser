import time
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pywinstyles
import json
import os
import requests
from io import StringIO
import threading
import webbrowser
from about_dialog import AboutDialog
from utils import create_outline_button
from window_style_utils import window_style_utils
from font_utils import APP_FONT, apply_font_to_styled_widgets
from language_strings import get_string, set_language, get_available_languages, CURRENT_LANGUAGE

from language_strings import load_language_from_config, get_string
load_language_from_config()

CONFIG_FILE = "server_checker_config.json"
VERSION_CSV_URL = "https://zhrradiant-l4d2.cn-nb1.rains3.com/%E7%89%88%E6%9C%AC%E4%BF%A1%E6%81%AF-L4D2SOB.csv"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VERSION = "1.3.2.367"


class SettingsDialog:
    def __init__(self, parent, main_app):
        self.parent = parent
        self.main_app = main_app
        self.window = None
        self.current_theme = main_app.style.theme.name if hasattr(main_app.style, 'theme') else 'litera'
        self.window_style_utils = window_style_utils

        # 初始化配置变量
        # 直接从主应用获取配置值，而不是用默认值
        self.language_var = tk.StringVar(value=getattr(main_app, 'language', CURRENT_LANGUAGE))
        self.theme_var = tk.StringVar(value=self.current_theme)
        self.font_var = tk.StringVar(value=getattr(main_app, 'font_var', tk.StringVar(value="微软雅黑")).get())
        self.window_style_var = tk.StringVar(value=getattr(main_app, 'window_style', "light"))
        self.dashboard_enabled_var = tk.BooleanVar(value=getattr(main_app, 'dashboard_enabled', False))
        self.filter_enabled_var = tk.BooleanVar(value=getattr(main_app, 'filter_enabled', False))
        self.map_display_format_var = tk.BooleanVar(value=getattr(main_app, 'map_display_format_enabled', False))
        self.player_info_enabled_var = tk.BooleanVar(value=getattr(main_app, 'player_info_enabled', False))
        self.tray_enabled_var = tk.BooleanVar(value=getattr(main_app, 'tray_enabled', False))
        self.startup_enabled_var = tk.BooleanVar(value=getattr(main_app, 'startup_enabled', False))
        self.hotkey_var = tk.StringVar(value=getattr(main_app, 'workshop_hotkey', ""))

        # 初始化 dashboard_status_label 为 None，避免属性错误
        self.dashboard_status_label = None

        # 版本检查相关变量
        self.latest_version = None
        self.download_url = None
        self.current_version = VERSION  # 当前版本号

        # 启动版本检查
        self.check_version_in_background()

        # 检查是否已有窗口存在
        if hasattr(self.main_app,
                   'settings_window') and self.main_app.settings_window and self.main_app.settings_window.winfo_exists():
            # 如果窗口已存在，直接显示
            self.window = self.main_app.settings_window
            self.window.deiconify()
            self.window.focus()
            # 确保主题变量与当前主题一致
            self.theme_var.set(self.current_theme)

            # 对于已存在的窗口，直接获取 dashboard_status_label 的引用
            # 我们需要遍历窗口的子控件来找到它
            self.find_existing_dashboard_label()
        else:
            # 否则创建新窗口
            self.create_window()
            self.main_app.settings_window = self.window  # 保存窗口引用

        self.load_settings()

    def create_window(self):
        """创建设置窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title(get_string("settings_title", "设置"))
        self.window.geometry("420x520")  # 增加高度以容纳功能模块区域
        self.window.resizable(False, False)
        self.window.transient(self.parent)
        # self.window.grab_set()
        # 应用窗口样式
        self.window_style_utils.apply_window_style(self.window)

        # 设置窗口关闭事件处理
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        # 设置窗口图标（如果存在）
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            self.window.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except:
            pass

        # 主容器
        main_container = ttk.Frame(self.window, padding=(20, 20, 20, 35))
        main_container.pack(fill=tk.BOTH, expand=True)

        # 创建可滚动的容器
        self.create_scrollable_container(main_container)

        # 应用窗口样式后添加延迟
        self.window.after(100, self.center_window)

    def center_window(self):
        """专门用于居中窗口的函数"""
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.window.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")

    def create_scrollable_container(self, parent):
        """创建可滚动的容器"""
        # 创建Canvas和滚动框架
        self.canvas = tk.Canvas(parent, highlightthickness=0)
        scroll_frame = ttk.Frame(self.canvas)

        # 将滚动框架绑定到Canvas
        self.scrollable_window = self.canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        # 配置Canvas滚动
        self.canvas.configure(yscrollcommand=None)  # 不显示滚动条

        # 绑定鼠标滚轮事件
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        scroll_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # 打包Canvas
        self.canvas.pack(side="left", fill="both", expand=True)

        # 关于区域
        self.create_about_section(scroll_frame)

        # 功能模块区域
        self.create_feature_modules_section(scroll_frame)

        # 快捷键模块区域
        self.create_hotkey_section(scroll_frame)

        # 语言设置区域
        self.create_language_section(scroll_frame)

        # 界面设置区域
        self.create_theme_settings(scroll_frame)

    def on_canvas_configure(self, event):
        """当Canvas大小改变时"""
        self.canvas.itemconfig(self.scrollable_window, width=event.width)

    def on_frame_configure(self, event):
        """当框架大小改变时更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, event):
        """鼠标滚轮事件处理"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def hide(self):
        """隐藏设置窗口而不是销毁它"""
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def create_about_section(self, parent):
        """创建关于区域"""
        # 关于LabelFrame
        about_frame = ttk.LabelFrame(parent, text=get_string("about_section", "关于"), padding=15)
        about_frame.pack(fill=tk.X, pady=(0, 15))

        # 创建可点击的关于行
        about_row = ttk.Frame(about_frame)
        about_row.pack(fill=tk.X)

        # 左侧关于文字
        about_label = ttk.Label(
            about_row,
            text=get_string("about_text", "关于 L4D2 Server OptiBrowser"),
            font=(APP_FONT, 10)
        )
        about_label.pack(side=tk.LEFT)

        # 右侧箭头
        arrow_label = ttk.Label(
            about_row,
            text="›",  # 使用右箭头符号
            font=(APP_FONT, 16, 'bold'),
            foreground="#666666"
        )
        arrow_label.pack(side=tk.RIGHT)

        # 使整个行可点击
        for widget in [about_row, about_label, arrow_label]:
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", self.show_about_dialog)

        # 添加分隔线
        separator = ttk.Separator(about_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)

        # 版本信息行（保持原有位置）
        version_row = ttk.Frame(about_frame)
        version_row.pack(fill=tk.X)

        # 版本标签（左侧）
        version_label = ttk.Label(
            version_row,
            text=get_string("version", f"版本: {self.current_version}").format(current_version=self.current_version),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        version_label.pack(side=tk.LEFT)

        # 新版本提示（右侧，初始隐藏）
        self.new_version_label = ttk.Label(
            version_row,
            text=get_string("new_version", "检测到新版本"),
            font=(APP_FONT, 9),
            foreground="#007bff",
            cursor="hand2"
        )
        self.new_version_label.pack(side=tk.RIGHT)
        self.new_version_label.bind("<Button-1>", self.on_new_version_click)
        self.new_version_label.pack_forget()  # 初始隐藏

    def check_version_in_background(self):
        """在后台线程中检查版本"""

        def check_task():
            try:
                response = requests.get(VERSION_CSV_URL, timeout=10)
                response.encoding = 'utf-8-sig'

                csv_data = StringIO(response.text)
                # 读取CSV数据
                import csv
                reader = csv.DictReader(csv_data)

                # 获取最新版本信息（假设第一行是最新版本）
                for row in reader:
                    version = row.get('版本号', '').strip()
                    download_url = row.get('下载地址', '').strip()

                    if version and download_url:
                        self.latest_version = version
                        self.download_url = download_url
                        break

                # 比较版本
                if self.latest_version and self.is_newer_version(self.latest_version, self.current_version):
                    # 在主线程中更新UI
                    self.parent.after(0, self.show_new_version_notification)

            except Exception as e:
                print(f"版本检查失败: {e}")

        # 启动后台线程
        threading.Thread(target=check_task, daemon=True).start()

    def is_newer_version(self, latest, current):
        """比较版本号，判断是否有新版本"""
        try:
            # 将版本号转换为数字元组进行比较
            latest_parts = tuple(map(int, latest.split('.')))
            current_parts = tuple(map(int, current.split('.')))

            return latest_parts > current_parts
        except:
            # 如果版本号格式异常，使用字符串比较
            return latest > current

    def show_new_version_notification(self):
        """显示新版本通知"""
        if hasattr(self, 'new_version_label') and self.new_version_label:
            self.new_version_label.pack(side=tk.RIGHT)

    def on_new_version_click(self, event):
        """点击新版本链接的处理"""
        if self.download_url:
            webbrowser.open(self.download_url)

    def create_feature_modules_section(self, parent):
        """创建功能模块区域"""
        # 功能模块LabelFrame
        feature_frame = ttk.LabelFrame(parent, text=get_string("feature_modules", "功能模块"), padding=15)
        feature_frame.pack(fill=tk.X, pady=(0, 15))

        # 仪表盘开关
        dashboard_frame = ttk.Frame(feature_frame)
        dashboard_frame.pack(fill=tk.X, pady=5)

        # 仪表盘标签
        ttk.Label(
            dashboard_frame,
            text=get_string("dashboard_set", "仪表盘:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 仪表盘开关按钮（使用rounded toggle样式）
        dashboard_switch = ttk.Checkbutton(
            dashboard_frame,
            bootstyle="round-toggle",
            variable=self.dashboard_enabled_var,
            command=self.on_dashboard_toggled
        )
        dashboard_switch.pack(side=tk.RIGHT)

        # 仪表盘状态标签
        self.dashboard_status_label = ttk.Label(
            dashboard_frame,
            text=get_string("enabled", "已启用") if self.dashboard_enabled_var.get() else get_string("disabled", "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.dashboard_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        # 仪表盘描述
        dashboard_desc = ttk.Label(
            feature_frame,
            text=get_string("dashboard_desc", "服务器状态监控仪表盘，提供在线服务器和玩家占用率的可视化统计"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        dashboard_desc.pack(anchor=tk.W, pady=(5, 0))

        # 过滤控件开关
        filter_frame = ttk.Frame(feature_frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            filter_frame,
            text=get_string("filter_controls", "筛选控件:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        filter_switch = ttk.Checkbutton(
            filter_frame,
            bootstyle="round-toggle",
            variable=self.filter_enabled_var,
            command=self.on_filter_toggled
        )
        filter_switch.pack(side=tk.RIGHT)

        self.filter_status_label = ttk.Label(
            filter_frame,
            text=get_string("enabled", "已启用") if self.filter_enabled_var.get() else get_string("disabled", "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.filter_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        filter_desc = ttk.Label(
            feature_frame,
            text=get_string("filter_desc", "显示服务器筛选控件，支持按空房、有人房、超时服务器等进行筛选"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        filter_desc.pack(anchor=tk.W, pady=(5, 0))

        # 地图显示格式开关
        map_format_frame = ttk.Frame(feature_frame)
        map_format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            map_format_frame,
            text=get_string("map_format", "地图格式:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        map_format_switch = ttk.Checkbutton(
            map_format_frame,
            bootstyle="round-toggle",
            variable=self.map_display_format_var,
            command=self.on_map_format_toggled
        )
        map_format_switch.pack(side=tk.RIGHT)

        self.map_format_status_label = ttk.Label(
            map_format_frame,
            text=get_string("enabled", "已启用") if self.map_display_format_var.get() else get_string("disabled", "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.map_format_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        map_format_desc = ttk.Label(
            feature_frame,
            text=get_string("map_format_desc", "将已收录的地图显示格式从'换图代码'改为'中文名 [换图代码]'格式"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        map_format_desc.pack(anchor=tk.W, pady=(5, 0))

        # 玩家信息开关
        player_info_frame = ttk.Frame(feature_frame)
        player_info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            player_info_frame,
            text=get_string("player_info", "玩家信息:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        player_info_switch = ttk.Checkbutton(
            player_info_frame,
            bootstyle="round-toggle",
            variable=self.player_info_enabled_var,
            command=self.on_player_info_toggled
        )
        player_info_switch.pack(side=tk.RIGHT)

        self.player_info_status_label = ttk.Label(
            player_info_frame,
            text=get_string("enabled", "已启用") if self.player_info_enabled_var.get() else get_string("disabled",
                                                                                                       "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.player_info_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        player_info_desc = ttk.Label(
            feature_frame,
            text=get_string("player_info_desc", "记录服务器中的玩家信息，包括玩家名称和游玩时间"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        player_info_desc.pack(anchor=tk.W, pady=(5, 0))

        # 系统托盘开关
        tray_frame = ttk.Frame(feature_frame)
        tray_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            tray_frame,
            text=get_string("system_tray", "系统托盘:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        tray_switch = ttk.Checkbutton(
            tray_frame,
            bootstyle="round-toggle",
            variable=self.tray_enabled_var,
            command=self.on_tray_toggled
        )
        tray_switch.pack(side=tk.RIGHT)

        self.tray_status_label = ttk.Label(
            tray_frame,
            text=get_string("enabled", "已启用") if self.tray_enabled_var.get() else get_string("disabled", "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.tray_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        tray_desc = ttk.Label(
            feature_frame,
            text=get_string("tray_desc", "启用后关闭窗口时最小化到系统托盘，单击托盘图标可恢复显示"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        tray_desc.pack(anchor=tk.W, pady=(5, 0))

        # 开机启动开关
        startup_frame = ttk.Frame(feature_frame)
        startup_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            startup_frame,
            text=get_string("startup", "开机启动:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.startup_enabled_var = tk.BooleanVar(value=False)  # 在__init__中也要初始化这个变量
        startup_switch = ttk.Checkbutton(
            startup_frame,
            bootstyle="round-toggle",
            variable=self.startup_enabled_var,
            command=self.on_startup_toggled
        )
        startup_switch.pack(side=tk.RIGHT)

        self.startup_status_label = ttk.Label(
            startup_frame,
            text=get_string("enabled", "已启用") if self.startup_enabled_var.get() else get_string("disabled",
                                                                                                   "已禁用"),
            font=(APP_FONT, 9),
            foreground="#666666"
        )
        self.startup_status_label.pack(side=tk.RIGHT, padx=(0, 10))

        startup_desc = ttk.Label(
            feature_frame,
            text=get_string("startup_desc", "启用后系统启动时自动运行程序，如果开启了托盘功能则会隐藏启动"),
            font=(APP_FONT, 8),
            foreground="#888888",
            wraplength=350
        )
        startup_desc.pack(anchor=tk.W, pady=(5, 0))

    def create_hotkey_section(self, parent):
        """创建工坊快捷键设置区域"""
        # 快捷键LabelFrame
        hotkey_frame = ttk.LabelFrame(parent, text=get_string("workshop_hotkey", "工坊快捷键"), padding=15)
        hotkey_frame.pack(fill=tk.X, pady=(0, 15))

        # 快捷键说明
        hotkey_desc = ttk.Label(
            hotkey_frame,
            text=get_string("workshop_hotkey_desc", "设置快捷键，按下时自动解析选中的工坊链接"),
            font=(APP_FONT, 9)
        )
        hotkey_desc.pack(anchor=tk.W, pady=(0, 10))

        # 快捷键设置框架 - 使用fill=tk.X让框架占据整行
        hotkey_setting_frame = ttk.Frame(hotkey_frame)
        hotkey_setting_frame.pack(fill=tk.X, pady=5)

        # 快捷键标签（左侧固定宽度）
        ttk.Label(
            hotkey_setting_frame,
            text=get_string("hotkey", "快捷键:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 中间容器 - 占据剩余空间
        middle_container = ttk.Frame(hotkey_setting_frame)
        middle_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 快捷键输入框 - 使用主应用的快捷键值，占据左侧剩余空间
        self.hotkey_var = tk.StringVar(value=self.main_app.workshop_hotkey)
        self.hotkey_entry = ttk.Entry(
            middle_container,
            textvariable=self.hotkey_var,
            state='readonly'
        )
        self.hotkey_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 录制按钮（右侧固定宽度）
        self.recording_hotkey = False
        self.record_btn = create_outline_button(
            middle_container,
            text=get_string("record_hotkey", "录制"),
            command=self.start_hotkey_recording,
            width=6
        )
        self.record_btn.pack(side=tk.RIGHT)

        # 绑定快捷键输入框的点击事件
        self.hotkey_entry.bind('<Button-1>', lambda e: self.start_hotkey_recording())

    def create_language_section(self, parent):
        """创建语言设置区域"""
        # 语言设置LabelFrame
        language_frame = ttk.LabelFrame(parent, text=get_string("language_confirm", "语言"), padding=15)
        language_frame.pack(fill=tk.X, pady=(0, 15))

        # 语言选择说明
        language_label = ttk.Label(
            language_frame,
            text=get_string("language_desc", "选择应用程序的显示语言"),
            font=(APP_FONT, 9)
        )
        language_label.pack(anchor=tk.W, pady=(0, 10))

        # 语言选择框架
        language_select_frame = ttk.Frame(language_frame)
        language_select_frame.pack(fill=tk.X)

        # 语言选择标签
        ttk.Label(
            language_select_frame,
            text=get_string("language"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 语言选择下拉框
        language_combo = ttk.Combobox(
            language_select_frame,
            textvariable=self.language_var,
            values=get_available_languages(),
            state="readonly",
            width=15
        )
        language_combo.pack(side=tk.LEFT)
        language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)

        # 重启提示
        restart_label = ttk.Label(
            language_frame,
            text=get_string("restart_required", "需要重启应用以应用此设置"),
            font=(APP_FONT, 8),
            foreground="#888888"
        )
        restart_label.pack(anchor=tk.W, pady=(5, 0))

    def create_theme_settings(self, parent):
        """创建主题设置区域"""
        # 界面主题LabelFrame
        theme_frame = ttk.LabelFrame(parent, text=get_string("ui_theme", "界面主题"), padding=15)
        theme_frame.pack(fill=tk.X, pady=(0, 15))

        # 主题选择说明
        theme_label = ttk.Label(
            theme_frame,
            text=get_string("theme_desc", "选择应用程序的视觉主题风格"),
            font=(APP_FONT, 9)
        )
        theme_label.pack(anchor=tk.W, pady=(0, 10))

        # 主题选择框架
        theme_select_frame = ttk.Frame(theme_frame)
        theme_select_frame.pack(fill=tk.X)

        # 主题选择标签
        ttk.Label(
            theme_select_frame,
            text=get_string("theme", "主题:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 主题选择下拉框
        theme_combo = ttk.Combobox(
            theme_select_frame,
            textvariable=self.theme_var,
            values=["litera", "cosmo", "flatly", "minty", "lumen", "sandstone", "yeti",
                    "pulse", "united", "journal", "simplex", "cerculean", "morph", "superhero"],
            state="readonly",
            width=15
        )
        theme_combo.pack(side=tk.LEFT)
        theme_combo.bind("<<ComboboxSelected>>", self.on_theme_changed)

        # 字体选择框架（移除预览按钮，改为选择后直接弹出预览）
        font_frame = ttk.Frame(theme_frame)
        font_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(
            font_frame,
            text=get_string("font", "字体:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 获取系统可用字体
        try:
            import tkinter.font as font
            available_fonts = list(font.families())
            available_fonts.sort()
            # 在字体列表开头添加"Default"选项
            available_fonts = ["Default"] + available_fonts
        except:
            available_fonts = ["Default", "Arial", "Times New Roman", "Courier New", "Verdana",
                               "Tahoma", "微软雅黑", "宋体", "黑体"]

        # 字体选择下拉框
        font_combo = ttk.Combobox(
            font_frame,
            textvariable=self.font_var,
            values=available_fonts,
            state="readonly",
            width=15
        )
        font_combo.pack(side=tk.LEFT)
        # 选择字体后直接弹出预览窗口
        font_combo.bind("<<ComboboxSelected>>", self.on_font_changed)

        # 窗口样式选择框架
        window_style_frame = ttk.Frame(theme_frame)
        window_style_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(
            window_style_frame,
            text=get_string("window_style", "窗口:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 窗口样式选择下拉框
        window_style_combo = ttk.Combobox(
            window_style_frame,
            textvariable=self.window_style_var,
            values=["light", "dark", "win7"],
            state="readonly",
            width=15
        )
        window_style_combo.pack(side=tk.LEFT)
        window_style_combo.bind("<<ComboboxSelected>>", self.on_window_style_changed)

        # 主题预览区域
        preview_frame = ttk.Frame(theme_frame)
        preview_frame.pack(fill=tk.X, pady=(15, 0))

        # 预览标签
        ttk.Label(
            preview_frame,
            text=get_string("preview", "预览:"),
            font=(APP_FONT, 9)
        ).pack(anchor=tk.W, pady=(0, 5))

        # 预览示例控件
        preview_container = ttk.Frame(preview_frame, relief="solid", borderwidth=1)
        preview_container.pack(fill=tk.X, pady=5)

        # 示例按钮
        example_btn = create_outline_button(
            preview_container,
            text=get_string("example_button", "示例按钮"),
            width=12
        )
        example_btn.pack(pady=10)

        # 示例输入框
        example_entry = ttk.Entry(
            preview_container,
            width=20
        )
        example_entry.insert(0, get_string("example_text", "示例文本"))
        example_entry.pack(pady=5)

        # 示例复选框
        example_check = ttk.Checkbutton(
            preview_container,
            text=get_string("example_checkbox", "示例复选框")
        )
        example_check.pack(pady=5)

    def on_dashboard_toggled(self):
        """当仪表盘开关状态改变时的处理"""
        enabled = self.dashboard_enabled_var.get()

        # 更新主应用的dashboard_enabled状态
        self.main_app.dashboard_enabled = enabled

        # 更新状态标签
        self.dashboard_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 保存设置
        self.save_settings()

        # 更新主界面按钮显示
        self.update_main_ui_dashboard_button()

    def update_main_ui_dashboard_button(self):
        """更新主界面的仪表盘按钮显示"""
        enabled = self.dashboard_enabled_var.get()

        # 通过主应用引用直接控制按钮显示
        if hasattr(self.main_app, 'dashboard_btn'):
            if enabled:
                self.main_app.dashboard_btn.pack(fill=tk.X, pady=3)
            else:
                self.main_app.dashboard_btn.pack_forget()

        # 删除下面这段有问题的代码，因为它是不必要的
        # 主应用已经保存了 dashboard_btn 的引用，直接使用即可

        # 只需要保存设置即可
        self.save_settings()

    def on_language_changed(self, event=None):
        """当语言改变时的处理"""
        new_language = self.language_var.get()

        # 显示确认对话框
        confirm_win = tk.Toplevel(self.window)
        confirm_win.title(get_string("language_confirm"))
        confirm_win.geometry("350x175")
        confirm_win.iconbitmap(os.path.join(BASE_DIR, "transparent_16x16.ico"))
        confirm_win.resizable(False, False)
        confirm_win.transient(self.window)
        confirm_win.grab_set()

        # 应用窗口样式
        self.window_style_utils.apply_window_style(confirm_win)

        # 确认消息
        message = f"{get_string('restart_required')}\n\n{get_string('language')} {new_language}"

        ttk.Label(
            confirm_win,
            text=message,
            font=(APP_FONT, 10),
            wraplength=300
        ).pack(pady=20)

        # 按钮框架
        btn_frame = ttk.Frame(confirm_win)
        btn_frame.pack(pady=10)

        def confirm_change():
            # 保存语言设置
            set_language(new_language)
            self.save_settings()
            confirm_win.destroy()
            # 标记需要重启
            self.main_app.need_restart = True
            self.window.destroy()
            self.main_app.root.destroy()

        def cancel_change():
            # 恢复原来的语言
            self.language_var.set(CURRENT_LANGUAGE)
            confirm_win.destroy()

        create_outline_button(
            btn_frame,
            text=get_string("confirm", "确定"),
            command=confirm_change
        ).pack(side=tk.LEFT, padx=10)

        create_outline_button(
            btn_frame,
            text=get_string("cancel", "取消"),
            command=cancel_change
        ).pack(side=tk.RIGHT, padx=10)

        # 居中显示
        confirm_win.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - confirm_win.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - confirm_win.winfo_height()) // 2
        confirm_win.geometry(f"+{x}+{y}")

    def on_theme_changed(self, event=None):
        """当主题改变时的处理"""
        new_theme = self.theme_var.get()

        try:
            # 应用新主题
            self.main_app.style.theme_use(new_theme)
            self.current_theme = new_theme

            # 重新设置Treeview行高
            self.main_app.style.configure("Treeview", rowheight=25)

            # 重新为无法直接使用font属性的控件设置字体样式
            apply_font_to_styled_widgets(self.main_app.style, APP_FONT)

            # 保存设置到配置文件
            self.save_settings()

            # 更新当前窗口的样式（如果需要）
            self.update_window_style()

        except Exception as e:
            print(f"主题切换失败: {str(e)}")
            # 恢复原来的主题
            self.theme_var.set(self.current_theme)

    def update_window_style(self):
        """更新当前设置窗口的样式"""
        # 这里可以添加更新设置窗口样式的代码
        # 由于ttkbootstrap主题是全局的，通常不需要特别处理
        pass

    def on_font_changed(self, event=None):
        """当字体改变时的处理 - 直接弹出预览窗口"""
        selected_font = self.font_var.get()
        if not selected_font or selected_font == "Default":
            # 如果选择Default或空值，设置为空字符串
            selected_font = ""

        # 显示字体预览窗口
        self.show_font_preview(selected_font)

    def show_font_preview(self, selected_font):
        """显示字体预览窗口（简化版，与窗口样式预览一致）"""
        preview_win = tk.Toplevel(self.window)
        preview_win.title(get_string("font_preview_title", "字体预览"))
        preview_win.geometry("300x200")
        preview_win.iconbitmap(os.path.join(BASE_DIR, "transparent_16x16.ico"))
        preview_win.resizable(False, False)
        preview_win.transient(self.window)
        preview_win.grab_set()

        # 应用窗口样式
        self.window_style_utils.apply_window_style(preview_win)

        # 预览内容 - 简化显示
        if selected_font:
            preview_text = get_string("font_preview_current", f"当前预览: {selected_font}").format(font_name=selected_font)
        else:
            preview_text = get_string("font_preview_default", "当前预览: Default (系统默认字体)")

        ttk.Label(
            preview_win,
            text=preview_text,
            font=(APP_FONT, 12)
        ).pack(pady=20)

        # 字体示例
        if selected_font:
            example_font = (selected_font, 11)
        else:
            example_font = (APP_FONT, 11)  # 使用默认字体预览

        example_label = ttk.Label(
            preview_win,
            text="中文示例文本 ABCabc 123",
            font=example_font
        )
        example_label.pack(pady=5)

        ttk.Label(
            preview_win,
            text=get_string("font_preview_restart_hint", "点击确定将关闭程序以应用此字体"),
            font=(APP_FONT, 9),
            foreground="#666666"
        ).pack(pady=5)

        # 按钮框架
        btn_frame = ttk.Frame(preview_win)
        btn_frame.pack(pady=20)

        def confirm_change():
            # 保存字体设置
            self.font_var.set(selected_font)
            self.save_settings()
            preview_win.destroy()
            # 直接重启应用（想实现重启会有很多问题，现保持重启无效，不完善重启逻辑）
            self.main_app.need_restart = True
            self.window.destroy()
            self.main_app.root.destroy()

        def cancel_change():
            # 恢复原来的字体
            self.font_var.set(self.current_font)
            preview_win.destroy()

        create_outline_button(
            btn_frame,
            text=get_string("confirm", "确定"),
            command=confirm_change
        ).pack(side=tk.LEFT, padx=10)

        create_outline_button(
            btn_frame,
            text=get_string("cancel", "取消"),
            command=cancel_change
        ).pack(side=tk.RIGHT, padx=10)

        # 居中显示
        preview_win.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - preview_win.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - preview_win.winfo_height()) // 2
        preview_win.after(100, lambda: preview_win.geometry(f"+{x}+{y}"))

    def on_window_style_changed(self, event=None):
        """当窗口样式改变时的处理"""
        new_style = self.window_style_var.get()

        # 显示预览窗口
        self.show_style_preview(new_style)

    def show_style_preview(self, style):
        """显示样式预览窗口"""
        preview_win = tk.Toplevel(self.window)
        preview_win.title(get_string("window_style_preview_title", "窗口样式预览"))
        preview_win.geometry("300x200")
        preview_win.iconbitmap(os.path.join(BASE_DIR, "transparent_16x16.ico"))
        preview_win.resizable(False, False)
        preview_win.transient(self.window)
        preview_win.grab_set()

        # 应用窗口样式
        self.window_style_utils.apply_window_style(preview_win, style)

        # 先让窗口显示出来
        preview_win.update_idletasks()

        # 应用选择的样式
        try:
            pywinstyles.apply_style(preview_win, style)
            # 强制刷新窗口和标题栏
            preview_win.withdraw()  # 隐藏窗口
            preview_win.deiconify()  # 重新显示窗口
            preview_win.update_idletasks()
            preview_win.update()
        except Exception as e:
            print(f"应用窗口样式失败: {e}")
            # 回退到默认样式
            self.window_style_var.set("light")
            preview_win.destroy()
            messagebox.showerror("错误", f"应用窗口样式失败: {e}")
            return

        # 预览内容
        ttk.Label(
            preview_win,
            text=get_string("window_style_preview_current", f"当前预览: {style} 样式").format(style=style),
            font=(APP_FONT, 12)
        ).pack(pady=20)

        ttk.Label(
            preview_win,
            text=get_string("window_style_preview_restart_hint", "点击确定将关闭程序以应用此样式"),
            font=(APP_FONT, 9),
            foreground="#666666"
        ).pack(pady=10)

        # 按钮框架
        btn_frame = ttk.Frame(preview_win)
        btn_frame.pack(pady=20)

        def confirm_change():
            # 保存设置
            self.window_style = style
            self.save_settings()
            preview_win.destroy()
            # 直接重启应用（想实现重启会有很多问题，现保持重启无效，不完善重启逻辑）
            self.main_app.need_restart = True
            self.window.destroy()
            self.main_app.root.destroy()

        def cancel_change():
            # 恢复原来的样式
            self.window_style_var.set(self.window_style)
            preview_win.destroy()

        create_outline_button(
            btn_frame,
            text=get_string("confirm", "确定"),
            command=confirm_change
        ).pack(side=tk.LEFT, padx=10)

        create_outline_button(
            btn_frame,
            text=get_string("cancel", "取消"),
            command=cancel_change
        ).pack(side=tk.RIGHT, padx=10)

        # 居中显示
        preview_win.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - preview_win.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - preview_win.winfo_height()) // 2
        preview_win.geometry(f"+{x}+{y}")

    # 查找已存在的 dashboard_status_label
    def find_existing_dashboard_label(self):
        """在已存在的设置窗口中查找 dashboard_status_label"""
        if not self.window:
            return

        # 递归查找所有子控件
        def find_label(widget):
            if hasattr(widget, '_name') and getattr(widget, '_name', '').startswith('dashboard_status'):
                return widget
            for child in widget.winfo_children():
                result = find_label(child)
                if result:
                    return result
            return None

        self.dashboard_status_label = find_label(self.window)

        # 如果没找到，创建一个临时的空标签避免错误
        if not self.dashboard_status_label:
            self.dashboard_status_label = ttk.Label(self.window)
            self.dashboard_status_label._name = 'dashboard_status_temp'

    def on_filter_toggled(self):
        """当过滤控件开关状态改变时的处理"""
        enabled = self.filter_enabled_var.get()

        # 更新主应用的filter_enabled状态
        self.main_app.filter_enabled = enabled

        # 更新状态标签
        self.filter_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 保存设置
        self.save_settings()

        # 更新主界面过滤控件显示
        self.update_main_ui_filter_controls()

    def update_main_ui_filter_controls(self):
        """更新主界面的过滤控件显示"""
        enabled = self.filter_enabled_var.get()

        # 通过主应用引用直接控制过滤控件显示
        if hasattr(self.main_app, 'filter_utils') and self.main_app.filter_utils:
            if enabled:
                self.main_app.filter_utils.frame.pack(side=tk.RIGHT, padx=10)
            else:
                self.main_app.filter_utils.frame.pack_forget()

        # 更新主应用的状态
        self.main_app.filter_enabled = enabled
        self.main_app.save_config()

    def on_map_format_toggled(self):
        """当地图显示格式开关状态改变时的处理"""
        enabled = self.map_display_format_var.get()

        # 更新主应用的地图显示格式状态
        self.main_app.map_display_format_enabled = enabled

        # 更新状态标签
        self.map_format_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 保存设置
        self.save_settings()

        # 刷新当前显示的服务器列表
        self.main_app.refresh_current_page_display()

    def on_player_info_toggled(self):
        """当玩家信息开关状态改变时的处理"""
        enabled = self.player_info_enabled_var.get()

        # 更新主应用的player_info_enabled状态
        self.main_app.player_info_enabled = enabled

        # 更新状态标签
        self.player_info_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 保存设置
        self.save_settings()

        # 更新主界面玩家信息按钮显示
        self.update_main_ui_player_info_button()

    def update_main_ui_player_info_button(self):
        """更新主界面的玩家信息按钮显示"""
        enabled = self.player_info_enabled_var.get()

        # 通过主应用引用直接控制按钮显示
        if hasattr(self.main_app, 'player_info_btn'):
            if enabled:
                self.main_app.player_info_btn.pack(fill=tk.X, pady=3)
            else:
                self.main_app.player_info_btn.pack_forget()

        # 更新主应用的状态
        self.main_app.player_info_enabled = enabled
        self.main_app.save_config()

    def on_tray_toggled(self):
        """当系统托盘开关状态改变时的处理"""
        enabled = self.tray_enabled_var.get()

        # 更新主应用的tray_enabled状态
        self.main_app.tray_enabled = enabled

        # 更新状态标签
        self.tray_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 保存设置
        self.save_settings()

        # 更新主应用的托盘状态
        self.update_main_ui_tray_setting()

        # 如果开机启动已启用，同步更新快捷方式参数
        if self.startup_enabled_var.get():
            self.update_startup_shortcut_parameters()

    def update_startup_shortcut_parameters(self):
        """更新开机启动快捷方式的启动参数"""
        try:
            from startup_manager import get_startup_manager
            startup_manager = get_startup_manager()

            # 检查快捷方式是否存在
            if startup_manager.shortcut_exists():
                # 获取当前的托盘设置状态
                tray_enabled = self.tray_enabled_var.get()
                # 更新快捷方式参数
                success = startup_manager.update_shortcut(tray_enabled)
                if not success:
                    print("更新开机启动快捷方式参数失败")
        except Exception as e:
            print(f"更新开机启动快捷方式参数时出错: {e}")

    def update_main_ui_tray_setting(self):
        """更新主应用的托盘设置"""
        enabled = self.tray_enabled_var.get()

        # 更新主应用的状态
        self.main_app.tray_enabled = enabled

        # 如果启用了托盘，立即设置托盘图标
        if enabled and hasattr(self.main_app, 'setup_tray_icon'):
            self.main_app.setup_tray_icon()

        # 保存配置
        self.main_app.save_config()

    def start_hotkey_recording(self):
        """开始录制快捷键"""
        if self.recording_hotkey:
            return

        self.recording_hotkey = True
        self.hotkey_entry.config(state='normal')
        self.hotkey_var.set(get_string("press_hotkey", "按下快捷键..."))
        # self.hotkey_status_label.config(text=get_string("recording", "录制中..."), foreground="#dc3545")
        self.record_btn.config(state='disabled')

        # 绑定全局键盘事件
        self.hotkey_bind_id = self.hotkey_entry.bind('<KeyPress>', self.on_hotkey_pressed)
        self.hotkey_entry.focus_set()

    def on_hotkey_pressed(self, event):
        """处理快捷键按键事件"""
        if not self.recording_hotkey:
            return

        # 获取按键组合
        modifiers = []
        if event.state & 0x4:  # Control
            modifiers.append('ctrl')
        if event.state & 0x8:  # Alt
            modifiers.append('alt')
        if event.state & 0x1:  # Shift
            modifiers.append('shift')
        if event.state & 0x2:  # Caps Lock (通常不使用)
            pass

        # 获取主键
        key = event.keysym.lower()

        # 忽略修饰键本身
        if key in ['control_l', 'control_r', 'alt_l', 'alt_r', 'shift_l', 'shift_r']:
            return

        # 构建快捷键字符串
        if modifiers:
            hotkey = '+'.join(modifiers + [key])
        else:
            hotkey = key

        # 更新显示
        self.hotkey_var.set(hotkey)
        self.finish_hotkey_recording()

        return "break"  # 阻止默认事件

    def finish_hotkey_recording(self):
        self.recording_hotkey = False
        self.hotkey_entry.config(state='readonly')
        # self.hotkey_status_label.config(
        #     text=get_string("set", "已设置"),
        #     foreground="#28a745"
        # )
        self.record_btn.config(state='normal')

        # 解绑事件
        if hasattr(self, 'hotkey_bind_id'):
            self.hotkey_entry.unbind('<KeyPress>', self.hotkey_bind_id)

        # 更新主程序的快捷键值
        self.main_app.workshop_hotkey = self.hotkey_var.get()

        # 保存设置
        self.save_settings()

    def on_startup_toggled(self):
        """当开机启动开关状态改变时的处理"""
        enabled = self.startup_enabled_var.get()

        # 更新状态标签
        self.startup_status_label.config(
            text=get_string("enabled", "已启用") if enabled else get_string("disabled", "已禁用"),
            foreground="#28a745" if enabled else "#dc3545"
        )

        # 更新主应用的开机启动状态
        self.main_app.startup_enabled = enabled

        # 保存设置
        self.save_settings()

        # 实际创建或删除快捷方式
        self.update_startup_shortcut()

    def update_startup_shortcut(self):
        """更新开机启动快捷方式"""
        try:
            from startup_manager import get_startup_manager
            startup_manager = get_startup_manager()

            if self.startup_enabled_var.get():
                # 获取托盘设置状态，决定是否最小化启动
                tray_enabled = self.tray_enabled_var.get()  # 使用当前托盘设置
                success = startup_manager.create_shortcut(tray_enabled)
                if not success:
                    messagebox.showerror("错误", "创建开机启动快捷方式失败，请检查权限设置")
                    # 回滚开关状态
                    self.startup_enabled_var.set(False)
                    self.startup_status_label.config(
                        text=get_string("disabled", "已禁用"),
                        foreground="#dc3545"
                    )
            else:
                success = startup_manager.remove_shortcut()
                if not success:
                    messagebox.showerror("错误", "删除开机启动快捷方式失败，请手动检查启动文件夹")
        except ImportError as e:
            messagebox.showerror("错误", f"开机启动功能需要pywin32和winshell库支持: {str(e)}")
            # 回滚开关状态
            self.startup_enabled_var.set(False)
            self.startup_status_label.config(
                text=get_string("disabled", "已禁用"),
                foreground="#dc3545"
            )
        except Exception as e:
            messagebox.showerror("错误", f"操作开机启动失败: {str(e)}")
            # 回滚开关状态
            self.startup_enabled_var.set(False)
            self.startup_status_label.config(
                text=get_string("disabled", "已禁用"),
                foreground="#dc3545"
            )

    def load_settings(self):
        """从配置文件加载所有设置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 加载语言设置
                if 'language' in config:
                    language = config['language']
                    if language in get_available_languages():
                        self.language_var.set(language)
                        set_language(language)

                # 加载主题设置
                if 'theme' in config:
                    theme = config['theme']
                    if theme in ["litera", "cosmo", "flatly", "minty", "lumen", "sandstone", "yeti",
                                 "pulse", "united", "journal", "simplex", "cerculean", "morph", "superhero"]:
                        self.theme_var.set(theme)
                        # 只在第一次创建窗口时应用主题，避免重复应用
                        if not hasattr(self, 'window_created') or not self.window_created:
                            self.on_theme_changed()

                # 加载字体设置
                if 'font' in config:
                    font_value = config['font']
                    # 如果配置中的字体值为空，使用默认微软雅黑
                    if not font_value:
                        self.font_var.set("Default")
                        self.current_font = ""
                    else:
                        self.font_var.set(font_value)
                        self.current_font = font_value
                else:
                    self.font_var.set("微软雅黑")  # 默认显示为微软雅黑
                    self.current_font = "微软雅黑"  # 实际值为微软雅黑

                # 加载窗口样式设置
                if 'window_style' in config:
                    self.window_style_var.set(config['window_style'])
                    self.window_style = config['window_style']  # 保存当前样式
                else:
                    # 默认light样式
                    self.window_style_var.set("light")
                    self.window_style = "light"

                # 加载仪表盘设置
                if 'dashboard_enabled' in config:
                    self.dashboard_enabled_var.set(config['dashboard_enabled'])
                else:
                    # 默认禁用仪表盘（向后兼容）
                    self.dashboard_enabled_var.set(False)

                # 更新状态标签（只有在标签存在时才更新）
                if hasattr(self,
                           'dashboard_status_label') and self.dashboard_status_label and self.dashboard_status_label.winfo_exists():
                    self.dashboard_status_label.config(
                        text=get_string("enabled", "已启用") if self.dashboard_enabled_var.get() else get_string("disabled", "已禁用"),
                        foreground="#28a745" if self.dashboard_enabled_var.get() else "#dc3545"
                    )

                # 加载过滤控件设置
                if 'filter_enabled' in config:
                    self.filter_enabled_var.set(config['filter_enabled'])
                else:
                    # 默认禁用过滤控件
                    self.filter_enabled_var.set(False)

                # 更新状态标签
                if hasattr(self, 'filter_status_label'):
                    self.filter_status_label.config(
                        text=get_string("enabled", "已启用") if self.filter_enabled_var.get() else get_string("disabled", "已禁用"),
                        foreground="#28a745" if self.filter_enabled_var.get() else "#dc3545"
                    )

                # 加载地图显示格式设置
                if 'map_display_format' in config:
                    self.map_display_format_var.set(config['map_display_format'])
                else:
                    # 默认禁用
                    self.map_display_format_var.set(False)

                # 更新状态标签
                if hasattr(self, 'map_format_status_label'):
                    self.map_format_status_label.config(
                        text=get_string("enabled", "已启用") if self.map_display_format_var.get() else get_string("disabled", "已禁用"),
                        foreground="#28a745" if self.map_display_format_var.get() else "#dc3545"
                    )

                # 加载玩家信息设置
                if 'player_info_enabled' in config:
                    self.player_info_enabled_var.set(config['player_info_enabled'])
                else:
                    self.player_info_enabled_var.set(False)

                # 更新状态标签
                if hasattr(self, 'player_info_status_label'):
                    self.player_info_status_label.config(
                        text=get_string("enabled", "已启用") if self.player_info_enabled_var.get() else get_string(
                            "disabled", "已禁用"),
                        foreground="#28a745" if self.player_info_enabled_var.get() else "#dc3545"
                    )

                # 加载系统托盘设置
                if 'tray_enabled' in config:
                    self.tray_enabled_var.set(config['tray_enabled'])
                else:
                    # 默认禁用系统托盘
                    self.tray_enabled_var.set(False)

                # 更新状态标签
                if hasattr(self, 'tray_status_label'):
                    self.tray_status_label.config(
                        text=get_string("enabled", "已启用") if self.tray_enabled_var.get() else get_string("disabled",
                                                                                                            "已禁用"),
                        foreground="#28a745" if self.tray_enabled_var.get() else "#dc3545"
                    )

                # 加载开机启动设置
                if 'startup_enabled' in config:
                    self.startup_enabled_var.set(config['startup_enabled'])
                else:
                    self.startup_enabled_var.set(False)

                # 更新状态标签
                if hasattr(self, 'startup_status_label'):
                    self.startup_status_label.config(
                        text=get_string("enabled", "已启用") if self.startup_enabled_var.get() else get_string(
                            "disabled", "已禁用"),
                        foreground="#28a745" if self.startup_enabled_var.get() else "#dc3545"
                    )

                # 加载工坊快捷键设置
                if 'workshop_hotkey' in config:
                    self.hotkey_var.set(config['workshop_hotkey'])
                    # self.hotkey_status_label.config(
                    #     text=get_string("set", "已设置") if config['workshop_hotkey'] else get_string("not_set",
                    #                                                                                   "未设置"),
                    #     foreground="#28a745" if config['workshop_hotkey'] else "#666666"
                    # )
                else:
                    # 默认快捷键
                    self.hotkey_var.set("")
                    # self.hotkey_status_label.config(text=get_string("set", "已设置"), foreground="#28a745")

        except Exception as e:
            print(f"加载设置失败: {str(e)}")
            # 设置默认值
            self.font_var.set("微软雅黑")
            self.current_font = "微软雅黑"
            self.window_style_var.set("light")
            self.window_style = "light"
            self.dashboard_enabled_var.set(False)
            self.filter_enabled_var.set(False)
            self.map_display_format_var.set(False)
            self.player_info_enabled_var.set(False)
            self.hotkey_var.set()
            self.tray_enabled_var.set(False)
            self.startup_enabled_var.set(False)
            # 只有在标签存在时才更新
            if hasattr(self,
                       'dashboard_status_label') and self.dashboard_status_label and self.dashboard_status_label.winfo_exists():
                self.dashboard_status_label.config(
                    text=get_string("enabled", "已启用"),
                    foreground="#28a745"
                )

    def save_settings(self):
        """保存所有设置到配置文件"""
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # 更新版本信息
            config['version'] = self.current_version

            # 更新语言设置
            config['language'] = self.language_var.get()

            # 更新主题设置
            config['theme'] = self.theme_var.get()

            # 更新字体设置
            config['font'] = self.font_var.get()

            # 更新窗口样式设置
            config['window_style'] = self.window_style_var.get()

            # 更新仪表盘设置
            config['dashboard_enabled'] = self.dashboard_enabled_var.get()

            # 更新过滤控件设置
            config['filter_enabled'] = self.filter_enabled_var.get()

            # 更新地图显示格式设置
            config['map_display_format'] = self.map_display_format_var.get()

            # 更新玩家信息设置
            config['player_info_enabled'] = self.player_info_enabled_var.get()

            # 更新系统托盘设置
            config['tray_enabled'] = self.tray_enabled_var.get()

            # 保存开机启动设置
            config['startup_enabled'] = self.startup_enabled_var.get()

            # 保存工坊快捷键设置
            config['workshop_hotkey'] = self.hotkey_var.get()

            # 保存回文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 更新主应用的快捷键设置并立即生效
            self.main_app.workshop_hotkey = self.hotkey_var.get()
            self.main_app.hotkey_manager.setup_hotkey(self.hotkey_var.get())

        except Exception as e:
            print(f"保存设置失败: {str(e)}")

    def show_about_dialog(self, event=None):
        """显示关于对话框"""
        AboutDialog(self.window)