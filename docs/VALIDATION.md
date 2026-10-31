# 验证状态

本轮有意将软件检查与硬件验收分开。几何用例和合成消息不能证明相机深度精度。

## 无硬件检查入口

```bash
python .github/scripts/check_repository.py
python -m pytest -q
python examples/offline_localization.py
```

测试覆盖深度编码、无效深度、中值、边界、光学轴向、畸变校正、配置路径、推理适配和数据划分防覆盖。
普通 pytest 在没有构建 ROS overlay 时会跳过 `tests/ros`。要执行完整合成消息通路：

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source ros2_ws/install/setup.bash
ROS_LOCALHOST_ONLY=1 python -m pytest -q tests/ros
```

它使用假的模型输出和合成图像、深度、内参，通过真实 ROS 发布订阅验证双目标结果、采集时间戳、16UC1/32FC1、无效深度及标注图 Header，不使用相机或 NPU。
有模型时另做真实 Ultralytics 离线推理检查；空白图无检出只证明加载与推理调用可用，不代表病害识别效果。

旧系统 pytest 与用户目录插件冲突时，优先在项目虚拟环境安装 dev 依赖；临时诊断可设 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 并通过 `PYTHONPATH=src` 显式提供公共包。

## 待硬件验收

- Gemini 305 枚举、udev 权限、USB 带宽和稳定取流。
- 可用分辨率、帧率、彩色画面形态，以及对齐后的深度重投影。
- 标定内参、畸变、深度单位、时间同步、无效深度与测距误差。
- 通用目标三维通路，再验证真实病害叶片和果实。
- RK3588 ARM64 驱动与推理环境、NPU 适配、精度对比、延迟、帧率和长时稳定性。

本轮实际运行的检查与环境见 [验证结果](VALIDATION_RESULTS.md)。未在此列为通过的能力不得按已验证部署能力描述。
