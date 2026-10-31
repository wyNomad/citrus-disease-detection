# 柑橘病害检测与 RGB-D 三维定位

上游准备数据、训练和导出模型；下游接入 **Orbbec Gemini 305（G40351-191）**，输出检测类别、像素位置和相机光学坐标系下的三维位置。

开发环境：Ubuntu 22.04 / ROS 2 Humble。目标设备：香橙派 5 Plus / RK3588 / Ubuntu 22.04 ARM64。
当前阶段完成仓库整合与软件检查；相机实测、定位精度、RK3588 NPU 适配与性能仍待验证。

```text
图片 + YOLO 标签 → 数据划分 → YOLO 微调 → 权重 / 模型导出
                                             ↓
Gemini 305 彩色图 → 公共检测接口 → 多目标检测消息
Gemini 305 对齐深度 + 彩色内参 ──→ 三维定位 → 目标坐标（米）
```

## 目录

| 目录 | 职责 |
| --- | --- |
| [src/citrus_vision](src/citrus_vision) | 共用推理接口、运行配置、深度采样和反投影 |
| [scripts](scripts) | 数据准备、训练、离线检测、导出与相机驱动准备入口 |
| [configs](configs) | 数据集、训练、运行模型和相机配置 |
| [ros2_ws/src](ros2_ws/src) | 消息、检测、三维定位和统一启动五个 ROS 包 |
| [dependencies](dependencies) | 相机驱动固定版本、补丁与来源说明 |
| [examples](examples) | 无硬件坐标计算示例和历史演示归档 |
| [tests](tests) | 几何、配置、数据划分、推理接口与合成 ROS 测试 |
| [weights](weights) / [data](data) | 本地模型和数据的存放约定，内容不入 Git |

## 快速开始：无相机开发

以下命令从仓库根目录执行。使用系统 Python 3.10，避免 Conda Python 与 ROS 二进制不匹配。

```bash
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade 'pip<26' 'setuptools>=68,<80' wheel
python -m pip install -e . -r requirements/laptop.txt -r requirements/dev.txt
python -m pytest -q
python examples/offline_localization.py
```

合成示例预期输出 `[0.1, 0.0, 1.0]` 米；这只验证数学计算，不代表相机精度。

准备 `weights/yolov8n.pt` 后，使用通用物体测试：

```bash
citrus-detect --config configs/runtime/generic.yaml --source /absolute/path/image.jpg --save-images
```

`runs/detect/detections.jsonl` 保存每帧检测结果，框和中心均为原图像素。程序不会自动下载缺失权重。

## 上游：准备数据、训练、导出

```bash
citrus-prepare-data --source data/raw/testA --output data/citrus_mini --sample 100 --seed 42
citrus-train --config configs/training/citrus.yaml
citrus-export --weights runs/train/citrus_experiment/weights/best.pt --format onnx
```

数据划分默认不删除或覆盖已有输出。训练产物目录会在同名任务存在时递增，查看命令最终输出定位 `best.pt`。
训练结束后，将目标权重复制为 `weights/citrus/best.pt`，通过 `citrus` 运行配置切换。类别 ID 的具体顺序见 [数据与模型](docs/DATA_AND_MODELS.md)。

## 下游：ROS 2

按 [环境安装](docs/SETUP.md) 准备依赖和驱动，然后构建：

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
python scripts/build_ros.py
source ros2_ws/install/setup.bash
ros2 launch citrus_bringup pipeline.launch.py profile:=generic weights_dir:="$PWD/weights"
```

业务话题：`/citrus/detections`、`/citrus/targets_3d`。光学坐标方向为 x 向右、y 向下、z 向前，单位米；无效深度的目标保留在结果中，`depth_valid=false` 且位置为 NaN。

没有相机时可执行 [合成 ROS 测试](docs/VALIDATION.md)。`start_camera:=false` 用于外部数据源或 rosbag，不会生成虚拟相机数据。

## 进一步阅读

- [环境与相机驱动安装](docs/SETUP.md)
- [运行与配置切换](docs/USAGE.md)
- [数据、类别和模型管理](docs/DATA_AND_MODELS.md)
- [训练流程](docs/TRAINING.md)
- [架构与消息约定](docs/ARCHITECTURE.md)
- [香橙派部署边界](docs/DEPLOYMENT.md)
- [验证状态与待办](docs/VALIDATION.md)
- [迁移记录](docs/MIGRATION.md) / [历史实验记录](docs/EXPERIMENTS.md)
- [协作约定](CONTRIBUTING.md)
