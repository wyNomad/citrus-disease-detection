# 本轮验证结果

当前修复验收：2026-11-01。环境为 Ubuntu 22.04.5 x86_64、Python 3.10、ROS 2 Humble。相机与 RK3588 目标板未参与本轮验证。

| 检查 | 本地结果 | 边界 |
| --- | --- | --- |
| Python / XML / YAML / Markdown 链接 | 通过 | 不检查外部网站可达性 |
| 完整 pytest，禁止跳过 | 49 项通过、0 跳过 | 含 14 项 ROS 用例 |
| 自有五包与 Orbbec 三包 | 八包构建通过 | x86_64，不代表 ARM64 或取流通过 |
| 公共包 sdist / wheel | 构建通过 | wheel 只包含公共核心 |
| 仓库外的干净 venv 安装 wheel | 通过 | 核心依赖、导入、extras 元数据和四个 CLI 校验 |
| ROS overlay 加载后的包元数据 | 通过 | `citrus-vision-core` 和 `citrus_vision` 独立，公共 extras 保留 |
| 真实 YOLOv8n 图片推理 | 通过 | 通用模型，不是病害精度评估 |
| 实际 ROS 无相机启动与停止 | 通过 | 真实模型加载，两进程正常停止 |
| 损坏模型启动 | 返回失败状态 1 | 不再把节点失败报告为成功 |
| 合成 YOLO11 CPU 训练 | 一轮训练完成，best.pt 重载通过 | 随机初始化、小型人工数据，不评估业务精度 |
| ONNX 导出与重载 | 通过 | ONNX checker、CPU Runtime、公共检测接口均执行 |
| PyTorch / ONNX 数值一致性 | rtol=1e-3、atol=1e-3 通过 | 同一模型与输入的原始输出比较 |
| 固定相机依赖全新获取 | 通过 | 从上游固定提交拉取并应用补丁；不依赖旧参考目录 |

新增回归覆盖：错误深度坐标系、缺失/错误标定、过期深度、空检测、输出防覆盖、训练数据快照隔离、Python/ROS 发行包命名，以及子进程失败的退出状态。
测试还覆盖两种深度编码、无效深度、光学轴向、畸变校正、原图坐标、类别过滤、数据划分与采集 Header。

本地关键版本：NumPy 1.26.4、PyYAML 6.0.3、OpenCV wheel 4.11.0.86、Ultralytics 8.4.140、PyTorch 2.14.0+cu130（本轮使用 CPU）、ONNX 1.18.0、ONNX Runtime 1.23.2、pytest 8.4.2、setuptools 79.0.1。
ONNX 限制 `<1.19`，避免新版依赖解析把 ROS 环境带入 NumPy 2。训练导出 CI 另使用匹配的 CPU PyTorch 2.5.1 / torchvision 0.20.1 组合，具体通过状态以 PR 检查为准。

CI 分为 core、ros、training-export：核心 job 不含 ROS，用 OpenCV 执行畸变用例；ROS job 在 Humble 容器构建五个自有包并运行 ROS 与元数据检查；训练 job 运行实际训练和导出。必需测试使用 `CITRUS_FAIL_ON_SKIP=1`，不允许跳过后报告成功。

未验证：真实病害数据与精度、Gemini 305 取流/对齐/测距、ARM64 驱动运行、RKNN NPU 后端、板端帧率与长时稳定性。
