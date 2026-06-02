import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import requests
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import webbrowser

from utils import create_outline_button
from window_style_utils import window_style_utils

from language_strings import load_language_from_config, get_string

load_language_from_config()


class WorkshopUtils:
    def __init__(self, root, style=None):
        self.root = root
        self.style = style
        self.workshop_images = {}
        self.workshop_win = None
        self.workshop_url_var = None  # 初始化变量
        self.workshop_tree = None
        self.workshop_status = None

        self.configure_workshop_styles()

        # 绑定主题变化事件
        if self.style:
            self._bind_theme_change()

    def _bind_theme_change(self):
        """绑定主题变化事件，在主题变化时重新配置工坊样式"""
        # 保存原始theme_use方法
        original_theme_use = self.style.theme_use

        def theme_use_wrapper(theme_name):
            result = original_theme_use(theme_name)
            # 主题变化后重新配置工坊样式
            self.configure_workshop_styles()
            return result

        # 替换theme_use方法
        self.style.theme_use = theme_use_wrapper

    def configure_workshop_styles(self):
        """配置工坊解析器样式"""
        if self.style:
            self.style.configure('Workshop.Treeview', rowheight=67, background='white')
        else:
            # 回退方案
            style = ttk.Style()
            style.configure('Workshop.Treeview', rowheight=67, background='white')

    def show_workshop_parser(self):
        """显示工坊解析窗口"""
        if self.workshop_win is None or not self.workshop_win.winfo_exists():
            self.workshop_win = tk.Toplevel(self.root)
            self.workshop_win.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"))
            self.workshop_win.title(get_string("workshop_parser_title", "工坊链接解析"))
            self.workshop_win.geometry("800x600")
            # 应用窗口样式
            window_style_utils.apply_window_style(self.workshop_win)

            input_frame = ttk.Frame(self.workshop_win)
            input_frame.pack(fill=tk.X, padx=10, pady=5)

            self.workshop_url_var = tk.StringVar()
            url_entry = ttk.Entry(input_frame, textvariable=self.workshop_url_var, width=50)
            url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            create_outline_button(
                input_frame,
                text=get_string("parse_button", "解析"),
                command=lambda: self.start_workshop_parse(self.workshop_win)
            ).pack(side=tk.LEFT, padx=5)

            tree_frame = ttk.Frame(self.workshop_win)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            self.workshop_tree = ttk.Treeview(
                tree_frame,
                columns=('title', 'created', 'updated', 'url'),
                show='tree headings',
                selectmode='extended',
                style="Workshop.Treeview",  # 应用样式
                height=6
            )
            self.workshop_tree.bind('<Double-Button-1>', self.on_workshop_tree_double_click)
            self.workshop_tree.bind('<Button-1>', self.on_workshop_tree_click)
            self.workshop_tree.bind('<Button-1>', self.on_tree_click, add=True)

            columns = [
                ('title', get_string("column_title", '物品名称')),
                ('created', get_string("column_created", '创建时间')),
                ('updated', get_string("column_updated", '更新时间')),
                ('url', get_string("column_url", '下载'))
            ]

            for col_id, col_text in columns:
                self.workshop_tree.heading(col_id, text=col_text)
                self.workshop_tree.column(col_id, width=120)

            self.workshop_tree.heading('#0', text=get_string("column_preview", '浏览图'))
            self.workshop_tree.column('#0', width=125, stretch=tk.NO, anchor=tk.CENTER)
            self.workshop_tree.column('title', width=210)
            self.workshop_tree.column('url', width=125, stretch=tk.NO, anchor=tk.CENTER)

            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.workshop_tree.yview)
            self.workshop_tree.configure(yscroll=scrollbar.set)

            self.workshop_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            def on_workshop_right_click(event):
                selected_items = self.workshop_tree.selection()
                if not selected_items:
                    return

                workshop_urls = []
                download_urls = []
                for item in selected_items:
                    tags = self.workshop_tree.item(item, 'tags')
                    download_url = tags[0]
                    workshop_url = tags[1]
                    workshop_urls.append(workshop_url)
                    download_urls.append(download_url)

                menu = tk.Menu(self.workshop_win, tearoff=0)
                menu.add_command(
                    label=get_string("copy_workshop_links", f"复制{len(selected_items)}个工坊链接").format(
                        count=len(selected_items)),
                    command=lambda: self.copy_to_clipboard('\n'.join(workshop_urls))
                )
                menu.add_command(
                    label=get_string("open_workshop_pages", f"打开{len(selected_items)}个工坊页面").format(
                        count=len(selected_items)),
                    command=lambda: [webbrowser.open(u) for u in workshop_urls]
                )
                menu.add_separator()
                menu.add_command(
                    label=get_string("copy_download_links", f"复制{len(selected_items)}个下载链接").format(
                        count=len(selected_items)),
                    command=lambda: self.copy_to_clipboard('\n'.join(download_urls))
                )
                menu.add_command(
                    label=get_string("open_download_pages", f"打开{len(selected_items)}个下载页面").format(
                        count=len(selected_items)),
                    command=lambda: [webbrowser.open(u) for u in download_urls if u]
                )
                menu.post(event.x_root, event.y_root)

            self.workshop_tree.bind("<Button-3>", on_workshop_right_click)

            link_frame = ttk.Frame(self.workshop_win)
            link_frame.pack(fill=tk.X, pady=5)

            # 配置网格布局（三列式结构）
            link_frame.columnconfigure(0, weight=0)  # 左侧内容固定宽度
            link_frame.columnconfigure(1, weight=1)  # 中间弹性空间
            link_frame.columnconfigure(2, weight=0)  # 右侧内容固定宽度

            # 提示信息容器（左对齐）
            left_container = ttk.Frame(link_frame)
            left_container.grid(row=0, column=0, sticky='w')

            # 静态文本部分
            ttk.Label(left_container, text=" ").pack(side=tk.LEFT)

            # 状态标签（右侧对齐）
            self.workshop_status = ttk.Label(link_frame, text=get_string("ready_status", "就绪"))
            self.workshop_status.grid(row=0, column=2, sticky=tk.E, padx=(0, 10))

            self.workshop_win.bind('<Escape>', lambda e: self.workshop_win.destroy())
        else:
            self.workshop_win.lift()
        return self.workshop_win

    def start_workshop_parse(self, window):
        """开始解析工坊内容"""
        from workshop_parser import get_workshop_items, get_item_details, get_multiple_item_details

        url = self.workshop_url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", get_string("input_workshop_url", "请输入Steam工坊合集链接"), parent=window)
            return

        self.workshop_tree.delete(*self.workshop_tree.get_children())
        self.workshop_status.config(text=get_string("parsing_collection", "正在解析链接..."))

        def parse_task():
            try:
                item_ids, error = get_workshop_items(url)
                if error:
                    window.after(0, lambda: messagebox.showerror("错误", error, parent=window))
                    return

                if not item_ids:
                    window.after(0, lambda: messagebox.showwarning("提示",
                                                                   get_string("no_items_found", "未找到任何工坊物品"),
                                                                   parent=window))
                    return

                window.after(0, lambda: [
                    self.workshop_tree.insert('', 'end', iid=item_id,
                                              values=(get_string("loading_image", "加载中..."),
                                                      get_string("loading_image", "加载中..."),
                                                      get_string("loading_image", "加载中..."),
                                                      get_string("loading_image", "加载中...")),
                                              tags=("",
                                                    f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}",
                                                    item_id))
                    for item_id in item_ids
                ])

                window.after(0, self.workshop_status.config, {
                    "text": get_string("found_items_loading", f"找到{len(item_ids)}个物品，正在获取详情...").format(
                        count=len(item_ids))})

                success_count = 0
                error_count = 0

                # 批量获取物品详情（优化性能）
                if len(item_ids) > 1:
                    details_list, batch_error = get_multiple_item_details(item_ids)
                    if details_list:
                        for details in details_list:
                            created = datetime.fromtimestamp(details["created"]).strftime('%Y-%m-%d %H:%M')
                            updated = datetime.fromtimestamp(details["updated"]).strftime('%Y-%m-%d %H:%M')
                            success_count += 1
                            window.after(0, self._update_workshop_item, details["item_id"], details, created, updated)

                    if batch_error:
                        error_count = len(item_ids) - success_count
                else:
                    # 单个物品处理
                    for item_id in item_ids:
                        details, err = get_item_details(item_id)
                        if err:
                            error_count += 1
                            continue

                        created = datetime.fromtimestamp(details["created"]).strftime('%Y-%m-%d %H:%M')
                        updated = datetime.fromtimestamp(details["updated"]).strftime('%Y-%m-%d %H:%M')

                        success_count += 1
                        window.after(0, self._update_workshop_item, item_id, details, created, updated)

                final_msg = []
                if success_count > 0:
                    final_msg.append(get_string("parse_complete_partial_1", f"成功解析 {success_count} 个").format(
                        success_count=success_count))
                if error_count > 0:
                    final_msg.append(get_string("parse_complete_partial_2", f"失败 {error_count} 个").format(
                        error_count=error_count))
                status_text = get_string("parse_complete_success", "解析完成，") + "，".join(final_msg)

                window.after(0, self.workshop_status.config, {"text": status_text})
                if error_count > 0:
                    window.after(0, lambda: messagebox.showwarning("部分失败",
                                                                   get_string("partial_failed",
                                                                              f"{error_count}个物品详情获取失败，请检查是否可以连接Steam网络").format(
                                                                       error_count=error_count), parent=window))

            except Exception as e:
                window.after(0, lambda: messagebox.showerror("错误",
                                                             get_string("parse_failed", f"解析失败: {str(e)}").format(
                                                                 error=str(e)), parent=window))

        threading.Thread(target=parse_task, daemon=True).start()

    def _update_workshop_item(self, item_id, details, created, updated):
        """更新工坊条目数据"""
        workshop_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"

        placeholder = self.create_placeholder_image()
        self.workshop_tree.item(
            item_id,
            image=placeholder,
            values=(
                details["title"],
                created,
                updated,
                get_string("click_to_download", "[点击此处下载]") if details["url"] else get_string("no_download", "无")
            ),
            tags=(
                details["url"],
                workshop_url,
                item_id
            )
        )

        if details["preview"]:
            self.load_preview_async(details["preview"], item_id)

    def create_placeholder_image(self):
        """创建灰色占位图"""
        img = Image.new('RGB', (100, 100), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((10, 45), get_string("loading_image", "加载中..."), fill=(200, 200, 200))
        return ImageTk.PhotoImage(img)

    def load_preview_async(self, url, item_id):
        """异步加载浏览图"""

        def download_task():
            try:
                response = requests.get(url, stream=True, verify=False, timeout=10)
                img = Image.open(response.raw)
                img.thumbnail((100, 100))

                self.root.after(0, self.update_tree_image, img, item_id)
            except Exception as e:
                print(f"图片加载失败: {str(e)}")

        threading.Thread(target=download_task, daemon=True).start()

    def update_tree_image(self, pil_image, item_id):
        """更新树状图图片"""
        photo = ImageTk.PhotoImage(pil_image)
        self.workshop_images[item_id] = photo
        self.workshop_tree.item(item_id, image=photo)

    def on_workshop_tree_double_click(self, event):
        """处理工坊列表的双击事件"""
        tree = event.widget
        item = tree.identify_row(event.y)
        column = tree.identify_column(event.x)

        if item and column in ('#1', '#2', '#3'):
            workshop_url = tree.item(item, 'tags')[1]
            webbrowser.open(workshop_url)
            return "break"

    def on_workshop_tree_click(self, event):
        """处理工坊解析列表的点击事件"""
        tree = event.widget
        column = tree.identify_column(event.x)
        item = tree.identify_row(event.y)

        if column == '#4' and item:
            tags = tree.item(item, 'tags')
            download_url = tags[0]

            if download_url:
                webbrowser.open(download_url)
                return "break"

    def on_tree_click(self, event):
        """处理树状图点击事件：点击空白处取消选中"""
        tree = event.widget
        item = tree.identify_row(event.y)
        if not item:
            tree.selection_remove(tree.selection())

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception as e:
            messagebox.showerror(get_string("copy_failed_workshop", "复制失败"), str(e))