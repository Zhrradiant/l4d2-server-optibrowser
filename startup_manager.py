import os
import sys
import winshell
from win32com.client import Dispatch
import pythoncom

class StartupManager:
    def __init__(self, app_name="L4D2 Server OptiBrowser"):
        self.app_name = app_name
        self.shortcut_name = f"{app_name}.lnk"
        self.startup_folder = self.get_startup_folder()

    def get_startup_folder(self):
        """获取Windows启动文件夹路径"""
        try:
            return winshell.startup()
        except Exception as e:
            print(f"获取启动文件夹失败: {e}")
            # 备用方案：使用常见的启动文件夹路径
            user_profile = os.environ.get('USERPROFILE', '')
            if user_profile:
                return os.path.join(user_profile, 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu',
                                    'Programs', 'Startup')
            return None

    def get_target_path(self):
        """获取应用程序的目标路径"""
        # 如果是打包后的exe文件
        if getattr(sys, 'frozen', False):
            return sys.executable
        # 如果是Python脚本
        else:
            # 返回主脚本的路径
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_checker_app.py")
            python_exe = sys.executable
            return f'"{python_exe}" "{main_script}"'

    def create_shortcut(self, minimized=False):
        """创建启动快捷方式"""
        try:
            if not self.startup_folder:
                print("无法确定启动文件夹路径")
                return False

            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
            actual_dir = os.path.dirname(sys.executable)

            # 初始化COM
            pythoncom.CoInitialize()

            # 创建快捷方式
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)

            # 设置目标路径和起始位置
            shortcut.Targetpath = sys.executable
            shortcut.WorkingDirectory = actual_dir

            # 设置参数
            arguments = ""
            if minimized:
                arguments = "--minimized"

            shortcut.Arguments = arguments
            shortcut.IconLocation = self.get_icon_path()
            shortcut.save()

            print(f"开机启动快捷方式创建成功: {shortcut_path}")
            print(f"目标: {sys.executable} {arguments}")
            print(f"起始位置: {actual_dir}")
            return True

        except Exception as e:
            print(f"创建开机启动快捷方式失败: {e}")
            return False
        finally:
            # 清理COM
            try:
                pythoncom.CoUninitialize()
            except:
                pass

    def get_icon_path(self):
        """获取图标路径"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            return icon_path

        # 如果找不到图标文件，使用默认图标
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return os.path.join(os.path.dirname(sys.executable), "DLLs", "py.ico")

    def remove_shortcut(self):
        """删除启动快捷方式"""
        try:
            if not self.startup_folder:
                return False

            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                print(f"开机启动快捷方式已删除: {shortcut_path}")
                return True
            else:
                print("开机启动快捷方式不存在")
                return True

        except Exception as e:
            print(f"删除开机启动快捷方式失败: {e}")
            return False

    def shortcut_exists(self):
        """检查快捷方式是否存在"""
        try:
            if not self.startup_folder:
                return False

            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
            return os.path.exists(shortcut_path)

        except Exception as e:
            print(f"检查开机启动快捷方式失败: {e}")
            return False

    def update_shortcut(self, minimized=False):
        """更新现有的启动快捷方式参数"""
        try:
            if not self.shortcut_exists():
                print("快捷方式不存在，无需更新")
                return True

            shortcut_path = os.path.join(self.startup_folder, self.shortcut_name)
            actual_dir = os.path.dirname(sys.executable)

            # 初始化COM
            pythoncom.CoInitialize()

            # 重新创建快捷方式
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.WorkingDirectory = actual_dir

            # 设置参数
            arguments = ""
            if minimized:
                arguments = "--minimized"

            shortcut.Arguments = arguments
            shortcut.IconLocation = self.get_icon_path()
            shortcut.save()

            print(f"开机启动快捷方式更新成功: {shortcut_path} (minimized: {minimized})")
            return True

        except Exception as e:
            print(f"更新开机启动快捷方式失败: {e}")
            return False
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass


# 单例实例
_startup_manager = None


def get_startup_manager():
    """获取StartupManager单例实例"""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = StartupManager()
    return _startup_manager