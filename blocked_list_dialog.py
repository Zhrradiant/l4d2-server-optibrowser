import tkinter as tk
from tkinter import ttk
from tkinter import Toplevel, messagebox
import os
import re

from language_strings import get_string
from utils import create_outline_button
from window_style_utils import window_style_utils
from font_utils import APP_FONT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOCKED_FILE = "blocked.txt"


class BlockedListDialog(Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        try:
            self.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        self.title(get_string("block_list_title", "屏蔽列表"))
        self.geometry("700x400")  # 增加宽度以容纳第三列
        self.app = app
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.port_config_dialog = None  # 端口配置窗口实例引用
        # 应用窗口样式
        window_style_utils.apply_window_style(self)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 增加第三列'mode'用于显示模式
        self.tree = ttk.Treeview(main_frame, columns=('ip', 'name', 'mode'), show='headings', selectmode='extended')
        self.tree.heading('ip', text=get_string("ip_address_column", 'IP地址'))
        self.tree.heading('name', text=get_string("server_name_column", '屏蔽时的服务器名称'))
        self.tree.heading('mode', text=get_string("block_mode_column", '屏蔽模式'))
        self.tree.bind('<Button-1>', self.app.on_tree_click)
        self.tree.bind('<Double-Button-1>', self.on_double_click)
        self.tree.column('ip', width=250)
        self.tree.column('name', width=250)
        self.tree.column('mode', width=150)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        create_outline_button(
            btn_frame,
            text=get_string("unblock_button", "解除屏蔽"),
            command=self.unblock_selected
        ).pack(side=tk.LEFT, padx=5)

        create_outline_button(
            btn_frame,
            text=get_string("refresh_list_button", "刷新列表"),
            command=self.refresh_list
        ).pack(side=tk.LEFT, padx=5)

        self.refresh_list()

    def on_double_click(self, event):
        """处理双击事件，弹出端口配置窗口"""
        item = self.tree.identify_row(event.y)
        if item:
            values = self.tree.item(item, 'values')
            if values:
                # 获取显示的IP:第一端口
                display_ip = values[0]
                name = values[1] if len(values) > 1 else "未知"
                mode = values[2] if len(values) > 2 else "all_ports"

                # 需要从原始文件中查找完整的端口规则和模式
                full_ip_part, mode = self.get_full_ip_part_and_mode_from_file(display_ip)

                # 确保只有一个端口配置窗口实例
                if self.port_config_dialog is None or not self.port_config_dialog.winfo_exists():
                    self.port_config_dialog = PortConfigDialog(self, full_ip_part, name, mode)
                    # 设置窗口关闭时的回调
                    self.port_config_dialog.protocol("WM_DELETE_WINDOW", self.on_port_config_close)
                else:
                    # 如果窗口已存在，将其提到前台
                    self.port_config_dialog.lift()
                    self.port_config_dialog.focus_force()

    def on_port_config_close(self):
        """处理端口配置窗口关闭事件"""
        if self.port_config_dialog:
            self.port_config_dialog.destroy()
            self.port_config_dialog = None

    def get_full_ip_part_and_mode_from_file(self, display_ip):
        """从文件中查找完整的IP端口规则和模式"""
        if not os.path.exists(BLOCKED_FILE):
            return display_ip, "all_ports"

        with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 获取文件中的完整IP部分
                if ' ' in line:
                    file_ip_part, _ = line.split(' ', 1)
                else:
                    file_ip_part = line

                # 检查是否匹配显示的IP（IP部分应该相同）
                if ':' in display_ip:
                    display_ip_only = display_ip.split(':')[0]
                    if ':' in file_ip_part:
                        file_ip_only = file_ip_part.split(':')[0]
                        if display_ip_only == file_ip_only:
                            # 检查是否有模式信息（模式信息在最后一个逗号后面）
                            if ',' in file_ip_part:
                                parts = file_ip_part.split(',')
                                # 检查最后一个部分是否是模式标识
                                last_part = parts[-1]
                                if last_part in ["all_ports", "single_port", "custom"]:
                                    mode = last_part
                                    file_ip_part_without_mode = ','.join(parts[:-1])
                                    return file_ip_part_without_mode, mode
                            # 如果没有模式信息，返回英文模式
                            return file_ip_part, "all_ports"

        return display_ip, "all_ports"

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # 解析新格式: IP:端口,端口规则 服务器名称
                    if ' ' in line:
                        ip_part, name = line.split(' ', 1)
                    else:
                        ip_part, name = line, "未知"

                    # 提取模式信息（如果有）
                    mode = get_string("all_ports_mode", "全端口")  # 默认值
                    if ',' in ip_part:
                        parts = ip_part.split(',')
                        if parts[-1] in ["all_ports", "single_port", "custom"]:
                            # 提取模式并转换为中文显示
                            mode_en = parts[-1]
                            if mode_en == "all_ports":
                                mode = get_string("all_ports_mode", "全端口")
                            elif mode_en == "single_port":
                                mode = get_string("single_port_mode", "仅此端口")
                            elif mode_en == "custom":
                                mode = get_string("custom_port_mode", "自定义端口")
                            ip_part = ','.join(parts[:-1])

                    # 只显示IP和第一个端口
                    if ':' in ip_part:
                        ip, ports = ip_part.split(':', 1)
                        # 只取第一个端口（如果有逗号分隔）
                        first_port = ports.split(',')[0]
                        display_ip = f"{ip}:{first_port}"
                    else:
                        display_ip = ip_part

                    self.tree.insert('', 'end', values=(display_ip, name, mode))

    def unblock_selected(self):
        selected = self.tree.selection()
        if not selected:
            return

        entries = []
        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                entries = f.readlines()

        new_entries = []
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            entry_ip = entry.split(' ', 1)[0].split(':')[0]  # 只比较IP部分
            keep = True
            for item in selected:
                item_ip = self.tree.item(item, 'values')[0].split(' ', 1)[0].split(':')[0]
                if entry_ip == item_ip:
                    keep = False
                    break
            if keep:
                new_entries.append(entry + '\n')

        with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_entries)

        self.refresh_list()
        if self.app.query_engine is not None:
            self.app.query_engine.blocked_ips = self.app.load_blocked_ips()

    def on_close(self):
        """窗口关闭时刷新主应用的屏蔽列表"""
        if self.app.query_engine is not None:
            self.app.query_engine.blocked_ips = self.app.load_blocked_ips()

        # 关闭所有子窗口
        if self.port_config_dialog and self.port_config_dialog.winfo_exists():
            self.port_config_dialog.destroy()

        self.destroy()
        # 通知主应用窗口已关闭
        if hasattr(self.app, 'on_blocked_list_close'):
            self.app.on_blocked_list_close()


class PortConfigDialog(Toplevel):
    def __init__(self, parent, ip_with_port, server_name, initial_mode="all_ports"):  # 默认值改为英文
        super().__init__(parent)
        try:
            self.iconbitmap(os.path.join(BASE_DIR, "icon.ico"))
        except Exception as e:
            print(f"图标加载错误: {str(e)}")
        self.title(get_string("port_config_title", "端口屏蔽配置"))
        self.geometry("545x400")
        self.parent_dialog = parent
        self.app = parent.app
        # self.transient(parent)  # 设置为父窗口的临时窗口（注意会导致标题栏最大最小化消失）
        self.grab_set()  # 设置为模态窗口
        # 应用窗口样式
        window_style_utils.apply_window_style(self)

        # 解析传入的IP和端口（现在传入的是完整规则）
        if ':' in ip_with_port:
            self.ip, ports_part = ip_with_port.split(':', 1)
            # 解析端口规则
            if ',' in ports_part:
                port_parts = ports_part.split(',')
                self.initial_port = port_parts[0]  # 第一个端口
                self.custom_rules = ','.join(port_parts[1:])  # 剩余的自定义规则
            else:
                self.initial_port = ports_part
                self.custom_rules = ""
        else:
            self.ip = ip_with_port
            self.initial_port = "27015"  # 默认端口
            self.custom_rules = ""

        self.server_name = server_name
        # 直接使用传入的英文模式，不需要转换
        self.mode = tk.StringVar(value=initial_mode)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # IP地址显示
        ttk.Label(main_frame, text=get_string("ip_address_column_info", f"IP地址: {self.ip}:{self.initial_port}").format(ip=self.ip, initial_port=self.initial_port)).pack(anchor=tk.W, pady=5)

        # 模式选择
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Label(mode_frame, text=get_string("block_mode_label", "屏蔽模式:")).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text=get_string("all_ports_mode", "全端口"), variable=self.mode, value="all_ports",
                        command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text=get_string("single_port_mode", "仅此端口"), variable=self.mode, value="single_port",
                        command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text=get_string("custom_port_mode", "自定义端口"), variable=self.mode, value="custom",
                        command=self.on_mode_change).pack(side=tk.LEFT, padx=5)

        # 自定义规则区域（始终显示）
        self.custom_frame = ttk.Frame(main_frame)
        self.custom_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(self.custom_frame, text=get_string("custom_rules_label", "自定义端口规则（每行一个规则）:")).pack(anchor=tk.W)

        # 文本框和滚动条
        text_frame = ttk.Frame(self.custom_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.rules_text = tk.Text(text_frame, height=8)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.rules_text.yview)
        self.rules_text.configure(yscrollcommand=scrollbar.set)

        self.rules_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入初始自定义规则
        if self.custom_rules:
            # 将逗号替换为换行符以便于阅读和编辑
            formatted_rules = self.custom_rules.replace(',', '\n')
            self.rules_text.insert('1.0', formatted_rules)

        # 示例说明
        example_frame = ttk.Frame(main_frame)
        example_frame.pack(fill=tk.X, pady=5)
        ttk.Label(example_frame, text=get_string("port_rules_example", "25565 (屏蔽25565端口) 25565-25569 (屏蔽25565到25569整个范围的端口) 最大值65535"),
                  font=(APP_FONT, 9), foreground="gray").pack(anchor=tk.W)

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

        # 初始模式显示
        self.on_mode_change()

    def on_mode_change(self):
        """根据选择的模式启用/禁用自定义规则输入框"""
        mode = self.mode.get()

        if mode == "custom":  # 改为英文比较
            # 自定义模式：启用输入框
            self.rules_text.config(state=tk.NORMAL)
        else:
            # 其他模式：禁用输入框
            self.rules_text.config(state=tk.DISABLED)

    def validate_port_rules(self, rules_text):
        """验证端口规则格式"""
        # 支持逗号和换行符分隔
        rules = []
        for part in rules_text.replace('\n', ',').split(','):
            part = part.strip()
            if part:
                rules.append(part)

        for rule in rules:
            if '-' in rule:
                # 端口范围验证
                parts = rule.split('-')
                if len(parts) != 2:
                    return False, get_string("invalid_port_range_format", f"无效的端口范围格式: {rule}").format(rule=rule)

                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    if not (1 <= start <= 65535 and 1 <= end <= 65535):
                        return False, get_string("port_range_out_of_bounds", f"端口范围超出有效范围: {rule}").format(rule=rule)
                    if start > end:
                        return False, get_string("port_range_start_greater", f"端口范围起始值大于结束值: {rule}").format(rule=rule)
                except ValueError:
                    return False, get_string("port_range_invalid_chars", f"端口范围包含非数字字符: {rule}").format(rule=rule)
            else:
                # 单个端口验证
                try:
                    port = int(rule)
                    if not (1 <= port <= 65535):
                        return False, get_string("port_out_of_bounds", f"端口号超出有效范围: {rule}").format(rule=rule)
                except ValueError:
                    return False, get_string("port_invalid_chars", f"端口号包含非数字字符: {rule}").format(rule=rule)

        return True, ""

    def save_config(self):
        """保存端口配置"""
        mode = self.mode.get()
        custom_rules = self.rules_text.get('1.0', tk.END).strip()

        # 将换行符替换为逗号
        custom_rules = custom_rules.replace('\n', ',')

        # 构建新的条目，包含模式信息
        if mode == "all_ports":
            # 全端口模式：保存IP、第一个端口和自定义规则（如果有）
            if custom_rules:
                new_entry = f"{self.ip}:{self.initial_port},{custom_rules},all_ports {self.server_name}"
            else:
                new_entry = f"{self.ip}:{self.initial_port},all_ports {self.server_name}"
        elif mode == "single_port":
            # 仅此端口模式：保存IP、第一个端口和自定义规则（如果有）
            if custom_rules:
                new_entry = f"{self.ip}:{self.initial_port},{custom_rules},single_port {self.server_name}"
            else:
                new_entry = f"{self.ip}:{self.initial_port},single_port {self.server_name}"
        else:
            # 自定义模式：获取并验证自定义规则
            if not custom_rules:
                messagebox.showerror(get_string("error_title", "错误"), get_string("custom_mode_requires_rules", "自定义模式需要至少一个端口规则"))
                return

            # 验证规则格式
            is_valid, error_msg = self.validate_port_rules(custom_rules)
            if not is_valid:
                messagebox.showerror(get_string("error_title", "错误"), error_msg)
                return

            # 使用原来的initial_port作为第一个端口，后面接新的自定义规则和模式
            new_entry = f"{self.ip}:{self.initial_port},{custom_rules},custom {self.server_name}"

        # 更新屏蔽列表文件
        self.update_blocked_file(new_entry)
        self.parent_dialog.refresh_list()
        # 保存后关闭窗口
        self.destroy()
        # 通知父窗口
        if self.parent_dialog:
            self.parent_dialog.on_port_config_close()

    def destroy(self):
        """重写destroy方法，确保正确清理"""
        if hasattr(self, 'parent_dialog') and self.parent_dialog:
            self.parent_dialog.port_config_dialog = None
        super().destroy()

    def update_blocked_file(self, new_entry):
        """更新屏蔽列表文件"""
        entries = []
        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                entries = [line.strip() for line in f.readlines() if line.strip()]

        # 移除旧条目（基于IP匹配）
        ip_to_remove = self.ip
        new_entries = []
        for entry in entries:
            entry_ip = entry.split(' ', 1)[0].split(':')[0]
            if entry_ip != ip_to_remove:
                new_entries.append(entry)

        # 添加新条目
        new_entries.append(new_entry)

        # 写回文件
        with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
            for entry in new_entries:
                f.write(entry + '\n')

        # 更新查询引擎的屏蔽列表
        if self.app.query_engine is not None:
            self.app.query_engine.blocked_ips = self.app.load_blocked_ips()