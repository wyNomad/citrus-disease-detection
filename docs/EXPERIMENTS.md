# 实验记录规范

实验围绕 Gemini 305 检测定位主线记录；训练和导出实验用于选定适合这条通路的模型。
可通过 [实验与实机验证表单](../.github/ISSUE_TEMPLATE/experiment.yml) 记录结果。

| 实验类型 | 必须说明的条件 | 结果关注点 |
| --- | --- | --- |
| 数据与模型训练 | 代码提交、数据版本、划分 seed、类别、模型和超参数 | 识别指标、失败样本、权重 SHA-256 |
| 模型导出与推理 | 输入尺寸、前后处理、后端和依赖版本 | PyTorch/部署格式一致性、实际加载与输出 |
| 合成或回放 ROS 通路 | 输入来源、时间戳、frame_id、深度编码、内参 | 消息匹配、异常输入处理、输出契约 |
| Gemini 305 真机定位 | 固件、驱动、流 profile、对齐、标定与深度单位 | 重投影、测距误差、运动误差和稳定性 |
| RK3588 部署 | 板卡系统、NPU 驱动与 Runtime、模型格式和量化 | 精度变化、完整处理延迟、帧率和长时稳定性 |

## 病害检测实验矩阵

训练实验在[公开数据集](DATA_AND_MODELS.md)上进行。按症状分组组合出三种训练集，用于考察「类别构成」对检测效果的影响；同一模型再在三种采集环境下测试，考察「采集条件」对泛化的影响。

| 维度 | 取值 | 关注点 |
| --- | --- | --- |
| 类别组合 | ABC / ABCD / ABCDE | 混入易混淆病害后，黄龙病相关类别的精度与误检如何变化 |
| 采集环境 | testA 手机·田间或纯色背景、testB 相机·田间、testC 白板二次拍摄 | 跨环境的精度落差 |
| 架构对比 | 官方 YOLOv5l 基线与 YOLO11n | 参数量与精度的权衡 |

矩阵定义在 `configs/experiments/lab.yaml`，训练与评估配置分别为 `configs/training/lab_*.yaml` 与 `configs/datasets/lab_*.yaml`。

```bash
python scripts/run_experiments.py --device 0
```

每次实验保留 `citrus-train` 生成的配置快照与 `citrus-val` 记录的权重 SHA-256，指标汇总写入 `runs/summary.json`。本机目前只完成链路冒烟（`configs/training/lab_smoke.yaml`，抽样 3%、2 轮），正式精度需在 GPU 环境跑完整矩阵后补记。

## 已有验收

当前已验证合成训练、模型导出与软件通路，详见 [软件验证结果](VALIDATION_RESULTS.md)。
真实病害效果、相机实测和板端/NPU 部署仍需分别记录，不将合成数据结果当成实机精度结论。

工程来源和演进见 [整合记录](MIGRATION.md)，各类检查入口见 [验证指南](VALIDATION.md)。
