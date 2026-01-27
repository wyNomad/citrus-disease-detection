import time
import cv2
from pathlib import Path
from utils.arm_vision import GraspDetector


# === 模拟串口通信函数 (未来你要替换成真实的 serial 代码) ===
def send_cmd_to_arduino(x, y):
    """
    模拟向单片机(STM32/Arduino)发送坐标指令
    """
    # 真实场景可能是: ser.write(f"G:{x},{y}\n".encode())
    print(f"📡 [串口发送] 目标锁定! 请求抓取 -> X:{x}, Y:{y}")
    # 模拟机械臂运动需要时间
    time.sleep(1)
    print("✅ [串口接收] 抓取动作完成，准备复位...")


def main():
    print("🚀 系统初始化中...")

    # 1. 实例化视觉大脑
    # 它会自动加载 weights/best.pt (或者你指定的模型)
    detector = GraspDetector()

    # 2. 准备图像源
    # 方案 A: 使用 USB 摄像头 (推荐)
    # cap = cv2.VideoCapture(0)

    # 方案 B: 使用本地图片循环模拟 (测试用)
    # 我们这里为了演示，先用一张本地图片假装是摄像头画面
    test_img_path = "datasets/citrus_mini/images/val/image_1.jpg"  # 请确保这张图存在，或者改个存在的名字
    if not Path(test_img_path).exists():
        # 如果找不到指定图片，就自动找文件夹里第一张
        test_dir = Path("datasets/citrus_mini/images/val")
        test_img_path = str(next(test_dir.glob("*.jpg"), ""))

    print("🟢 主循环开始 (按 Ctrl+C 退出)...")

    try:
        while True:
            # === 第一步：获取画面 ===
            # 如果是摄像头: ret, frame = cap.read()
            # 如果是模拟: 读取本地图片
            frame = cv2.imread(test_img_path)

            if frame is None:
                print("❌ 无法读取图像，请检查路径或摄像头")
                break

            # === 第二步：调用视觉模块进行分析 ===
            # 直接把图片传给我们在 utils 里写的函数
            found, target_info = detector.get_target_coordinate(frame)

            # === 第三步：根据结果做决策 ===
            if found:
                print(f"\n👀 发现 {target_info['name']} (置信度: {target_info['confidence']:.2f})")

                # 获取坐标
                tx = target_info['x']
                ty = target_info['y']

                # 判断是否在“可抓取区域” (简单的逻辑示例)
                # 假设画面中心是 (320, 320)，如果不居中就调整车体，居中就抓
                if abs(tx - 320) < 20 and abs(ty - 320) < 20:
                    print("🎯 目标已对准中心，执行抓取！")
                    send_cmd_to_arduino(tx, ty)
                    # 抓完可能需要休息一下，或者等下一轮
                    time.sleep(2)
                else:
                    print(f"⚠️ 目标偏差，正在调整云台/底盘... (当前: {tx}, {ty})")
                    # 这里可以发送调整指令，比如 send_adjust_cmd(tx)

            else:
                print(".", end="", flush=True)  # 没目标时打印点点点，表示在巡逻

            # 模拟循环延时，防止刷屏太快
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n🛑 程序已手动停止")
    finally:
        # cap.release() # 如果用了摄像头记得释放
        print("👋 系统关闭")


if __name__ == "__main__":
    main()