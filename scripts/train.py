from ultralytics import YOLO


def train_model():
    # 1. 加载模型
    # 建议先用 yolo11n.pt (最新版 Nano)，如果报错找不到文件，改回 yolov8n.pt
    # 确保 weights/yolo11n.pt 存在，不存在会自动下载
    print("🚀 正在加载模型...")
    model = YOLO('weights/yolo11n.pt')

    # 2. 开始训练 (CPU 专用参数配置)
    print("🔥 开始训练 (CPU模式)...")
    results = model.train(
        data='configs/custom_data.yaml',  # 指定刚才写的配置文件
        epochs=10,  # CPU 跑 10 轮意思一下，验证流程通不通
        imgsz=640,  # 标准图像大小
        device='cpu',  # 强制使用 CPU
        workers=0,  # Windows 用户必选！防止 DataLoader 蓝屏或报错
        batch=4,  # 批次大小，CPU 建议 4 或 8，太大跑不动
        project='runs/train',  # 结果保存路径
        name='citrus_cpu_exp',  # 本次实验的名字
        exist_ok=True,  # 允许覆盖同名实验
        amp=False  # 关闭混合精度 (CPU 上有时候开启反而慢或报错)
    )

    print("✅ 训练结束！去 runs/train/citrus_cpu_exp 查看结果吧！")


if __name__ == '__main__':
    train_model()