import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import time

from utils import create_outline_button
from window_style_utils import window_style_utils
from font_utils import APP_FONT

from language_strings import load_language_from_config, get_string
load_language_from_config()


class Dashboard:
    def __init__(self, master, main_app):
        self.master = master
        self.main_app = main_app
        self.window = None
        self.following = False  # 跟踪是否正在跟随主窗口
        self._minimized = False  # 跟踪主窗口是否最小化

        # 绑定主窗口移动和大小变化事件
        self.master.bind('<Configure>', self.on_master_move, add='+')
        self.master.bind('<Unmap>', self.on_master_minimize, add='+')
        self.master.bind('<Map>', self.on_master_restore, add='+')

    def on_master_minimize(self, event):
        """当主窗口最小化时"""
        if event.widget == self.master:
            self._minimized = True
            # 如果仪表盘可见，也隐藏它
            if self.window and self.window.winfo_exists():
                self.window.withdraw()

    def on_master_restore(self, event):
        """当主窗口从最小化恢复时"""
        if event.widget == self.master:
            self._minimized = False
            # 如果仪表盘应该显示，则恢复它
            if self.following and self.window and self.window.winfo_exists():
                self.window.deiconify()
                self.update_position()
                # 重新应用窗口样式，确保样式不会丢失
                window_style_utils.apply_window_style(self.window)

    def on_master_move(self, event):
        """当主窗口移动或改变大小时，调整仪表盘位置"""
        if (self.window and self.window.winfo_exists() and
                self.master.winfo_viewable() and self.following and
                not self._minimized):  # 不在最小化状态下更新
            self.update_position()

    def update_position(self):
        """更新仪表盘位置，使其紧贴主窗口右侧，并跟随主窗口高度"""
        if not self.window or not self.window.winfo_exists():
            return

        # 如果主窗口最小化，不更新位置
        if self._minimized:
            return

        # 获取主窗口位置和大小
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()

        # 计算仪表盘应该出现的位置
        dash_x = main_x + main_width + 10  # 紧贴主窗口右侧，留5像素间隙
        dash_y = main_y

        # 设置仪表盘位置和高度
        self.window.geometry(f"300x{main_height}+{dash_x}+{dash_y}")

    def show(self):
        """显示仪表盘窗口"""
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.focus()
            self.following = True
            self.update_position()
            # 确保样式正确应用
            window_style_utils.apply_window_style(self.window)
            return

        self.window = tk.Toplevel(self.master)
        self.window.title(get_string("dashboard_window_title", "服务器状态仪表盘"))
        self.window.geometry("300x600")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        # 设置仪表盘为工具窗口样式，减少任务栏显示
        self.window.attributes('-toolwindow', True)

        # 设置为附属窗口
        self.window.transient(self.master)

        # 禁止仪表盘获得焦点，避免干扰主窗口操作
        self.window.attributes('-disabled', False)

        # 初始位置设置
        self.following = True
        self.update_position()

        # 创建仪表盘框架
        self.setup_ui()

        # 启动位置跟踪
        self.start_position_tracking()

        # 应用窗口样式
        window_style_utils.apply_window_style(self.window)

    def start_position_tracking(self):
        """启动位置跟踪，确保仪表盘始终跟随主窗口"""
        if hasattr(self, '_tracking') and self._tracking:
            return

        self._tracking = True

        def track_position():
            while (self.window and self.window.winfo_exists() and
                   self.master.winfo_exists() and self.following):
                try:
                    # 只有在主窗口不最小化时才更新位置
                    if not self._minimized:
                        self.update_position()
                    time.sleep(0.1)  # 每100毫秒检查一次位置
                except:
                    break
            self._tracking = False

        # 在后台线程中运行位置跟踪
        threading.Thread(target=track_position, daemon=True).start()

    def hide(self):
        """隐藏仪表盘窗口"""
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
            text=get_string("dashboard_main_title", "服务器状态监控"),
            font=(APP_FONT, 14, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # 服务器状态仪表盘
        server_frame = ttk.LabelFrame(main_frame, text=get_string("server_status_section", "服务器状态"), padding=10)
        server_frame.pack(fill=tk.X, pady=(0, 20))

        self.server_gauge = ttk.Meter(
            server_frame,
            metersize=150,
            padding=5,
            amountused=0,
            amounttotal=100,
            metertype="semi",
            subtext=get_string("active_servers_text", "活跃服务器"),
            interactive=False,
            stripethickness=10,
            subtextfont=(APP_FONT, 10),
            textfont=(APP_FONT, 20, 'bold')
        )
        self.server_gauge.pack()

        self.server_label = ttk.Label(
            server_frame,
            text="0/0 (0%)",
            font=(APP_FONT, 10)
        )
        self.server_label.pack(pady=(5, 0))

        # 玩家状态仪表盘
        player_frame = ttk.LabelFrame(main_frame, text=get_string("player_status_section", "玩家状态"), padding=10)
        player_frame.pack(fill=tk.X)

        self.player_gauge = ttk.Meter(
            player_frame,
            metersize=150,
            padding=5,
            amountused=0,
            amounttotal=100,
            metertype="semi",
            subtext=get_string("online_players_text", "在服玩家"),
            interactive=False,
            stripethickness=10,
            subtextfont=(APP_FONT, 10),
            textfont=(APP_FONT, 20, 'bold')
        )
        self.player_gauge.pack()

        self.player_label = ttk.Label(
            player_frame,
            text="0/0 (0%)",
            font=(APP_FONT, 10)
        )
        self.player_label.pack(pady=(5, 0))

        # 关闭按钮
        close_btn = create_outline_button(
            main_frame,
            text=get_string("close_button", "关闭"),
            command=self.hide,
            width=10
        )
        close_btn.pack(side=tk.BOTTOM, pady=(20, 0))

    def update_data(self):
        """更新仪表盘数据（不受过滤影响，使用完整数据）"""
        if not self.window or not self.window.winfo_exists():
            return

        # 重置计数器
        online_servers = 0
        total_servers = 0
        total_players = 0
        total_slots = 0
        servers_with_players = 0

        # 根据当前页面获取完整数据（忽略过滤状态）
        if self.main_app.current_page == "main":
            # 主页面数据 - 使用 all_items 而不是 tree 的可见项
            total_servers = len(self.main_app.all_items['main'])

            # 计算在线服务器和玩家数据
            for addr in self.main_app.all_items['main']:
                if self.main_app.tree.exists(addr) and 'online' in self.main_app.tree.item(addr, 'tags'):
                    online_servers += 1
                    values = self.main_app.tree.item(addr, 'values')
                    if len(values) > 5:
                        players_str = values[5]
                        if '/' in players_str:
                            current, max_players = players_str.split('/')
                            try:
                                current_players = int(current)
                                total_players += current_players
                                total_slots += int(max_players)
                                if current_players > 0:
                                    servers_with_players += 1
                            except ValueError:
                                pass
        else:
            # 自定义页面数据
            if self.main_app.current_page in self.main_app.custom_pages:
                page_data = self.main_app.custom_pages[self.main_app.current_page]
                if 'all_items' in page_data:
                    total_servers = len(page_data['all_items'])

                    # 计算在线服务器和玩家数据
                    for addr in page_data['all_items']:
                        if (page_data['tree'].exists(addr) and
                                'online' in page_data['tree'].item(addr, 'tags')):
                            online_servers += 1
                            values = page_data['tree'].item(addr, 'values')
                            if len(values) > 5:
                                players_str = values[5]
                                if '/' in players_str:
                                    current, max_players = players_str.split('/')
                                    try:
                                        current_players = int(current)
                                        total_players += current_players
                                        total_slots += int(max_players)
                                        if current_players > 0:
                                            servers_with_players += 1
                                    except ValueError:
                                        pass

        # 防止除以零的错误
        safe_online_servers = max(online_servers, 1)
        safe_total_slots = max(total_slots, 1)

        # 计算百分比
        server_percent = (servers_with_players / safe_online_servers * 100) if online_servers > 0 else 0
        player_percent = (total_players / safe_total_slots * 100) if total_slots > 0 else 0

        try:
            # 更新服务器仪表盘
            self.server_gauge.configure(amountused=servers_with_players, amounttotal=safe_online_servers)
            self.server_label.configure(text=f"{servers_with_players}/{online_servers} ({server_percent:.1f}%)")

            # 更新玩家仪表盘
            self.player_gauge.configure(amountused=total_players, amounttotal=safe_total_slots)
            self.player_label.configure(text=f"{total_players}/{total_slots} ({player_percent:.1f}%)")
        except ZeroDivisionError:
            # 如果仍然出现除以零错误，设置默认值
            self.server_gauge.configure(amountused=0, amounttotal=1)
            self.server_label.configure(text="0/0 (0%)")
            self.player_gauge.configure(amountused=0, amounttotal=1)
            self.player_label.configure(text="0/0 (0%)")
        except Exception as e:
            print(f"仪表盘更新错误: {str(e)}")