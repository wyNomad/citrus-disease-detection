import os
from pathlib import Path
from ultralytics import YOLO

# === 1. 自动定位工程根目录 (不要改) ===
# 这样无论你把项目拷到哪里，代码都能找到 weights 和 configs
ROOT = Path(__file__).resolve().parents[1]


def train_model():
    # === 2. 模型选择区 (可调整) ===
    # 想要换模型？改这里的文件名即可 (如 yolov8n.pt, yolo11s.pt)
    # 确保文件已经下载在 weights 文件夹里
    model_name = 'yolo11n.pt'
    model_path = ROOT / 'weights' / model_name

    # 配置文件路径 (一般不用动)
    config_path = ROOT / 'configs' / 'custom_data.yaml'

    # 🛡️ 防呆检查：防止文件名写错
    if not model_path.exists():
        print(f"❌ 找不到模型: {model_path}")
        return

    print(f"🔥 加载模型: {model_name}")
    print(f"📍 配置文件: {config_path}")

    # 加载预训练模型
    model = YOLO(str(model_path))

    # === 3. 训练参数配置区 (核心调整区！) ===
    print("🚀 开始训练 (10轮)...")

    model.train(
        # --- 基础配置 ---
        data=str(config_path),  # 数据集配置文件路径
        project=str(ROOT / 'runs/train'),  # 结果存哪里
        name='citrus_experience',  # ⭐ [可调] 本次训练任务的名字 (会生成 runs/train/citrus_experience)
        exist_ok=True,  # True=覆盖同名结果，False=自动新建文件夹(exp1, exp2...)

        # --- 训练强度 ---
        epochs=10,  # ⭐ [可调] 训练轮数。
        # 调试/体验流程用 10-20；
        # 正式训练想出效果，建议 50-100甚至300。

        pretrained=True,  # ⭐ [可调] 是否加载预训练权重。
        # True = 站在巨人肩膀上学 (推荐，收敛快)
        # False = 从零开始瞎猜 (不推荐，除非数据极其庞大)

        # --- 硬件性能相关 (CPU党慎重) ---
        imgsz=640,  # ⭐ [可调] 输入图片大小。640是标准；320速度快但在小目标上变瞎；1280精度高但慢。
        device='cpu',  # ⭐ [可调] 'cpu' 或 '0' (如果有显卡)。你目前必须用 'cpu'。
        workers=0,  # ⚠️ [Windows必填] 必须为0，否则多进程报错。Linux可设为 4 或 8。
        batch=4,  # ⭐ [可调] 一次塞多少张图。
        # CPU 或 显存小：设 2, 4, 8。
        # 显卡强：设 16, 32, 64 (越大越稳)。

        # --- 进阶技巧 ---
        amp=False,  # ⚠️ [CPU建议关闭] 混合精度训练。CPU上开启有时会报错或变慢，关掉最稳。
        plots=True,  # 训练结束自动画出混淆矩阵、P-R曲线等图表

        # augment=True, # (可选) 是否开启强力数据增强(马赛克/旋转等)，默认就是True
        # lr0=0.01,     # (可选) 初始学习率。如果发现Loss不下降，可以改小点试试
    )

    print("✅ 训练结束！快去 runs/train/citrus_experience 看看生成了什么！")


if __name__ == '__main__':
    train_model()