import os
from pathlib import Path
from ultralytics import YOLO

# === 自动定位工程根目录 ===
ROOT = Path(__file__).resolve().parents[1]


def run_pure_detection():
    # ==========================
    # 🎛️ 参数微调区 (在这里修改配置)
    # ==========================

    # 1. 模型路径
    #    平时测试用训练好的 best.pt
    #    如果想对比官方效果，改用 'weights/yolo11n.pt'
    MODEL_PATH = ROOT / 'runs/train/citrus_experience/weights/best.pt'

    # 2. 测试目标
    #    可以是文件夹、单张图片路径，或者 '0' (开启电脑摄像头)
    SOURCE = ROOT / 'datasets/citrus_mini/images/val'

    # 3. 阈值设置
    #    conf: 置信度 (0.0 - 1.0)，低于这个分数的框不显示
    #    iou:  重叠去重阈值，如果一个物体被框了好几次，调大这个值
    CONF = 0.25
    IOU = 0.45

    # ==========================
    # 🚀 执行检测
    # ==========================
    if not os.path.exists(MODEL_PATH) and str(SOURCE) != '0':
        print(f"❌ 错误: 找不到模型文件 {MODEL_PATH}")
        return

    print(f"🔮 加载模型: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))

    print(f"🖼️ 正在检测: {SOURCE}")

    # 纯粹的检测，保存结果图
    results = model.predict(
        source=str(SOURCE),
        conf=CONF,
        iou=IOU,
        save=True,  # 必须为True，不然看不到图
        project=str(ROOT / 'runs/detect'),  # 结果保存路径
        name='visual_test',  # 结果文件夹名
        exist_ok=True  # 允许覆盖
    )

    print(f"\n✅ 检测完成！快去打开图片看看效果吧：")
    print(f"📂 {results[0].save_dir}")


if __name__ == "__main__":
    run_pure_detection()