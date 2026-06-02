import tkinter as tk
from tkinter import ttk
from tkinter import Toplevel, messagebox
import os
import re

from font_utils import APP_FONT
from language_strings import load_language_from_config, get_string
from utils import create_outline_button
from window_style_utils import window_style_utils

load_language_from_config()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class FilterUtils:
    def __init__(self, parent_frame, app_instance):
        self.app = app_instance
        self.frame = ttk.Frame(parent_frame)

        # 过滤状态变量
        self.show_empty_only = tk.BooleanVar(value=False)
        self.show_occupied_only = tk.BooleanVar(value=False)
        self.hide_timeout = tk.BooleanVar(value=False)
        self.custom_filter_enabled = tk.BooleanVar(value=False)  # 自定义规则启用状态

        # 自定义规则配置
        self.custom_filter_mode = "show"  # "show" 或 "hide"
        self.custom_filter_rules = []  # 自定义规则列表

        self.custom_filter_dialog = None  # 自定义规则配置窗口实例引用

        self.setup_filter_ui()

    def setup_filter_ui(self):
        """设置过滤UI"""
        # 使用与引擎状态相同的字体
        ttk.Label(self.frame, text=get_string("filter_label", "筛选:"), font=(APP_FONT, 10)).pack(side=tk.LEFT)

        # 只显示空房
        self.empty_cb = ttk.Checkbutton(
            self.frame,
            text=get_string("filter_empty", "空房"),
            variable=self.show_empty_only,
            command=lambda: self.toggle_filter('empty', self.show_empty_only)
        )
        self.empty_cb.pack(side=tk.LEFT, padx=2)

        # 只显示有人房
        self.occupied_cb = ttk.Checkbutton(
            self.frame,
            text=get_string("filter_occupied", "有人"),
            variable=self.show_occupied_only,
            command=lambda: self.toggle_filter('occupied', self.show_occupied_only)
        )
        self.occupied_cb.pack(side=tk.LEFT, padx=2)

        # 不显示超时服务器
        self.timeout_cb = ttk.Checkbutton(
            self.frame,
            text=get_string("filter_hide_timeout", "隐藏超时"),
            variable=self.hide_timeout,
            command=lambda: self.toggle_filter('timeout', self.hide_timeout)
        )
        self.timeout_cb.pack(side=tk.LEFT, padx=2)

        # 自定义规则勾选框和加号按钮
        custom_frame = ttk.Frame(self.frame)
        custom_frame.pack(side=tk.LEFT, padx=2)

        self.custom_cb = ttk.Checkbutton(
            custom_frame,
            text=get_string("filter_custom", "自定义规则"),
            variable=self.custom_filter_enabled,
            command=lambda: self.toggle_filter('custom', self.custom_filter_enabled)
        )
        self.custom_cb.pack(side=tk.LEFT)

        # 加号按钮（文本形式）
        self.plus_label = ttk.Label(
            custom_frame,
            text="[...]",
            cursor="hand2"
        )
        self.plus_label.pack(side=tk.LEFT, padx=(2, 0))

        # 绑定点击事件
        self.plus_label.bind("<Button-1>", self.show_custom_filter_dialog)

    def show_custom_filter_dialog(self, event=None):
        """显示自定义过滤规则配置窗口"""
        if self.custom_filter_dialog is None or not self.custom_filter_dialog.winfo_exists():
            self.custom_filter_dialog = CustomFilterDialog(self.app.root, self)
            # 设置窗口关闭时的回调
            self.custom_filter_dialog.protocol("WM_DELETE_WINDOW", self.on_custom_filter_close)
        else:
            # 如果窗口已存在，将其提到前台
            self.custom_filter_dialog.lift()
            self.custom_filter_dialog.focus_force()

    def on_custom_filter_close(self):
        """处理自定义过滤规则窗口关闭事件"""
        if self.custom_filter_dialog:
            self.custom_filter_dialog.destroy()
            self.custom_filter_dialog = None

    def toggle_filter(self, filter_type, var):
        """切换过滤选项"""
        # 处理互斥选项：空房和有人房不能同时选择
        if filter_type == 'empty' and var.get():
            self.show_occupied_only.set(False)
        elif filter_type == 'occupied' and var.get():
            self.show_empty_only.set(False)

        # 应用过滤
        self.apply_filters()

    def apply_filters(self):
        """应用所有过滤条件"""
        if self.app.current_page == "main":
            self.apply_main_filters()
        else:
            self.apply_custom_filters(self.app.current_page)

    def apply_main_filters(self):
        """应用到主页面"""
        tree = self.app.tree
        keyword = self.app.filter_var.get().lower()

        # 重新显示所有条目
        for item in self.app.all_items['main']:
            if tree.exists(item):
                tree.reattach(item, '', 'end')

        # 应用关键词过滤
        if keyword:
            for item in tree.get_children():
                values = [str(v).lower() for v in tree.item(item, 'values')]
                if not any(keyword in v for v in values):
                    tree.detach(item)

        # 应用状态过滤
        for item in tree.get_children():
            values = tree.item(item, 'values')
            tags = tree.item(item, 'tags')

            should_hide = False

            # 检查空房/有人房过滤
            if self.show_empty_only.get() or self.show_occupied_only.get():
                players_str = values[5] if len(values) > 5 else "0/0"
                if '/' in players_str:
                    current, max_players = players_str.split('/')
                    try:
                        current_players = int(current)
                        if self.show_empty_only.get() and current_players > 0:
                            should_hide = True
                        elif self.show_occupied_only.get() and current_players == 0:
                            should_hide = True
                    except ValueError:
                        pass

            # 检查超时服务器过滤
            if self.hide_timeout.get() and 'offline' in tags:
                should_hide = True

            # 应用自定义规则过滤 - 检索所有列
            if self.custom_filter_enabled.get() and self.custom_filter_rules:
                matches_rule = self.matches_custom_rules(values)

                if self.custom_filter_mode == "show":
                    # 显示模式：只显示匹配规则的服务器
                    if not matches_rule:
                        should_hide = True
                else:  # hide模式
                    # 隐藏模式：隐藏匹配规则的服务器
                    if matches_rule:
                        should_hide = True

            if should_hide:
                tree.detach(item)

    def apply_custom_filters(self, page_name):
        """应用到自定义页面"""
        if page_name not in self.app.custom_pages:
            return

        page_data = self.app.custom_pages[page_name]
        tree = page_data['tree']
        keyword = self.app.filter_var.get().lower()

        # 重新显示所有条目
        if 'all_items' in page_data:
            for item in page_data['all_items']:
                if tree.exists(item):
                    tree.reattach(item, '', 'end')

        # 应用关键词过滤
        if keyword:
            for item in tree.get_children():
                values = [str(v).lower() for v in tree.item(item, 'values')]
                if not any(keyword in v for v in values):
                    tree.detach(item)

        # 应用状态过滤
        for item in tree.get_children():
            values = tree.item(item, 'values')
            tags = tree.item(item, 'tags')

            should_hide = False

            # 检查空房/有人房过滤
            if self.show_empty_only.get() or self.show_occupied_only.get():
                players_str = values[5] if len(values) > 5 else "0/0"
                if '/' in players_str:
                    current, max_players = players_str.split('/')
                    try:
                        current_players = int(current)
                        if self.show_empty_only.get() and current_players > 0:
                            should_hide = True
                        elif self.show_occupied_only.get() and current_players == 0:
                            should_hide = True
                    except ValueError:
                        pass

            # 检查超时服务器过滤
            if self.hide_timeout.get() and 'offline' in tags:
                should_hide = True

            # 应用自定义规则过滤 - 检索所有列
            if self.custom_filter_enabled.get() and self.custom_filter_rules:
                matches_rule = self.matches_custom_rules(values)

                if self.custom_filter_mode == "show":
                    # 显示模式：只显示匹配规则的服务器
                    if not matches_rule:
                        should_hide = True
                else:  # hide模式
                    # 隐藏模式：隐藏匹配规则的服务器
                    if matches_rule:
                        should_hide = True

            if should_hide:
                tree.detach(item)

    def matches_custom_rules(self, server_values):
        """检查服务器是否匹配自定义规则 - 检索所有列信息"""
        # 将所有列的值转换为小写字符串进行匹配
        all_values = ' '.join([str(v).lower() for v in server_values])

        for rule in self.custom_filter_rules:
            rule_lower = rule.lower()
            # 检查规则是否在任意列的值中出现
            if rule_lower in all_values:
                return True
        return False

    def clear_filters(self):
        """清除所有过滤条件"""
        self.show_empty_only.set(False)
        self.show_occupied_only.set(False)
        self.hide_timeout.set(False)
        self.custom_filter_enabled.set(False)

        # 重新应用过滤（实际上是清除过滤）
        self.apply_filters()

    def get_filter_state(self):
        """获取过滤状态用于保存配置"""
        return {
            'show_empty_only': self.show_empty_only.get(),
            'show_occupied_only': self.show_occupied_only.get(),
            'hide_timeout': self.hide_timeout.get(),
            'custom_filter_enabled': self.custom_filter_enabled.get(),
            'custom_filter_mode': self.custom_filter_mode,
            'custom_filter_rules': self.custom_filter_rules
        }

    def set_filter_state(self, state):
        """从配置恢复过滤状态"""
        if 'show_empty_only' in state:
            self.show_empty_only.set(state['show_empty_only'])
        if 'show_occupied_only' in state:
            self.show_occupied_only.set(state['show_occupied_only'])
        if 'hide_timeout' in state:
            self.hide_timeout.set(state['hide_timeout'])
        if 'custom_filter_enabled' in state:
            self.custom_filter_enabled.set(state['custom_filter_enabled'])
        if 'custom_filter_mode' in state:
            self.custom_filter_mode = state['custom_filter_mode']
        if 'custom_filter_rules' in state:
            self.custom_filter_rules = state['custom_filter_rules']

        # 应用恢复的过滤状态
        self.apply_filters()

    def update_custom_filter_rules(self, mode, rules):
        """更新自定义过滤规则"""
        self.custom_filter_mode = mode
        self.custom_filter_rules = rules

        # 重新应用过滤
        if self.custom_filter_enabled.get():
            self.apply_filters()


class CustomFilterDialog(Toplevel):
    def __init__(self, parent, filter_utils):
        super().__init__(parent)
        try:
            self.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        self.title(get_string("custom_filter_title", "过滤自定义规则"))
        self.geometry("500x400")
        self.filter_utils = filter_utils
        self.grab_set()  # 设置为模态窗口
        # 应用窗口样式
        window_style_utils.apply_window_style(self)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 模式选择
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Label(mode_frame, text=get_string("custom_filter_mode", "过滤模式:")).pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value=filter_utils.custom_filter_mode)
        ttk.Radiobutton(mode_frame, text=get_string("custom_filter_show", "显示"),
                        variable=self.mode_var, value="show").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text=get_string("custom_filter_hide", "隐藏"),
                        variable=self.mode_var, value="hide").pack(side=tk.LEFT, padx=5)

        # 规则说明
        ttk.Label(main_frame, text=get_string("custom_filter_rules_desc", "自定义规则（每行一个关键词）:"),
                  font=(APP_FONT, 9)).pack(anchor=tk.W, pady=(10, 5))

        # 规则输入区域
        rules_frame = ttk.Frame(main_frame)
        rules_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.rules_text = tk.Text(rules_frame, height=10)
        scrollbar = ttk.Scrollbar(rules_frame, orient=tk.VERTICAL, command=self.rules_text.yview)
        self.rules_text.configure(yscrollcommand=scrollbar.set)

        self.rules_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入现有规则
        if filter_utils.custom_filter_rules:
            self.rules_text.insert('1.0', '\n'.join(filter_utils.custom_filter_rules))

        # 说明文本
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame,
                  text=get_string("custom_filter_example", "示例: 输入'合作'将过滤包含'合作'的服务器名称或地图名称"),
                  font=(APP_FONT, 9),
                  foreground="gray").pack(anchor=tk.W)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        create_outline_button(
            btn_frame,
            text=get_string("save_button", "保存"),
            command=self.save_config
        ).pack(side=tk.LEFT, padx=5)

        create_outline_button(
            btn_frame,
            text=get_string("cancel_button", "取消"),
            command=self.destroy
        ).pack(side=tk.LEFT, padx=5)

    def save_config(self):
        """保存自定义过滤规则"""
        rules_text = self.rules_text.get('1.0', tk.END).strip()
        mode = self.mode_var.get()

        # 解析规则
        rules = []
        for line in rules_text.split('\n'):
            rule = line.strip()
            if rule:  # 忽略空行
                rules.append(rule)

        # 更新过滤工具
        self.filter_utils.update_custom_filter_rules(mode, rules)

        # 关闭窗口
        self.destroy()
        # 通知父窗口
        if self.filter_utils:
            self.filter_utils.on_custom_filter_close()