# 环境与相机依赖

基线：Ubuntu 22.04、Python 3.10、ROS 2 Humble。笔记本开发与 RK3588 ARM64 运行分别建立环境，不复制 `.venv`、`build` 或 `install`。

## Python 环境

从仓库根目录：

```bash
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade 'pip<26' 'setuptools>=68,<80' wheel
python -m pip install -e . -r requirements/laptop.txt -r requirements/dev.txt
```

`--system-site-packages` 使虚拟环境可见 apt 安装的 ROS 和 cv_bridge；仍需 source ROS 环境。
NumPy 限制为 1.x，OpenCV wheel 限制为 `<4.12`，避免在 ROS Humble 环境拉入要求 NumPy 2 的组合。
已有匹配的 PyTorch 时按对应硬件管理，不把笔记本 CUDA wheel 拷到 ARM64。

## ROS 依赖

已安装 ROS Humble 的机器按需补齐：

```bash
sudo apt install git patch python3-colcon-common-extensions python3-rosdep python3-venv ros-humble-cv-bridge ros-humble-message-filters
source /opt/ros/humble/setup.bash
```

未配置 rosdep 的新机器先按 ROS 官方流程初始化；然后安装源码声明的系统依赖：

```bash
rosdep install --from-paths ros2_ws/src --ignore-src -r -y
```

先准备驱动再运行 rosdep，可以覆盖驱动的系统依赖。公共包的 ROS 包装引用同一份源代码，并导出到 overlay，供系统 ros2 启动器读取；推理环境仍由虚拟环境提供。
`citrus_bringup` 不强制声明驱动为必须安装的运行依赖，因此没有驱动也能构建和测试业务节点；启动相机时才需要 `orbbec_camera`。

## 驱动

默认拉取固定提交并应用点云补丁，不跟随移动分支：

```bash
python scripts/setup_camera.py
```

也可从已有 v2.7.6 目录导入，导入不会修改原资料：

```bash
python scripts/setup_camera.py --source /absolute/path/OrbbecSDK_ROS2-2-main
```

输出为 `ros2_ws/src/vendor/orbbec`，不入 Git。脚本拒绝覆盖已有目录；失败后先检查不完整的目标目录，再删除该目录重试。
版本、补丁和本地差异见 [依赖说明](../dependencies/README.md)。相机 udev 规则在获取的驱动 `orbbec_camera/scripts` 内，使用前阅读安装脚本。

## 构建

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
python scripts/build_ros.py
source ros2_ws/install/setup.bash
```

只构建本仓库的五个包时使用 `python scripts/build_ros.py --core-only`。
不要同时 source 旧工作空间和本仓库的 overlay，避免同名驱动覆盖。

构建脚本使用当前 Python 解释器运行 colcon，并明确传递 CMake Python 路径，确保 ROS 节点能读取该虚拟环境的模型依赖。构建和运行均使用同一个环境；更换环境后重新构建。

升级旧整合版本时，在未加载 ROS overlay 的终端执行 `.venv/bin/python -m pip uninstall citrus-vision`，再执行 `.venv/bin/python -m pip install -e .`。新的 Python 发行包使用 `citrus-vision-core`，避免与 ROS 包的归一化名称冲突。
