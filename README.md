<div align="center">

<img src="assets/project-header.svg" width="100%" alt="Citrus Disease Detection · 柑橘病害检测" />

**基于 YOLO11 的柑橘果实与叶片病害检测实验项目**

数据准备 · 模型微调 · 目标检测 · 像素坐标提取

[运行指南](docs/USAGE.md) · [数据与模型](docs/DATA_AND_MODELS.md) · [实验记录](docs/EXPERIMENTS.md)

</div>

## 项目介绍

本项目面向柑橘果实与叶片图像，使用 Ultralytics YOLO11 开展目标检测实验，包含数据抽样与划分、模型训练、检测结果保存，以及目标像素位置提取。

当前标签配置共 **15 类**，涵盖健康果实、健康叶片、病害及缺素症状。训练脚本默认使用 YOLO11n 和 CPU 小规模训练配置，便于先验证数据与训练流程，再根据实验需求调整。

*A YOLO11-based experimental project for citrus disease detection, covering dataset preparation, training, inference and pixel-coordinate extraction.*

## 功能与目录

| 入口 | 内容 |
| --- | --- |
| [split_data.py](split_data.py) | 配对图片与 YOLO 标签，抽样并划分训练集、验证集 |
| [configs/custom_data.yaml](configs/custom_data.yaml) | 数据路径与 15 类标签映射 |
| [scripts/train.py](scripts/train.py) | 使用预训练 YOLO11n 微调，输出训练产物 |
| [scripts/detect.py](scripts/detect.py) | 加载训练权重进行图片检测，保存标注结果 |
| [utils/arm_vision.py](utils/arm_vision.py) | 封装检测接口，返回目标类别、置信度与像素框 |
| [main.py](main.py) | 用本地图片演示目标对准判断与模拟抓取流程 |

核心检测流程：

```text
图片 + YOLO 标签
    → 抽样与训练/验证划分
    → YOLO11n 微调
    → 加载 best.pt 检测
    → 类别、置信度、检测框与像素中心
```

`main.py` 是基于检测结果的应用演示，默认循环读取本地验证图片。相机采集代码尚为注释，串口发送和抓取完成通过打印、延时模拟。

## 环境与快速开始

需要 Python 3。Python 依赖见 [requirements.txt](requirements.txt)；PyTorch 的安装方式需与所用 CPU / GPU 环境匹配。

```bash
git clone https://github.com/wyNomad/citrus-disease-detection.git
cd citrus-disease-detection

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

仓库未附带数据集与权重。先按[数据与模型说明](docs/DATA_AND_MODELS.md)准备标注数据和 `weights/yolo11n.pt`，再依照[运行指南](docs/USAGE.md)核对路径与参数。

从仓库根目录执行：

```bash
# 数据划分：先核对 SOURCE_ROOT、TARGET_ROOT 和 CLEAN_MODE
python split_data.py

# 使用 configs/custom_data.yaml 训练
python scripts/train.py

# 使用训练得到的 best.pt 检测
python scripts/detect.py
```

**数据划分脚本默认 `CLEAN_MODE=True`，会删除并重建 `TARGET_ROOT`；请将它设为专用的派生数据目录。** 脚本路径、输出位置和运行顺序见运行指南。

## 当前实现与实验状态

| 项目 | 当前情况 |
| --- | --- |
| 数据准备 | 配对复制、最多抽样 100 张、默认 80% / 20% 划分 |
| 模型训练 | YOLO11n；默认 10 epochs、640 输入、batch 4、CPU |
| 推理输出 | 检测框与类别结果图；目标接口返回像素中心和宽高 |
| 应用扩展 | 本地图片上的对准判断与模拟抓取 |
| 数据与权重 | 需另行准备，当前不随代码分发 |
| 实验效果 | 尚未提供可核对的数据规模、mAP、速度或效果图 |

当前没有相机标定、三维定位或真实机械臂控制接口。模拟动作不能视为已完成硬件联调。

项目的实际检测效果需结合数据来源、划分方式、模型权重和评估结果判断；[实验记录](docs/EXPERIMENTS.md)列出了补充结果时需要保留的信息。

## 数据类别

完整类别名称与 ID 见[标签说明](docs/DATA_AND_MODELS.md#类别映射)。其中 ID `12` 对应 `S14 Canker`，ID `14` 对应 `S12 Algal spot`，应以标签文件的数值 ID 为准，不能仅按名称中的编号重排。

## 开发与反馈

运行问题可以通过 [Issue](https://github.com/wyNomad/citrus-disease-detection/issues) 提交，附上运行入口、错误信息、依赖版本与所用配置。仓库提供运行问题和实验记录模板。

## 参考与许可证

- [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/)
- [YOLO 检测数据格式](https://docs.ultralytics.com/datasets/detect/)

仓库根目录暂未指定统一许可证；Ultralytics、数据集和预训练权重分别遵循其原有授权说明。
