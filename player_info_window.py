import os
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from collections import defaultdict
import threading
import time

from language_strings import load_language_from_config, get_string

load_language_from_config()

from utils import create_outline_button
from font_utils import APP_FONT
from window_style_utils import window_style_utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PlayerInfoWindow:
    def __init__(self, master, main_app):
        self.master = master
        self.main_app = main_app
        self.window = None
        self.following = False
        self._minimized = False

        # 初始化 player_tree 为 None
        self.player_tree = None
        self.total_players_label = None
        self.total_servers_label = None

        # 使用嵌套字典存储玩家信息 {page_name: {player_name: {'duration': seconds, 'servers': {}}}}
        self.player_data = defaultdict(lambda: defaultdict(lambda: {'duration': 0, 'servers': {}}))
        self.player_lock = threading.Lock()

        # 缓冲队列，用于存储待处理的玩家信息
        self.pending_player_data = []
        self.pending_lock = threading.Lock()

        # 鼠标悬停相关变量
        self.tooltip_timer = None
        self.tooltip_window = None
        self.last_hover_item = None

        # 绑定主窗口移动和大小变化事件
        self.master.bind('<Configure>', self.on_master_move, add='+')
        self.master.bind('<Unmap>', self.on_master_minimize, add='+')
        self.master.bind('<Map>', self.on_master_restore, add='+')

    def on_master_minimize(self, event):
        """当主窗口最小化时"""
        if event.widget == self.master:
            self._minimized = True
            if self.window and self.window.winfo_exists():
                self.window.withdraw()

    def on_master_restore(self, event):
        """当主窗口从最小化恢复时"""
        if event.widget == self.master:
            self._minimized = False
            if self.following and self.window and self.window.winfo_exists():
                self.window.deiconify()
                self.update_position()
                window_style_utils.apply_window_style(self.window)

    def on_master_move(self, event):
        """当主窗口移动或改变大小时，调整玩家信息窗口位置"""
        if (self.window and self.window.winfo_exists() and
                self.master.winfo_viewable() and self.following and
                not self._minimized):
            self.update_position()

    def update_position(self):
        """更新玩家信息窗口位置，使其紧贴主窗口左侧"""
        if not self.window or not self.window.winfo_exists():
            return

        if self._minimized:
            return

        # 获取主窗口位置和大小
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_height = self.master.winfo_height()

        # 计算玩家信息窗口应该出现的位置
        player_x = main_x - 300  # 窗口宽度300，留5像素间隙
        player_y = main_y

        # 设置玩家信息窗口位置
        self.window.geometry(f"300x{main_height}+{player_x}+{player_y}")

    def show(self):
        """显示玩家信息窗口"""
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.focus()
            self.following = True
            self.update_position()
            window_style_utils.apply_window_style(self.window)
            return

        self.window = tk.Toplevel(self.master)
        self.window.title(get_string("player_info_window_title", "玩家信息"))
        self.window.geometry("300x600")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        # 设置窗口样式
        self.window.attributes('-toolwindow', True)
        self.window.transient(self.master)
        self.window.attributes('-disabled', False)

        # 初始位置设置
        self.following = True
        self.update_position()

        # 创建UI
        self.setup_ui()

        # 启动位置跟踪
        self.start_position_tracking()

        # 应用窗口样式
        window_style_utils.apply_window_style(self.window)

    def start_position_tracking(self):
        """启动位置跟踪，确保窗口始终跟随主窗口"""
        if hasattr(self, '_tracking') and self._tracking:
            return

        self._tracking = True

        def track_position():
            while (self.window and self.window.winfo_exists() and
                   self.master.winfo_exists() and self.following):
                try:
                    if not self._minimized:
                        self.update_position()
                    time.sleep(0.1)
                except:
                    break
            self._tracking = False

        threading.Thread(target=track_position, daemon=True).start()

    def hide(self):
        """隐藏玩家信息窗口"""
        self.following = False
        if self.window and self.window.winfo_exists():
            self.window.withdraw()

    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text=get_string("player_info_main_title", "玩家信息统计"),
            font=(APP_FONT, 14, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # 玩家统计框架
        stats_frame = ttk.LabelFrame(main_frame, text=get_string("player_stats_section", "玩家统计"), padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 20))

        # 玩家总数
        total_players_frame = ttk.Frame(stats_frame)
        total_players_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            total_players_frame,
            text=get_string("total_players", "总玩家数:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT)

        self.total_players_label = ttk.Label(
            total_players_frame,
            text="0",
            font=(APP_FONT, 10, 'bold')
        )
        self.total_players_label.pack(side=tk.RIGHT)

        # 服务器总数
        total_servers_frame = ttk.Frame(stats_frame)
        total_servers_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            total_servers_frame,
            text=get_string("total_servers_with_players", "有玩家的服务器数:"),
            font=(APP_FONT, 10)
        ).pack(side=tk.LEFT)

        self.total_servers_label = ttk.Label(
            total_servers_frame,
            text="0",
            font=(APP_FONT, 10, 'bold')
        )
        self.total_servers_label.pack(side=tk.RIGHT)

        # 玩家列表框架
        player_list_frame = ttk.LabelFrame(main_frame, text=get_string("player_list_section", "玩家列表"), padding=10)
        player_list_frame.pack(fill=tk.BOTH, expand=True)

        # 创建树状视图
        columns = ('player_name', 'duration')  # 注释掉'servers'列
        self.player_tree = ttk.Treeview(
            player_list_frame,
            columns=columns,
            show='headings',
            selectmode='browse',
            height=10
        )

        # 设置列
        self.player_tree.heading('player_name', text=get_string("player_name", "玩家名称"))
        self.player_tree.heading('duration', text=get_string("play_time", "游玩时间"))
        # 注释掉服务器数列
        # self.player_tree.heading('servers', text=get_string("servers_count", "服务器数"))

        self.player_tree.column('player_name', width=100, anchor=tk.W)  # 调整宽度
        self.player_tree.column('duration', width=80, anchor=tk.CENTER)
        # 注释掉服务器数列
        # self.player_tree.column('servers', width=50, anchor=tk.CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(player_list_frame, orient=tk.VERTICAL, command=self.player_tree.yview)
        self.player_tree.configure(yscroll=scrollbar.set)

        # 布局
        self.player_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击事件查看玩家详情
        self.player_tree.bind('<Double-Button-1>', self.show_player_details)

        # 绑定鼠标移动事件用于显示悬停提示
        self.player_tree.bind('<Motion>', self.on_mouse_motion)
        self.player_tree.bind('<Leave>', self.on_mouse_leave)

        # 关闭按钮
        close_btn = create_outline_button(
            main_frame,
            text=get_string("close_button", "关闭"),
            command=self.hide,
            width=10
        )
        close_btn.pack(pady=(20, 0))

    def format_duration(self, seconds):
        """格式化时间显示"""
        if seconds < 60:
            return f"00:{int(seconds):02d}"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            seconds_remaining = int(seconds % 60)
            return f"{minutes:02d}:{seconds_remaining:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds_remaining = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds_remaining:02d}"

    def add_player_info(self, server_addr, server_name, players, page_name):
        """添加玩家信息到缓冲队列，查询完成后统一处理"""
        if not self.main_app.player_info_enabled:
            return

        # 将数据添加到缓冲队列
        with self.pending_lock:
            self.pending_player_data.append((server_addr, server_name, players, page_name))

    def process_pending_data(self, page_name):
        """处理缓冲队列中的数据，在查询完成后调用"""
        if not self.pending_player_data:
            return

        with self.pending_lock:
            # 获取所有待处理数据
            pending_data = self.pending_player_data.copy()
            self.pending_player_data.clear()

        # 批量处理数据
        with self.player_lock:
            for server_addr, server_name, players, data_page_name in pending_data:
                # 只处理当前页面的数据
                if data_page_name != page_name:
                    continue

                for player in players:
                    player_name = player.name
                    duration = player.duration

                    # 更新玩家信息，关联到当前页面
                    self.player_data[page_name][player_name]['duration'] += duration
                    self.player_data[page_name][player_name]['servers'][server_addr] = server_name

        # 如果窗口显示且跟随，更新显示
        if (self.window and self.window.winfo_exists() and
                self.following and not self._minimized):
            self.update_player_display(page_name)

    def update_player_display(self, page_name=None):
        """更新玩家信息显示，可指定页面名称"""
        if not self.window or not self.window.winfo_exists():
            return

        # 如果没有指定页面，使用当前活动页面
        if page_name is None:
            page_name = self.main_app.current_page

        with self.player_lock:
            # 清空现有数据
            for item in self.player_tree.get_children():
                self.player_tree.delete(item)

            # 添加当前页面的玩家数据
            if page_name in self.player_data:
                page_players = self.player_data[page_name]

                # 按游玩时间降序排序
                sorted_players = sorted(
                    page_players.items(),
                    key=lambda x: x[1]['duration'],
                    reverse=True
                )

                for player_name, data in sorted_players:
                    duration_str = self.format_duration(data['duration'])
                    # server_count = len(data['servers'])  # 不再显示服务器数

                    # 插入玩家条目，只显示名称和时间
                    self.player_tree.insert('', 'end', values=(
                        player_name, duration_str
                    ), tags=(player_name,))  # 添加标签以便识别

                # 更新统计信息
                self.total_players_label.config(text=str(len(page_players)))

                # 计算有玩家的服务器数量
                servers_with_players = set()
                for data in page_players.values():
                    servers_with_players.update(data['servers'])

                self.total_servers_label.config(text=str(len(servers_with_players)))
            else:
                # 如果没有该页面的数据，清空显示
                self.total_players_label.config(text="0")
                self.total_servers_label.config(text="0")

    def clear_player_data(self, page_name=None):
        """清空指定页面或所有页面的玩家数据"""
        with self.player_lock:
            if page_name:
                # 清空指定页面的数据
                if page_name in self.player_data:
                    del self.player_data[page_name]
            else:
                # 清空所有数据
                self.player_data.clear()

            # 检查 player_tree 是否已初始化
            if self.player_tree is not None:
                for item in self.player_tree.get_children():
                    self.player_tree.delete(item)

                # 检查标签是否已初始化
                if self.total_players_label is not None:
                    self.total_players_label.config(text="0")
                if self.total_servers_label is not None:
                    self.total_servers_label.config(text="0")

        # 清空缓冲队列
        with self.pending_lock:
            self.pending_player_data.clear()

    def on_page_changed(self, page_name):
        """当页面切换时调用，更新玩家信息显示"""
        if self.window and self.window.winfo_exists() and self.following:
            self.update_player_display(page_name)

    def show_player_details(self, event):
        """显示玩家详情"""
        selection = self.player_tree.selection()
        if not selection:
            return

        item = selection[0]
        player_name = self.player_tree.item(item, 'values')[0]

        # 获取玩家详情
        with self.player_lock:
            page_name = self.main_app.current_page
            if page_name not in self.player_data or player_name not in self.player_data[page_name]:
                return

            data = self.player_data[page_name][player_name]
            duration = data['duration']
            servers = data['servers']

        # 创建详情窗口
        detail_win = tk.Toplevel(self.window)
        detail_win.title(get_string("player_details", "玩家详情"))
        detail_win.geometry("400x300")
        detail_win.iconbitmap(os.path.join(BASE_DIR, "transparent_16x16.ico"))
        detail_win.resizable(False, False)

        # 应用窗口样式
        window_style_utils.apply_window_style(detail_win)

        # 主框架
        main_frame = ttk.Frame(detail_win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 玩家名称
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            name_frame,
            text=get_string("player_name", "玩家名称:"),
            font=(APP_FONT, 10, 'bold')
        ).pack(side=tk.LEFT)

        ttk.Label(
            name_frame,
            text=player_name,
            font=(APP_FONT, 10)
        ).pack(side=tk.RIGHT)

        # 总游玩时间
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            time_frame,
            text=get_string("total_play_time", "总游玩时间:"),
            font=(APP_FONT, 10, 'bold')
        ).pack(side=tk.LEFT)

        ttk.Label(
            time_frame,
            text=self.format_duration(duration),
            font=(APP_FONT, 10)
        ).pack(side=tk.RIGHT)

        # 服务器数量
        servers_frame = ttk.Frame(main_frame)
        servers_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            servers_frame,
            text=get_string("servers_played_on", "游玩过的服务器数:"),
            font=(APP_FONT, 10, 'bold')
        ).pack(side=tk.LEFT)

        ttk.Label(
            servers_frame,
            text=str(len(servers)),
            font=(APP_FONT, 10)
        ).pack(side=tk.RIGHT)

        # 服务器列表标题
        ttk.Label(
            main_frame,
            text=get_string("servers_list", "服务器列表:"),
            font=(APP_FONT, 10, 'bold')
        ).pack(anchor=tk.W, pady=(10, 5))

        # 服务器列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        servers_list = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=(APP_FONT, 9)
        )
        servers_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=servers_list.yview)

        # 添加服务器地址
        for server_addr in sorted(servers.keys()):
            server_name = servers[server_addr]
            display_text = f"{server_addr} {server_name}"
            servers_list.insert(tk.END, display_text)

        # 关闭按钮
        close_btn = ttk.Button(
            main_frame,
            text=get_string("close_button", "关闭"),
            command=detail_win.destroy,
            width=10
        )
        close_btn.pack(pady=(10, 0))

        # 居中显示
        detail_win.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - detail_win.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - detail_win.winfo_height()) // 2
        detail_win.geometry(f"+{x}+{y}")

    def on_mouse_motion(self, event):
        """处理鼠标移动事件，显示悬停提示"""
        # 取消之前的计时器
        if self.tooltip_timer:
            self.window.after_cancel(self.tooltip_timer)
            self.tooltip_timer = None

        # 获取鼠标下方的项目
        item = self.player_tree.identify_row(event.y)
        if not item:
            self.hide_tooltip()
            return

        # 如果鼠标移动到新项目上
        if item != self.last_hover_item:
            self.hide_tooltip()
            self.last_hover_item = item

            # 设置新的计时器，秒后显示提示
            self.tooltip_timer = self.window.after(1, lambda: self.show_tooltip(item, event))

    def on_mouse_leave(self, event):
        """处理鼠标离开事件，隐藏提示"""
        self.hide_tooltip()
        if self.tooltip_timer:
            self.window.after_cancel(self.tooltip_timer)
            self.tooltip_timer = None
        self.last_hover_item = None

    def show_tooltip(self, item, event):
        """显示悬停提示"""
        # 获取玩家名称
        player_name = self.player_tree.item(item, 'values')[0]

        # 获取玩家详情
        with self.player_lock:
            page_name = self.main_app.current_page
            if page_name not in self.player_data or player_name not in self.player_data[page_name]:
                return

            data = self.player_data[page_name][player_name]
            servers = data['servers']
            server_count = len(servers)

        # 创建提示内容
        tooltip_text = get_string("player_info_tooltip_text", f"相关的服务器数: {server_count}\n\n服务器列表:\n").format(count=server_count)

        # 添加服务器信息
        for i, (server_addr, server_name) in enumerate(servers.items()):
            if i >= 5:  # 最多显示5个服务器
                tooltip_text += "...\n"
                break
            tooltip_text += f"• {server_addr} {server_name}\n"

        # 创建提示窗口
        self.hide_tooltip()
        self.tooltip_window = tk.Toplevel(self.window)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        # 创建提示标签
        label = ttk.Label(
            self.tooltip_window,
            text=tooltip_text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=(APP_FONT, 9),
            padding=5
        )
        label.pack()

    def hide_tooltip(self):
        """隐藏悬停提示"""
        if self.tooltip_window and self.tooltip_window.winfo_exists():
            self.tooltip_window.destroy()
            self.tooltip_window = None