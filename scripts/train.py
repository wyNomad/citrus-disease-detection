import os
from pathlib import Path
from ultralytics import YOLO

# === 1. 动态计算路径 (核心修复) ===
# 获取当前脚本文件的绝对路径
FILE = Path(__file__).resolve()
# 获取项目根目录 (即 scripts 文件夹的上一级)
# parents[0] 是 scripts, parents[1] 是 Yolo_Version_Project
ROOT = FILE.parents[1]


def train_model():
    # 使用 join 拼接出绝对路径，彻底解决找不到文件的问题
    # 相当于: "D:/.../Yolo_Version_Project/weights/yolo11n.pt"
    model_path = ROOT / 'weights' / 'yolo11n.pt'
    config_path = ROOT / 'configs' / 'custom_data.yaml'

    # 打印出来给你看一眼，让你放心
    print(f"📍 项目根目录定位: {ROOT}")
    print(f"🔍 寻找模型路径: {model_path}")

    # 🛡️ 检查文件是否存在
    if not model_path.exists():
        print(f"❌ 严重错误！在 {model_path} 依然找不到模型。")
        print("请检查：1. 文件名是不是 yolo11n.pt.pt (Windows隐藏后缀坑)？")
        print("        2. weights 文件夹是不是真的在根目录下？")
        return

    print("✅ 成功定位模型文件！")

    # 加载模型 (注意要转成 str 字符串格式传给 YOLO)
    model = YOLO(str(model_path))

    # === 2. 开始训练 ===
    print("🔥 开始训练 (CPU模式)...")
    model.train(
        data=str(config_path),  # 配置文件也要用绝对路径，防止找不到
        epochs=10,
        imgsz=640,
        device='cpu',
        workers=0,
        batch=4,
        project=str(ROOT / 'runs/train'),  # 结果保存路径也指定好
        name='citrus_cpu_exp',
        exist_ok=True,
        amp=False,
        plots=True
    )

    print("✅ 训练流程结束！")


if __name__ == '__main__':
    train_model()