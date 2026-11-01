# 仓库结构与开发导航

本说明对应当前主分支 `master`。主工程位于本地 `depth_estimation/citrus-disease-detection`，远端仓库为 `wyNomad/citrus-disease-detection`。

工程连接两条流程：上游准备数据、训练并导出模型；下游调用 Gemini 305 与选定模型，输出目标类别、像素位置和相机光学坐标系下的三维位置。

开发环境为 Ubuntu 22.04、Python 3.10、ROS 2 Humble；目标设备为香橙派 5 Plus、RK3588、Ubuntu 22.04 ARM64。
当前已完成软件整合与软件通路验证。真实相机、真实病害效果、板端环境及 NPU 后端仍待后续工作。

## 1. 目录全貌

以下目录树同时展示版本管理中的源码和本地生成目录。注释为“本地”的内容不随 Git 克隆；模型和数据条目注明了已有文件与约定位置。

```text
citrus-disease-detection/
├── README.md                         # 快速开始、常用入口
├── AGENTS.md                         # 面向 Agent 的项目约定
├── CONTRIBUTING.md                   # 协作与修改校验要求
├── pyproject.toml                    # Python 包、依赖、CLI、pytest 设置
├── requirements.txt                  # 笔记本推理依赖的兼容入口
├── .gitignore                        # 本地产物和大文件忽略规则
│
├── src/citrus_vision/                # 公共算法与命令实现
│   ├── __init__.py
│   ├── types.py                      # 检测结果数据结构
│   ├── config.py                     # 运行配置、模型路径、参数校验
│   ├── inference.py                  # 推理后端与统一检测接口
│   ├── geometry.py                   # 深度处理、相机反投影
│   ├── dataset.py                    # 数据配对、抽样、划分
│   └── cli.py                        # 训练、离线检测、导出实现
│
├── scripts/                          # 命令包装与工程工具
│   ├── prepare_data.py
│   ├── train.py
│   ├── detect.py
│   ├── export.py
│   ├── setup_camera.py               # 获取/导入固定版本相机驱动并应用补丁
│   ├── build_ros.py                  # 使用当前 Python 构建 ROS 工作空间
│   └── check_training_export.py      # 真实训练与 ONNX 导出烟雾检查
│
├── configs/                          # 业务与硬件配置
│   ├── datasets/citrus.yaml          # 数据位置、训练/验证子目录、15 类标签
│   ├── training/citrus.yaml          # 预训练模型及训练超参数
│   ├── runtime/generic.yaml          # 通用物体检测与定位配置
│   ├── runtime/citrus.yaml           # 病害检测与定位配置
│   └── cameras/gemini305.yaml        # 相机 launch 参数
│
├── ros2_ws/
│   ├── src/
│   │   ├── citrus_interfaces/        # ROS 消息
│   │   ├── citrus_vision/            # 公共算法的 ROS 包装
│   │   ├── citrus_detector/          # ROS 图像检测节点
│   │   ├── citrus_localizer/         # ROS 三维定位节点
│   │   ├── citrus_bringup/           # 统一启动与配置安装
│   │   └── vendor/orbbec/            # 本地：第三方驱动与 SDK
│   ├── build/                        # 本地：编译中间产物
│   ├── install/                      # 本地：节点、消息、环境与安装资源
│   └── log/                          # 本地：构建日志
│
├── dependencies/
│   ├── orbbec.repos                  # 相机驱动来源与固定提交
│   ├── patches/                      # 驱动补丁
│   └── README.md                     # 版本、来源、本地差异说明
│
├── requirements/                     # 按用途记录依赖
│   ├── core.txt
│   ├── laptop.txt
│   ├── train.txt
│   ├── export.txt
│   ├── dev.txt
│   └── rk3588.txt
│
├── data/                             # README 入 Git，数据留在本地
├── weights/                          # README 入 Git，权重留在本地
├── runs/                             # 本地：训练、检测输出和配置快照
├── .venv/                            # 本地：Python 开发环境
├── build/、dist/                     # 本地：Python 包构建产物
│
├── tests/                            # 核心算法、配置与 CLI 回归
│   └── ros/                          # ROS 传输、输入保护、退出状态回归
├── examples/
│   ├── offline_localization.py       # 无硬件的几何计算示例
│   └── legacy_grasp/                 # 原模拟抓取与数据划分代码归档
├── docs/                             # 安装、架构、部署、迁移和验证文档
│   └── history/                      # 旧工作空间总结与相机调查记录
├── .github/                          # CI、检查脚本、Issue/PR 模板
├── assets/                           # 仓库展示素材
├── main.py                           # 离线检测的兼容入口
├── split_data.py                     # 数据划分的兼容入口
└── utils/arm_vision.py               # 旧像素坐标 API 的兼容适配
```

## 2. 分层关系

公共算法集中在 [src/citrus_vision](../src/citrus_vision)。离线工具与 ROS 检测节点都调用这份实现。

```text
scripts / citrus-* 命令 ──→ 公共 Python 核心
                                   ↑
Gemini 305 驱动 ──→ ROS 适配节点 ────┘
                       ↓
              ROS 检测和三维位置消息
```

这使模型推理和坐标计算可以独立于相机、ROS 进行检查，也让后续板端后端复用相同的检测结果格式。

| 层 | 主要目录 | 责任 |
| --- | --- | --- |
| 公共算法 | `src/citrus_vision` | 检测、配置、数据处理、几何计算 |
| 操作入口 | `scripts`、已安装的 CLI | 把用户参数传给核心，实现操作流程 |
| ROS 适配 | `ros2_ws/src/citrus_*` | 接收图像、组织消息、同步数据、启动节点 |
| 配置 | `configs` | 决定模型、类别过滤、阈值、相机和定位参数 |
| 依赖和环境 | `dependencies`、`requirements` | 记录来源、版本和安装用途 |
| 本地产物 | `data`、`weights`、`runs`、构建目录 | 保存实验输入与运行输出 |

## 3. 公共核心各文件做什么

| 文件 | 主要内容 | 常见修改场景 |
| --- | --- | --- |
| [types.py](../src/citrus_vision/types.py) | `Detection`：类别 ID、类别名、置信度、`xyxy`，由框计算中心 | 扩展公共检测结果 |
| [config.py](../src/citrus_vision/config.py) | 模型、定位、话题配置及输入检查，解析模型位置 | 新增配置项、调整参数契约 |
| [inference.py](../src/citrus_vision/inference.py) | `Detector` 接口、Ultralytics 实现、后端工厂 | 更换推理后端、调整检测接入 |
| [geometry.py](../src/citrus_vision/geometry.py) | 深度单位转换、有效值中位数、反畸变、像素反投影 | 调整深度采样或定位方法 |
| [dataset.py](../src/citrus_vision/dataset.py) | 图片/标签配对、固定 seed 抽样与划分、输出清单 | 数据准备流程 |
| [cli.py](../src/citrus_vision/cli.py) | 训练、离线检测、导出入口 | 命令参数、结果保存和实验快照 |

推理输出使用原始彩色图像的像素坐标。图像缩放和 letterbox 的逆变换由推理后端负责，定位层按原图像素查询对应深度。
当前推理后端为 `ultralytics`。`rknn` 只是明确报未实现的预留分支，后续需要实现并在板卡上验证。

## 4. Python 包名与 ROS 包名

| 名称 | 用途 |
| --- | --- |
| `citrus-vision-core` | pip 管理的 Python 发行包，定义依赖、extras 和四个 CLI |
| `citrus_vision` | Python 导入模块，例如 `from citrus_vision.geometry import deproject` |
| `citrus_vision` ROS 包 | 向 ROS overlay 安装公共模块，供 ROS 启动器与节点使用 |

ROS 包中的 `citrus_vision` 目录是指向根目录 `src/citrus_vision` 的相对符号链接。真实算法源码统一维护在根目录下，ROS 包装负责注册和安装。
发行包名独立，保证加载 ROS 环境后，pip 的 extras 与 CLI 元数据仍可正确识别。

## 5. 上游：数据到模型

从仓库根目录执行，先激活已安装项目依赖的虚拟环境：

```bash
citrus-prepare-data --source data/raw/testA --output data/citrus_mini --sample 100 --seed 42
citrus-train --config configs/training/citrus.yaml
citrus-export --weights runs/train/citrus_experiment/weights/best.pt --format onnx
```

| 步骤 | 输入 | 输出 |
| --- | --- | --- |
| 数据准备 | 原始 `images/` 与对应 `labels/` | 训练/验证图片和标签、`split_manifest.json` |
| 模型训练 | 预训练权重、数据集 YAML、训练 YAML | 训练目录、权重、参数、评估产物 |
| 模型选择 | 候选模型的验证结果 | 选定的业务权重 |
| 模型导出 | `.pt` 模型 | ONNX 等部署产物 |

数据划分只使用图片和标签配对，拒绝重复文件 stem 和已有输出目录。固定 seed 便于复现划分。
数据配置保留原仓库 15 类顺序，其中 ID 12 对应 `S14 Canker`，ID 14 对应 `S12 Algal spot`；不能按名称中的数字重新排序。

每次训练的配置与产物关系如下：

```text
runs/train/
├── configs/train-<唯一标识>/
│   ├── dataset.yaml                 # 解析成绝对路径的数据集快照
│   └── training.yaml                # 本次训练请求的配置
└── citrus_experiment/               # 同名目录存在时训练器自动递增
    ├── weights/
    │   ├── best.pt
    │   └── last.pt
    ├── args.yaml
    ├── training_config.yaml         # 原配置与独立快照的引用
    └── 其他训练和验证产物
```

选定业务模型后，将其放到 `weights/citrus/best.pt`，或者修改运行配置中的模型位置。运行节点加载配置指定的权重；训练结束不会自动替换正在使用的模型。

## 6. 下游：相机到坐标

```text
/camera/color/image_raw
           ↓
    citrus_detector ──→ 公共推理接口
           ↓
/citrus/detections ──────────────────┐
/camera/depth/image_raw ─────────────┼─→ citrus_localizer
/camera/color/camera_info ───────────┘           ↓
                                    /citrus/targets_3d
```

| ROS 包 | 具体职责 |
| --- | --- |
| [citrus_interfaces](../ros2_ws/src/citrus_interfaces) | 定义 2D 检测数组和 3D 目标数组 |
| [citrus_vision](../ros2_ws/src/citrus_vision) | 将同一份公共核心安装进 ROS overlay |
| [citrus_detector](../ros2_ws/src/citrus_detector) | 接收彩色图、调用模型、发布检测及可选标注图 |
| [citrus_localizer](../ros2_ws/src/citrus_localizer) | 匹配检测与对齐深度，结合内参计算各目标位置 |
| [citrus_bringup](../ros2_ws/src/citrus_bringup) | 安装运行配置并组合相机、检测、定位启动流程 |

定位节点按采集时间近似同步检测与深度，彩色 CameraInfo 单独缓存。默认时间窗口 0.04 秒、缓存 30 帧。
启动相机时显式要求深度对齐到 COLOR。定位节点再检查检测、深度和内参的坐标系与尺寸；错误输入会被拒绝。

## 7. 坐标与消息约定

| 消息 | 内容 |
| --- | --- |
| `Detection2D` | 类别 ID、类别名、置信度、原图 `xyxy`、中心像素 |
| `Detection2DArray` | 原图 Header、原图宽高、本帧全部检测 |
| `Target3D` | 本帧检测序号、对应检测、深度有效标记、状态和三维位置 |
| `Target3DArray` | 彩色图 Header、匹配深度时间戳、本帧全部目标 |

主要输出为 `/citrus/targets_3d`。其中：

- 单位为米，光学坐标方向为 x 向右、y 向下、z 向前。
- Header 保留原图采集时间和真实光学坐标系。
- `detection_index` 是本帧序号，未提供跨帧跟踪 ID。
- 深度无效时保留目标，设置 `depth_valid=false`，位置为 NaN。
- 整帧标定或坐标系错误时不发布三维结果，并输出节流警告。

默认在中心像素周围取半径 2 的区域，即最多 5×5 像素，剔除无效和超范围深度后取中位数。
`16UC1` 按配置的 `depth_scale` 转米，默认 0.001；`32FC1` 按米处理。实际相机深度单位仍需实机核对。
几何模块处理支持的畸变模型；带分箱或部分 ROI 的标定暂不支持。

输出代表中心邻域可见表面位置。手眼标定、机械臂 base 系转换、抓取点规划和硬件控制属于后续范围。

## 8. 四类配置及路径规则

| 配置 | 控制内容 | 典型用途 |
| --- | --- | --- |
| `configs/datasets/citrus.yaml` | 数据目录、训练/验证子目录、15 类名称 | 更换数据集 |
| `configs/training/citrus.yaml` | 初始化模型、epochs、batch、imgsz、device、seed 等 | 调整训练任务 |
| `configs/runtime/*.yaml` | 模型、后端、阈值、目标类别、定位和话题参数 | 切换业务与调试模式 |
| `configs/cameras/gemini305.yaml` | 传给驱动 launch 的取流、对齐、帧率等参数 | 调整硬件采集 |

运行配置默认值：

| 项目 | generic | citrus |
| --- | --- | --- |
| 模型路径，相对 weights_dir | `yolov8n.pt` | `citrus/best.pt` |
| 用途 | 日常物体坐标通路检查 | 业务病害检测 |
| 后端 | ultralytics | ultralytics |
| 设备 | cpu | cpu |
| 置信度 | 0.25 | 0.4 |
| 输入尺寸 | 640 | 640 |
| 类别过滤 | 空列表，不过滤 | 空列表，不过滤 |

类别名来自模型元数据。`target_classes` 可填写模型中的完整名称，未知名称会在初始化时被拒绝。
定位有效深度范围默认 0.1～10 米，标注图默认关闭。通过 `topics` 可更换输入输出话题。
模型输入尺寸 640 属于推理预处理参数；相机宽、高、帧率当前配置为设备自动选择的 `0`，实际可用 profile 待实机确认。

| 路径项 | 相对位置如何解释 |
| --- | --- |
| 运行配置中的 `model.path` | 相对 `--weights-dir` 或 ROS 的 `weights_dir`；绝对路径直接使用 |
| 训练配置中的 `model` | 相对 `--weights-dir`，默认当前目录的 `weights` |
| 训练配置中的 `data` | 相对训练 YAML 所在目录 |
| 数据集配置中的 `path` | 相对数据集 YAML 所在目录，由训练入口解析 |
| 检测 `--output`、训练 `--project` | 相对当前工作目录，或显式指定绝对位置 |
| 相机准备与 ROS 构建脚本的默认工作空间 | 根据脚本位置定位仓库根目录 |

日常从仓库根目录运行最方便。跨工作目录启动时，显式传入配置与权重目录的绝对路径。

## 9. 本地模型、数据与大文件

| 位置 | 当前角色 |
| --- | --- |
| `weights/yolov8n.pt` | 已从旧工程迁入，用于通用目标检查 |
| `weights/legacy/HLB_*.pt` | 已保留的三个历史权重，格式与标签兼容性待核对 |
| `weights/yolo11n.pt` | 训练初始化模型的约定位置，需要另行准备 |
| `weights/citrus/best.pt` | 选定业务权重的约定位置，需要训练或准备后放入 |
| `weights/manifest.local.json` | 本机迁移权重的大小和 SHA-256 记录 |
| `data/raw/` | 原始数据的约定位置 |
| `data/citrus_mini/` | 默认训练数据配置指向的位置，需要准备数据 |
| `runs/` | 训练、检测和配置快照 |

Git 只保留 `data/README.md` 和 `weights/README.md` 等说明，不提交数据集与权重。
`.venv`、SDK 检出、ROS/Python 构建产物和日志也不入 Git；新设备克隆后需要重新准备。

## 10. 相机驱动与依赖组织

[dependencies/orbbec.repos](../dependencies/orbbec.repos) 固定 OrbbecSDK_ROS2 v2.7.6 对应提交。
[setup_camera.py](../scripts/setup_camera.py) 可以从上游获取，或从已知本地 v2.7.6 来源导入，并校验/应用点云 row_step 补丁。
默认目标为 `ros2_ws/src/vendor/orbbec`，其中包含 `orbbec_camera`、`orbbec_camera_msgs`、`orbbec_description`。

这样形成五个自有包加三个第三方包。相机参数由本仓库配置管理；驱动更新应同时复核固定提交、补丁和实际相机行为。

| 依赖文件 | 用途 |
| --- | --- |
| `requirements/core.txt` | NumPy 1.x、PyYAML 等公共核心依赖 |
| `requirements/laptop.txt` | 笔记本推理，包含核心及 Ultralytics/OpenCV |
| `requirements/train.txt` | 训练入口，目前复用 laptop 依赖 |
| `requirements/export.txt` | 增加 ONNX 和 CPU Runtime 验证依赖 |
| `requirements/dev.txt` | pytest、构建和兼容的 setuptools |
| `requirements/rk3588.txt` | 板端依赖预留，目前只含公共核心要求 |

`rk3588.txt` 尚未构成完整 NPU 环境。后续仍需匹配板端驱动、librknnrt、转换工具和推理实现。
跨设备重新建立环境并构建；`.venv` 和编译产物与当前机器、解释器及架构有关。

## 11. 常用操作入口

以下命令从仓库根目录执行，具体系统安装步骤见 [SETUP.md](SETUP.md)。

| 想做的事 | 入口 |
| --- | --- |
| 准备训练数据 | `citrus-prepare-data` 或 `python scripts/prepare_data.py` |
| 训练模型 | `citrus-train` 或 `python scripts/train.py` |
| 图片/视频离线检测 | `citrus-detect` 或 `python scripts/detect.py` |
| 模型导出 | `citrus-export` 或 `python scripts/export.py` |
| 准备相机依赖 | `python scripts/setup_camera.py` |
| 构建全部 ROS 包 | `python scripts/build_ros.py` |
| 只构建五个自有包 | `python scripts/build_ros.py --core-only` |
| 无相机几何示例 | `python examples/offline_localization.py` |
| 合成训练与 ONNX 检查 | `python scripts/check_training_export.py --output /tmp/new-smoke-directory` |

统一启动示例：

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
python scripts/build_ros.py
source ros2_ws/install/setup.bash
ros2 launch citrus_bringup pipeline.launch.py profile:=generic weights_dir:="$PWD/weights"
```

`profile:=citrus` 选择病害运行配置。`profile_file` 和 `camera_file` 支持指定自定义配置。
`start_camera:=false` 用于已有外部相机话题或 rosbag 输入，检测与定位节点会等待相应数据。

根目录 `main.py` 是离线 2D 检测入口，需要提供 `--source`；统一相机三维流程通过 ROS launch 启动。
根目录 `split_data.py` 继续包装数据准备入口；`utils/arm_vision.py` 保留旧像素坐标 API，内部复用公共检测器。
`examples/legacy_grasp` 用于追溯原图片对准、模拟串口和模拟抓取演示，日常开发使用新的 CLI 与 ROS 入口。

## 12. 校验和 CI

| 位置 | 覆盖内容 |
| --- | --- |
| `tests/test_config.py` | 配置、模型路径、非法参数与预留后端边界 |
| `tests/test_dataset.py` | 数据划分复现、防覆盖和路径保护 |
| `tests/test_geometry.py` | 深度编码、边界、无效值、光学轴向和畸变 |
| `tests/test_inference.py` | 公共检测结果与类别过滤契约 |
| `tests/test_detection_output.py` | 失败任务与重复运行不能覆盖旧检测结果 |
| `tests/test_training.py` | 训练路径与独立配置快照 |
| `tests/test_packaging.py` | 公共发行包元数据与 CLI |
| `tests/ros/` | 实际消息传输、输入保护、时间匹配和启动失败状态 |

`.github/workflows/repository-checks.yml` 包含三个任务：

1. `core`：安装核心与 OpenCV、检查 Python/XML/YAML/文档链接、运行核心测试、构建分发包、在仓库外的干净环境安装 wheel。
2. `ros`：在 Ubuntu 22.04 / Humble 容器内构建五个自有包，检查 ROS 通路、保护条件、退出状态和包元数据。
3. `training-export`：运行合成 YOLO11 CPU 训练、checkpoint 重载、ONNX 导出与 PyTorch/ONNX 一致性检查。

必需测试通过 `CITRUS_FAIL_ON_SKIP=1` 禁止跳过后报告成功。完整本地测试需先构建并加载 ROS overlay。
最近的软件验收为 49 项测试零跳过、八包本地构建通过；详情与版本见 [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md)。

## 13. 文档与日常修改导航

| 问题或需求 | 先看哪里 |
| --- | --- |
| 安装环境、准备驱动 | [SETUP.md](SETUP.md) |
| 启动节点、切换模型 | [USAGE.md](USAGE.md) |
| 标签、权重和数据约定 | [DATA_AND_MODELS.md](DATA_AND_MODELS.md) |
| 调整训练任务 | [TRAINING.md](TRAINING.md) |
| ROS 消息与坐标约定 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 部署到香橙派 | [DEPLOYMENT.md](DEPLOYMENT.md) |
| 修改后应运行哪些检查 | [VALIDATION.md](VALIDATION.md) |
| 已验证和未验证能力 | [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md) |
| 迁移来源、旧入口和行为变化 | [MIGRATION.md](MIGRATION.md) |

具体修改时：换模型或阈值先改 `configs/runtime`；改训练超参数先改 `configs/training`；改相机 profile 先改 `configs/cameras`；改推理实现进入 `inference.py`；改坐标算法进入 `geometry.py`；改 ROS 数据匹配进入 `citrus_localizer/node.py`。

## 14. 工作空间中另外两个目录

`/home/wyi/orbbec_305` 保持独立，作为相机参考资料和历史用例工作空间。主仓库吸收必要资料与配置，相关历史总结位于 `docs/history`。

`/home/wyi/depth_estimation_backup_20261031` 保留原深度工程的压缩归档、逐文件校验清单和说明文件。重复的 `original-tree` 已在归档回读核验后清理，约释放 825 MB。
当前日常工作在新的主仓库进行；主流程运行不依赖旧工程备份路径。

## 15. 后续验收范围

- Gemini 305：实机枚举、取流、彩色画面、深度对齐、内参、单位、时间同步、测距误差与稳定性。
- 病害模型：真实数据训练或模型选定、类别核对、准确率与实际场景效果。
- 香橙派：ARM64 环境与相机驱动运行，再实现 RKNN 后端，验证模型转换、量化、精度、帧率和稳定性。

当前几何检查与合成训练验证软件通路，实际设备与业务效果按以上范围继续验收。
