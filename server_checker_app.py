import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
import pywinstyles
from tkinter import Toplevel
import webbrowser
from PIL import Image, ImageTk, ImageDraw
import socket
import struct
import a2s
import os
import threading
import time
from threading import Thread
from collections import deque
import random
import json
import requests
import csv
from io import StringIO
from about_dialog import AboutDialog
from async_server_query import AsyncServerQuery
from blocked_list_dialog import BlockedListDialog
from utils import fetch_ips, create_outline_button
from map_utils import MapUtils
from workshop_utils import WorkshopUtils
from icon_utils import IconUtils
from dashboard import Dashboard
from filter_utils import FilterUtils
from window_style_utils import window_style_utils
from font_utils import APP_FONT, apply_font_to_styled_widgets
from player_info_window import PlayerInfoWindow
from hotkey_manager import HotkeyManager

from language_strings import load_language_from_config, get_string
load_language_from_config()

IP_FILE = "servers.txt"
BLOCKED_FILE = "blocked.txt"
CONFIG_FILE = "server_checker_config.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VERSION = "1.3.2.367"

class ServerCheckerApp:
    def __init__(self, root):
        self.root = root
        self.current_version = VERSION
        self.icon_utils = IconUtils()
        self.transparent_icon = self.icon_utils.create_transparent_icon()
        self.magnifier_icon = self.icon_utils.create_magnifier_icon()
        self.refresh_icon = self.icon_utils.create_refresh_icon()
        self.map_utils = MapUtils(root)
        self.workshop_utils = WorkshopUtils(root)
        self.dashboard = Dashboard(root, self)
        self.player_info_window = PlayerInfoWindow(root, self)
        self.hotkey_manager = HotkeyManager(self)
        self.filter_utils = None # 初始化过滤器
        self.blocked_list_dialog = None  # 屏蔽列表窗口实例引用
        self.root.title("L4D2 Server OptiBrowser")
        self.query_engine = None
        self.progress = None
        self.current_sort = {'column': None, 'reverse': False}
        self.all_items = {'main': set()}  # 跟踪所有条目
        self.custom_pages = {}
        self.page_order = []  # 记录页面顺序
        self.total_servers = 0
        self.queried_count = 0
        self.completed_count = 0
        self.query_mode = tk.StringVar(value=get_string("standard", "标准"))  # 模式变量

        # UI刷新系统
        self.tree_lock = threading.Lock()
        self.update_buffer = []

        # 加载配置中的主题设置
        self.load_theme_from_config()

        self.workshop_utils = WorkshopUtils(root, self.style)  # 传递 style
        self.map_utils = MapUtils(root, self.workshop_utils)

        # 窗口样式相关
        self.window_style = "light"  # 默认样式
        self.need_restart = False

        # 默认启用仪表盘
        self.font_var = tk.StringVar(value="微软雅黑")
        self.dashboard_enabled = False
        self.filter_enabled = False
        self.map_display_format_enabled = False
        self.player_info_enabled = False
        self.workshop_hotkey = ""
        self.tray_enabled = False
        self.startup_enabled = False

        self.tray_icon = None

        self.setup_ui()

        # 在加载配置之前检查语言设置
        self.check_language_setting()

        self.current_page = "main"
        self.load_config()
        # 确保历史记录页面存在（禁止自动显示）
        if "history" not in self.custom_pages:
            self.add_custom_page(page_name="history", auto_show=False)  # auto_show参数
        if self.query_engine:
            self.query_engine.blocked_ips = self.load_blocked_ips()
        self.load_servers()
        self.start_ui_refresh_timer()
        # 应用窗口样式到主窗口
        self.window_style_utils = window_style_utils
        self.window_style_utils.set_global_style(self.window_style)
        self.window_style_utils.apply_window_style(root)

        self.root.after(100, lambda: self.show_page(self.current_page))

    def check_language_setting(self):
        """检查语言设置，如果没有设置则显示选择对话框"""
        config_exists = os.path.exists(CONFIG_FILE)
        has_language = False
        config_backup_created = False

        if config_exists:
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'language' in config:
                        has_language = True
                    else:
                        # 备份缺少language字段的配置文件
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # 改为时间格式
                        backup_path = f"{CONFIG_FILE}.backup_{timestamp}"
                        import shutil
                        shutil.copy2(CONFIG_FILE, backup_path)
                        config_backup_created = True
                        print(f"已备份配置文件: {backup_path}")
            except:
                pass  # 配置文件损坏，视为没有语言设置

        # 如果没有配置文件或者配置文件中没有language字段，则显示选择对话框
        if not config_exists or not has_language:
            if config_backup_created:
                # 显示备份提示
                from tkinter import messagebox
                messagebox.showinfo("配置文件已备份 / Configuration file has been backed up",
                                    "检测到未加入语言设置的配置文件，已进行备份，如果从高版本回到1.2.3.268及以前的低版本请使用备份的配置文件\nDetected a configuration file without language settings, backup created. If downgrading from a higher version to version 1.2.3.268 or earlier, please use the backup configuration file")
            self.show_language_selection_dialog()

    def show_language_selection_dialog(self):
        """显示语言选择对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("选择语言 / Select Language")
        dialog.geometry("300x150")
        dialog.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # 提示文本
        label = ttk.Label(dialog, text="请选择语言 / Please select language:", font=(APP_FONT, 12))
        label.pack(pady=20)

        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def select_language(lang_code):
            # 保存语言选择到配置
            config = {}
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except:
                    pass

            config['language'] = lang_code

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            dialog.destroy()

            # 根据选择的语言显示对应的提示消息
            if lang_code == "Chinese":
                messagebox.showinfo("提示", "语言设置已保存，需要重启应用生效。")
            else:
                messagebox.showinfo("Info", "Language settings saved. Application restart required to take effect.")

            self.root.after(100, self.on_close)  # 延迟关闭以避免对话框销毁问题

        # 中文按钮
        chinese_btn = create_outline_button(btn_frame, text="中文",
                                 command=lambda: select_language("Chinese"),
                                 width=10)
        chinese_btn.pack(side=tk.LEFT, padx=10)

        # 英文按钮
        english_btn = create_outline_button(btn_frame, text="English",
                                 command=lambda: select_language("English"),
                                 width=10)
        english_btn.pack(side=tk.RIGHT, padx=10)

        # 等待对话框关闭
        self.root.wait_window(dialog)

    def on_tree_click(self, event):
        """处理树状图点击事件：点击空白处取消选中"""
        tree = event.widget
        item = tree.identify_row(event.y)
        if not item:  # 点击在空白区域
            tree.selection_remove(tree.selection())

    def block_server(self, addr, server_name, window=None):  # window参数
        """屏蔽服务器"""
        try:
            # 创建文件如果不存在
            if not os.path.exists(BLOCKED_FILE):
                open(BLOCKED_FILE, 'w').close()

            # 检查是否已存在
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                existing = [line.split()[0] for line in f.readlines() if line.strip()]

            if addr in existing:
                messagebox.showinfo("提示", get_string("server_in_blocklist", "该服务器已在屏蔽列表中"))
                return

            # 追加新条目
            with open(BLOCKED_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{addr} {server_name}\n")

            # 关闭窗口逻辑
            if window is not None:
                window.destroy()  # 关闭传入的窗口

            messagebox.showinfo(get_string("success", "成功"), get_string("block_success", "下次查询时会屏蔽同IP服务器"))

            # 立即更新查询引擎的屏蔽列表
            if self.query_engine:
                self.query_engine.blocked_ips = self.load_blocked_ips()

        except Exception as e:
            messagebox.showerror("错误", get_string("block_failed", f"屏蔽失败: {str(e)}").format(msg=str(e)))

    def show_blocked_list(self):
        """显示屏蔽列表窗口，确保只有一个实例"""
        if self.blocked_list_dialog is None or not self.blocked_list_dialog.winfo_exists():
            self.blocked_list_dialog = BlockedListDialog(self.root, self)
            # 设置窗口关闭时的回调
            self.blocked_list_dialog.protocol("WM_DELETE_WINDOW", self.on_blocked_list_close)
        else:
            # 如果窗口已存在，将其提到前台
            self.blocked_list_dialog.lift()
            self.blocked_list_dialog.focus_force()

    def on_blocked_list_close(self):
        """处理屏蔽列表窗口关闭事件"""
        if self.blocked_list_dialog:
            self.blocked_list_dialog.destroy()
            self.blocked_list_dialog = None

    def load_blocked_ips(self):
        """加载被屏蔽的IP地址和端口规则"""
        blocked = {
            'full_ips': set(),  # 全IP屏蔽
            'single_ports': set(),  # 单端口屏蔽 (格式: "ip:port")
            'custom_rules': []  # 自定义规则 (格式: (ip, rule))
        }

        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # 解析格式: IP:端口,端口规则,模式 服务器名称
                    parts = line.split(' ', 1)
                    ip_part = parts[0]
                    server_name = parts[1] if len(parts) > 1 else ""

                    # 检查是否有模式标识（在最后一个逗号后面）
                    if ',' in ip_part:
                        ip_parts = ip_part.split(',')
                        # 检查最后一个部分是否是模式标识
                        last_part = ip_parts[-1]
                        if last_part in ["all_ports", "single_port", "custom"]:
                            mode = last_part
                            ip_without_mode = ','.join(ip_parts[:-1])

                            if ':' in ip_without_mode:
                                ip, port_rules = ip_without_mode.split(':', 1)

                                if mode == "all_ports":
                                    # 全端口模式：屏蔽整个IP
                                    blocked['full_ips'].add(ip)
                                elif mode == "single_port":
                                    # 仅此端口模式：只屏蔽第一个端口
                                    first_port = port_rules.split(',')[0]
                                    blocked['single_ports'].add(f"{ip}:{first_port}")
                                elif mode == "custom":
                                    # 自定义模式：存储规则而不是展开所有端口
                                    if ',' in port_rules:
                                        first_port, *custom_rules = port_rules.split(',')
                                        # 存储自定义规则
                                        for rule in custom_rules:
                                            rule = rule.strip()
                                            blocked['custom_rules'].append((ip, rule))
                                    else:
                                        # 如果没有自定义规则，使用第一个端口
                                        blocked['single_ports'].add(f"{ip}:{port_rules}")
                            else:
                                # 没有端口的IP，按全端口处理
                                blocked['full_ips'].add(ip_without_mode)
                        else:
                            # 没有模式标识的旧格式，按全端口处理
                            if ':' in ip_part:
                                ip_only = ip_part.split(':')[0]
                                blocked['full_ips'].add(ip_only)
                            else:
                                blocked['full_ips'].add(ip_part)
                    else:
                        # 没有逗号的简单格式，按全端口处理
                        if ':' in ip_part:
                            ip_only = ip_part.split(':')[0]
                            blocked['full_ips'].add(ip_only)
                        else:
                            blocked['full_ips'].add(ip_part)
        return blocked

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        apply_font_to_styled_widgets(style, APP_FONT)

        # 创建主容器：侧边栏 + 中间栏 + 主内容区
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # === 左侧功能区域 ===
        left_sidebar_container = ttk.Frame(main_container)
        left_sidebar_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 左侧边栏内容区域
        left_sidebar = ttk.Frame(left_sidebar_container, padding=(10, 0, 10, 0))
        left_sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧分隔线
        left_separator = ttk.Separator(left_sidebar_container, orient='vertical')
        left_separator.pack(side=tk.RIGHT, fill='y', padx=(5, 0))

        # 加载按钮图片
        try:
            # 加载各个功能对应的图标
            self.settings_icon = self.load_icon_image("settings.png")
            self.blocked_icon = self.load_icon_image("blocked.png")
            self.map_icon = self.load_icon_image("map.png")
            self.steam_icon = self.load_icon_image("steam.png")
            self.history_icon = self.load_icon_image("history.png")
            self.dashboard_icon = self.load_icon_image("dashboard.png")
            self.player_icon = self.load_icon_image("player.png")
        except Exception as e:
            print(f"按钮图片加载失败: {str(e)}")
            # 如果图片加载失败，设置所有图标为None
            self.settings_icon = None
            self.blocked_icon = None
            self.map_icon = None
            self.steam_icon = None
            self.history_icon = None
            self.dashboard_icon = None
            self.player_icon = None

        # 创建顶部功能按钮容器
        top_buttons_frame = ttk.Frame(left_sidebar)
        top_buttons_frame.pack(fill=tk.X, pady=(0, 10))

        # 将主要功能按钮放在顶部
        self.block_list_btn = self.create_image_button(
            top_buttons_frame,
            image=self.blocked_icon,
            tooltip=get_string("block_list", "屏蔽列表"),
            command=self.show_blocked_list
        )
        self.block_list_btn.pack(fill=tk.X, pady=3)

        self.map_list_btn = self.create_image_button(
            top_buttons_frame,
            image=self.map_icon,
            tooltip=get_string("map_list", "三方图列表"),
            command=self.map_utils.show_map_list
        )
        self.map_list_btn.pack(fill=tk.X, pady=3)

        self.workshop_btn = self.create_image_button(
            top_buttons_frame,
            image=self.steam_icon,
            tooltip=get_string("workshop_parser", "工坊链接解析"),
            command=self.workshop_utils.show_workshop_parser
        )
        self.workshop_btn.pack(fill=tk.X, pady=3)

        # 仪表盘按钮放到顶部区域
        self.dashboard_btn = self.create_image_button(
            top_buttons_frame,
            image=self.dashboard_icon,
            tooltip=get_string("dashboard", "仪表盘"),
            command=self.dashboard.show
        )

        # 根据当前设置决定是否显示
        if self.dashboard_enabled:
            self.dashboard_btn.pack(fill=tk.X, pady=3)

        # 玩家信息按钮放到顶部区域
        self.player_info_btn = self.create_image_button(
            top_buttons_frame,
            image=self.player_icon,
            tooltip=get_string("player_info_window_title", "玩家信息"),
            command=self.player_info_window.show
        )

        # 根据当前设置决定是否显示
        if self.player_info_enabled:
            self.player_info_btn.pack(fill=tk.X, pady=3)
        else:
            self.player_info_btn.pack_forget()

        # 创建底部功能按钮容器
        bottom_buttons_frame = ttk.Frame(left_sidebar)
        bottom_buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # 历史记录按钮放到底部区域
        self.history_btn = self.create_image_button(
            bottom_buttons_frame,
            image=self.history_icon,
            tooltip=get_string("history", "历史记录"),
            command=lambda: self.show_page(get_string("history", "历史记录"))
        )
        self.history_btn.pack(fill=tk.X, pady=3)

        # 设置按钮放到底部区域
        self.settings_btn = self.create_image_button(
            bottom_buttons_frame,
            image=self.settings_icon,
            tooltip=get_string("settings", "设置"),
            command=self.show_settings
        )
        self.settings_btn.pack(fill=tk.X, pady=(1, 3))

        # 创建一个填充框架，让顶部和底部按钮分开
        fill_frame = ttk.Frame(left_sidebar)
        fill_frame.pack(fill=tk.BOTH, expand=True)

        # === 中间页面区域 ===
        self.middle_sidebar_container = ttk.Frame(main_container)  # 改为实例变量
        self.middle_sidebar_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 使用固定宽度的容器
        fixed_width = 200
        middle_wrapper = ttk.Frame(self.middle_sidebar_container, width=fixed_width)
        middle_wrapper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        middle_wrapper.pack_propagate(False)

        # Canvas占据整个wrapper
        self.middle_canvas = tk.Canvas(middle_wrapper, highlightthickness=0)
        self.middle_canvas.pack(fill="both", expand=True)

        # 滚动条使用place布局覆盖在右侧
        self.middle_scrollbar = ttk.Scrollbar(
            self.middle_canvas,
            orient="vertical",
            command=self.middle_canvas.yview
        )

        # 将滚动条放置在Canvas的右侧
        self.middle_scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne", x=-1)

        # 内容区域，宽度减去滚动条宽度
        self.middle_sidebar = ttk.Frame(self.middle_canvas, padding=(10, 0, 10, 0))

        self.middle_canvas.create_window((0, 0), window=self.middle_sidebar, anchor="nw", width=fixed_width - 5)
        self.middle_canvas.configure(yscrollcommand=self.middle_scrollbar.set)

        # 默认隐藏滚动条
        self.middle_scrollbar.place_forget()

        # 右侧分隔线
        middle_separator = ttk.Separator(self.middle_sidebar_container, orient='vertical')
        middle_separator.pack(side=tk.RIGHT, fill='y', padx=(5, 0))

        # 页面按钮容器
        page_btn_container = ttk.Frame(self.middle_sidebar)
        page_btn_container.pack(fill=tk.X, pady=(0, 10))

        # 主页面按钮
        self.main_btn = create_outline_button(page_btn_container, text=get_string("internet", "互联网"),
                                              command=lambda: self.show_page("main"))
        self.main_btn.pack(fill=tk.X, pady=2)

        # 自定义页面按钮容器
        self.custom_btn_frame = ttk.Frame(page_btn_container)
        self.custom_btn_frame.pack(fill=tk.X)

        # "+" 添加按钮
        create_outline_button(page_btn_container, text="+", width=3,
                              command=self.add_custom_page).pack(fill=tk.X, pady=2)

        # 绑定鼠标事件
        self._bind_middle_sidebar_events()

        # === 主内容区域 ===
        content_frame = ttk.Frame(main_container)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 页面信息框架
        self.page_info_frame = ttk.Frame(content_frame)
        self.page_info_frame.pack(fill=tk.X, padx=10, pady=(5, 5))
        self.current_page_label = ttk.Label(self.page_info_frame, text=get_string("internet", "互联网"),
                                            font=(APP_FONT, 10, 'bold'))
        self.current_page_label.pack(side=tk.LEFT)

        # 模式切换控件（靠右）
        mode_frame = ttk.Frame(self.page_info_frame)
        mode_frame.pack(side=tk.RIGHT)

        # 修改模式标签字体
        ttk.Label(mode_frame, text=get_string("engine_status", "引擎状态"), font=(APP_FONT, 10)).pack(side=tk.LEFT)

        # 配置Combobox的样式（确保字体生效）
        style = ttk.Style()
        style.configure('TCombobox', font=(APP_FONT, 10))  # 适配不同主题

        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.query_mode,
            values=[get_string("stable", "稳定"), get_string("standard", "标准"), get_string("fast", "快速"),
                    get_string("aggressive", "暴力")],
            state="readonly",
            width=6,
            font=(APP_FONT, 10)
        )
        mode_combo.pack(side=tk.LEFT, padx=5)

        # 在页面信息框架中添加过滤器
        self.filter_utils = FilterUtils(self.page_info_frame, self)
        self.filter_utils.frame.pack(side=tk.RIGHT, padx=10)

        # 根据当前设置决定是否显示过滤控件
        if not self.filter_enabled:
            self.filter_utils.frame.pack_forget()

        # 筛选框容器
        filter_frame = ttk.Frame(content_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        # 筛选输入框
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.filter_entry.bind('<KeyRelease>', self.apply_filter)

        # 清除按钮
        create_outline_button(filter_frame, text="×", width=3,
                              command=self.clear_filter).pack(side=tk.RIGHT)

        self.page_container = ttk.Frame(content_frame)
        self.page_container.pack(fill=tk.BOTH, expand=True)

        self.setup_main_page()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_icon_image(self, filename):
        """加载图标图片并调整大小"""
        try:
            image_path = os.path.join(BASE_DIR, "images", filename)
            if os.path.exists(image_path):
                image = Image.open(image_path)
                image = image.resize((24, 24), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(image)
            else:
                print(f"图标文件不存在: {filename}")
                return None
        except Exception as e:
            print(f"加载图标 {filename} 失败: {str(e)}")
            return None

    def create_image_button(self, parent, image=None, tooltip="", command=None, width=3):
        """创建带图片和悬停提示的按钮"""

        # 创建按钮框架
        btn_frame = ttk.Frame(parent)

        # 创建按钮
        if image:
            btn = ttk.Button(btn_frame, image=image, command=command, width=width, bootstyle="outline")
        else:
            # 如果没有图片，使用文本作为回退
            btn = ttk.Button(btn_frame, text="X_X", command=command, width=width, bootstyle="outline")

        btn.pack(fill=tk.X)

        # 添加悬停提示
        self.create_tooltip(btn, tooltip)

        return btn_frame

    def create_tooltip(self, widget, text):
        """为控件创建悬停提示"""

        def on_enter(event):
            # 创建提示窗口
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = ttk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()

            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip') and widget.tooltip:
                widget.tooltip.destroy()
                widget.tooltip = None

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _bind_middle_sidebar_events(self):
        """绑定中间侧边栏事件 - 修复内存泄漏版本"""

        # 原有的静态事件绑定保持不变
        def on_mousewheel(event):
            """处理鼠标滚轮事件 - 静态绑定，不递归"""
            widget = event.widget
            if widget in [self.middle_canvas, self.middle_sidebar] or self._is_child_of(widget, self.middle_sidebar):
                if self._should_enable_middle_scroll():
                    self.middle_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def on_enter(event):
            """鼠标进入中间侧边栏区域"""
            self._update_middle_sidebar_scrollbar_visibility()

        def on_leave(event):
            """鼠标离开中间侧边栏区域"""
            if self.root and self.root.winfo_exists():
                self.root.after(50, self._update_middle_sidebar_scrollbar_visibility)

        def on_configure(event):
            """容器大小变化时更新"""
            self._update_middle_sidebar_scroll_region()

        # 绑定静态事件（这些不会产生内存泄漏）
        self.middle_canvas.bind("<MouseWheel>", on_mousewheel)
        self.middle_canvas.bind("<Enter>", on_enter)
        self.middle_canvas.bind("<Leave>", on_leave)
        self.middle_canvas.bind("<Configure>", on_configure)

        # 为中间侧边栏及其所有子控件绑定事件
        def bind_to_all_children(parent):
            """递归绑定事件到所有子控件 - 一次性操作"""
            parent.bind("<MouseWheel>", on_mousewheel)
            parent.bind("<Enter>", on_enter)
            parent.bind("<Leave>", on_leave)
            for child in parent.winfo_children():
                bind_to_all_children(child)

        bind_to_all_children(self.middle_sidebar)

        # 启动定期检查（使用类方法避免闭包）
        self._scheduled_sidebar_check()

    def _scheduled_sidebar_check(self):
        """定期检查新控件并更新状态 - 使用类方法避免内存泄漏"""
        try:
            # 检查是否需要重新绑定新控件（如果有新控件添加）
            def check_and_bind_new_children(parent):
                """检查并绑定新添加的子控件"""
                for child in parent.winfo_children():
                    # 检查是否已经绑定了事件
                    bind_tags = child.bindtags()
                    if "mousewheel_binding" not in bind_tags:
                        child.bind("<MouseWheel>", self._on_middle_sidebar_mousewheel)
                        child.bind("<Enter>", self._on_middle_sidebar_enter)
                        child.bind("<Leave>", self._on_middle_sidebar_leave)
                        child.bindtags(bind_tags + ("mousewheel_binding",))

                    # 递归检查子控件
                    check_and_bind_new_children(child)

            check_and_bind_new_children(self.middle_sidebar)

            # 更新滚动区域
            self._update_middle_sidebar_scroll_region()

        except Exception as e:
            print(f"侧边栏检查错误: {str(e)}")
        finally:
            # 使用弱引用方式继续调度
            if self.root and self.root.winfo_exists():
                self.root.after(500, self._scheduled_sidebar_check)

    # 添加辅助方法（这些是类方法，不会产生闭包）
    def _on_middle_sidebar_mousewheel(self, event):
        """中间侧边栏鼠标滚轮事件处理 - 类方法"""
        widget = event.widget
        if widget in [self.middle_canvas, self.middle_sidebar] or self._is_child_of(widget, self.middle_sidebar):
            if self._should_enable_middle_scroll():
                self.middle_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_middle_sidebar_enter(self, event):
        """鼠标进入中间侧边栏区域 - 类方法"""
        self._update_middle_sidebar_scrollbar_visibility()

    def _on_middle_sidebar_leave(self, event):
        """鼠标离开中间侧边栏区域 - 类方法"""
        if self.root and self.root.winfo_exists():
            self.root.after(50, self._update_middle_sidebar_scrollbar_visibility)

    def _is_child_of(self, widget, parent):
        """检查widget是否是parent的子控件"""
        current = widget
        while current:
            if current == parent:
                return True
            current = current.master
        return False

    def _should_enable_middle_scroll(self):
        """判断是否需要启用滚动条"""
        bbox = self.middle_canvas.bbox("all")
        if not bbox:
            return False
        content_height = bbox[3] - bbox[1]
        canvas_height = self.middle_canvas.winfo_height()
        return content_height > canvas_height

    def _update_middle_sidebar_scroll_region(self):
        """更新中间侧边栏滚动区域"""
        self.middle_sidebar.update_idletasks()
        bbox = self.middle_canvas.bbox("all")
        if bbox:
            self.middle_canvas.configure(scrollregion=bbox)
        self._update_middle_sidebar_scrollbar_visibility()

    def _update_middle_sidebar_scrollbar_visibility(self):
        """更新中间侧边栏滚动条可见性"""
        if self._should_enable_middle_scroll():
            # 获取当前鼠标位置
            x, y = self.root.winfo_pointerxy()

            # 使用精确的区域检测
            if self._is_in_middle_sidebar_area(x, y):
                self.middle_scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne", x=-1)
            else:
                self.middle_scrollbar.place_forget()
        else:
            self.middle_scrollbar.place_forget()

    def _is_in_middle_sidebar_area(self, x, y):
        """精确判断坐标是否在中间侧边栏区域内"""
        try:
            middle_x = self.middle_sidebar_container.winfo_rootx()
            middle_y = self.middle_sidebar_container.winfo_rooty()
            middle_width = self.middle_sidebar_container.winfo_width()
            middle_height = self.middle_sidebar_container.winfo_height()

            return (middle_x <= x <= middle_x + middle_width and
                    middle_y <= y <= middle_y + middle_height)
        except:
            return False

    def update_button_display(self):
        # 清空当前按钮
        for widget in self.custom_btn_frame.winfo_children():
            widget.destroy()

        # 显示所有自定义页面按钮（跳过历史记录）
        for name in self.page_order:
            if name == get_string("history", "历史记录"):
                continue
            if name not in self.custom_pages:
                continue

            page_data = self.custom_pages[name]
            if page_data['btn'] is None:  # 跳过历史记录
                continue

            btn = create_outline_button(
                self.custom_btn_frame,
                text=name,
                command=lambda n=name: self.show_page(n)
            )
            btn.pack(fill=tk.X, pady=2)
            btn.bind("<Button-3>", lambda e, name=name: self.rename_page(name, e.widget))
            # 更新按钮引用
            self.custom_pages[name]['btn'] = btn

        # 更新后重新配置滚动区域
        self.middle_sidebar.update_idletasks()
        bbox = self.middle_canvas.bbox("all")
        if bbox:
            content_height = bbox[3] - bbox[1]
            canvas_height = self.middle_canvas.winfo_height()

            if content_height > canvas_height:
                self.middle_canvas.configure(scrollregion=bbox)
                # 只有在鼠标悬停时才显示滚动条
                if not self.middle_canvas.winfo_containing(
                        self.middle_canvas.winfo_pointerx(),
                        self.middle_canvas.winfo_pointery()
                ) in [self.middle_canvas, self.middle_sidebar]:
                    self.middle_scrollbar.pack_forget()
            else:
                self.middle_canvas.configure(scrollregion=(0, 0, 0, 0))
                self.middle_scrollbar.pack_forget()

    def save_config(self):
        # 同步过滤无效页面名称
        valid_page_order = [name for name in self.page_order if name in self.custom_pages]

        # 导入语言设置相关
        from language_strings import CURRENT_LANGUAGE

        # 获取当前查询模式的英文键名（用于保存）
        current_mode = self.query_mode.get()
        mode_mapping = {
            get_string("stable", "稳定"): "stable",
            get_string("standard", "标准"): "standard",
            get_string("fast", "快速"): "fast",
            get_string("aggressive", "暴力"): "aggressive"
        }
        mode_key = mode_mapping.get(current_mode, "standard")

        # 处理页面名称的国际化保存（与query_mode完全一致的方式）
        # 历史记录页面的映射
        history_mapping = {
            "历史记录": "history", "History": "history"
        }

        # 构建保存用的页面数据
        saved_pages = {}
        for name, page_data in self.custom_pages.items():
            # 如果是历史记录页面，保存英文键名
            if name in history_mapping:
                saved_name = history_mapping[name]  # 将显示名称映射回内部键名
            else:
                saved_name = name
            saved_pages[saved_name] = {
                "servers": page_data['servers']
            }

        # 保存页面顺序（历史记录页面使用英文键名）
        saved_page_order = []
        for name in valid_page_order:
            if name in history_mapping:
                saved_page_order.append(history_mapping[name])
            else:
                saved_page_order.append(name)

        config = {
            "version": self.current_version,
            "current_page": history_mapping.get(self.current_page, self.current_page),
            "query_mode": mode_key,  # 保存英文键名
            "custom_pages": saved_pages,
            "sort": self.current_sort,
            "page_order": saved_page_order,  # 保存转换后的页面顺序
            "language": CURRENT_LANGUAGE,
            "theme": self.style.theme.name if hasattr(self, 'style') else 'litera',
            "font": self.font_var.get() if hasattr(self, 'font_var') else "",
            "window_style": self.window_style,
            "dashboard_enabled": self.dashboard_enabled,
            "filter_enabled": self.filter_enabled,
            "filter_state": self.filter_utils.get_filter_state() if self.filter_utils else {},
            "map_display_format": self.map_display_format_enabled,
            "player_info_enabled": self.player_info_enabled,
            "tray_enabled": self.tray_enabled,
            "startup_enabled": self.startup_enabled,
            "workshop_hotkey": self.workshop_hotkey
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    config = json.load(f)

                # 加载查询模式 - 根据保存的英文键名转换为当前语言的显示文本
                if 'query_mode' in config:
                    mode_mapping = {
                        "stable": get_string("stable", "稳定"),
                        "standard": get_string("standard", "标准"),
                        "fast": get_string("fast", "快速"),
                        "aggressive": get_string("aggressive", "暴力")
                    }
                    # 如果配置中的模式不存在，使用默认值
                    saved_mode = config['query_mode']
                    if saved_mode in mode_mapping:
                        self.query_mode.set(mode_mapping[saved_mode])
                    else:
                        self.query_mode.set(get_string("standard", "标准"))

                # 处理页面名称的国际化加载（与query_mode完全一致的方式）
                # 正向映射：从内部键名到可能的显示名称列表
                history_mapping = {
                    "history": ["历史记录", "History"]
                }

                # 反向映射：从显示名称到内部键名
                reverse_history_mapping = {}
                for internal_key, display_names in history_mapping.items():
                    for display_name in display_names:
                        reverse_history_mapping[display_name] = internal_key

                # 加载页面顺序（将英文键名转换为当前语言的显示文本）
                if 'page_order' in config:
                    self.page_order = []
                    for saved_name in config['page_order']:
                        # 如果是历史记录页面，转换为当前语言的显示文本
                        if saved_name in reverse_history_mapping:
                            self.page_order.append(reverse_history_mapping[saved_name])
                        else:
                            self.page_order.append(saved_name)

                # 加载自定义页面
                if 'custom_pages' in config:
                    for saved_name, page_data in config['custom_pages'].items():
                        # 如果是历史记录页面，转换为当前语言的显示文本
                        if saved_name in reverse_history_mapping:
                            display_name = reverse_history_mapping[saved_name]
                        else:
                            display_name = saved_name

                        # 创建页面
                        self.add_custom_page(page_name=display_name, auto_show=False)
                        self.custom_pages[display_name]['servers'] = page_data['servers']

                        # 更新状态标签
                        count = len(page_data['servers'])
                        self.custom_pages[display_name]['status_label'].config(
                            text=get_string("servers_loaded", f"已装载{count}服务器").format(count=count))
                        self.update_query_button_state(display_name)

                # 清理无效的页面记录
                self.page_order = [name for name in self.page_order
                                   if name in self.custom_pages]

                # 加载语言设置
                if 'language' in config:
                    from language_strings import set_language
                    set_language(config['language'])

                # 加载字体设置
                if 'font' in config:
                    self.font_var.set(config['font'])
                else:
                    self.font_var.set("微软雅黑")

                # 加载窗口设置
                if 'window_style' in config:
                    self.window_style = config['window_style']
                else:
                    self.window_style = "light"

                # 加载仪表盘设置
                if 'dashboard_enabled' in config:
                    self.dashboard_enabled = config['dashboard_enabled']
                else:
                    self.dashboard_enabled = False

                # 立即更新仪表盘按钮显示
                if hasattr(self, 'dashboard_btn'):
                    if self.dashboard_enabled:
                        self.dashboard_btn.pack(fill=tk.X, pady=3)  # 改为垂直排列
                    else:
                        self.dashboard_btn.pack_forget()

                # 加载玩家信息设置
                if 'player_info_enabled' in config:
                    self.player_info_enabled = config['player_info_enabled']
                else:
                    self.player_info_enabled = False

                # 立即更新玩家信息按钮显示
                if hasattr(self, 'player_info_btn'):
                    if self.player_info_enabled:
                        self.player_info_btn.pack(fill=tk.X, pady=3)  # 改为垂直排列
                    else:
                        self.player_info_btn.pack_forget()

                # 加载系统托盘设置
                if 'tray_enabled' in config:
                    self.tray_enabled = config['tray_enabled']
                else:
                    self.tray_enabled = False

                # 如果启用了托盘，设置托盘图标
                if self.tray_enabled:
                    self.setup_tray_icon()

                # 加载开机启动设置
                if 'startup_enabled' in config:
                    self.startup_enabled = config['startup_enabled']
                else:
                    self.startup_enabled = False

                # 加载过滤状态
                if self.filter_utils and 'filter_state' in config:
                    self.filter_utils.set_filter_state(config['filter_state'])

                # 加载过滤控件设置
                if 'filter_enabled' in config:
                    self.filter_enabled = config['filter_enabled']
                else:
                    self.filter_enabled = False

                # 立即更新过滤控件显示
                if hasattr(self, 'filter_utils'):
                    if self.filter_enabled:
                        self.filter_utils.frame.pack(side=tk.RIGHT, padx=10)
                    else:
                        self.filter_utils.frame.pack_forget()

                # 加载快捷键设置
                if 'workshop_hotkey' in config:
                    self.workshop_hotkey = config['workshop_hotkey']
                    # 立即设置快捷键
                    self.hotkey_manager.setup_hotkey(self.workshop_hotkey)
                else:
                    self.workshop_hotkey = ""  # 默认快捷键

                # 加载地图显示格式设置
                if 'map_display_format' in config:
                    self.map_display_format_enabled = config['map_display_format']
                else:
                    # 默认禁用
                    self.map_display_format_enabled = False

                # 显示当前页面（将保存的页面名称转换为当前语言的显示文本）
                current_page = config.get('current_page', 'main')
                if current_page in reverse_history_mapping:
                    self.current_page = reverse_history_mapping[current_page]
                else:
                    self.current_page = current_page

                self.root.after(100, lambda: self.show_page(self.current_page))
            except Exception as e:
                messagebox.showerror("配置错误", f"加载配置失败: {str(e)}")
        else:
            # 配置文件不存在时的默认设置
            self.font_var = tk.StringVar(value="微软雅黑")
            self.dashboard_enabled = False  # 默认禁用仪表盘
            self.filter_enabled = False  # 默认禁用过滤控件
            self.map_display_format_enabled = False  # 默认禁用地图显示格式
            self.workshop_hotkey = ""
            self.startup_enabled = False

    def load_theme_from_config(self):
        """从配置文件加载主题设置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                if 'theme' in config:
                    theme = config['theme']
                    # 设置主题
                    self.style = ttk.Style(theme=theme)
                    return

            # 默认主题
            self.style = ttk.Style(theme='litera')

        except Exception as e:
            print(f"加载主题失败: {str(e)}")
            self.style = ttk.Style(theme='litera')

    def setup_main_page(self):
        self.main_frame = ttk.Frame(self.page_container)
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(tree_frame,
                                 columns=('ip', 'vac', 'name', 'game', 'map', 'players', 'latency', 'keywords'),
                                 show='headings')
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.heading('ip', text=get_string("column_ip", 'IP地址'), command=lambda: self.sort_column('ip'))
        self.tree.heading('vac', text=get_string("column_vac", 'VAC'), command=lambda: self.sort_column('vac'))
        self.tree.heading('name', text=get_string("column_name", '服务器名称'),
                          command=lambda: self.sort_column('name'))
        self.tree.heading('game', text=get_string("column_game", '游戏'), command=lambda: self.sort_column('game'))
        self.tree.heading('map', text=get_string("column_map", '当前地图'), command=lambda: self.sort_column('map'))
        self.tree.heading('players', text=get_string("column_players", '玩家数量'),
                          command=lambda: self.sort_column('players'))
        self.tree.heading('latency', text=get_string("column_latency", '工具延迟'),
                          command=lambda: self.sort_column('latency'))
        self.tree.heading('keywords', text=get_string("column_keywords", '标签'),
                          command=lambda: self.sort_column('keywords'))
        self.tree.column('ip', width=140, anchor=tk.W, stretch=tk.NO)
        self.tree.column('vac', width=50, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.column('name', width=200, anchor=tk.W)
        self.tree.column('game', width=100, anchor=tk.W)
        self.tree.column('map', width=110, anchor=tk.W)
        self.tree.column('players', width=80, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.column('latency', width=80, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.column('keywords', width=60, anchor=tk.W)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.fetch_btn = create_outline_button(btn_frame, text=get_string("get_server_list", "获取服务器列表"),
                                               command=self.show_region_dialog)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)

        self.query_btn = create_outline_button(btn_frame, text=get_string("query_server_status", "查询服务器状态"),
                                               command=self.start_query)
        self.query_btn.pack(side=tk.LEFT, padx=5)

        # 移除已转移到侧边栏的按钮，只保留获取服务器列表和查询服务器状态按钮
        # 原来的屏蔽列表、三方图列表、工坊链接解析按钮已移到侧边栏

        self.status_label = ttk.Label(btn_frame, text=get_string("ready", "就绪"))
        self.status_label.pack(side=tk.RIGHT)

        self.tree.bind('<Button-3>', self.show_main_context_menu)
        self.tree.bind('<Double-Button-1>', self.on_double_click)

        self.main_frame.pack(fill=tk.BOTH, expand=True)

    # UI刷新方法-----------------------------------------
    def start_ui_refresh_timer(self):
        """启动UI刷新定时器 - 修复内存泄漏版本"""
        # 直接启动类方法，避免闭包
        self._scheduled_ui_refresh()

    def _scheduled_ui_refresh(self):
        """定时UI刷新 - 使用类方法避免闭包内存泄漏"""
        try:
            # 页面存在性检查
            if self.current_page != "main" and self.current_page not in self.custom_pages:
                self.show_page("main")
                raise ValueError(f"页面 {self.current_page} 不存在，已切换回主页面")

            if self.current_page == "main":
                self._batch_update_main_tree()
            else:
                self._batch_update_custom_tree(self.current_page)
        except Exception as e:
            print(f"刷新错误: {str(e)}")
        finally:
            # 使用弱引用避免循环引用，同时保持定时器运行
            if self.root and self.root.winfo_exists():
                self.root.after(1000, self._scheduled_ui_refresh)

    # 刷新当前页面显示的方法
    def refresh_current_page_display(self):
        """刷新当前页面的显示（应用新的地图显示格式）"""
        if self.current_page == "main":
            # 重新查询主页面
            if self.query_engine and not self.query_engine.running:
                self.start_query()
        else:
            # 重新查询自定义页面
            page_data = self.custom_pages[self.current_page]
            if page_data['query_engine'] and not page_data['query_engine'].running:
                self.start_custom_query(self.current_page)

    # 修改地图显示格式的工具方法
    def format_map_name(self, map_code):
        """根据设置和语言模式格式化地图名称"""
        if not self.map_display_format_enabled or not hasattr(self, 'map_utils'):
            return map_code

        # 导入语言设置相关
        from language_strings import CURRENT_LANGUAGE

        # 查找地图代码对应的名称
        if self.map_utils.map_data:
            for item in self.map_utils.map_data:
                codes = item.get('换图代码 (按章节顺序)', '')
                if codes:
                    code_list = [c.strip() for c in codes.replace('，', ',').split(',')]
                    if map_code in code_list:
                        # 根据当前语言选择显示字段
                        if CURRENT_LANGUAGE == "English":
                            display_name = item.get('地图大厅展示名', '').strip()
                        else:
                            display_name = item.get('中文名 (仅参考)', '').strip()

                        if display_name:
                            return f"{display_name} [{map_code}]"

        return map_code

    def _batch_update_main_tree(self):
        """批量更新主界面树状表格的核心方法"""
        with self.tree_lock:
            # 即使没有缓冲数据也检查进度（处理去重后的完成状态）
            if not self.update_buffer:
                if self.query_engine:
                    completed, total = self.query_engine.get_progress()
                    if completed >= total and total > 0:
                        self.query_btn.config(text=get_string("query_server_status", "查询服务器状态"))
                        online_count = len(self.tree.tag_has('online'))
                        self.status_label.config(
                            text=get_string("online_count", f"查询完成，在线 {online_count} 个").format(online_count=online_count)
                        )
                        if self.query_engine.running:
                            self.query_engine.stop()
                        # 服务器查询完成后更新仪表盘
                        if hasattr(self, 'dashboard'):
                            self.dashboard.update_data()
                        # 在查询完成后处理玩家信息
                        if hasattr(self, 'player_info_window') and self.player_info_enabled:
                            self.player_info_window.process_pending_data(self.current_page)
                return

            # 处理缓冲区的更新数据
            online_count = len(self.tree.tag_has('online'))
            for item in self.update_buffer:
                status, data = item
                if status == 'start_query':
                    self.all_items['main'].add(data['addr'])
                    # 检查是否存在再插入
                    if self.tree.exists(data['addr']):
                        self.tree.delete(data['addr'])  # 先删除已存在的条目
                    self.tree.insert('', 'end', iid=data['addr'],
                                     values=(data['addr'], get_string("querying", "查询中..."), "", "", "", "", ""),
                                     tags=('pending',))
                    self.queried_count += 1
                    online_count = len(self.tree.tag_has('online'))
                    self.status_label.config(
                        text=get_string("online_count_1", f"开始查询 {self.queried_count}/{self.total_servers} | 在线 {online_count}").format(queried_count=self.queried_count, total_servers=self.total_servers, online_count=online_count)
                    )
                else:
                    # 更新查询结果
                    if status == 'success':
                        # 格式化地图名称
                        formatted_map = self.format_map_name(data['map'])
                        values = (
                            data['addr'],
                            data.get('vac', get_string("unknown", '未知')),
                            data['name'],
                            data.get('game', get_string("unknown", '未知')),
                            formatted_map,  # 使用格式化后的地图名称
                            f"{data['players']}/{data['max_players']}",
                            f"{data.get('latency', 0)}ms",
                            data.get('keywords', get_string("none", '无'))
                        )
                        tags = ('online',)
                        online_count += 1
                    else:
                        values = (
                            data['addr'],
                            "",
                            get_string("connection_failed", "连接失败"),
                            "",
                            data['msg'],
                            "",
                            get_string("timeout", "超时")
                        )
                        tags = ('offline',)

                    # 确保更新或插入操作
                    if self.tree.exists(data['addr']):
                        self.tree.delete(data['addr'])  # 先删除已存在的条目
                    self.tree.insert('', 'end', iid=data['addr'], values=values, tags=tags)

            # 检查完成状态（使用查询引擎的实际计数）
            if self.query_engine:
                completed, total = self.query_engine.get_progress()
                if completed >= total and total > 0:
                    self.query_btn.config(text=get_string("query_server_status", "查询服务器状态"))
                    online_count = len(self.tree.tag_has('online'))
                    self.status_label.config(
                        text=get_string("online_count", f"查询完成，在线 {online_count} 个").format(online_count=online_count)
                    )
                    if self.query_engine.running:
                        self.query_engine.stop()
                    # 服务器查询完成后更新仪表盘
                    if hasattr(self, 'dashboard'):
                        self.dashboard.update_data()
                    # 在查询完成后处理玩家信息
                    if hasattr(self, 'player_info_window') and self.player_info_enabled:
                        self.player_info_window.process_pending_data(self.current_page)

            # if self.current_sort['column']:
            # self.sort_treeview_column(self.tree, self.current_sort, self.current_sort['column'],
            # toggle_reverse=False)

            self.update_buffer.clear()

        if self.filter_utils:
            self.filter_utils.apply_filters()

    # 在ServerCheckerApp类中添加以下方法
    def add_custom_fetch_button(self, control_frame, page_name):
        """为自定义页面添加获取服务器按钮"""
        fetch_btn = create_outline_button(
            control_frame,
            text=get_string("add_server", "添加服务器"),
            command=lambda p=page_name: self.show_custom_fetch_dialog(p)
        )
        fetch_btn.pack(side=tk.LEFT, padx=5)

    def show_custom_fetch_dialog(self, page_name):
        """显示自定义页面获取服务器对话框"""
        try:
            from tkinterdnd2 import DND_FILES  # 确保导入DND_FILES
        except ImportError:
            messagebox.showerror("错误", "拖拽功能需要tkinterdnd2库支持")
            return

        # 使用标准Toplevel窗口
        dialog = tk.Toplevel(self.root)
        try:
            dialog.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))  # 图标
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        dialog.title(get_string("add_server", "添加服务器"))
        dialog.geometry("500x500")
        # 应用窗口样式
        self.window_style_utils.apply_window_style(dialog)

        # 增加区域标题
        ttk.Label(dialog, text=get_string("file_drop_zone", "文件拖拽区"), font=(APP_FONT, 10, 'bold'), anchor=tk.W).pack(
            fill=tk.X, padx=15, pady=(5, 2))

        # 拖拽区域配置保持不变
        drop_frame = ttk.Frame(dialog)
        drop_frame.pack(pady=10, fill=tk.BOTH, padx=20)

        text_drop = tk.Text(
            drop_frame,
            height=3,
            state='disabled',
            bg='#f0f0f0',
            relief="groove",
            wrap=tk.WORD
        )
        text_drop.pack(fill=tk.BOTH, expand=True)

        # 通过标签实现居中
        text_drop.tag_configure("center", justify='center')

        text_drop.configure(state='normal')
        text_drop.insert('1.0', get_string("drop_file_here", "\n拖拽服务器列表文件至此或手动输入内容"))  # 前后换行
        text_drop.tag_add("center", "1.0", "end")  # 应用居中标签
        text_drop.configure(state='disabled')

        # 绑定拖拽事件到文本框
        def handle_drop(event):
            file_path = event.data.strip('{}')  # 处理Windows路径
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                text.delete('1.0', tk.END)
                text.insert(tk.END, content)
                text_drop.configure(state='normal')
                text_drop.delete('1.0', tk.END)
                text_drop.insert('1.0', get_string("file_loaded", f"已加载文件: {os.path.basename(file_path)}").format(filename=os.path.basename(file_path)))
                text_drop.configure(state='disabled')
            except Exception as e:
                messagebox.showerror("错误", get_string("cannot_read_file", f"无法读取文件: {str(e)}").format(msg=str(e)))

        # 注册拖放目标
        text_drop.drop_target_register(DND_FILES)
        text_drop.dnd_bind('<<Drop>>', handle_drop)

        # 添加手动输入区标题
        ttk.Label(dialog, text=get_string("manual_input_zone", "手动输入区"), font=(APP_FONT, 10, 'bold'), anchor=tk.W).pack(
            fill=tk.X, padx=15, pady=(5, 2))

        # 其余代码保持不变...
        text = tk.Text(dialog, height=4)
        text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # 添加解析结果区标题
        ttk.Label(dialog, text=get_string("parse_result", "解析结果"), font=(APP_FONT, 10, 'bold'), anchor=tk.W).pack(
            fill=tk.X, padx=15, pady=(5, 2))

        result_frame = ttk.Frame(dialog)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        result_list = tk.Listbox(
            result_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            height=5
        )
        result_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=result_list.yview)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def parse_content():
            content = text.get("1.0", tk.END)
            servers = self.extract_servers(content)
            result_list.delete(0, tk.END)
            for s in servers:
                result_list.insert(tk.END, s)

        create_outline_button(
            btn_frame,
            text=get_string("parse_content", "解析内容"),
            command=parse_content
        ).pack(side=tk.LEFT, padx=5)

        def confirm_add():
            selected = result_list.get(0, tk.END)
            if selected:
                # 动态获取当前页面名称，解决闭包问题
                current_page = self.current_page
                self.add_to_page(current_page, selected)
                dialog.destroy()

        create_outline_button(
            btn_frame,
            text=get_string("confirm_add", "确认添加"),
            command=confirm_add  # 直接绑定到修改后的函数
        ).pack(side=tk.RIGHT, padx=5)

    def extract_servers(self, content):
        """从文本中提取有效的服务器地址，直接保留原始地址"""
        import re
        # 匹配地址:端口，保留原始地址
        pattern = r'\b([^\s:]+):(\d{1,5})\b'
        matches = re.findall(pattern, content)

        valid_servers = []
        for addr_part, port_part in matches:
            # 验证端口有效性
            try:
                port = int(port_part)
                if port < 1 or port > 65535:
                    continue
            except ValueError:
                continue

            # 直接保留原始地址（可以是域名或IP）
            valid_servers.append(f"{addr_part}:{port}")

        # 去重并保持顺序
        seen = set()
        unique_servers = []
        for s in valid_servers:
            if s not in seen:
                seen.add(s)
                unique_servers.append(s)
        return unique_servers

    def start_custom_query(self, page_name):
        page_data = self.custom_pages[page_name]

        # 如果正在运行则停止
        if page_data['query_engine'] and page_data['query_engine'].running:
            page_data['query_engine'].stop()
            page_data['query_btn'].config(text=get_string("query_server_status", "查询服务器状态"))
            return

        # 获取当前全局模式（第一个方法的优势）
        current_mode = self.query_mode.get()

        # UI重置
        page_data['query_btn'].config(text=get_string("stop_server_query", "停止服务器查询"))
        page_data['tree'].delete(*page_data['tree'].get_children())

        # 清空当前页面的玩家信息
        if self.player_info_enabled and hasattr(self, 'player_info_window'):
            self.player_info_window.clear_player_data(page_name)  # 只清空当前页面

        # 初始化计数器
        page_data['completed_count'] = 0  # 来自第二个方法
        page_data['queried_count'] = 0

        # 创建查询引擎（保留第一个方法的模式传递方式）
        page_data['query_engine'] = AsyncServerQuery(
            lambda r: self.update_custom_table(page_name, r),
            current_mode,  # 显式传递模式参数
            self
        )

        # 添加任务并获取实际数量（第一个方法的正确逻辑）
        actual_count = page_data['query_engine'].add_task(page_data['servers'])
        page_data['total_servers'] = actual_count  # 使用实际任务数

        # 更新状态（保持第一个方法的进度提示）
        page_data['status_label'].config(
            text=f"正在查询（0/{page_data['total_servers']}）"
        )

        # 当实际任务数为0时的处理
        if actual_count == 0:
            page_data['query_btn'].config(get_string("query_server_status", text="查询服务器状态"))
            page_data['status_label'].config(text=get_string("no_servers_to_query", "没有可查询的服务器（可能已被屏蔽）"))
            # 确保查询引擎处于停止状态
            if page_data['query_engine']:
                page_data['query_engine'].running = False
            return  # 直接返回不启动查询

        page_data['status_label'].config(
            text=f"正在查询（0/{page_data['total_servers']}）"
        )

        # 为自定义页面初始化缓冲区系统（如果不存在）
        if 'tree_lock' not in page_data:
            page_data['tree_lock'] = threading.Lock()
            page_data['update_buffer'] = []

        # 确保计数器重置
        if 'completed_count' not in page_data:
            page_data['completed_count'] = 0
        else:
            page_data['completed_count'] = 0

    def _batch_update_custom_tree(self, page_name):
        # 前置校验
        if page_name not in self.custom_pages:
            print(f"警告：尝试更新不存在的页面 {page_name}")
            return

        page_data = self.custom_pages[page_name]

        # 存在性检查 + 运行状态检查
        if page_data.get('query_engine') and page_data['query_engine'].running:
            # 仅当引擎运行时才同步模式
            if self.query_mode.get() != page_data['query_engine'].mode:
                page_data['query_engine'].mode = self.query_mode.get()
                page_data['query_engine']._update_intervals()

        if 'tree_lock' not in page_data:
            return
        with page_data['tree_lock']:
            if not page_data['update_buffer']:
                # 检查查询是否完成
                if page_data.get('query_engine'):
                    completed, total = page_data['query_engine'].get_progress()
                    if completed >= total and total > 0:
                        page_data['query_btn'].config(text=get_string("query_server_status", "查询服务器状态"))
                        online_count = len(page_data['tree'].tag_has('online'))
                        page_data['status_label'].config(text=get_string("online_count", f"查询完成，在线 {online_count} 个").format(online_count=online_count))
                        page_data['query_engine'].stop()
                        # 服务器查询完成后更新仪表盘
                        if hasattr(self, 'dashboard'):
                            self.dashboard.update_data()
                        # 在查询完成后处理玩家信息
                        if hasattr(self, 'player_info_window') and self.player_info_enabled:
                            self.player_info_window.process_pending_data(self.current_page)
                return

            online_count = len(page_data['tree'].tag_has('online'))
            for item in page_data['update_buffer']:
                status, data = item
                if status == 'start_query':
                    if 'all_items' not in page_data:
                        page_data['all_items'] = set()
                    page_data['all_items'].add(data['addr'])
                    # 插入查询中的条目
                    if page_data['tree'].exists(data['addr']):
                        page_data['tree'].delete(data['addr'])  # 先删除已存在的条目
                    page_data['tree'].insert('', 'end',
                                             iid=data['addr'],
                                             values=(data['addr'], get_string("querying", "查询中..."), "", "", "", "", ""),
                                             tags=('pending',))
                    page_data['queried_count'] += 1
                    page_data['status_label'].config(
                        text=get_string("online_count_1", f"开始查询 {page_data['queried_count']}/{page_data['total_servers']} | 在线 {online_count}").format(queried_count=page_data['queried_count'], total_servers=page_data['total_servers'], online_count=online_count)
                    )
                else:
                    # 处理查询结果
                    if status == 'success':
                        # 格式化地图名称
                        formatted_map = self.format_map_name(data['map'])
                        values = (
                            data['addr'],
                            data.get('vac', get_string("unknown", '未知')),
                            data['name'],
                            data.get('game', get_string("unknown", '未知')),
                            formatted_map,  # 使用格式化后的地图名称
                            f"{data['players']}/{data['max_players']}",
                            f"{data.get('latency', 0)}ms",
                            data.get('keywords', get_string("none", '无'))
                        )
                        tags = ('online',)
                        online_count += 1
                    else:
                        values = (
                            data['addr'],
                            "",
                            get_string("connection_failed", "连接失败"),
                            "",
                            data['msg'],
                            "",
                            get_string("timeout", "超时"),
                        )
                        tags = ('offline',)

                    # 更新或插入树节点
                    if page_data['tree'].exists(data['addr']):
                        page_data['tree'].delete(data['addr'])  # 先删除已存在的条目
                    page_data['tree'].insert('', 'end',
                                             iid=data['addr'],
                                             values=values,
                                             tags=tags)
                    page_data['completed_count'] += 1

            # 更新状态标签和按钮
            if page_data['completed_count'] >= page_data['total_servers']:
                page_data['query_btn'].config(text=get_string("query_server_status", "查询服务器状态"))
                if page_data['query_engine']:
                    page_data['query_engine'].stop()
                # 服务器查询完成后更新仪表盘
                if hasattr(self, 'dashboard'):
                    self.dashboard.update_data()
                # 在查询完成后处理玩家信息
                if hasattr(self, 'player_info_window') and self.player_info_enabled:
                    self.player_info_window.process_pending_data(self.current_page)
                online_count = len(page_data['tree'].tag_has('online'))
                page_data['status_label'].config(text=get_string("online_count", f"查询完成，在线 {online_count} 个").format(online_count=online_count))

            # if page_data['sort']['column']:
            # self.sort_treeview_column(page_data['tree'], page_data['sort'],
            # page_data['sort']['column'], toggle_reverse=False)

            page_data['update_buffer'].clear()

        if self.filter_utils:
            self.filter_utils.apply_filters()

    def update_table(self, result):
        with self.tree_lock:
            self.update_buffer.append(result)

    def update_custom_table(self, page_name, result):
        page_data = self.custom_pages[page_name]
        if 'tree_lock' not in page_data:
            page_data['tree_lock'] = threading.Lock()
            page_data['update_buffer'] = []
        with page_data['tree_lock']:
            page_data['update_buffer'].append(result)

    # ------------------------------------------------------

    def show_region_dialog(self):
        region_map = {
            get_string("global_region", '全球'): 0xFF,
            get_string("us_east", '美国东部'): 0x00,
            get_string("us_west", '美国西部'): 0x01,
            get_string("south_america", '南美'): 0x02,
            get_string("europe", '欧洲'): 0x03,
            get_string("asia", '亚洲'): 0x04,
            get_string("australia", '澳洲'): 0x05,
            get_string("middle_east", '中东'): 0x06,
            get_string("africa", '非洲'): 0x07
        }

        region_win = tk.Toplevel(self.root)
        try:
            region_win.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        region_win.title(get_string("region", "区域"))
        region_win.geometry("400x590")
        region_win.resizable(False, False)
        # 应用窗口样式
        self.window_style_utils.apply_window_style(region_win)

        # 主容器
        main_container = ttk.Frame(region_win, padding=20)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 区域查询功能 LabelFrame
        region_frame = ttk.LabelFrame(main_container, text=get_string("region_query", "区域查询"), padding=15)
        region_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            region_frame,
            text=get_string("from_steam", "从Steam主服务器获取指定区域的服务器列表"),
            font=(APP_FONT, 9)
        ).pack(anchor=tk.W, pady=(0, 10))

        # 区域选择框架
        region_select_frame = ttk.Frame(region_frame)
        region_select_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            region_select_frame,
            text=get_string("select_region", "选择区域:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        combo = ttk.Combobox(region_select_frame, values=list(region_map.keys()), state="readonly")
        combo.current(0)
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_region_confirm():
            selected = combo.get()
            region_win.destroy()
            if selected in region_map:
                self.fetch_servers(region_map[selected])

        region_btn = create_outline_button(
            region_frame,
            text=get_string("get_region_servers", "获取区域服务器"),
            command=on_region_confirm,
            width=15
        )
        region_btn.pack(pady=(10, 0))

        # 云端获取功能 LabelFrame
        cloud_frame = ttk.LabelFrame(main_container, text=get_string("cloud_fetch", "云端获取"), padding=15)
        cloud_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            cloud_frame,
            text=get_string("from_cloud", "从云端服务器列表文件快速获取服务器地址"),
            font=(APP_FONT, 9)
        ).pack(anchor=tk.W, pady=(0, 10))

        # 云端选择框架（使用下拉框，只有一个"云端"选项）
        cloud_select_frame = ttk.Frame(cloud_frame)
        cloud_select_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            cloud_select_frame,
            text=get_string("select_source", "选择来源:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        cloud_combo = ttk.Combobox(cloud_select_frame, values=[get_string("cloud_weekly", "云端 - 按小时更新")],
                                   state="readonly")
        cloud_combo.current(0)
        cloud_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def on_cloud_fetch():
            # 使用固定的云端URL
            cloud_url = "https://serverlist.zhrradiantcos.top/get"
            region_win.destroy()
            self.fetch_cloud_servers(cloud_url)

        cloud_btn = create_outline_button(
            cloud_frame,
            text=get_string("get_from_cloud", "从云端获取"),
            command=on_cloud_fetch,
            width=15
        )
        cloud_btn.pack(pady=(10, 0))

        # Steam Web API 获取功能 LabelFrame
        api_frame = ttk.LabelFrame(main_container, text=get_string("steam_api_fetch", "Steam API 获取"), padding=15)
        api_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            api_frame,
            text=get_string("from_steam_api", "通过 Steam Web API 获取服务器列表（需要 API 密钥）"),
            font=(APP_FONT, 9)
        ).pack(anchor=tk.W, pady=(0, 10))

        # API 密钥输入框架
        api_key_frame = ttk.Frame(api_frame)
        api_key_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            api_key_frame,
            text=get_string("api_key", "API 密钥:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(api_key_frame, textvariable=api_key_var, show="*")
        api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        remember_key_var = tk.BooleanVar()
        remember_check = ttk.Checkbutton(
            api_key_frame,
            text=get_string("remember_key", "记住密钥"),
            variable=remember_key_var
        )
        remember_check.pack(side=tk.RIGHT, padx=(10, 0))

        # 尝试加载已保存的密钥
        def load_saved_key():
            key_file = "steam_web_api_key.txt"
            if os.path.exists(key_file):
                try:
                    with open(key_file, 'r', encoding='utf-8') as f:
                        saved_key = f.read().strip()
                        if saved_key:
                            api_key_var.set(saved_key)
                            remember_key_var.set(True)
                except Exception as e:
                    print(f"加载保存的API密钥失败: {e}")

        # 在对话框显示后加载密钥
        region_win.after(100, load_saved_key)

        def on_api_fetch():
            api_key = api_key_var.get().strip()
            if not api_key:
                messagebox.showerror(get_string("error", "错误"),
                                     get_string("api_key_required", "请输入 Steam Web API 密钥"))
                return

            # 处理密钥保存逻辑
            key_file = "steam_web_api_key.txt"
            if remember_key_var.get():
                # 保存密钥到文件
                try:
                    with open(key_file, 'w', encoding='utf-8') as f:
                        f.write(api_key)
                except Exception as e:
                    print(f"保存API密钥失败: {e}")
            else:
                # 删除密钥文件
                try:
                    if os.path.exists(key_file):
                        os.remove(key_file)
                except Exception as e:
                    print(f"删除API密钥文件失败: {e}")

            region_win.destroy()
            self.fetch_steam_api_servers(api_key)

        api_btn = create_outline_button(
            api_frame,
            text=get_string("get_from_api", "通过 API 获取"),
            command=on_api_fetch,
            width=15
        )
        api_btn.pack(pady=(10, 0))

        # 居中显示
        region_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - region_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - region_win.winfo_height()) // 2
        region_win.geometry(f"+{x}+{y}")

    def fetch_cloud_servers(self, url):
        """从云端URL获取服务器列表"""

        def fetch_task(cloud_url):
            try:
                self.root.after(0, self.toggle_buttons, False)
                self.root.after(0, self.status_label.config, {"text": get_string("getting_cloud_servers", "正在从云端获取服务器列表...")})

                # 显示进度条
                if not hasattr(self, 'progress') or not self.progress:
                    self.progress = ttk.Progressbar(self.root, mode='indeterminate')
                    self.progress.pack(fill=tk.X, padx=10, pady=5)
                self.root.after(0, self.progress.start)

                # 发送HTTP请求获取服务器列表
                response = requests.get(cloud_url, timeout=30)
                response.raise_for_status()

                # 解析服务器列表
                servers = []
                for line in response.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):  # 忽略空行和注释
                        servers.append(line)

                # 保存到本地文件
                with open(IP_FILE, "w", encoding='utf-8') as f:
                    f.write("\n".join(servers))

                # 重新加载服务器列表
                self.root.after(0, self.load_servers)
                self.root.after(0, lambda: messagebox.showinfo("完成", f"从云端获取到{len(servers)}个服务器"))

            except requests.exceptions.RequestException as e:
                error_msg = get_string("network_error", f"网络错误: {str(e)}").format(msg=str(e))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
            except Exception as e:
                error_msg = get_string("fetch_failed", f"获取失败: {str(e)}").format(msg=str(e))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
            finally:
                self.root.after(0, self.toggle_buttons, True)
                if hasattr(self, 'progress'):
                    self.root.after(0, self.progress.stop)
                    self.root.after(0, self.progress.pack_forget)
                self.root.after(0, self.status_label.config, {"text": get_string("ready", "就绪")})

        # 启动后台线程
        threading.Thread(target=lambda: fetch_task(url), daemon=True).start()

    def fetch_steam_api_servers(self, api_key):
        """通过 Steam Web API 获取服务器列表"""

        def fetch_task(steam_api_key):
            try:
                self.root.after(0, self.toggle_buttons, False)
                self.root.after(0, self.status_label.config,
                                {"text": get_string("getting_api_servers", "正在通过 Steam API 获取服务器列表...")})

                # 显示进度条
                if not hasattr(self, 'progress') or not self.progress:
                    self.progress = ttk.Progressbar(self.root, mode='indeterminate')
                    self.progress.pack(fill=tk.X, padx=10, pady=5)
                self.root.after(0, self.progress.start)

                import urllib.request
                import urllib.parse
                import ssl
                import json

                # 创建不验证 SSL 的上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # 构建 API 请求 URL - 严格按照 steamweb3.py 的逻辑
                url = f"https://api.steampowered.com/IGameServersService/GetServerList/v1/?key={steam_api_key}&format=json&filter=\\appid\\550&limit=10000"

                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response:
                    data = response.read().decode('utf-8')
                    json_data = json.loads(data)

                    # 提取IP地址和端口
                    servers = json_data['response']['servers']
                    server_addresses = []
                    for server in servers:
                        addr = server.get('addr', '')  # 格式为 "IP:端口"
                        if addr:
                            server_addresses.append(addr)

                    # 保存到本地文件
                    with open(IP_FILE, "w", encoding='utf-8') as f:
                        f.write("\n".join(server_addresses))

                    # 重新加载服务器列表
                    self.root.after(0, self.load_servers)
                    self.root.after(0, lambda: messagebox.showinfo(
                        get_string("complete", "完成"),
                        get_string("api_servers_fetched", "通过 Steam API 获取到 {count} 个服务器").format(
                            count=len(server_addresses))
                    ))

            except urllib.error.HTTPError as e:
                if e.code == 403:
                    error_msg = get_string("api_key_invalid", "API 密钥无效或无权访问")
                elif e.code == 401:
                    error_msg = get_string("api_key_unauthorized", "API 密钥未经授权")
                else:
                    error_msg = get_string("api_http_error", f"HTTP 错误: {e.code}")
                self.root.after(0, lambda msg=error_msg: messagebox.showerror(get_string("error", "错误"), msg))
            except urllib.error.URLError as e:
                error_msg = get_string("network_error", f"网络错误: {str(e)}").format(msg=str(e))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror(get_string("error", "错误"), msg))
            except json.JSONDecodeError as e:
                error_msg = get_string("api_response_invalid", "API 响应格式无效")
                self.root.after(0, lambda msg=error_msg: messagebox.showerror(get_string("error", "错误"), msg))
            except Exception as e:
                error_msg = get_string("api_fetch_failed", f"获取失败: {str(e)}").format(msg=str(e))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror(get_string("error", "错误"), msg))
            finally:
                self.root.after(0, self.toggle_buttons, True)
                if hasattr(self, 'progress'):
                    self.root.after(0, self.progress.stop)
                    self.root.after(0, self.progress.pack_forget)
                self.root.after(0, self.status_label.config, {"text": get_string("ready", "就绪")})

        # 启动后台线程
        threading.Thread(target=lambda: fetch_task(api_key), daemon=True).start()

    def add_custom_page(self, page_name=None, auto_show=True):  # auto_show参数
        """新增或加载自定义页面，允许指定页面名称"""
        if not page_name:
            page_num = len(self.custom_pages)
            page_name = get_string("custom_page", f"自定义{page_num}").format(page_num=page_num)

        if page_name in self.custom_pages:
            return

        if page_name not in self.page_order:
            self.page_order.append(page_name)

        # +++ 初始化btn变量 +++
        btn = None  # 确保变量存在

        # 历史记录页面跳过按钮创建
        if page_name != "history":
            btn = create_outline_button(self.custom_btn_frame, text=page_name,
                             command=lambda p=page_name: self.show_page(p))
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Button-3>", lambda e, name=page_name: self.rename_page(name, e.widget))
        # +++ 修改结束 +++

        # 创建页面框架及组件（保持原有逻辑）
        frame = ttk.Frame(self.page_container)

        tree_container = ttk.Frame(frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tree = ttk.Treeview(tree_container, columns=('ip', 'vac', 'name', 'game', 'map', 'players', 'latency', 'keywords'), show='headings', selectmode='extended')
        tree.bind('<Button-1>', self.on_tree_click)
        # 为每个列标题绑定排序命令
        tree.heading('ip', text=get_string("column_ip", 'IP地址'), command=lambda p=page_name: self.sort_custom_column(p, 'ip'))
        tree.heading('vac', text=get_string("column_vac", 'VAC'), command=lambda p=page_name: self.sort_custom_column(p, 'vac'))
        tree.heading('name', text=get_string("column_name", '服务器名称'), command=lambda p=page_name: self.sort_custom_column(p, 'name'))
        tree.heading('game', text=get_string("column_game", '游戏'), command=lambda p=page_name: self.sort_custom_column(p, 'game'))
        tree.heading('map', text=get_string("column_map", '当前地图'), command=lambda p=page_name: self.sort_custom_column(p, 'map'))
        tree.heading('players', text=get_string("column_players", '玩家数量'), command=lambda p=page_name: self.sort_custom_column(p, 'players'))
        tree.heading('latency', text=get_string("column_latency", '工具延迟'), command=lambda p=page_name: self.sort_custom_column(p, 'latency'))
        tree.heading('keywords', text=get_string("column_keywords", '标签'), command=lambda p=page_name: self.sort_custom_column(p, 'keywords'))
        tree.column('ip', width=140, stretch=tk.NO)
        tree.column('vac', width=50, anchor=tk.CENTER, stretch=tk.NO)
        tree.column('name', width=200)
        tree.column('game', width=100, anchor=tk.W)
        tree.column('map', width=110)
        tree.column('players', width=80, anchor=tk.CENTER, stretch=tk.NO)
        tree.column('latency', width=80, anchor=tk.CENTER, stretch=tk.NO)
        tree.column('keywords', width=60, anchor=tk.W)
        tree.bind('<Button-3>', lambda e, p=page_name: self.show_custom_context_menu(e, p))

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        left_btn_frame = ttk.Frame(control_frame)
        left_btn_frame.pack(side=tk.LEFT)

        self.add_custom_fetch_button(left_btn_frame, page_name)

        query_btn = create_outline_button(left_btn_frame, text=get_string("query_server_status", "查询服务器状态"),
                               command=lambda p=page_name: self.start_custom_query(p))
        query_btn.pack(side=tk.LEFT, padx=5)

        del_btn = create_outline_button(left_btn_frame, text=get_string("delete_server", "删除服务器"),
                             command=lambda p=page_name: self.delete_selected_servers(p))
        del_btn.pack(side=tk.LEFT, padx=5)

        # 初始化 config_btn 为 None
        config_btn = None

        if page_name != get_string("history", "历史记录"):
            # 先创建按钮实例
            config_btn = create_outline_button(left_btn_frame, text=get_string("page_config", "页面配置"))

            # 配置按钮命令，通过默认参数传递当前按钮实例
            config_btn.config(
                command=lambda p=page_name, btn=config_btn: self.rename_page(p, btn)
            )

            # 将按钮添加到界面
            config_btn.pack(side=tk.LEFT, padx=5)

        status_frame = ttk.Frame(control_frame)
        status_frame.pack(side=tk.RIGHT)
        status_label = ttk.Label(status_frame, text=get_string("servers_loaded_zero", "已装载0服务器"))
        status_label.pack(side=tk.RIGHT)

        # 为自定义页面添加缓冲区系统
        self.custom_pages[page_name] = {
            'frame': frame,
            'tree': tree,
            'btn': btn,
            'query_btn': query_btn,
            'del_btn': del_btn,
            'config_btn': config_btn,
            'servers': [],
            'query_engine': None,
            'status_label': status_label,
            'total_servers': 0,
            'queried_count': 0,
            'completed_count': 0,
            'tree_lock': threading.Lock(),
            'update_buffer': [],
            # 排序状态
            'sort': {'column': None, 'reverse': False}
        }

        # 更新按钮显示
        self.update_button_display()
        if auto_show:  # 判断
            self.show_page(page_name)
        self.update_query_button_state(page_name)

        tree.bind('<Double-Button-1>', self.on_double_click)

    def setup_tray_icon(self):
        """设置系统托盘图标"""
        if not self.tray_enabled:
            return

        try:
            import pystray
            from PIL import Image, ImageDraw
            import threading

            # 创建托盘图标
            def create_image():
                try:
                    # 尝试加载工具图标
                    icon_path = os.path.join(BASE_DIR, "icon.ico")
                    if os.path.exists(icon_path):
                        image = Image.open(icon_path)
                        image = image.resize((64, 64), Image.Resampling.LANCZOS)
                        return image
                    else:
                        image = Image.new('RGB', (64, 64), color='white')
                        dc = ImageDraw.Draw(image)
                        dc.rectangle([16, 16, 48, 48], fill='blue')
                        return image
                except Exception as e:
                    print(f"加载托盘图标失败: {e}")
                    image = Image.new('RGB', (64, 64), color='white')
                    dc = ImageDraw.Draw(image)
                    dc.rectangle([16, 16, 48, 48], fill='blue')
                    return image

            def on_quit(icon, item):
                # 停止托盘图标
                icon.stop()
                # 在主线程中执行强制退出
                self.root.after(0, lambda: self.on_close(force_quit=True))

            def on_show(icon, item):
                # 显示主窗口
                self.root.after(0, self.show_main_window)

            def on_double_click(icon, item):
                """处理双击托盘图标事件"""
                self.root.after(0, self.show_main_window)

            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem(
                    "显示主窗口",
                    on_show,
                    default=True  # 这个菜单项将成为左键单击的默认动作
                ),
                pystray.MenuItem("退出", on_quit)
            )

            # 创建托盘图标
            image = create_image()
            self.tray_icon = pystray.Icon("L4D2 Server OptiBrowser", image, "L4D2 Server OptiBrowser", menu)

            # 设置双击事件处理
            self.tray_icon.on_left_click = on_double_click

            # 在后台线程中运行托盘图标
            def run_tray():
                self.tray_icon.run()

            tray_thread = threading.Thread(target=run_tray, daemon=True)
            tray_thread.start()

            # 如果开机启动已启用，更新快捷方式参数
            if self.startup_enabled:
                try:
                    from startup_manager import get_startup_manager
                    startup_manager = get_startup_manager()
                    if startup_manager.shortcut_exists():
                        startup_manager.update_shortcut(True)  # 托盘启用时总是最小化启动
                except Exception as e:
                    print(f"更新开机启动快捷方式失败: {e}")

        except ImportError:
            print("pystray库未安装，无法启用系统托盘功能")
            messagebox.showwarning("功能不可用", "系统托盘功能需要pystray库支持，请安装：pip install pystray")
            self.tray_enabled = False
        except Exception as e:
            print(f"设置系统托盘失败: {e}")
            self.tray_enabled = False

    def show_main_window(self):
        """显示主窗口（用于托盘菜单调用）"""
        # 确保窗口显示在最前面
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        # 确保窗口状态正常
        self.root.state('normal')  # 确保不是最小化状态

    def on_close(self, force_quit=False):
        """修改关闭事件处理，支持关闭时最小化到托盘
        force_quit: 是否强制退出（忽略托盘设置）
        """
        # 如果启用了托盘功能且不是强制退出，关闭时最小化到托盘而不是直接退出
        if self.tray_enabled and hasattr(self, 'tray_icon') and self.tray_icon and not force_quit:
            self.root.withdraw()  # 隐藏窗口
            return  # 不继续执行关闭逻辑

        # 停止快捷键管理器
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop()

        # 原有的关闭逻辑
        self.save_config()
        if self.query_engine:
            self.query_engine.stop()

        # 停止托盘图标（如果存在）
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()

        # 如果需要重启，启动新实例（想实现重启会有很多问题，现保持重启无效，不完善重启逻辑）
        if self.need_restart:
            try:
                import sys
                import subprocess
                subprocess.Popen([sys.executable] + sys.argv)
            except Exception as e:
                print(f"重启应用失败: {e}")

        self.root.destroy()

    def on_page_changed(self, event=None):
        """处理页面切换事件"""
        if hasattr(self, 'player_info_window'):
            self.player_info_window.on_page_changed(self.current_page)

    def show_page(self, page_name):
        # 处理历史记录页面的特殊映射
        if page_name == get_string("history", "历史记录"):
            internal_page_name = "history"
        else:
            internal_page_name = page_name

        self.current_page = internal_page_name  # 使用内部页面名称
        self.main_frame.pack_forget()
        for p in self.custom_pages.values():
            p['frame'].pack_forget()

        if internal_page_name == "main":
            self.main_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.custom_pages[internal_page_name]['frame'].pack(fill=tk.BOTH, expand=True)

        # 显示名称保持不变（使用传入的page_name）
        if internal_page_name == "main":
            display_name = get_string("internet", "互联网")
        elif internal_page_name == "history":
            display_name = get_string("history", "历史记录")  # 使用本地化的历史记录名称
        else:
            display_name = page_name

        self.current_page_label.config(text=f"{display_name}")

        # 触发页面切换事件
        self.on_page_changed()

    def rename_page(self, page_name, window):
        if page_name == get_string("history", "历史记录"):
            messagebox.showerror("错误", get_string("cannot_rename_history", "无法重命名历史记录页面"), parent=window)
            return

        if page_name not in self.custom_pages:
            return

        rename_win = tk.Toplevel(self.root)
        try:
            rename_win.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))  # 图标
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        rename_win.title(get_string("page_config", "页面配置"))
        rename_win.grab_set()  # 设置为模式对话框
        # 应用窗口样式
        self.window_style_utils.apply_window_style(rename_win)

        # 输入框和删除按钮行
        input_frame = ttk.Frame(rename_win)
        input_frame.pack(padx=10, pady=(10, 5), fill=tk.X)

        # 在输入框下方添加顺序调整控件容器
        order_container = ttk.Frame(rename_win)
        order_container.pack(fill=tk.X, padx=10, pady=5)

        # 初始化顺序控件
        self.add_order_controls(order_container, page_name)

        entry = ttk.Entry(input_frame)
        entry.insert(0, page_name)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        del_btn = create_outline_button(
            input_frame,
            text=get_string("delete_page", "删除页面"),
            width=8,
            command=lambda: self.confirm_delete(page_name, rename_win)
        )
        del_btn.pack(side=tk.RIGHT)

        # 按钮行
        btn_frame = ttk.Frame(rename_win)
        btn_frame.pack(pady=(0, 10), padx=10)

        create_outline_button(
            btn_frame,
            text=get_string("confirm_1", "确认"),
            command=lambda: self.process_rename(page_name, entry.get(), rename_win)
        ).pack(side=tk.LEFT, padx=5)

        create_outline_button(
            btn_frame,
            text=get_string("cancel", "取消"),
            command=rename_win.destroy
        ).pack(side=tk.RIGHT, padx=5)

        # 绑定回车键
        entry.bind("<Return>", lambda e: self.process_rename(page_name, entry.get(), rename_win))

    def add_order_controls(self, parent, page_name):
        """在指定父容器中添加顺序控件"""
        # 清除旧控件
        for widget in parent.winfo_children():
            widget.destroy()

        current_index = self.page_order.index(page_name)
        max_index = len(self.page_order) - 1

        order_frame = ttk.Frame(parent)
        order_frame.pack(fill=tk.X)

        # 上移按钮 (靠左)
        up_btn = create_outline_button(
            order_frame,
            text=get_string("move_up", "↑上移"),
            command=lambda: self.move_page(page_name, -1, parent),
            state='normal' if current_index > 1 else 'disabled'
        )
        up_btn.pack(side=tk.LEFT, padx=2)

        # 当前位置显示 (居中)
        position_label = ttk.Label(
            order_frame,
            text=get_string("current_order", f"当前顺序：{current_index + 1}/{len(self.page_order)}").format(current=current_index + 1, total=len(self.page_order))
        )
        position_label.pack(side=tk.LEFT, expand=True, padx=5)  # 使用expand和fill让标签居中

        # 下移按钮 (靠右)
        down_btn = create_outline_button(
            order_frame,
            text=get_string("move_down", "↓下移"),
            command=lambda: self.move_page(page_name, 1, parent),
            state='normal' if current_index < max_index else 'disabled'
        )
        down_btn.pack(side=tk.RIGHT, padx=2)

    def move_page(self, page_name, direction, order_container):
        """调整页面顺序"""
        current_index = self.page_order.index(page_name)
        new_index = current_index + direction

        if 0 <= new_index < len(self.page_order):
            # 交换页面顺序
            self.page_order[current_index], self.page_order[new_index] = \
                self.page_order[new_index], self.page_order[current_index]

            # 更新顺序控件
            self.add_order_controls(order_container, page_name)
            self.update_button_display()
            self.save_config()

    def confirm_delete(self, page_name, window):
        if page_name == get_string("history", "历史记录"):
            messagebox.showerror("错误", get_string("cannot_delete_history", "无法删除历史记录页面"), parent=window)
            return

        if messagebox.askyesno(
                get_string("confirm_delete", "确认删除"),
                get_string("delete_page_confirm", f"确定要永久删除页面 '{page_name}' 吗？\n该操作不可恢复！").format(page_name=page_name),
                parent=window
        ):
            # 切换页面如果当前显示
            if self.current_page == page_name:
                self.show_page("main")
            # 删除页面数据
            del self.custom_pages[page_name]
            # 更新页面顺序记录
            if page_name in self.page_order:
                self.page_order.remove(page_name)
            # 更新界面
            self.update_button_display()
            self.save_config()
            window.destroy()

    def process_rename(self, old_name, new_name, window):
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("错误", get_string("page_name_empty", "页面名称不能为空"), parent=window)
            return

        if new_name == old_name:
            window.destroy()
            return

        if new_name in self.custom_pages:
            messagebox.showerror("错误", get_string("page_name_exists", "该页面名称已存在"), parent=window)
            return

        # 更新页面顺序记录
        if old_name in self.page_order:
            index = self.page_order.index(old_name)
            self.page_order[index] = new_name

        # 更新当前页面显示
        if self.current_page == old_name:
            self.current_page = new_name

        # 执行重命名
        page_data = self.custom_pages[old_name]

        # 更新按钮引用前先销毁旧实例
        page_data['btn'].destroy()

        # 创建新按钮并更新引用
        new_btn = create_outline_button(self.custom_btn_frame, text=new_name,
                             command=lambda: self.show_page(new_name))
        new_btn.pack(side=tk.LEFT, padx=2)
        new_btn.bind("<Button-3>", lambda e: self.rename_page(new_name))

        # 更新字典键和按钮引用
        self.custom_pages[new_name] = page_data
        self.custom_pages[new_name]['btn'] = new_btn
        del self.custom_pages[old_name]
        # 更新查询按钮的命令绑定
        self.custom_pages[new_name]['query_btn'].config(
            command=lambda: self.start_custom_query(new_name)
        )

        # 重新绑定Treeview列排序命令
        new_tree = self.custom_pages[new_name]['tree']
        for col in new_tree['columns']:
            new_tree.heading(col,
                             command=lambda c=col, p=new_name: self.sort_custom_column(p, c))

        # 更新删除按钮的命令绑定
        if 'del_btn' in self.custom_pages[new_name]:
            self.custom_pages[new_name]['del_btn'].config(
                command=lambda p=new_name: self.delete_selected_servers(p)
            )

        # 更新配置按钮的命令绑定
        if 'config_btn' in self.custom_pages[new_name]:
            self.custom_pages[new_name]['config_btn'].config(
                command=lambda p=new_name, btn=new_btn: self.rename_page(p, btn)
            )

        # 更新界面
        self.update_button_display()
        self.save_config()
        window.destroy()

    def show_custom_context_menu(self, event, page_name):
        """显示自定义页面的右键菜单（支持多选）"""
        page_data = self.custom_pages[page_name]
        tree = page_data['tree']
        selected_items = tree.selection()  # 获取所有选中的项目

        if not selected_items:
            return

        menu = tk.Menu(self.root, tearoff=0)

        # 添加移除选项（顶部）
        menu.add_command(
            label=get_string("remove_selected_items", f"移除选中的 {len(selected_items)} 个条目").format(
                count=len(selected_items)),
            command=lambda: self.remove_selected_from_page(page_name, selected_items)
        )

        # 屏蔽选项
        menu.add_command(
            label=get_string("block_selected_servers", "屏蔽选中的 {count} 个服务器").format(count=len(selected_items)),
            command=lambda: self.block_selected_servers_from_custom(page_name, selected_items)
        )

        # 添加分割线
        menu.add_separator()

        # 原有的添加到其他自定义页面选项
        for target_page in self.custom_pages:
            if target_page != page_name:  # 排除当前页面
                menu.add_command(
                    label=get_string("add_to_page", f"添加到 {target_page}").format(page=target_page),
                    command=lambda p=target_page, items=selected_items: self.add_selected_to_page(p, page_name, items)
                )

        menu.post(event.x_root, event.y_root)

    def block_selected_servers_from_custom(self, page_name, selected_items):
        """从自定义页面屏蔽选中的多个服务器（相同IP只添加第一个）"""
        if not selected_items:
            return

        page_data = self.custom_pages[page_name]
        tree = page_data['tree']

        # 获取选中的服务器地址和名称
        servers_to_block = []
        seen_ips = set()  # 用于跟踪已处理的IP

        for item in selected_items:
            values = tree.item(item, 'values')
            if len(values) >= 3:
                addr = values[0]  # IP地址
                server_name = values[2]  # 服务器名称

                # 提取IP部分（去掉端口）
                ip_part = addr.split(':')[0]

                # 如果这个IP还没有被处理过，添加到屏蔽列表
                if ip_part not in seen_ips:
                    servers_to_block.append((addr, server_name))
                    seen_ips.add(ip_part)

        if not servers_to_block:
            return

        # 批量屏蔽服务器
        success_count = 0
        for addr, server_name in servers_to_block:
            try:
                # 调用静默屏蔽逻辑
                if self.block_server_silent(addr, server_name):
                    success_count += 1
            except Exception as e:
                print(f"屏蔽服务器 {addr} 失败: {str(e)}")

        # 显示结果提示
        if success_count > 0:
            messagebox.showinfo(
                get_string("success", "成功"),
                get_string("block_selected_success",
                           "成功屏蔽 {success_count} 个服务器\n下次查询时会屏蔽同IP服务器").format(
                    success_count=success_count)
            )

            # 立即更新查询引擎的屏蔽列表
            if self.query_engine:
                self.query_engine.blocked_ips = self.load_blocked_ips()

            # 如果当前正在查询，重新查询以应用屏蔽
            if page_data.get('query_engine') and page_data['query_engine'].running:
                self.start_custom_query(page_name)

    def add_selected_to_page(self, target_page, source_page, selected_items):
        """将选中的服务器添加到目标页面"""
        page_data = self.custom_pages[source_page]
        tree = page_data['tree']

        # 获取选中的服务器地址
        servers_to_add = []
        for item in selected_items:
            values = tree.item(item, 'values')
            if len(values) > 0:
                addr = values[0]  # IP地址
                servers_to_add.append(addr)

        if servers_to_add:
            self.add_to_page(target_page, servers_to_add)

    def remove_selected_from_page(self, page_name, selected_items):
        """从自定义页面移除选中的多个服务器"""
        page_data = self.custom_pages[page_name]
        tree = page_data['tree']

        # 获取要删除的服务器地址列表
        servers_to_remove = []
        for item in selected_items:
            addr = tree.item(item, 'values')[0]
            servers_to_remove.append(addr)

        # 从服务器列表中移除
        page_data['servers'] = [s for s in page_data['servers'] if s not in servers_to_remove]

        # 更新Treeview
        for item in selected_items:
            tree.delete(item)

        # 更新状态标签和按钮状态
        count = len(page_data['servers'])
        page_data['status_label'].config(text=get_string("servers_loaded", f"已装载{count}服务器").format(count=count))
        self.update_query_button_state(page_name)
        self.save_config()  # 保存配置变更

    def show_main_context_menu(self, event):
        """显示主页面的右键菜单（支持多选）"""
        selected_items = self.tree.selection()  # 获取所有选中的项目
        if not selected_items:
            return

        menu = tk.Menu(self.root, tearoff=0)

        # 添加移除选项（顶部）
        menu.add_command(
            label=get_string("remove_selected_items", f"移除选中的 {len(selected_items)} 个条目").format(
                count=len(selected_items)),
            command=lambda: self.remove_selected_from_main(selected_items)
        )

        # 屏蔽选项
        menu.add_command(
            label=get_string("block_selected_servers", "屏蔽选中的 {count} 个服务器").format(count=len(selected_items)),
            command=lambda: self.block_selected_servers(selected_items)
        )

        # 添加分割线
        menu.add_separator()

        # 原有的添加到自定义页面选项
        for page in self.custom_pages:
            menu.add_command(
                label=get_string("add_to_page", f"添加到 {page}").format(page=page),
                command=lambda p=page, items=selected_items: self.add_to_page(p, items)
            )

        menu.post(event.x_root, event.y_root)

    def block_server_silent(self, addr, server_name):
        """静默屏蔽服务器（不显示弹窗）"""
        try:
            # 创建文件如果不存在
            if not os.path.exists(BLOCKED_FILE):
                open(BLOCKED_FILE, 'w').close()

            # 检查是否已存在
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                existing = [line.split()[0] for line in f.readlines() if line.strip()]

            if addr in existing:
                return False  # 已存在，不重复添加

            # 追加新条目
            with open(BLOCKED_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{addr} {server_name}\n")

            return True

        except Exception as e:
            print(f"静默屏蔽失败: {str(e)}")
            return False

    def block_selected_servers(self, selected_items):
        """屏蔽选中的多个服务器（相同IP只添加第一个）"""
        if not selected_items:
            return

        # 获取选中的服务器地址和名称
        servers_to_block = []
        seen_ips = set()  # 用于跟踪已处理的IP

        for item in selected_items:
            values = self.tree.item(item, 'values')
            if len(values) >= 3:
                addr = values[0]  # IP地址
                server_name = values[2]  # 服务器名称

                # 提取IP部分（去掉端口）
                ip_part = addr.split(':')[0]

                # 如果这个IP还没有被处理过，添加到屏蔽列表
                if ip_part not in seen_ips:
                    servers_to_block.append((addr, server_name))
                    seen_ips.add(ip_part)

        if not servers_to_block:
            return

        # 批量屏蔽服务器
        success_count = 0
        for addr, server_name in servers_to_block:
            try:
                # 调用静默屏蔽逻辑
                if self.block_server_silent(addr, server_name):
                    success_count += 1
            except Exception as e:
                print(f"屏蔽服务器 {addr} 失败: {str(e)}")

        # 显示结果提示
        if success_count > 0:
            messagebox.showinfo(
                get_string("success", "成功"),
                get_string("block_selected_success",
                           "成功屏蔽 {success_count} 个服务器\n下次查询时会屏蔽同IP服务器").format(
                    success_count=success_count)
            )

            # 立即更新查询引擎的屏蔽列表
            if self.query_engine:
                self.query_engine.blocked_ips = self.load_blocked_ips()

    def remove_selected_from_main(self, selected_items):
        """从主页面移除选中的多个服务器"""
        servers_to_remove = []
        for item in selected_items:
            if item in self.servers:
                servers_to_remove.append(item)

        if not servers_to_remove:
            return

        # 从服务器列表中移除
        self.servers = [s for s in self.servers if s not in servers_to_remove]

        # 更新文件
        with open(IP_FILE, "w") as f:
            f.write("\n".join(self.servers))

        # 更新UI
        for item in selected_items:
            self.tree.delete(item)

        self.status_label.config(text=get_string("servers_loaded", f"已装载{len(self.servers)}服务器").format(count=len(self.servers)))

        # 更新查询按钮状态
        if len(self.servers) > 0:
            self.query_btn.state(['!disabled'])
        else:
            self.query_btn.state(['disabled'])

    def update_query_button_state(self, page_name):
        page_data = self.custom_pages[page_name]
        if len(page_data['servers']) > 0:
            page_data['query_btn'].state(['!disabled'])
        else:
            page_data['query_btn'].state(['disabled'])

    def add_to_page(self, page_name, servers):
        """批量添加服务器到指定页面"""
        page_data = self.custom_pages[page_name]
        existing = set(page_data['servers'])

        # 去重处理
        new_servers = [s for s in servers if s not in existing]
        if not new_servers:
            return

        # 添加服务器并更新界面
        page_data['servers'].extend(new_servers)
        count = len(page_data['servers'])
        page_data['status_label'].config(text=get_string("servers_loaded", f"已装载{count}服务器").format(count=count))

        # 自动刷新目标页面
        # if self.current_page == page_name:
            # self.refresh_custom_page(page_name)  # 原自动刷新/查询的触发点

        self.update_query_button_state(page_name)
        self.save_config()

    def refresh_custom_page(self, page_name):
        page_data = self.custom_pages[page_name]
        page_data['tree'].delete(*page_data['tree'].get_children())
        if page_data['query_engine']:
            page_data['query_engine'].stop()

        # 使用全局模式设置
        page_data['query_engine'] = AsyncServerQuery(
            lambda r: self.update_custom_table(page_name, r),
            self.query_mode.get()  # 模式参数
        )
        page_data['query_engine'].add_task(page_data['servers'])

    def apply_filter(self, event=None):
        # 先应用关键词过滤
        keyword = self.filter_var.get().lower()

        if self.current_page == "main":
            tree = self.tree
            all_items = self.all_items['main']
        else:
            page_data = self.custom_pages[self.current_page]
            tree = page_data['tree']
            all_items = page_data.get('all_items', set())

        # 重新显示所有条目
        for item in all_items:
            if tree.exists(item):
                tree.reattach(item, '', 'end')

        # 应用关键词过滤
        if keyword:
            for item in tree.get_children():
                values = [str(v).lower() for v in tree.item(item, 'values')]
                if not any(keyword in v for v in values):
                    tree.detach(item)

        # 应用状态过滤
        if self.filter_utils:
            self.filter_utils.apply_filters()

    def clear_filter(self):
        """只清除关键词过滤，保留状态过滤"""
        self.filter_var.set('')

        # 不再调用 filter_utils.clear_filters()
        # 只重新应用当前的状态过滤
        if self.filter_utils:
            self.filter_utils.apply_filters()
        else:
            # 回退到原来的清除逻辑（只针对关键词）
            if self.current_page == "main":
                for item in self.all_items['main']:
                    if self.tree.exists(item):
                        self.tree.reattach(item, '', 'end')
            else:
                page_data = self.custom_pages[self.current_page]
                if 'all_items' in page_data:
                    for item in page_data['all_items']:
                        if page_data['tree'].exists(item):
                            page_data['tree'].reattach(item, '', 'end')

    def sort_column(self, column):
        """处理主页面列排序"""
        self.sort_treeview_column(self.tree, self.current_sort, column)

    def sort_custom_column(self, page_name, column):
        """处理自定义页面的列排序"""
        page_data = self.custom_pages[page_name]
        self.sort_treeview_column(page_data['tree'], page_data['sort'], column)

    def sort_treeview_column(self, tree, sort_info, column, toggle_reverse=True):
        """通用列排序逻辑，toggle_reverse参数控制是否切换排序方向"""
        if toggle_reverse:
            reverse = (sort_info.get('column') == column) and not sort_info.get('reverse', False)
        else:
            reverse = sort_info.get('reverse', False)

        items = [(tree.set(child, column), child) for child in tree.get_children('')]

        try:
            if column == 'players':
                def player_sort_key(item):
                    value = item[0]
                    if '/' in value:
                        current, max_players = value.split('/')
                        return int(current) if current.isdigit() else -1
                    return -1

                items.sort(key=player_sort_key, reverse=reverse)
            elif column == 'latency':
                items.sort(key=lambda x: int(x[0][:-2]) if x[0].endswith('ms') else float('inf'), reverse=reverse)
            elif column == 'ip':
                def ip_key(item):
                    try:
                        ip, port = item[0].split(':')
                        return tuple(map(int, ip.split('.') + [port]))
                    except:
                        return (0, 0, 0, 0, 0)

                items.sort(key=ip_key, reverse=reverse)
            elif column == 'name':  # 服务器名称列的自然排序
                import re
                def natural_sort_key(item):
                    """
                    自然排序键函数，将文本中的数字转换为整数进行比较
                    例如：'服务器2' -> ['服务器', 2], '服务器12' -> ['服务器', 12]
                    """
                    text = item[0]
                    return [int(part) if part.isdigit() else part.lower()
                            for part in re.split(r'(\d+)', text)]

                items.sort(key=natural_sort_key, reverse=reverse)
            elif column == 'keywords':
                items.sort(key=lambda x: x[0].lower(), reverse=reverse)
            else:
                items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        except:
            items.sort(reverse=reverse)

        for index, (_, child) in enumerate(items):
            tree.move(child, '', index)

        sort_info['column'] = column
        sort_info['reverse'] = reverse

    def load_servers(self):
        if os.path.exists(IP_FILE):
            with open(IP_FILE, "r") as f:
                self.servers = f.read().splitlines()
            self.query_btn.state(['!disabled'])
            self.status_label.config(text=get_string("servers_loaded", f"已装载{len(self.servers)}服务器").format(count=len(self.servers)))
        else:
            self.servers = []
            self.query_btn.state(['disabled'])
            self.status_label.config(text=get_string("servers_loaded_zero", "已装载0服务器"))

    def fetch_servers(self, region):
        def fetch_task(region_code):
            try:
                self.root.after(0, self.toggle_buttons, False)
                self.root.after(0, self.status_label.config, {"text": get_string("getting_servers", "正在获取服务器列表...")})
                self.root.after(0, self.progress.start)

                self.servers = []
                if os.path.exists(IP_FILE):
                    os.remove(IP_FILE)

                servers = fetch_ips(region_code)
                with open(IP_FILE, "w") as f:
                    f.write("\n".join(servers))

                # 重新加载服务器列表
                self.root.after(0, self.load_servers)
                self.root.after(0, lambda: messagebox.showinfo("完成", get_string("servers_fetched", f"获取到{len(servers)}个服务器").format(count=len(servers))))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
            finally:
                self.root.after(0, self.toggle_buttons, True)
                self.root.after(0, self.progress.stop)
                self.root.after(0, self.progress.pack_forget)
                self.root.after(0, self.status_label.config, {"text": get_string("ready", "就绪")})

        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)

        threading.Thread(target=lambda: fetch_task(region), daemon=True).start()

    def start_query(self):
        if self.query_engine and self.query_engine.running:
            self.query_engine.stop()
            self.query_btn.config(text=get_string("query_server_status", "查询服务器状态"))
            # 停止服务器刷新按钮时更新仪表盘
            if hasattr(self, 'dashboard'):
                self.dashboard.update_data()
            return

        # 检查是否有可查询的服务器（考虑屏蔽列表）
        if self.query_engine:
            self.query_engine.blocked_ips = self.load_blocked_ips()

        self.query_btn.config(text=get_string("stop_server_query", "停止服务器查询"))
        self.tree.delete(*self.tree.get_children())
        self.all_items['main'].clear()  # 清空条目跟踪集合

        # 清空当前页面的玩家信息（只清空主页面）
        if self.player_info_enabled and hasattr(self, 'player_info_window'):
            self.player_info_window.clear_player_data("main")  # 只清空主页面

        # 重置计数器
        self.queried_count = 0
        self.completed_count = 0

        self.query_engine = AsyncServerQuery(self.update_table, self.query_mode.get(), self)
        actual_count = self.query_engine.add_task(self.servers)
        self.total_servers = actual_count

        # 当实际任务数为0时的处理（无可查询服务器）
        if actual_count == 0:
            self.query_btn.config(text=get_string("query_server_status", "查询服务器状态"))
            self.status_label.config(text=get_string("no_servers_to_query", "没有可查询的服务器（可能已被屏蔽）"))
            # 确保查询引擎处于停止状态
            if self.query_engine:
                self.query_engine.running = False
            return  # 直接返回不启动查询

        self.status_label.config(text=f"正在查询（0/{self.total_servers}）")

    def join_server(self, addr):
        import webbrowser
        try:
            # 域名解析逻辑
            if not addr.count(":") == 1:
                raise ValueError("Invalid address format")

            host, port = addr.split(":")

            # 域名解析
            try:
                # 优先尝试作为IP处理
                socket.inet_aton(host)
                ip_addr = host  # 已经是合法IP
            except socket.error:
                # 如果失败则尝试DNS解析
                ip_addr = socket.gethostbyname(host)

            resolved_addr = f"{ip_addr}:{port}"
            # 使用解析后的地址 (修改此行)
            webbrowser.open(f"steam://connect/{resolved_addr}")

            # 保持原记录地址
            self.add_to_page("history", [addr])
            if self.current_page == "history":
                self.start_custom_query("history")
        except socket.gaierror as e:
            messagebox.showerror(get_string("dns_error", "DNS错误"), f"无法解析服务器域名: {host}\n错误信息: {str(e)}")
        except Exception as e:
            messagebox.showerror(get_string("connect_error", "连接错误"), f"无法启动Steam连接: {str(e)}")

    def on_double_click(self, event):
        widget = event.widget
        item = widget.identify_row(event.y)
        if item:
            try:
                addr = item
                if ':' not in addr:
                    raise ValueError(f"无效的服务器地址格式: {addr}")

                ip, port = addr.split(':')

                # 创建自动刷新控制变量
                self.active_refreshes = getattr(self, 'active_refreshes', {})
                self.active_refreshes[addr] = True

                # 创建详情窗口 - 修改图标设置方式
                detail_win = tk.Toplevel()
                try:
                    detail_win.iconbitmap(os.path.join(BASE_DIR, "transparent_16x16.ico"))
                except Exception as e:
                    print(f"图标加载错误: {str(e)}")
                detail_win.title(get_string("server_details", "服务器详情"))
                # 应用窗口样式
                self.window_style_utils.apply_window_style(detail_win)

                # 先隐藏窗口，等待加载完成后再显示
                detail_win.withdraw()  # 隐藏窗口

                # 自动加入控制变量
                auto_join_var = tk.BooleanVar()

                # 服务器信息显示
                info_frame = ttk.Frame(detail_win)
                info_frame.pack(padx=10, pady=5, fill=tk.X)

                server_name_label = ttk.Label(info_frame, text="加载中...")
                server_name_label.pack(anchor=tk.CENTER, pady=5)

                map_frame = ttk.Frame(info_frame)
                map_frame.pack(anchor=tk.CENTER, pady=5)

                # 刷新按钮
                refresh_btn = create_outline_button(
                    map_frame,
                    image=self.refresh_icon if self.refresh_icon else "",
                    compound='center',
                    width=3,
                    padding=(2, 2),
                    command=lambda: [
                        # 取消当前的自动刷新任务
                        detail_win.after_cancel(getattr(detail_win, '_auto_refresh_id', '')),
                        # 立即执行刷新
                        refresh()
                    ]
                )
                if not self.refresh_icon:  # 图标创建失败时的回退方案
                    refresh_btn.config(text="↻")
                refresh_btn.pack(side=tk.LEFT, padx=5)

                map_label = ttk.Label(map_frame, text=get_string("map_loading", "地图: 加载中..."))
                map_label.pack(side=tk.LEFT)

                # 初始化时创建按钮（仅一次）
                map_btn = create_outline_button(
                    map_frame,
                    image=self.magnifier_icon if self.magnifier_icon else "",
                    compound='center',
                    width=3,
                    padding=(2, 2)
                )
                if not self.magnifier_icon:  # 图标创建失败时的回退方案
                    map_btn.config(text="?")
                map_btn.pack(side=tk.LEFT, padx=5)

                # IP地址操作区域
                ip_frame = ttk.Frame(detail_win)
                ip_frame.pack(pady=10, padx=10, fill=tk.X)

                # 加入服务器按钮
                join_btn = create_outline_button(
                    ip_frame,
                    text=get_string("join_server", "加入服务器"),
                    command=lambda: self.join_server(addr)
                )
                join_btn.pack(side=tk.LEFT, padx=5)

                # 复制按钮
                copy_btn = create_outline_button(
                    ip_frame,
                    text=get_string("copy_connect_command", "复制连接命令"),
                    command=lambda: self.copy_to_clipboard(f"connect {addr}")
                )
                copy_btn.pack(side=tk.RIGHT, padx=5)

                # IP地址显示框
                ip_entry = ttk.Entry(
                    ip_frame,
                    width=35,
                    font=(APP_FONT, 10),
                    state="readonly"
                )
                ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                ip_entry.configure(state="normal")
                ip_entry.insert(0, f"connect {addr}")
                ip_entry.configure(state="readonly")

                # 玩家数和自动加入区域
                players_frame = ttk.Frame(detail_win)
                players_frame.pack(pady=5, fill=tk.X)

                players_label = ttk.Label(players_frame, text="玩家数: -/-")
                players_label.pack(side=tk.LEFT, padx=10)

                # 自动加入勾选框（保持功能但调整布局）
                ttk.Checkbutton(
                    players_frame,
                    text=get_string("auto_join", "自动加入（有空位时）"),
                    variable=auto_join_var,
                    command=lambda: self.update_auto_join_status(auto_join_var, addr)
                ).pack(side=tk.RIGHT, padx=10)

                # 玩家列表容器
                player_container = ttk.Frame(detail_win)
                player_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

                # 玩家列表树状图（恢复文档1的列配置）
                columns = ('name', 'score', 'duration')
                player_tree = ttk.Treeview(
                    player_container,
                    columns=columns,
                    show='headings',
                    selectmode='extended',
                    height=8  # 保持文档1的高度设置
                )
                player_tree.bind('<Button-1>', self.on_tree_click)

                # 列配置（保持文档1的样式）
                player_tree.column('name', width=200, anchor=tk.W)
                player_tree.column('score', width=80, anchor=tk.CENTER)
                player_tree.column('duration', width=100, anchor=tk.CENTER)

                # 列标题（保留排序功能）
                player_tree.heading('name', text=get_string("player_name",'玩家名称'))
                player_tree.heading('score', text=get_string("score", '分数'), command=lambda: self.sort_player_column(player_tree, 'score'))
                player_tree.heading('duration', text=get_string("online_time", '在线时间'),
                                    command=lambda: self.sort_player_column(player_tree, 'duration'))

                # 滚动条
                scrollbar = ttk.Scrollbar(player_container, orient=tk.VERTICAL, command=player_tree.yview)
                player_tree.configure(yscrollcommand=scrollbar.set)

                # 布局
                player_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                # 操作按钮框架（保持文档1的布局）
                action_frame = ttk.Frame(detail_win)
                action_frame.pack(pady=5)

                create_outline_button(
                    action_frame,
                    text=get_string("favorite_server", "收藏该服务器"),
                    command=lambda: self.show_add_menu(addr, detail_win)
                ).pack(side=tk.LEFT, padx=5)

                create_outline_button(
                    action_frame,
                    text=get_string("favorite_same_ip", "收藏同一IP服务器"),
                    command=lambda: self.show_ip_add_menu(addr, detail_win)
                ).pack(side=tk.LEFT, padx=5)

                values = widget.item(item, 'values')
                server_name = values[2] if len(values) > 2 else get_string("unknown", "未知")

                create_outline_button(
                    action_frame,
                    text=get_string("block_server_text", "屏蔽服务器"),
                    command=lambda: self.block_server(addr, server_name, detail_win)  # 添加detail_win参数
                ).pack(side=tk.LEFT, padx=5)

                # 自动刷新函数
                def refresh():
                    if not self.active_refreshes.get(addr, False) or not detail_win.winfo_exists():
                        return

                    try:
                        new_info = a2s.info((ip, int(port)), timeout=2)
                        new_players = a2s.players((ip, int(port)), timeout=2)

                        # 更新信息显示
                        server_name_label.config(text=f"{new_info.server_name}")

                        # 使用格式化地图名称
                        formatted_map = self.format_map_name(new_info.map_name)
                        map_label.config(text=get_string("map", f"地图: {formatted_map}").format(formatted_map=formatted_map))

                        map_name = new_info.map_name
                        if self.map_utils.check_map_exists(map_name):
                            map_btn.config(
                                command=lambda m=map_name: self.map_utils.check_map_detail(m, detail_win)
                            )
                            map_btn.state(['!disabled'])  # 确保按钮可用
                        else:
                            map_btn.config(state='disabled')

                        players_label.config(text=get_string("players_count", f"玩家数: {new_info.player_count}/{new_info.max_players}").format(player_count=new_info.player_count, max_players=new_info.max_players))

                        # 自动加入逻辑
                        if auto_join_var.get() and new_info.player_count < new_info.max_players:
                            self.join_server(addr)
                            auto_join_var.set(False)

                        # 更新玩家列表
                        player_tree.delete(*player_tree.get_children())
                        for p in new_players:
                            duration = p.duration
                            if duration < 60:
                                time_str = f"00:{int(duration):02d}"
                            elif duration < 3600:
                                minutes = int(duration // 60)
                                seconds = int(duration % 60)
                                time_str = f"{minutes:02d}:{seconds:02d}"
                            else:
                                hours = int(duration // 3600)
                                remaining = duration % 3600
                                minutes = int(remaining // 60)
                                seconds = int(remaining % 60)
                                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                            player_tree.insert('', 'end', values=(
                                p.name,
                                getattr(p, 'score', 0),
                                time_str
                            ))

                    except Exception as e:
                        players_label.config(text=get_string("refresh_failed", f"刷新失败: {str(e)}").format(msg=str(e)))

                    # 取消旧任务并安排新任务
                    if hasattr(detail_win, '_auto_refresh_id'):
                        detail_win.after_cancel(detail_win._auto_refresh_id)

                    detail_win._auto_refresh_id = detail_win.after(10000, refresh)

                # 窗口关闭处理
                def on_close():
                    self.active_refreshes[addr] = False
                    # 取消所有待执行的刷新任务
                    if hasattr(detail_win, '_auto_refresh_id'):
                        detail_win.after_cancel(detail_win._auto_refresh_id)
                    detail_win.destroy()

                detail_win.protocol("WM_DELETE_WINDOW", on_close)

                # 延迟显示窗口
                def show_window():
                    # 等待0.5秒后显示窗口
                    time.sleep(0.5)
                    detail_win.deiconify()  # 显示窗口
                    # 居中显示
                    detail_win.update_idletasks()
                    x = self.root.winfo_x() + (self.root.winfo_width() - detail_win.winfo_width()) // 2
                    y = self.root.winfo_y() + (self.root.winfo_height() - detail_win.winfo_height()) // 2
                    detail_win.geometry(f"+{x}+{y}")

                # 在后台线程中执行延迟显示
                threading.Thread(target=show_window, daemon=True).start()

                # 立即开始刷新数据
                detail_win.after(0, refresh)

                # 右键菜单（保持文档1的实现方式）
                def on_player_right_click(e):
                    item = player_tree.identify_row(e.y)
                    if item:
                        menu = tk.Menu(player_tree, tearoff=0)
                        menu.add_command(
                            label=get_string("copy_player_names", "复制玩家名称"),
                            command=lambda: self.copy_player_name(player_tree, item)
                        )
                        menu.post(e.x_root, e.y_root)

                player_tree.bind("<Button-3>", on_player_right_click)

            except Exception as e:
                messagebox.showerror("错误", get_string("init_failed", f"初始化失败: {str(e)}").format(msg=str(e)))

    def update_auto_join_status(self, var, addr):
        """更新自动加入状态（带弹窗）"""
        # if var.get():
            # messagebox.showinfo("提示", f"已启用自动加入功能\n当服务器 {addr} 有空位时将自动连接")

        # 典型示例：硬编码转换为多语言适配后，对于包含动态内容的字符串（如 {count} 占位符），使用 .format() 方法插入变量
        # if var.get():
        #     messagebox.showinfo(get_string("tip"), get_string("auto_join_enabled").format(addr=addr))
        pass

    def copy_player_name(self, tree, item):
        """复制选中玩家的名称到剪贴板"""
        values = tree.item(item, "values")
        if values:
            player_name = values[0]
            self.copy_to_clipboard(player_name)

    def sort_player_column(self, tree, column):
        items = [(tree.set(child, column), child) for child in tree.get_children('')]

        try:
            if column == 'score':
                items.sort(key=lambda x: int(x[0]), reverse=True)
            elif column == 'duration':
                items.sort(key=lambda x: int(x[0].replace(':', '')), reverse=True)
            else:
                items.sort(key=lambda x: x[0].lower(), reverse=True)
        except:
            items.sort(reverse=True)

        for index, (_, child) in enumerate(items):
            tree.move(child, '', index)

    def show_add_menu(self, addr, parent_widget):
        """显示添加当前服务器的菜单"""
        menu = tk.Menu(self.root, tearoff=0)

        # 获取所有自定义页面
        for page in self.custom_pages:
            menu.add_command(
                label=get_string("add_to_page", f"添加到 {page}").format(page=page),
                command=lambda p=page: self.add_to_page(p, [addr])
            )

        # 在按钮下方显示菜单
        menu.post(
            parent_widget.winfo_pointerx(),
            parent_widget.winfo_pointery() + 30
        )

    def show_ip_add_menu(self, addr, parent_widget):
        """显示添加同IP服务器的菜单"""
        menu = tk.Menu(self.root, tearoff=0)

        # 获取同IP服务器列表
        current_page = self.current_page
        ip_part = addr.split(':')[0]
        same_ip = self.get_same_ip_servers(ip_part, current_page)

        for page in self.custom_pages:
            menu.add_command(
                label=get_string("add_to_page", f"添加到 {page}").format(page=page),
                command=lambda p=page: self.add_to_page(p, same_ip)
            )

        menu.post(
            parent_widget.winfo_pointerx(),
            parent_widget.winfo_pointery() + 30
        )

    def get_same_ip_servers(self, ip_part, current_page):
        """获取当前页面中相同IP的服务器列表"""
        if current_page == "main":
            servers = self.servers
        else:
            servers = self.custom_pages[current_page]['servers']

        return [s for s in servers if s.startswith(ip_part + ":")]

    def refresh_custom_page(self, page_name):
        """刷新指定自定义页面的显示"""
        page_data = self.custom_pages[page_name]
        page_data['tree'].delete(*page_data['tree'].get_children())
        if page_data['query_engine']:
            page_data['query_engine'].stop()
        page_data['query_engine'] = AsyncServerQuery(
            lambda r: self.update_custom_table(page_name, r))
        page_data['query_engine'].add_task(page_data['servers'])

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as e:
            messagebox.showerror(get_string("copy_failed", "复制失败"), str(e))  # 仅保留错误提示

    def toggle_buttons(self, enable):
        state = 'normal' if enable else 'disabled'
        self.fetch_btn.state(['!disabled' if enable else 'disabled'])
        self.query_btn.state(['!disabled' if enable else 'disabled'])

    def show_settings(self):
        """显示设置窗口"""
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.root, self)
        # 确保设置对话框可以访问过滤控件和仪表盘状态
        dialog.filter_enabled_var.set(self.filter_enabled)
        dialog.dashboard_enabled_var.set(self.dashboard_enabled)
        dialog.map_display_format_var.set(self.map_display_format_enabled)
        # 设置窗口样式
        dialog.window_style_var.set(self.window_style)