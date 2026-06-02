import tkinter as tk
from tkinter import ttk
from tkinter import Toplevel
import webbrowser
from PIL import Image, ImageTk
import os

from utils import create_outline_button
from window_style_utils import window_style_utils
from language_strings import get_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class AboutDialog(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(get_string("about", "关于"))
        self.geometry("350x260")
        self.resizable(False, False)
        # 应用窗口样式
        window_style_utils.apply_window_style(self)

        self.icon_path = os.path.join(BASE_DIR, "icon.ico")
        self.about_img_path = os.path.join(BASE_DIR, "about.png")

        try:
            self.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"图标加载错误: {str(e)}")

        # 创建主容器
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)

        # 配置网格权重使内容垂直居中
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=0)  # 图片行
        container.grid_rowconfigure(2, weight=0)  # 文本行1
        container.grid_rowconfigure(3, weight=0)  # 文本行2
        container.grid_rowconfigure(4, weight=0)  # 链接行1
        container.grid_rowconfigure(5, weight=0)  # 链接行2
        container.grid_rowconfigure(6, weight=0)  # 链接行3
        container.grid_rowconfigure(7, weight=1)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=0)
        container.grid_columnconfigure(2, weight=1)

        # 图片居中
        try:
            img = Image.open(self.about_img_path).resize((80, 80))
            self.logo = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(container, image=self.logo)
            logo_label.grid(row=1, column=1, pady=(0, 10))
        except Exception as e:
            print(f"图片加载错误: {str(e)}")

        # 文本内容 - 修改为居中并支持换行
        text_content = [
            get_string("author", "作者：竹烨oО柠檬茶 / Zhrradiant LemonTea"),
            get_string("message", "留言：免费工具，方便自己查服，希望也能帮到你 :)")
        ]

        for i, text in enumerate(text_content):
            # 创建支持换行的标签
            label = ttk.Label(
                container,
                text=text,
                wraplength=300,  # 设置换行宽度
                justify='center'  # 文本居中
            )
            label.grid(row=2 + i, column=1, sticky='', pady=2)

        # 链接 - 修改为居中
        link_config = [
            ("zhrradiant.com", "//zhrradiant.com"),
            ("space.bilibili.com/10698756", "https://space.bilibili.com/10698756"),
            ("steamcommunity.com/profiles/76561198109766088", "https://steamcommunity.com/profiles/76561198109766088")
        ]

        for i, (text, url) in enumerate(link_config):
            lbl = ttk.Label(
                container,
                text=text,
                foreground="blue",
                cursor="hand2",
                wraplength=400,  # 链接也支持换行
                justify='center'  # 链接文本居中
            )
            lbl.grid(row=4 + i, column=1, sticky='', pady=2)
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))