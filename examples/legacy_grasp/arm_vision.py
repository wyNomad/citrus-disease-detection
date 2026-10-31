import cv2
from ultralytics import YOLO
from pathlib import Path

# === 自动定位工程根目录 ===
# 注意：utils 在根目录下一级，所以也是 parents[1]
ROOT = Path(__file__).resolve().parents[1]


class GraspDetector:
    def __init__(self, model_path=None):
        """
        初始化视觉抓取类
        """
        if model_path is None:
            # 默认加载训练好的 best.pt
            self.model_path = ROOT / 'runs/train/citrus_experience/weights/best.pt'
        else:
            self.model_path = model_path

        print(f"🤖 [机械臂视觉] 正在加载模型: {self.model_path}")
        try:
            self.model = YOLO(str(self.model_path))
        except Exception as e:
            print(f"❌ 模型加载失败，请检查路径! \n{e}")

    def get_target_coordinate(self, image_path_or_frame):
        """
        核心功能：输入一张图，返回机械臂需要抓取的坐标
        :return: (found, target_info)
                 found: True/False 是否找到目标
                 target_info: 包含类别、中心坐标(x,y)、宽高的字典
        """
        # 1. 推理 (不保存图片，为了速度)
        results = self.model.predict(
            source=image_path_or_frame,
            save=False,
            conf=0.4,  # 机械臂要求高一点，只有很确定的才抓
            verbose=False  # 不在控制台刷屏
        )

        result = results[0]

        # 2. 如果没找到任何东西
        if len(result.boxes) == 0:
            return False, None

        # 3. 策略：只抓置信度最高的那一个 (Best One)
        # result.boxes 默认是按置信度排序的，所以取第一个就是最好的
        best_box = result.boxes[0]

        # 4. 提取数据
        cls_id = int(best_box.cls[0])
        class_name = self.model.names[cls_id]
        conf = float(best_box.conf[0])

        # xywh: 中心点x, 中心点y, 宽, 高 (像素单位)
        x_center, y_center, w, h = best_box.xywh[0].tolist()

        target_info = {
            "name": class_name,
            "confidence": conf,
            "x": round(x_center, 2),  # 保留2位小数
            "y": round(y_center, 2),
            "w": round(w, 2),
            "h": round(h, 2)
        }

        return True, target_info


# === 单元测试 (Unit Test) ===
# 只有直接运行这个文件时才会执行下面的代码
# 被其他文件 import 时不会执行
if __name__ == "__main__":
    print("🧪 正在测试机械臂视觉模块...")

    # 实例化
    detector = GraspDetector()

    # 随便找张图测试
    test_img = ROOT / 'datasets/citrus_mini/images/val'
    # 获取文件夹里第一张图的路径 (为了演示方便)
    first_img = next(test_img.glob('*.jpg'), None)

    if first_img:
        print(f"📸 测试图片: {first_img.name}")

        # 调用核心函数
        found, info = detector.get_target_coordinate(first_img)

        if found:
            print("\n✅ 发现抓取目标！")
            print(f"   🍎 种类: {info['name']}")
            print(f"   🎯 坐标: ({info['x']}, {info['y']})")
            print(f"   📏 尺寸: {info['w']} x {info['h']}")
            print("   🚀 [指令] 发送给串口: UART_SEND(x={0}, y={1})".format(info['x'], info['y']))
        else:
            print("⚠️ 未发现目标，机械臂待机。")
    else:
        print("❌ 测试目录下没有图片，无法测试。")