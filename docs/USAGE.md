# 运行指南

[返回项目介绍](../README.md) · [数据与模型](DATA_AND_MODELS.md)

以下命令从仓库根目录运行。当前参数主要在脚本顶部或函数中设置，尚无统一的命令行参数入口。

## 1. 安装环境

使用虚拟环境安装 [requirements.txt](../requirements.txt)。训练脚本默认 `device='cpu'`、`workers=0`、`amp=False`；使用 GPU 时需先准备匹配的 PyTorch 环境，再调整训练参数。

依赖文件尚未锁定版本，因此它不是历史实验环境的完整复现清单。复现实验时应同时记录 Python、Ultralytics、PyTorch、CUDA（如使用）和 OpenCV 版本。

## 2. 准备与划分数据

原始数据目录由 [split_data.py](../split_data.py) 中的 `SOURCE_ROOT` 指定，默认结构：

```text
datasets/download_temp/testA/
├── images/
│   ├── example_001.jpg
│   └── example_002.jpg
└── labels/
    ├── example_001.txt
    └── example_002.txt
```

图片与标签使用相同文件名主干。脚本处理 jpg、jpeg、png、bmp 及大写后缀，跳过没有对应标签文件的图片；当前不会保留缺少标签文件的负样本。YOLO 标注格式见[数据说明](DATA_AND_MODELS.md)。

运行前核对：

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `SOURCE_ROOT` | `datasets/download_temp/testA` | 原始图片与标签目录 |
| `TARGET_ROOT` | `datasets/citrus_mini` | 划分后的专用输出目录 |
| `SAMPLE_NUM` | `100` | 图片数量超过上限时随机抽样；`None` 使用全量 |
| `TRAIN_RATIO` | `0.8` | 先随机划分为训练和验证部分，再跳过无标签图片 |
| `CLEAN_MODE` | `True` | 删除并重建目标目录 |

**`CLEAN_MODE=True` 会递归删除现有目标目录。目标目录应与原始数据目录分离，并只存放可重新生成的划分结果。**

```bash
python split_data.py
```

脚本没有固定随机种子；重复执行可能产生不同子集。由于无标签图片在划分后才被跳过，最终有效样本数与比例需以实际输出统计为准。进行对照实验时，应保存本次划分或记录文件清单。

## 3. 核对标签配置与模型

将预训练权重放到 `weights/yolo11n.pt`。在 [configs/custom_data.yaml](../configs/custom_data.yaml) 中，将 `path` 设置为实际派生数据根目录；推荐使用绝对路径，避免相对路径解析造成误读，例如：

```yaml
path: /absolute/path/to/citrus-disease-detection/datasets/citrus_mini
train: images/train
val: images/val
```

这段只示意路径字段，原文件中的完整 `names` 映射需要保留。检查标签 ID 为 0–14，且与配置中的顺序一致。

## 4. 训练

```bash
python scripts/train.py
```

[训练入口](../scripts/train.py)当前配置：

| 参数 | 默认值 |
| --- | --- |
| 预训练权重 | `weights/yolo11n.pt` |
| 训练轮数 | `10` |
| 输入尺寸 | `640` |
| 批大小 | `4` |
| 计算设备 | `cpu` |
| 数据加载进程 | `0` |
| 混合精度 | `False` |
| 输出项目 / 实验名 | `runs/train` / `citrus_experience` |

脚本要求预训练权重已存在，不会在文件缺失时继续训练。轻量配置用于实验流程调试，不能据此推断模型精度。

训练入口使用 `exist_ok=True` 复用实验目录。对比多次实验时，先修改 `name` 或保存已有产物，避免结果混杂。

## 5. 检测与像素坐标提取

训练结束后，默认检测入口读取：

```text
runs/train/citrus_experience/weights/best.pt
```

运行图片检测：

```bash
python scripts/detect.py
```

| 配置 | 默认值 |
| --- | --- |
| `MODEL_PATH` | 上述 `best.pt` |
| `SOURCE` | `datasets/citrus_mini/images/val` |
| `CONF` | `0.25` |
| `IOU` | `0.45` |
| 结果目录 | `runs/detect/visual_test` |

输出位置以实际运行打印的信息为准。当前检测入口以本地图片目录为默认输入；相机、视频等输入需结合实际环境调整，不能将默认入口视为已验证的在线采集方案。

[目标接口](../utils/arm_vision.py)的 `GraspDetector.get_target_coordinate(...)` 返回 `(found, target_info)`。成功时包含：

| 字段 | 内容 |
| --- | --- |
| `name`、`confidence` | 类别名称、置信度 |
| `x`、`y` | 检测框中心，像素 |
| `w`、`h` | 检测框宽高，像素 |

此接口置信度阈值为 `0.4`，取返回结果中的第一个检测框；未实现显式的业务类别筛选或抓取优先级策略。配置中的健康与病害类别均可能成为候选。

## 6. 可选应用演示

```bash
python main.py
```

该入口循环读取验证图片，判断目标像素中心是否接近 `(320, 320)`，容差为 20 像素。靶心采用固定值，并未随实际图片尺寸自动调整。

当判定居中时，函数仅打印模拟串口指令并延时；没有打开实际串口，也没有真实抓取反馈。它不属于核心训练和图片检测的必要步骤。

## 常见问题

| 现象 | 核对内容 |
| --- | --- |
| 找不到预训练模型 | `weights/yolo11n.pt` 是否已准备，名称是否与训练入口一致 |
| 数据目录不存在 | 核对 YAML 的 `path`、划分输出目录以及 train / val 子目录 |
| 有图片却没有训练样本 | 标签文件名是否配对、ID 是否正确、是否被脚本跳过 |
| 找不到 `best.pt` | 是否完成训练、是否修改了实验名，以及检测脚本的权重路径 |
| 抓取演示无法读取图片 | 验证目录是否有 jpg 图片，或直接修改 `test_img_path` |
| 多次实验结果混在一起 | 为训练和检测设置不同的实验名，单独保存结果和配置 |
