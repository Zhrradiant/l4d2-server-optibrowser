import csv
import os

import requests
from io import StringIO
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import time
import webbrowser

from utils import create_outline_button
from workshop_utils import WorkshopUtils
from window_style_utils import window_style_utils
from font_utils import APP_FONT

from language_strings import load_language_from_config, get_string
load_language_from_config()


class MapUtils:
    def __init__(self, root, workshop_utils=None):
        self.root = root
        self.map_data = None
        self.map_win = None
        self.load_map_data_on_startup()
        # 使用传入的 workshop_utils 实例，而不是创建新的
        self.workshop_utils = workshop_utils or WorkshopUtils(root)

    def load_map_data_on_startup(self):
        """应用启动时后台加载地图数据"""

        def load_task():
            try:
                csv_url = "https://zhrradiant-l4d2.cn-nb1.rains3.com/%E6%B1%82%E7%94%9F%E4%B9%8B%E8%B7%AF2-%E7%AC%AC%E4%B8%89%E6%96%B9%E5%9C%B0%E5%9B%BE%E5%88%97%E8%A1%A8-L4D2SOB.csv"
                response = requests.get(csv_url)
                response.encoding = 'utf-8-sig'

                csv_data = StringIO(response.text)
                reader = csv.DictReader(csv_data, skipinitialspace=True)
                valid_data = []
                for item in reader:
                    if any('>>>' in value or '<<<<<' in value for value in item.values()):
                        continue
                    cn_name = item.get('中文名 (仅参考)', '').strip() or item.get('中文名(仅参考)', '')
                    display = item.get('地图大厅展示名', '').strip()
                    code = item.get('换图代码 (按章节顺序)', '').strip()
                    image_url = item.get('浏览图', '') or item.get('浏览图 ', '')
                    if any([cn_name, display, code]):
                        valid_data.append({
                            '中文名 (仅参考)': cn_name,
                            '地图大厅展示名': display,
                            '地图文件识别名': item.get('地图文件识别名', ''),
                            '换图代码 (按章节顺序)': code,
                            '地图下载链接 (仅参考)': item.get('地图下载链接 (仅参考)', ''),
                            '浏览图': image_url
                        })
                self.map_data = valid_data
            except Exception as e:
                print(f"地图数据加载失败")

        threading.Thread(target=load_task, daemon=True).start()

    def show_map_list(self):
        """显示地图列表窗口（单例模式）"""
        if self.map_win and self.map_win.winfo_exists():
            self.map_win.lift()
            return

        self.map_win = tk.Toplevel(self.root)
        map_win = self.map_win
        map_win.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"))
        self.map_win.title(get_string("map_list_title", "第三方地图列表"))
        self.map_win.geometry("800x600")
        # 应用窗口样式
        window_style_utils.apply_window_style(self.map_win)

        self.map_win.protocol("WM_DELETE_WINDOW", self.on_map_win_close)

        filter_frame = ttk.Frame(map_win)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        self.map_filter_var = tk.StringVar()
        map_filter_entry = ttk.Entry(filter_frame, textvariable=self.map_filter_var)
        map_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        map_filter_entry.bind('<KeyRelease>', self.apply_map_filter)

        create_outline_button(filter_frame, text="×", width=3,
                   command=self.clear_map_filter).pack(side=tk.RIGHT)

        main_paned = ttk.PanedWindow(map_win, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(main_paned)
        main_paned.add(tree_frame, weight=95)

        self.map_tree = ttk.Treeview(tree_frame, columns=('name_cn', 'display_name', 'map_code'),
                                     show='headings', selectmode='extended')
        self.map_tree.bind('<Button-1>', self.on_tree_click)

        columns = [
            ('name_cn', get_string("column_chinese_name", '中文名 (仅参考)')),
            ('display_name', get_string("column_display_name", '地图大厅展示名')),
            ('map_code', get_string("column_map_code", '换图代码 (按章节顺序)'))
        ]
        for col_id, col_text in columns:
            self.map_tree.heading(col_id, text=col_text,
                                  command=lambda c=col_id: self.sort_map_column(self.map_tree, c))
            self.map_tree.column(col_id, width=200)

        self.map_tree_items = []
        if self.map_data:
            for item in self.map_data:
                cn = item.get('中文名 (仅参考)', '未知名称').strip()
                disp = item.get('地图大厅展示名', '-').strip()
                code = item.get('换图代码 (按章节顺序)', '-').strip()
                item_id = self.map_tree.insert('', 'end', values=(cn, disp, code))
                self.map_tree_items.append(item_id)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.map_tree.yview)
        self.map_tree.configure(yscroll=scrollbar.set)

        self.map_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        note_frame = ttk.Frame(main_paned)
        main_paned.add(note_frame, weight=2)

        link_frame = ttk.Frame(note_frame)
        link_frame.pack(pady=10)

        ttk.Label(link_frame, text="数据来源：", foreground="#808080").pack(side=tk.LEFT)

        link_label = ttk.Label(
            link_frame,
            text="求生之路2-第三方地图列表-L4D2SOB",
            foreground="#00008B",
            cursor="hand2"
        )
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>",
                        lambda e: webbrowser.open("https://docs.qq.com/sheet/DWkxueVpPb3FtUUha?tab=BB08J2"))

        map_win.bind('<Escape>', lambda e: self.on_map_win_close())
        self.map_tree.bind('<Double-1>', self.show_map_details)

    def on_map_win_close(self):
        """处理地图窗口关闭事件"""
        if self.map_win:
            self.map_win.destroy()
            self.map_win = None

    def show_map_details(self, event=None, map_info=None):
        """显示选中地图的详细信息"""
        if map_info is None:
            tree = event.widget
            selected = tree.selection()
            if not selected:
                return

            selected_item = selected[0]
            map_code = tree.item(selected_item, 'values')[2]
            code_list = [c.strip() for c in map_code.replace('，', ',').split(',')]

            for code in code_list:
                for item in self.map_data:
                    codes = item.get('换图代码 (按章节顺序)', '')
                    if not codes:
                        continue
                    item_codes = [c.strip() for c in codes.replace('，', ',').split(',')]
                    if code in item_codes:
                        map_info = item
                        break
                if map_info:
                    break
            else:
                return

        detail_win = tk.Toplevel(self.root)
        detail_win.title(get_string("map_details_title", "地图详情"))
        detail_win.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"))
        detail_win.geometry("800x600")
        # 应用窗口样式
        window_style_utils.apply_window_style(detail_win)

        main_paned = ttk.PanedWindow(detail_win, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        img_frame = ttk.Frame(main_paned)
        main_paned.add(img_frame) # 原weight=40无效，此处还会导致只从放大镜按钮首次进入该窗口后画布区域占总窗口空间过大

        image_url = map_info.get('浏览图', '')
        if image_url:
            self.load_map_image_async(image_url, img_frame)
        else:
            ttk.Label(img_frame, text=get_string("no_map_preview", "该地图暂无浏览图"), foreground="gray").pack(expand=True)

        info_frame = ttk.Frame(main_paned)
        main_paned.add(info_frame) # 原weight=60无效，有无没影响，配合上面一起删除

        main_container = ttk.Frame(info_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 定义原始列名（与map_info字典中的键一致）
        original_columns = [
            '中文名 (仅参考)',
            '地图大厅展示名',
            '地图文件识别名',
            '换图代码 (按章节顺序)'
        ]

        # 定义显示列名（国际化后的）
        display_columns = (
            get_string("column_chinese_name", '中文名 (仅参考)'),
            get_string("column_display_name", '地图大厅展示名'),
            get_string("column_map_identifier", '地图文件识别名'),
            get_string("column_map_code", '换图代码 (按章节顺序)')
        )

        main_tree = ttk.Treeview(
            main_container,
            columns=display_columns,
            show='headings',
            height=2
        )
        main_tree.bind('<Button-1>', self.on_tree_click)

        for col in display_columns:
            main_tree.heading(col, text=col)
            main_tree.column(col, width=150, anchor=tk.W)

        # 使用原始列名从map_info获取值
        main_values = [map_info.get(col, '') for col in original_columns]
        main_tree.insert('', 'end', values=main_values)

        def on_main_tree_right_click(event):
            item = main_tree.identify_row(event.y)
            col = main_tree.identify_column(event.x)
            if not item:
                return

            col_index = int(col[1:]) - 1
            col_name = display_columns[col_index]
            menu = tk.Menu(detail_win, tearoff=0)
            menu.add_command(
                label=get_string("copy_col_name", f"复制 {col_name}").format(col_name=col_name),
                command=lambda: self.copy_to_clipboard(main_values[col_index])
            )
            menu.post(event.x_root, event.y_root)

        main_tree.bind("<Button-3>", on_main_tree_right_click)

        download_frame = ttk.Frame(main_container)
        download_tree = ttk.Treeview(
            download_frame,
            columns=('download',),
            show='headings',
            height=4
        )
        download_tree.bind('<Button-1>', self.on_tree_click)
        download_tree.heading('download', text=get_string("column_download_link", '地图下载链接 (仅参考)'))
        download_tree.column('download', width=600, anchor=tk.W)

        download_url = map_info.get('地图下载链接 (仅参考)', '')
        links = [link.strip() for link in download_url.split(',') if link.strip()]
        for link in links:
            download_tree.insert('', 'end', values=(link,))

        def on_download_tree_right_click(event):
            item = download_tree.identify_row(event.y)
            if not item:
                return

            full_url = download_tree.item(item, 'values')[0]
            menu = tk.Menu(detail_win, tearoff=0)
            menu.add_command(
                label=get_string("copy_link", "复制链接"),
                command=lambda: self.copy_to_clipboard(full_url)
            )
            if full_url.startswith(('http://', 'https://')):
                menu.add_command(
                    label=get_string("open_in_browser", "浏览器打开"),
                    command=lambda: webbrowser.open(full_url)
                )
                if self.is_workshop_link(full_url):
                    menu.add_command(
                        label=get_string("parse_workshop_link", "解析工坊链接"),
                        command=lambda: self.open_workshop_parser(full_url)
                    )
            menu.tk_popup(event.x_root, event.y_root)

        download_tree.bind("<Button-3>", on_download_tree_right_click)

        main_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        download_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        download_tree.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_container,
                  text=get_string("download_link_note", "注：下载链接仅供参考，能否成功联机需以服务器端的实际版本为准"),
                  foreground="gray").pack(pady=5)

        detail_win.bind('<Escape>', lambda e: detail_win.destroy())

    def is_workshop_link(self, url):
        """判断是否为Steam工坊链接（支持sharedfiles和workshop两种路径）"""
        return any(
            path in url
            for path in (
                'steamcommunity.com/sharedfiles/filedetails',
                'steamcommunity.com/workshop/filedetails'
            )
        )

    def open_workshop_parser(self, url):
        """打开工坊解析窗口并填入指定链接"""
        # 确保使用正确的 workshop_utils 实例
        if self.workshop_utils:
            self.workshop_utils.show_workshop_parser()
            self.workshop_utils.workshop_url_var.set(url)

            # 自动开始解析
            if (hasattr(self.workshop_utils, 'workshop_win') and
                    self.workshop_utils.workshop_win and
                    self.workshop_utils.workshop_win.winfo_exists()):
                self.workshop_utils.start_workshop_parse(self.workshop_utils.workshop_win)

    def check_map_exists(self, map_name):
        """检查地图是否存在数据"""
        if not self.map_data:
            return False

        if '[' in map_name:
            clean_name = map_name.split('[')[0].strip()
            match_mode = "chinese"
        else:
            clean_name = map_name.split()[0].strip()
            match_mode = "code"

        for item in self.map_data:
            if match_mode == "chinese":
                # 中文名匹配 - 只处理 " / " 分隔符
                cn_names = item.get('中文名 (仅参考)', '')
                possible_names = [n.strip() for n in cn_names.split(' / ') if n.strip()]
                if any(clean_name == name for name in possible_names):
                    return True

                # 地图大厅展示名匹配 - 只处理 " / " 分隔符
                display_names = item.get('地图大厅展示名', '')
                possible_display_names = [n.strip() for n in display_names.split(' / ') if n.strip()]
                if any(clean_name == name for name in possible_display_names):
                    return True

            # 换图代码匹配（两种模式都适用）
            codes = item.get('换图代码 (按章节顺序)', '')
            if codes:
                code_list = [c.strip() for c in codes.replace('，', ',').split(',')]
                if clean_name in code_list:
                    return True
        return False

    def check_map_detail(self, map_name, parent_window):
        """检查并显示匹配的地图详情"""
        if not self.map_data:
            return

        # 导入语言设置相关
        from language_strings import CURRENT_LANGUAGE

        original_name = map_name
        if '[' in map_name:
            clean_name = map_name.split('[')[0].strip()
            match_mode = "display" if CURRENT_LANGUAGE == "English" else "chinese"
        else:
            clean_name = map_name.split()[0].strip()
            match_mode = "code"

        if match_mode == "chinese":
            # 中文名匹配 - 只处理 " / " 分隔符
            for item in self.map_data:
                cn_names = item.get('中文名 (仅参考)', '')
                possible_names = [n.strip() for n in cn_names.split(' / ') if n.strip()]
                if any(clean_name == name for name in possible_names):
                    self.show_map_details(map_info=item)
                    return
        elif match_mode == "display":
            # 地图大厅展示名匹配 - 只处理 " / " 分隔符
            for item in self.map_data:
                display_names = item.get('地图大厅展示名', '')
                possible_display_names = [n.strip() for n in display_names.split(' / ') if n.strip()]
                if any(clean_name == name for name in possible_display_names):
                    self.show_map_details(map_info=item)
                    return

        # 最后尝试换图代码匹配（两种模式都适用）
        for item in self.map_data:
            codes = item.get('换图代码 (按章节顺序)', '')
            if not codes:
                continue

            code_list = [c.strip() for c in codes.replace('，', ',').split(',')]
            if original_name in code_list:
                self.show_map_details(map_info=item)
                return

            if clean_name in code_list:
                self.show_map_details(map_info=item)
                return

    def load_map_image_async(self, image_url, parent_frame):
        """异步加载地图浏览图"""
        canvas = tk.Canvas(parent_frame, bg='#282828')
        canvas.pack(fill=tk.BOTH, expand=True)

        loading_label = ttk.Label(canvas, text=get_string("image_loading", "图片加载中..."),
                                  background='#282828', foreground='white')
        loading_id = canvas.create_window(0, 0, window=loading_label, anchor='center')

        def adjust_loading_position(event):
            canvas.coords(loading_id, event.width // 2, event.height // 2)

        canvas.bind("<Configure>", adjust_loading_position)

        def load_task():
            try:
                from io import BytesIO
                response = requests.get(image_url, timeout=10)
                img = Image.open(BytesIO(response.content))

                self.root.after(0, lambda: self._setup_scalable_image(canvas, img, loading_id))
            except Exception as e:
                canvas.unbind("<Configure>")
                self.root.after(0, self._show_image_error, canvas, loading_id)

        threading.Thread(target=load_task, daemon=True).start()

    def _setup_scalable_image(self, canvas, original_img, loading_id):
        """配置可缩放图片"""
        try:
            canvas.delete(loading_id)
        except tk.TclError:
            return

        canvas.original_img = original_img
        canvas.current_photo = None

        def on_configure(event):
            if hasattr(canvas, 'last_resize') and (time.time() - canvas.last_resize) < 0.05:
                return
            canvas.last_resize = time.time()

            if canvas.current_photo:
                canvas.delete("scaled_image")

            img_width, img_height = canvas.original_img.size
            canvas_width = event.width
            canvas_height = event.height

            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))

            resized_img = canvas.original_img.resize(new_size, Image.Resampling.LANCZOS)
            canvas.current_photo = ImageTk.PhotoImage(resized_img)

            x = canvas_width // 2
            y = canvas_height // 2
            canvas.create_image(x, y, image=canvas.current_photo, anchor=tk.CENTER, tags="scaled_image")

        canvas.bind("<Configure>", on_configure)
        canvas.event_generate("<Configure>", width=canvas.winfo_width(), height=canvas.winfo_height())

    def _show_image_error(self, canvas, loading_id):
        """显示错误信息"""
        canvas.delete(loading_id)
        canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2,
                           text=get_string("image_load_failed", "图片加载失败"), fill="white", font=(APP_FONT, 12))

    def sort_map_column(self, tree, column, reverse=False):
        """处理地图列表的列排序，中文按拼音首字母排序并放在最后"""
        items = [(tree.set(child, column), child) for child in tree.get_children('')]

        try:
            if column == 'map_code':
                items.sort(
                    key=lambda x: (self._map_code_key(x[0]), x[0].lower()),
                    reverse=reverse
                )
            else:
                # 根据首字符类型分离项目
                chinese_first_items = []
                non_chinese_first_items = []

                for value, child in items:
                    if not value:  # 空字符串
                        non_chinese_first_items.append((value, child))
                        continue

                    first_char = value[0]
                    # 判断首字符是否为中文
                    if '\u4e00' <= first_char <= '\u9fff':
                        chinese_first_items.append((value, child))
                    else:
                        non_chinese_first_items.append((value, child))

                # 对非中文首字符项按原逻辑排序
                non_chinese_first_items.sort(
                    key=lambda x: x[0].lower(),
                    reverse=reverse
                )

                # 对中文首字符项按拼音排序
                try:
                    import pypinyin
                    chinese_first_items.sort(
                        key=lambda x: ''.join(pypinyin.lazy_pinyin(x[0])).lower() if x[0] else '',
                        reverse=reverse
                    )
                except ImportError:
                    # 如果没有pypinyin库，则按原逻辑排序
                    chinese_first_items.sort(
                        key=lambda x: x[0].lower(),
                        reverse=reverse
                    )

                # 合并结果（中文首字符的放在最后）
                if reverse:
                    items = chinese_first_items + non_chinese_first_items
                else:
                    items = non_chinese_first_items + chinese_first_items

        except TypeError:
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)

        for index, (_, child) in enumerate(items):
            tree.move(child, '', index)

        tree.heading(column, command=lambda: self.sort_map_column(tree, column, not reverse))

    def _map_code_key(self, code):
        """生成安全的地图代码排序键"""
        parts = []
        current_number = ''
        current_str = ''

        for c in code:
            if c.isdigit():
                if current_str:
                    parts.append((1, current_str.lower()))
                    current_str = ''
                current_number += c
            else:
                if current_number:
                    parts.append((0, int(current_number)))
                    current_number = ''
                current_str += c

        if current_number:
            parts.append((0, int(current_number)))
        if current_str:
            parts.append((1, current_str.lower()))

        return tuple(parts)

    def apply_map_filter(self, event=None):
        """应用地图列表筛选"""
        keyword = self.map_filter_var.get().lower()
        tree = self.map_tree

        for item_id in self.map_tree_items:
            try:
                tree.reattach(item_id, '', 'end')
            except tk.TclError:
                pass

        if keyword:
            for item_id in self.map_tree_items:
                values = [str(v).lower() for v in tree.item(item_id, 'values')]
                if not any(keyword in v for v in values):
                    tree.detach(item_id)

    def clear_map_filter(self):
        """清除地图列表筛选"""
        self.map_filter_var.set('')
        self.apply_map_filter()

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
            messagebox.showerror(get_string("copy_failed", "复制失败"), str(e))