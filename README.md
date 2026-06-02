<h1 align="center">L4D2 Server OptiBrowser</h1>

<p align="center">
  <strong>L4D2SOB</strong> — L4D2 服务器浏览与管理桌面客户端
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.3.2.367-orange" alt="version" />
  <img src="https://img.shields.io/badge/platform-Windows-0078D6" alt="platform" />
  <img src="https://img.shields.io/badge/python-3.x-blue" alt="python" />
</p>

---

> **项目状态：已归档，不再维护**
>
> 这个项目是我为自己查 L4D2 服务器方便而写的工具，后来陆续加了不少功能。重心现在放到 ZSM 等其他项目，本项目已暂停维护，把代码开源出来，给有需要的朋友自行取用、修改。

---

## 这是什么

L4D2 Server OptiBrowser 是一个 Windows 桌面工具。你不用打开浏览器，就能快速浏览 L4D2 服务器状态、找到想玩的服、一键连接进游戏。

核心流程：**获取服务器列表 → 查询状态 → 筛选 → 一键进游戏**。

和网页版浏览器不同，这个工具让你可以：
- 离线管理自己收集的服务器列表（分组、收藏、历史）
- 多维度筛选（空房/有人/超时/自定义关键词）
- 按需屏蔽不想要的服务器（精确到端口级别）
- 浏览三方地图数据库，直接跳到工坊下载
- 解析 Steam 工坊合集链接，批量查看地图

---

## 功能一览

### 服务器浏览与查询

- **互联网（主页面）** — 从 Steam 主服务器或云端获取全球/区域服务器列表
- **A2S 实时查询** — 直接通过游戏协议查询服务器状态：在线状态、当前地图、玩家数/上限、VAC、游戏模式、延迟
- **四档查询速度** — 稳定/标准/快速/暴力，按需选择
- **自定义页面** — 创建多个页面对服务器分组管理，支持文件拖拽导入和手动输入
- **历史记录** — 自动记录通过客户端连接过的每一台服务器

### 筛选与屏蔽

- **快捷筛选** — 只看空房、只看有人房、隐藏超时服务器
- **关键词搜索** — 搜索服务器名称、地图、IP 等任意列
- **自定义规则** — 按关键词显示或隐藏匹配的服务器（如只显示"合作"模式的服）
- **屏蔽列表** — 屏蔽不想要的服务器，支持全端口/单端口/自定义端口范围三种模式
- **列排序** — 点击任意列头排序

### 地图模块

- **三方图列表** — 从云端 CSV 加载地图数据库，支持搜索、多列排序
- **地图详情** — 中文名、展示名、换图代码、文件识别名、浏览图
- **下载链接** — 直连地图下载地址，右键可复制、浏览器打开、跳转工坊解析
- **服务器关联** — 点击服务器详情中的地图名，可直接跳转到地图详情页

### 工坊链接解析

- 输入 Steam 工坊合集链接，批量获取所有物品的详情
- 显示物品名称、创建/更新时间、浏览图
- 支持批量复制工坊链接、下载链接、一键打开工坊页面

### 玩家信息统计

- 实时记录当前页面服务器的在线玩家
- 按在线时长排序，鼠标悬停查看该玩家出现在哪些服务器
- 双击玩家查看详情（名称、总在线时间、相关服务器列表）

### 仪表盘

- 服务器活跃度：显示"有玩家的服务器 / 在线服务器"的比例
- 玩家占用率：显示"当前在线玩家 / 总槽位"的比例
- 半圆仪表盘可视化，窗口自动跟随主窗口

### 连接与操作

- **一键加入** — 点击服务器详情中的"加入服务器"，通过 Steam 协议唤起游戏
- **自动加入** — 设置自动监控，服务器有空位时自动连接
- **复制连接命令** — 复制 `connect IP:端口` 命令，手动粘贴到游戏控制台
- **右键菜单** — 复制玩家名称、添加到自定义页面、屏蔽、复制整列数据

### 系统功能

- **中英双语** — 支持中文/English 切换
- **多主题** — 多种 ttkbootstrap 主题可选
- **窗口样式** — 支持浅色/深色等多种标题栏样式
- **字体设置** — 可选择系统任意字体
- **系统托盘** — 关闭时最小化到托盘
- **开机启动** — 可创建启动快捷方式，配合托盘功能隐藏启动
- **全局快捷键** — 录制快捷键，按下后自动解析剪贴板中的工坊链接
- **自动更新** — 启动时检测云端版本信息

---

## 技术栈

| 层级 | 技术 |
|:---|:---|
| 语言 | Python 3.x |
| GUI 框架 | Tkinter + ttkbootstrap |
| 窗口样式 | pywinstyles（标题栏） |
| 服务器查询 | python-a2s（A2S 协议）、Steam Master Server（UDP） |
| Steam API | ISteamRemoteStorage（工坊合集/物品详情） |
| 网络请求 | requests |
| 图像处理 | Pillow |
| 拖拽支持 | tkinterdnd2 |
| 系统托盘 | pystray |
| 全局热键 | keyboard |
| 开机启动 | pywin32 + winshell |
| 图标 | 内嵌 icon.ico / PIL 动态生成 |

---

## 项目结构

```
l4d2sob_start/
├── main.py                   # 入口：单实例检查、窗口创建
├── server_checker_app.py     # 主应用（UI 布局、页面管理、查询调度、配置读写）
├── async_server_query.py     # 异步 A2S 查询引擎（四档速度、屏蔽过滤、玩家查询）
├── settings_dialog.py        # 设置窗口（主题、字体、窗口样式、功能开关、快捷键录制）
├── dashboard.py              # 仪表盘面板（服务器/玩家占用率可视化）
├── player_info_window.py     # 玩家信息面板（在线时长统计、服务器关联）
├── filter_utils.py           # 筛选控件（空房/有人/超时/自定义关键词筛选）
├── blocked_list_dialog.py    # 屏蔽列表管理（全端口/单端口/自定义端口范围）
├── map_utils.py              # 三方图数据库浏览器（CSV 加载、列表、详情、图片预览）
├── workshop_utils.py         # 工坊解析器 UI（合集输入、结果展示、批量操作）
├── workshop_parser.py        # Steam Web API 集成（合集解析、物品详情、批量查询）
├── utils.py                  # 工具函数（Steam Master 查询、按钮工厂）
├── font_utils.py             # 字体配置（全局字体应用）
├── icon_utils.py             # 图标生成（放大镜、刷新图标等）
├── window_style_utils.py     # 窗口样式管理（pywinstyles 封装）
├── language_strings.py       # 国际化字符串（中文/English）
├── hotkey_manager.py         # 全局快捷键管理（录制、监听、触发）
├── startup_manager.py        # Windows 开机启动管理（快捷方式创建/删除）
├── about_dialog.py           # 关于对话框
├── images/                   # 按钮图标资源
│   ├── blocked.png
│   ├── dashboard.png
│   ├── history.png
│   ├── map.png
│   ├── player.png
│   ├── settings.png
│   └── steam.png
├── icon.ico                  # 应用程序图标
├── about.png                 # 关于页 Logo
├── servers.txt               # 服务器列表（可选）
├── blocked.txt               # 屏蔽列表（运行时生成）
└── server_checker_config.json # 用户配置文件（运行时生成）
```

---

## 运行

### 依赖安装

```bash
pip install -r requirements.txt
```

### 启动

```bash
python main.py
```

打包成 exe 的话，入口为 `main.py`，需要把 `images/`、`icon.ico`、`about.png`、`transparent_16x16.ico`、`transparent_1x1.png` 一起打包。推荐使用 [Nuitka](https://nuitka.net) 进行打包。

---

## 关于数据来源

- **服务器列表**：Steam Master Server（`hl2master.steampowered.com:27011`）或云端 CSV 文件
- **地图数据库**：云端 CSV 文件（数据来自 [腾讯文档 - 求生之路2第三方地图列表](https://docs.qq.com/sheet/DWkxueVpPb3FtUUha?tab=BB08J2)）
- **版本信息**：云端 CSV 文件
- **工坊数据**：Steam Web API

---

## 已知局限

- 仅支持 Windows（依赖 pywinstyles、pywin32 等 Windows 专属库）
- 查询速度依赖网络环境，暴力模式可能触发某些网络环境限制
- 三方图数据库依赖云端 CSV 更新，地图信息可能滞后
- Steam Web API 在国内网络环境下可能不稳定

---

## 相关链接

| 站点 | 地址 |
|:---|:---|
| 竹烨柠檬（主站） | [zhrradiant.com](https://zhrradiant.com) |
| 竹烨柠檬小世界 | [zhrradiant.cn](https://zhrradiant.cn) |
| 网页版服务器状态 | [l4d2srv.com](https://l4d2srv.com) |
| Zhrradiant SrvMap | [github.com/Zhrradiant/zhrradiant-srvmap](https://github.com/Zhrradiant/zhrradiant-srvmap) |

---

## 许可

本项目基于 MIT 协议开源，你可以自由使用、修改、分发。

项目已归档。如果你希望继续开发，可以 fork 本仓库。

如果你觉得这个工具曾经帮到过你，留个 Star 就行。
