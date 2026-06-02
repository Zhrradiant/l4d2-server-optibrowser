from PIL import Image, ImageDraw, ImageTk
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class IconUtils:
    @staticmethod
    def create_transparent_icon():
        """使用transparent_1x1.png作为透明图标"""
        try:
            icon_path = os.path.join(BASE_DIR, "transparent_1x1.png")
            img = Image.open(icon_path)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"加载透明图标失败: {str(e)}")
            # 备用方案：生成1x1透明图标
            img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            return ImageTk.PhotoImage(img)

    @staticmethod
    def create_magnifier_icon():
        """创建放大镜图标"""
        try:
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            draw.ellipse(
                xy=(5, 5, 25, 25),
                outline='black',
                width=3
            )

            draw.line(
                xy=(20, 20, 30, 30),
                fill='black',
                width=3,
                joint="curve"
            )

            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"图标创建失败: {str(e)}")
            return None

    @staticmethod
    def create_refresh_icon():
        """创建刷新图标（与放大镜风格一致）"""
        try:
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 绘制4分之3圆环（270度）
            draw.arc(
                xy=(5, 5, 27, 27),  # 稍微扩大一点让箭头有空间
                start=0,    # 从顶部开始
                end=270,    # 绘制270度（4分之3圆）
                fill='black',
                width=3
            )

            # 在圆环末端绘制箭头（顶部）
            arrow_size = 4
            # 箭头指向右侧（刷新图标通常箭头在顶部指向右侧）
            arrow_points = [
                (24, 6),           # 箭头尖
                (20, 6 - arrow_size),  # 上点
                (20, 6 + arrow_size)   # 下点
            ]
            draw.polygon(arrow_points, fill='black')

            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"刷新图标创建失败: {str(e)}")
            return None