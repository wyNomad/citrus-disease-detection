# 数据与模型

大文件不进入普通 Git 历史。数据位于 `data/`，预训练及部署权重位于 `weights/`，训练输出位于 `runs/`；需要单独复制或通过受控存储获取。

## 数据格式

原始数据应包含 `images/<name>.jpg` 和对应 `labels/<name>.txt`。标签使用 YOLO 检测格式：`class_id cx cy width height`，坐标归一化。
划分工具只选图片/标签配对，固定 seed 可复现，并写入 `split_manifest.json`。空标签文件可作为背景样本。
文件重名但扩展名不同会导致标签覆盖，因此工具拒绝重复 stem。输出存在时拒绝执行，不再默认删除旧数据。

数据配置为 `configs/datasets/citrus.yaml`。其中 `path` 相对该 YAML 文件；训练入口解析为绝对路径后生成运行用副本，避免 Ultralytics 全局 datasets_dir 影响位置解析。

## 原始 15 类映射

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

保留原仓库顺序，尤其 ID 12/14 不按名称数字重新排序。推理类别名默认来自模型内元数据；更换数据集时同时管理标签与权重。

## 权重约定

- `weights/yolo11n.pt`：训练用预训练权重，原仓库未附带。
- `weights/yolov8n.pt`：通用目标验证模型，可使用旧本地工程已有文件。
- `weights/citrus/best.pt`：训练完成后选定的业务模型。
- `weights/legacy/HLB_*.pt`：本地历史权重保留区，架构、标签和兼容性待核对，不默认加载。

每个正式发布模型应附架构、类别映射、训练代码提交、数据版本、输入尺寸、验证指标、权重 SHA-256 与部署后端版本。
`.pt`、ONNX 和 RKNN 是不同运行产物；`.pt` 扩展名不能证明模型家族和兼容性。只加载来源可信的权重。
