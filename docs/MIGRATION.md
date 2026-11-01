# 工程来源与演进

## 主线与上游能力

当前工程以本地 `depth_estimation` 的相机检测和三维定位为主线，主仓库为 `wyNomad/citrus-disease-detection`。
YOLO 数据准备、训练与导出融入上游工具，为视觉主线提供可配置的模型。
Gemini 305 / G40351-191 为目标相机，香橙派 5 Plus / RK3588 为最终运行平台。

| depth_estimation 模块 | 当前实现 |
| --- | --- |
| `vision_yolo_detector` | `citrus_detector` 与公共 `citrus_vision.inference` |
| `vision_target_locator` | `citrus_localizer` 与公共 `citrus_vision.geometry` |
| `vision_bringup` | `citrus_bringup/launch/pipeline.launch.py` |
| `yahboomcar_msgs` 检测消息 | 专用 `citrus_interfaces`，分开存放类别与坐标系 |
| 本地权重 | 本地 `weights/`，模型文件不进入 Git |

`orbbec_305` 保留为独立参考工程；主仓库仅使用必要相机资料、配置和固定版本驱动，不引入 SLAM、KCF、MediaPipe 等独立应用。

## 入口整理

正式系统入口为 `citrus_bringup` 的统一 launch；上游和离线检查使用 `scripts/` 或 `citrus-*` 命令。
原训练项目的模拟抓取演示、像素抓取适配和重复根目录入口已移除。历史实现可以通过 Git 历史追溯，工作树只保留当前维护的功能。
依赖统一由 `pyproject.toml` 和 `requirements/` 环境清单管理。

## 检测定位契约

结果从首目标扩展为整帧全部目标；类别与 frame_id 分开；Header 保留彩色图采集时间，并与深度按采集时间匹配。
检测、深度和内参必须属于匹配的彩色光学坐标系，尺寸一致。无效深度保留明确状态和 NaN 坐标；几何计算支持整数深度换算、浮点米制深度和已支持的非零畸变。
主接口为包含检测信息的三维目标数组，手眼标定和机械臂控制属于后续工作。

驱动固定到官方 OrbbecSDK_ROS2 v2.7.6 提交，并应用两处点云 row_step 修复。
相机配置显式开启 COLOR 深度对齐与 High Accuracy，默认关闭额外的 1.5 米阈值过滤。
原 depth_estimation 的 640×480 流设置尚未经本轮实机确认，当前使用设备自动 profile，具体参数需实测确定。

## 软件验收与边界

Python 公共发行包为 `citrus-vision-core`，Python 导入名和 ROS 包名为 `citrus_vision`，分别管理元数据。
检测输出拒绝覆盖已有目录；训练使用独立配置快照；启动器向外保留业务进程异常退出状态。
软件验证包括核心与 ROS 回归、干净 wheel 安装、合成数据实际训练、ONNX 导出与一致性检查，详见 [验证结果](VALIDATION_RESULTS.md)。
真实病害模型效果、相机取流/定位精度、ARM64 与 RKNN 后端待后续验收。

## 参考记录与备份

- [原 depth_estimation 总结](history/depth_estimation_20260907.md)
- [相机参考工程总结](history/orbbec_305_summary_20260905.md)
- [相机画面问题交接](history/orbbec_305_handoff_20260905.md)

这些历史记录中的路径和验证结论只用于追溯；实际运行以当前配置和实测为准。
相机原始画面需要先直看话题，不能套用历史左右拼接处理。

原 depth_estimation 工作空间已归档并逐普通文件核对 SHA-256。
本机 `/home/wyi/depth_estimation_backup_20261031` 目前保留压缩包、校验清单和说明文件，重复原目录树已清理；当前运行不依赖备份路径。
原 depth_estimation 的 HLB 权重保留在本地，启用前需要核对模型结构和标签。

仓库整体尚未选定许可证。第三方驱动保留原许可证与 NOTICE；历史 depth_estimation 节点的原包元数据声明 MIT。
