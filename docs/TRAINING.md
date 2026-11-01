# 训练与导出

数据准备、YOLO 训练与模型导出是相机检测定位工程的上游工具。通过训练得到的权重由运行配置交给同一套检测与定位通路使用。
仓库提供训练流程与 15 类标签配置，真实病害数据与业务模型效果需另行准备和评估。

```bash
python -m pip install -e . -r requirements/train.txt
citrus-prepare-data --source data/raw/testA --output data/citrus_mini --sample 100 --seed 42
citrus-train --config configs/training/citrus.yaml
```

`configs/training/citrus.yaml` 中设置预训练模型、数据配置、epochs、imgsz、device、batch 等。
`model` 相对 `--weights-dir`；`data` 相对训练配置文件；数据集配置中的 `path` 相对数据配置文件。
训练结果默认写入当前目录 `runs/train`，可通过 `--project` 指定其他位置。

```bash
citrus-train --config configs/training/citrus.yaml --epochs 50 --device 0
```

只有设备确有可用 GPU 时才指定 GPU。默认 CPU 小规模参数用于流程检查，不代表最终精度配置。
同名训练目录存在时自动递增，训练器实际目录和 `best.pt` 路径会打印；目录内保存本次训练配置，训练器另存实际参数。每次启动在项目输出的 `configs/train-<唯一标识>/` 中保存独立的数据集与训练配置快照，后续实验不会覆盖旧实验引用的 YAML；失败任务也保留其配置。

```bash
citrus-export --weights /absolute/path/best.pt --format onnx
```

ONNX 导出前执行 `python -m pip install -r requirements/export.txt`。为保持 NumPy 1.x 兼容，ONNX 固定在 `>=1.16,<1.19` 范围，默认关闭额外的模型简化。RKNN 导出入口提供 `--format rknn` 并指定 RK3588 目标，但工具链、量化与板端后处理尚未验证，见 [部署说明](DEPLOYMENT.md)。
训练权重与数据需要提前准备；训练入口不会自动下载缺失的初始化权重。
