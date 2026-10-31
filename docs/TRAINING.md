# 训练与导出

本阶段收录并重构原训练框架，未附带真实数据，也未重新训练病害模型。

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
同名训练目录存在时自动递增，训练器实际目录和 `best.pt` 路径会打印；目录内保存本次训练配置，训练器另存实际参数。

```bash
citrus-export --weights /absolute/path/best.pt --format onnx
```

ONNX 导出依赖按 Ultralytics 对应版本补齐。RKNN 导出入口提供 `--format rknn` 并指定 RK3588 目标，但工具链、量化与板端后处理尚未验证，见 [部署说明](DEPLOYMENT.md)。
不会为了仓库迁移启动长时间训练或自动下载模型。
