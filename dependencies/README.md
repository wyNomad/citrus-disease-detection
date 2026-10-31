# Orbbec 驱动来源

固定官方 `OrbbecSDK_ROS2` v2.7.6 对应提交：`c0c14f538a9faf24319d246a27580308c17b1b5e`。
仓库地址与固定版本记录在 `orbbec.repos`，准备脚本读取该清单；也可通过 vcstool 导入，但导入后仍须应用点云补丁。

本轮逐文件比较了原 `depth_estimation` 驱动与这个官方版本：除 Python 缓存外，仅 `gemini305.launch.py` 和 `ob_camera_node.cpp` 不同。
后者在两处点云裁剪后补充 `row_step=width*point_step`，保存在 [补丁](patches/orbbec-pointcloud-row-step.patch)。
原相机参考目录与深度工程目录之间仅启动文件的 depth_registration 默认值不同。
启动参数在新仓库的 `configs/cameras/gemini305.yaml` 管理，参考 [迁移说明](../docs/MIGRATION.md)。

```bash
python scripts/setup_camera.py
```

默认目标 `ros2_ws/src/vendor/orbbec` 不入 Git。脚本从固定提交获取，识别补丁是否已应用，并拒绝覆盖已有目录。
本地导入模式校验驱动版本与补丁兼容性，不声称外部目录所有文件都与上游一致；用于没有网络时迁移已知的本地驱动。
官方驱动带有 x64 与 ARM64 SDK 库，但本项目尚未在 RK3588 验证加载、设备兼容性或实际取流。
第三方 LICENSE、NOTICE 和 SDK 原内容随驱动获取，不复制到本项目的自有代码授权中。
