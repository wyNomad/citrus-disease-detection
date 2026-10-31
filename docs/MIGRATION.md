# 仓库整合记录

## 来源与边界

- 主仓库：`wyNomad/citrus-disease-detection`，整合起点 `227d04dff462317130be1dd6c90eeae5817e43a9`。
- 本地 `depth_estimation`：YOLO ROS 节点、深度定位、统一启动、历史权重和总结。
- 本地 `orbbec_305`：独立参考工程，保留原目录；收录资料摘要和必要相机参数，不迁入 SLAM、KCF、MediaPipe 等无关包。
- 硬件：Gemini 305 / G40351-191。最终运行目标为香橙派 5 Plus / RK3588。

原工作空间在目录之外完整归档，并逐普通文件核对 SHA-256。备份包含源码、权重、日志、构建产物和工作流资料，平台保护的元数据目录不在项目备份内。
本机备份路径：`/home/wyi/depth_estimation_backup_20261031`。这只是迁移记录，运行代码不依赖此路径。

## 对照

| 原入口 | 新位置 |
| --- | --- |
| `scripts/train.py` | 同名兼容入口 → 公共包训练 CLI |
| `scripts/detect.py` | 同名兼容入口 → 公共推理模块 |
| `split_data.py` | 兼容入口；新增显式参数、固定 seed、拒绝覆盖 |
| `configs/custom_data.yaml` | `configs/datasets/citrus.yaml`，保留 15 类顺序 |
| `utils/arm_vision.py` | 兼容像素接口，调用公共推理模块 |
| 原 `main.py` 模拟抓取 | `examples/legacy_grasp` 历史归档；根 main 改为离线检测入口 |
| `vision_yolo_detector` | `citrus_detector` + 公共 `citrus_vision` |
| `vision_target_locator` | `citrus_localizer` + 公共几何函数 |
| `vision_bringup` | `citrus_bringup`，配置与路径可传入 |
| `yahboomcar_msgs` | 替换为职责明确的 `citrus_interfaces`，旧消费者需适配 |

## 行为变化

输出从首目标扩展为本帧全部目标；类别与 frame_id 分开；Header 保留原始采集时间；检测与深度按采集时间匹配。
无效深度有明确状态和 NaN 坐标。支持整数深度比例换算与浮点米制深度，校验尺寸和内参，并考虑非零畸变。
旧 PointStamped 与 RViz Marker 话题不再作为主接口，新的数组包含类别与多目标信息。需要旧接口时后续可加桥接节点。

相机驱动基于官方 v2.7.6 固定提交；原两处点云 row_step 修复保留为补丁。
旧本地启动参数包括深度对齐、High Accuracy、阈值过滤最大 1500。新相机配置显式启用对齐和 High Accuracy，默认关闭额外阈值过滤，避免隐式限制到 1.5 米。
旧工程写死 640×480 未经本轮实机验证，新配置使用设备自动 profile，实际分辨率可配置。

## 保留资料

- [原深度工程总结](history/depth_estimation_20260907.md)
- [相机参考工程总结](history/orbbec_305_summary_20260905.md)
- [相机画面问题交接](history/orbbec_305_handoff_20260905.md)

这些是历史记录，其中路径、已完成状态和旧结论不作为新仓库验证结果。相机 color 画面先直看原始话题，不能盲目执行历史左右拼接操作。
旧 HLB 模型仅保留本地，未假设其兼容 YOLO11。
仓库整体尚未选定许可证；本次未替作者新增授权协议。第三方驱动按原许可证单独获取，历史自有节点的原包元数据声明 MIT。

## 2026-11-01 审查修复

公共 Python 发行名称调整为 `citrus-vision-core`，导入路径仍为 `citrus_vision`，ROS 包名不变。旧环境按安装文档卸载原 Python 发行包后重新安装。
定位必须校验深度帧的彩色光学坐标系；检测输出拒绝覆盖已有目录；每次训练使用独立数据配置快照。启动器保留异常退出状态。
新增负向回归、干净 wheel 安装、训练导出检查及分开的 CI 任务，详见验证文档。
