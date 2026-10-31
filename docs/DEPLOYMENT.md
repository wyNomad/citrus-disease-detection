# 可迁移部署与 RK3588

目标：香橙派 5 Plus、RK3588、Ubuntu 22.04 ARM64。当前工作是在 Ubuntu 22.04 笔记本完成仓库基础，未在目标板或相机上验收。

## 已有的迁移基础

路径通过配置和显式模型目录传入；代码与模型、数据、驱动、构建产物分离。
离线和 ROS 共用 `Detection` 接口，模型框已映射回原图像素。
相机驱动固定提交并附补丁，仓库不依赖开发机安装目录。
训练与运行依赖分开，ARM64 机器重新创建环境和编译，不能复制 x86 的 venv、.so 或 ROS install 目录。

## 两种切换

模型配置切换：通用物体 / 柑橘病害，当前可用的推理后端都是 `ultralytics`。
硬件后端切换：笔记本 PyTorch/Ultralytics 基线已接入；RKNN NPU 后端仅预留接口，配置为 `rknn` 会明确报未实现。
不把导出成功等同于板端可运行，也不承诺未经测量的 FPS。

## 后续板端工作

1. 确认板卡系统、内核、USB、ROS Humble、相机 SDK ARM64 库可以运行。
2. 固定 NPU 内核驱动、`librknnrt`、RKNN Toolkit2 / Runtime 的匹配版本。
3. 在支持的转换主机环境导出模型；如采用 INT8，准备能代表实际场景的校准数据。
4. 接入 RKNN 推理，实现与 `Detection` 一致的前后处理、类别映射、逆 letterbox 和 NMS。
5. 用同一输入对比笔记本与板端检测结果，再验证相机三维定位及性能。

Rockchip 官方提供 YOLO11 / RK3588 示例，但本项目尚未据此完成后端适配：
[RKNN Model Zoo](https://github.com/airockchip/rknn_model_zoo)。
模型导出方式参考 [Ultralytics RKNN 文档](https://docs.ultralytics.com/integrations/rockchip-rknn/)。

`requirements/rk3588.txt` 只列公共核心依赖，不能视为完整板端安装脚本；运行时版本待拿到板卡后固定。
部署时还要带上对应模型、运行配置、相机配置及模型校验值。板端正式环境可单独维护经过验证的锁定依赖快照。
