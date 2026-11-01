# 模型开发：从数据到下游调用

上游沿用 Ultralytics YOLO 检测框架，覆盖数据准备、训练调参、独立评估、离线检测、模型导出，再把选定模型交给 Gemini 305 检测定位通路。
仓库提供 15 类病害标签配置；真实数据、初始化权重与业务精度需要另行准备和评估。以下命令从仓库根目录执行。

## 1. 准备数据与环境

```bash
python -m pip install -e . -r requirements/train.txt
citrus-prepare-data --source data/raw/testA --output data/citrus_mini --sample 100 --seed 42
```

原始目录包含 `images/` 和对应的 YOLO `labels/`。工具配对、抽样和划分数据，保存 `split_manifest.json`，拒绝覆盖已有输出。默认抽样 100 对，完整数据使用 `--sample 0`。

`configs/datasets/citrus.yaml` 设置数据根目录、train/val 子目录及类别。当前入口使用图片目录形式的 split；`path` 相对数据 YAML，运行时解析为绝对路径。独立评估还可选择 `test`，需在 YAML 中定义相应目录。标签 ID 和模型类别顺序必须一致，见 [数据与模型](DATA_AND_MODELS.md)。

## 2. 训练与调参

先准备 `weights/yolo11n.pt`，训练入口不会自动下载缺失的初始化权重。

```bash
citrus-train --config configs/training/citrus.yaml
citrus-train --config configs/training/citrus.yaml --epochs 50 --batch 8 --imgsz 640 --workers 4 --device 0 --name citrus_e50
```

第二条命令仅适用于确有可用 GPU 的环境；笔记本 CPU 可使用 `--device cpu --batch 1 --workers 0`。默认的小规模参数用于流程检查。

| 参数层次 | 设置位置 | 示例 |
| --- | --- | --- |
| 初始化模型、数据与实验默认值 | `configs/training/citrus.yaml` | `model`、`data`、`epochs`、`batch`、`imgsz`、`device`、`seed` |
| 常用的本次调整 | `citrus-train` 参数 | `--epochs`、`--batch`、`--imgsz`、`--workers`、`--device`、`--name` |
| 优化器、学习率、增强等高级参数 | 训练 YAML 中增加 YOLO 支持的字段 | `optimizer: AdamW`、`lr0: 0.001`、`patience: 30`、`mosaic: 0.5` |

命令行覆盖同名 YAML 参数，仅影响本次任务，不改写配置。其他训练字段交给安装的 Ultralytics 版本校验和执行。`batch: -1` 表示由训练器自动选择，是否适用取决于设备。

训练 YAML 的 `model` 相对 `--weights-dir`（默认 `weights`），`data` 相对训练 YAML 所在目录。`--project` 默认 `runs/train`，相对当前目录。
默认同名实验目录自动递增，实际路径会打印。训练器保存 `weights/best.pt`、`last.pt`、`args.yaml`、`results.csv` 以及相应评估/绘图产物（受参数控制）。
每次任务还保存独立的 `configs/train-<唯一标识>/{dataset.yaml,training.yaml}`；实际训练目录中的 `training_config.yaml` 引用该快照，后续实验不会覆盖它，失败任务也保留配置。

## 3. 独立评估候选模型

训练内置的验证之外，可对选定 checkpoint 单独评估，便于比较实验或更换验证集：

```bash
citrus-val --weights runs/train/citrus_experiment/weights/best.pt --data configs/datasets/citrus.yaml --output runs/val/citrus-001 --imgsz 640 --device cpu --plots
```

也可执行 `python scripts/validate.py`，参数相同。`--split` 支持 `train`、`val`、`test`，默认 `val`；还支持 `--batch` 和 `--workers`。输出目录必须是新目录，模型与数据集类别 ID/名称不一致时拒绝评估。

输出包括 `metrics.json`（Precision、Recall、mAP 等训练器返回指标）、`validation_config.yaml`（模型路径、SHA-256、数据来源与本次参数）、`dataset.yaml`（解析后的数据快照）。`--plots` 启用训练器的评估图表。
评估用于确认模型效果，不能用在训练集上的结果代替独立验证集或测试集成绩。

## 4. 离线检测与推理参数调整

```bash
citrus-detect --config configs/runtime/citrus.yaml --model "$PWD/runs/train/citrus_experiment/weights/best.pt" --source data/citrus_mini/images/val --conf 0.3 --iou 0.45 --imgsz 640 --device cpu --output runs/detect/citrus-001 --save-images
```

离线工具与 ROS 检测节点共用推理接口。命令行的 `--model`、`--conf`、`--iou`、`--imgsz`、`--device`、`--classes` 可临时覆盖运行配置；`--classes` 后填完整类别名，空参数列表表示清除过滤。
配置文件不被改写。结果为 `detections.jsonl` 和可选标注图；单张彩色图只输出 2D 检测，三维位置需要相机深度和内参。
调好后把相应参数写入 `configs/runtime/citrus.yaml` 的 `model` 字段，供 ROS 使用。离线 `--conf` 对应 `confidence`，`--imgsz` 对应 `image_size`，`--classes` 对应 `target_classes`。

## 5. 导出与模型说明文件

```bash
python -m pip install -r requirements/export.txt
citrus-export --weights runs/train/citrus_experiment/weights/best.pt --format onnx --imgsz 640 --opset 17
```

ONNX 导出默认关闭额外简化。可用 `--dynamic` 请求动态输入；`--opset` 和 `--dynamic` 仅适用于 ONNX。ONNX 依赖限制在 `>=1.16,<1.19`，保持 NumPy 1.x 与 ROS 环境兼容。
导出器通常把 `best.onnx` 放在源权重旁；以命令打印路径为准。导出可能覆盖同位置旧产物，不同配置的导出应从不同的模型副本执行。

同时生成 `best.onnx.json`，记录来源权重与产物 SHA-256、类别映射、请求的输入尺寸、opset 和动态输入选项。`requested_image_size` 是请求值；实际张量形状以模型本身为准，训练器可能按 stride 调整尺寸。
说明文件用于交付核对，运行端仍从 runtime YAML 读取配置；它不包含完整数据版本、代码版本和真实精度记录，正式发布时仍需补齐这些信息。

`--format rknn` 仅为预留转换入口，指定 RK3588 目标；工具链、量化、板端后处理和运行后端尚未验证，见 [部署说明](DEPLOYMENT.md)。不能据此认为 NPU 已可用。

## 6. 交给下游检测定位

1. 根据独立评估、离线效果和部署约束选定模型，保留数据版本、训练配置、指标与导出说明。
2. 将选定的 `.pt` 或已验证的 `.onnx` 放到 `weights/citrus/`，并带上对应说明文件；也可在配置中使用绝对模型路径。
3. 更新 `configs/runtime/citrus.yaml` 的 `model.path`、输入尺寸、阈值和类别过滤。当前 `.pt`/ONNX 都由 `backend: ultralytics` 加载，文件路径相对 `weights_dir`。
4. 按 [运行指南](USAGE.md) 启动 `profile:=citrus`。模型输出仍通过公共检测格式进入 ROS 定位节点；定位的深度参数与模型训练参数分别管理。

上游训练结束后，由开发者选择并切换模型。相机实测、真实病害效果和 RK3588 部署分别验收。
