# 数据与模型

大文件不进入普通 Git 历史。数据位于 `data/`，预训练及部署权重位于 `weights/`，训练输出位于 `runs/`；需要单独复制或通过受控存储获取。

## 数据格式

原始数据应包含 `images/<name>.jpg` 和对应 `labels/<name>.txt`。标签使用 YOLO 检测格式：`class_id cx cy width height`，坐标归一化。
划分工具只选图片/标签配对，固定 seed 可复现，并写入 `split_manifest.json`。空标签文件可作为背景样本。
文件重名但扩展名不同会导致标签覆盖，因此工具拒绝重复 stem。输出存在时拒绝执行，不再默认删除旧数据。

数据配置为 `configs/datasets/citrus.yaml`。其中 `path` 相对该 YAML 文件；训练入口解析为绝对路径后生成运行用副本，避免 Ultralytics 全局 datasets_dir 影响位置解析。

## 数据来源

训练与评估使用公开发布的柑橘黄龙病田间症状图像数据集，采集、分类与标注由福建省农业科学院完成。

| 项目 | 内容 |
| --- | --- |
| 名称 | 柑橘黄龙病田间症状识别图像数据集 |
| 数据作者 | 池美香、陈韶萍、黄婷、陈世雄、梁勇、邱荣洲 |
| 数据机构 | 福建省农业科学院植物保护研究所、数字农业研究所 |
| 数据 DOI | [10.57760/sciencedb.j00001.00947](https://doi.org/10.57760/sciencedb.j00001.00947) |
| 关联论文 | 池美香等. 柑橘黄龙病田间症状识别图像数据集[J]. 中国科学数据, 2025, 10(1). DOI 10.11922/11-6035.csd.2023.0161.zh |
| 采集范围 | 2018–2021 年，福建省 12 个柑橘园，8 个柑橘品种 |
| 规模 | 9896 张图片；训练 7192、验证 898、测试 1806 |
| 标注 | 植保专家标注的水果与叶片边界框，YOLO txt 格式 |
| 图像规格 | 长边统一缩至 640 像素 |

数据集按症状分为 A–E 五个大类，并按采集条件提供 testA、testB、testC 三个互不重叠的测试集：

| 分组 | 语义 | 症状类别 |
| --- | --- | --- |
| A | 健康样本 | S1、S2 |
| B | 典型黄龙病特征 | S3、S4 |
| C | 疑似黄龙病特征 | S5、S6、S7 |
| D | 黄龙病相近特征 | S8、S9、S10、S11、S12 |
| E | 黄龙病不相关特征 | S13、S14 |

源数据集已发布基于 YOLOv5l 训练的 `HLB_ABC`、`HLB_ABCD`、`HLB_ABCDE` 三个模型，对应三种类别组合，可作为横向对比的基线。

## 组装可训练数据集

源数据按 `<分组>-<划分>/<Sx>/images` 与 `/labels` 组织，与 Ultralytics 需要的扁平结构不同。`citrus-build-groups` 按实验分组横向合并、纵向归入 train/val，并同时装配独立测试集：

```bash
citrus-build-groups --source /path/to/raw --output data \
    --test testA --test testB --test testC
```

输出 `data/lab_abc`、`data/lab_abcd`、`data/lab_abcde` 与 `data/lab_test{A,B,C}`，各自带 `data.yaml`；文件默认以符号链接接入，加 `--copy` 改为复制。类别 ID 沿用源数据集 `label_object.json` 的原始编号，不做重映射，以便与官方权重处于同一标签空间、可直接对比。对应配置位于 `configs/datasets/lab_*.yaml`。

实验矩阵与运行方式见 [实验设计](EXPERIMENTS.md)，矩阵配置位于 `configs/experiments/lab.yaml`。

## 病害数据集 15 类映射

| ID | 名称 |
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

标签 ID 与训练数据保持一致，尤其 ID 12/14 不按名称数字重新排序。推理类别名默认来自模型内元数据；更换数据集时同时管理标签与权重。

ID 0（`S0 others`）是源数据集预留的背景类，在全库 12115 个标注框中出现次数为 0。保留该占位是为了与源数据集及官方权重保持同一标签空间；训练与评估均可正常运行，指标表按实际出现的类别输出。

## 权重约定

- `weights/yolo11n.pt`：训练用预训练权重，需要提前准备。
- `weights/yolov8n.pt`：通用目标验证模型，可使用旧本地工程已有文件。
- `weights/citrus/best.pt`：训练完成后选定的业务模型。
- `weights/legacy/HLB_*.pt`：本地历史权重保留区，架构、标签和兼容性待核对，不默认加载。

每个正式发布模型应附架构、类别映射、训练代码提交、数据版本、输入尺寸、验证指标、权重 SHA-256 与部署后端版本。
`citrus-val` 保存独立评估指标、参数、数据快照及被评估模型的 SHA-256；`citrus-export` 为 ONNX 生成同名 `.onnx.json`，记录类别、请求的导出参数及来源/产物校验值。二者辅助追踪模型，代码版本和数据版本仍需在实验记录中补齐。
下游通过 `configs/runtime` 指定选定权重及推理参数；模型说明文件用于核对，不会自动修改运行配置。完整流程见 [模型开发指南](TRAINING.md)。
`.pt`、ONNX 和 RKNN 是不同运行产物；`.pt` 扩展名不能证明模型家族和兼容性。只加载来源可信的权重。
