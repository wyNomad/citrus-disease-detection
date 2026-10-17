# 数据与模型

[返回项目介绍](../README.md) · [运行指南](USAGE.md)

## 仓库内外的资源

| 资源 | 当前情况 |
| --- | --- |
| 数据处理、训练、检测源码 | 已包含 |
| 标签类别配置 | [configs/custom_data.yaml](../configs/custom_data.yaml)，15 类 |
| 原始图片与标注 | 未包含；原始来源、版本和样本数量尚未在仓库记录 |
| 预训练权重 | 需另行准备 `weights/yolo11n.pt`，参考 [YOLO11 官方说明](https://docs.ultralytics.com/models/yolo11/) |
| 柑橘检测权重 | 训练生成 `runs/train/citrus_experience/weights/best.pt`，当前未附带 |
| 效果图与评估产物 | 当前未附带，可按[实验记录说明](EXPERIMENTS.md)补充 |

数据、模型权重和训练输出默认由 `.gitignore` 排除。准备本地资源后才能运行训练与检测入口。

## 数据格式

数据采用 YOLO 检测标注：每张图片对应同名 txt 文件，每行一个目标，字段为 `class_id x_center y_center width height`；框中心与宽高归一化到 0–1，类别编号从 0 开始。详细定义见 [Ultralytics 检测数据格式](https://docs.ultralytics.com/datasets/detect/)。

`split_data.py` 当前要求图片有对应标签文件；未提供标签文件的图片会被跳过。

划分后的预期目录：

```text
datasets/citrus_mini/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

YAML 中 `path` 指向 `citrus_mini`，`train` 和 `val` 字段指向其下的图片目录。使用本机绝对路径可避免把历史相对路径当成已验证配置。

## 类别映射

下表保留当前配置的原始类别字符串；这些标签同时包含健康样本、病害及缺素症状，不能将它们统称为 15 种病害。

| 标签 ID | 配置中的名称 |
| --- | --- |
| 0 | S0 others |
| 1 | S1 Healthy fruit |
| 2 | S2 Healthy leaf |
| 3 | S3 Blotchy mottling |
| 4 | S4 Red nose fruit |
| 5 | S5 Zinc deficiency |
| 6 | S6 Vein yellowing |
| 7 | S7 Uniform yellowing |
| 8 | S8 Magnesium deficiency |
| 9 | S9 Boron deficiency |
| 10 | S10 Anthracnose |
| 11 | S11 Citrus greasy spot |
| 12 | S14 Canker |
| 13 | S13 Sooty mould |
| 14 | S12 Algal spot |

数字标签 ID 是训练匹配依据。名称前缀 S12 / S14 与 ID 顺序并不一致，不要仅根据前缀重排配置；如需调整类别，应同时转换全部标签并重新核对模型。

## 数据与权重的后续补充

补充实验材料时，记录数据来源链接、版本、授权、图片与标注数量、类别分布及训练/验证划分。发布训练权重时，附上对应代码版本、类别配置、训练参数和评估结果。

图片、标注、预训练权重与依赖库各自的授权说明分别适用；当前仓库不代替原始资源的分发入口。
