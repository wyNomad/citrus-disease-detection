# orbbec_305 工作空间说明

Yahboom 官方 **Orbbec Gemini 305 相机 + 视觉 demo** 工作空间，基于 ROS2 Humble。
本机路径：`/home/wyi/orbbec_305`

## 环境

- ROS2：Humble（`/opt/ros/humble`）
- 构建：`colcon build --symlink-install`
- 相机型号：Orbbec Gemini 305（对应 `gemini305.launch.py`）

## 包总览

工作空间 `src/` 下 10 个包，其中 9 个可构建，`ros2_orbslam` 暂跳过。

| 包 | 类型 | 作用 | 状态 |
|---|---|---|---|
| `orbbec_camera` | C++ | Orbbec 相机驱动（核心），发布 color/depth/IR/点云/IMU + tf | ✅ |
| `orbbec_camera_msgs` | C++ | 相机自定义消息 | ✅ |
| `orbbec_description` | C++ | 相机 URDF 模型，RViz 查看 | ✅ |
| `yahboomcar_msgs` | C++ | 通用消息：PointArray/Target/TargetArray/Position/ImageMsg | ✅ |
| `yahboomcar_slam` | C++ | SLAM 后处理（点云→octomap）、orb_slam 桥接 | ✅（但多数 launch 依赖未构建的 ros2_orbslam） |
| `yahboomcar_KCFTracker` | C++ | KCF 单目标跟踪（OpenCV + cv_bridge + image_transport） | ✅ |
| `yahboomcar_astra` | Python | 基于 HSV 的颜色识别/跟踪 | ✅ |
| `yahboomcar_visual` | Python | 图像处理工具集（显示/翻转/点云/AR/二维码） | ✅ |
| `yahboomcar_mediapipe` | Python | MediaPipe 手势/姿态/人脸/物体检测 | ✅ |
| `ros2_orbslam` | C++ | ORB_SLAM2 视觉 SLAM | ⏸ `COLCON_IGNORE` 跳过（依赖外部 ORB_SLAM2 库） |

## 环境准备（每次开终端先 source）

```bash
source /opt/ros/humble/setup.bash
source /home/wyi/orbbec_305/install/setup.bash
```

## 构建

```bash
cd /home/wyi/orbbec_305
colcon build --symlink-install
```
当前 9 包零报错构建通过。

## 各包详细信息

### orbbec_camera（核心驱动）

- **节点**：`orbbec_camera_node`（foxy）或 ComposableNode `orbbec_camera::OBCameraNodeDriver`（humble，gemini305.launch 走此路径）。
- **工具节点**：`list_devices_node`（列设备，无需接相机可用）、`set_device_ip`（网络相机）、`ob_benchmark_node`、`frame_latency_node`、`topic_statistics_node` 等。
- **默认话题**（namespace `/camera`）：
  - `/camera/color/image_raw`（彩色）
  - `/camera/depth/image_raw`（深度）
  - `/camera/depth/points`（点云）
  - `/camera/left_ir/image_raw`、`/camera/right_ir/image_raw`（红外）
  - `/camera/color/camera_info`、`/camera/depth/camera_info`
  - tf：`camera_link` 等
- **参数**：默认配置在 `config/gemini305.yaml`、`config/common.yaml`，launch 参数极多（分辨率/fps/滤镜/点云/对齐/HDR/同步…）。
- **启动**：
  ```bash
  ros2 launch orbbec_camera gemini305.launch.py            # Gemini 305
  ros2 launch orbbec_camera multi_camera.launch.py         # 多相机
  ros2 run orbbec_camera list_devices_node                 # 先确认硬件
  ```

### orbbec_description

- **作用**：相机 URDF + RViz 模型查看。
- **启动**：
  ```bash
  ros2 launch orbbec_description view_model.launch.py model:=<urdf文件名>
  ```

### yahboomcar_visual（Python，7 节点）

| 节点 | 作用 | 订阅话题 |
|---|---|---|
| `astra_rgb_image` | 显示彩色图 | `/camera/color/image_raw` |
| `astra_depth_image` | 显示深度图 | `/camera/depth/image_raw` |
| `astra_image_flip` | 图像翻转 | 相机话题 |
| `astra_color_point` | 彩色点云 | 相机话题 |
| `pub_image` | 发布/转发图像 | `/image_raw` |
| `laser_to_image` | 激光转图像叠加 | 激光话题 |
| `simple_AR` | 棋盘格 AR（需 astra.yaml 标定） | `/camera/color/image_raw` |
| `QRcode_Parsing` | 二维码识别（需 pyzbar） | `/camera/color/image_raw` |

启动：`ros2 run yahboomcar_visual <节点名>`

### yahboomcar_astra（Python，2 节点）

- **作用**：基于 HSV 的颜色识别与跟踪，订阅 `/camera/color/image_raw`，发布 `/Current_point`、`/cmd_vel`。
- **节点**：`colorHSV`（识别）、`colorTracker`（跟踪）。
- **启动**：`ros2 run yahboomcar_astra colorHSV`
- **注意**：自带 `colorTracker_X3.launch.py` 依赖外部 `yahboomcar_bringup` 包（不在本工作空间），单独无法 launch，只能 `ros2 run` 手动起。

### yahboomcar_KCFTracker（C++，1 节点）

- **作用**：KCF 单目标跟踪。
- **节点**：`KCF_Tracker_Node`。
- **启动**：
  ```bash
  ros2 run yahboomcar_KCFTracker KCF_Tracker_Node        # 手动起（配合相机或 usb_cam 话题）
  ros2 launch yahboomcar_KCFTracker KCFTracker_X3.launch.py  # 自带 usb_cam（需先装 ros-humble-usb-cam）
  ```
- **注意**：自带 launch 配 USB 摄像头（include `usb_cam`），非 Orbbec。

### yahboomcar_mediapipe（Python，6 注册节点 + 多脚本）

注册节点（可 `ros2 run`）：

| 节点 | 功能 |
|---|---|
| `01_HandDetector` | 手部检测 |
| `02_PoseDetector` | 人体姿态 |
| `03_Holistic` | 全身 Holistic |
| `04_FaceMesh` | 人脸网格 |
| `05_FaceEyeDetection` | 人脸/眼睛（用 haarcascade） |
| `test_msg` | 消息测试 |

目录内 `06`~`11` 脚本未在 setup.py 注册，需 `python3` 直接运行。

- **启动**：`ros2 run yahboomcar_mediapipe 01_HandDetector`
- **依赖**：`pip install mediapipe opencv-python`（运行时按需补）。
- **注意**：`mediapipe_points.launch.py` 依赖外部 `yahboomcar_point` 包（不在本工作空间），单独无法完整 launch。

### yahboomcar_slam（C++，多 launch）

- **launch**：`orbslam_ros_launch.py`、`orbslam_pcl_map_launch.py`、`octomap_server_launch.py`、`display_octomap_launch.py` 等。
- **注意**：多数 launch 名带 `orbslam`，依赖未构建的 `ros2_orbslam` + 外部 `yahboomcar_bringup`，当前搁置。

## 典型使用链

**链 1：相机 + 彩色图查看**
```bash
终端1: ros2 launch orbbec_camera gemini305.launch.py
终端2: ros2 run yahboomcar_visual astra_rgb_image
```

**链 2：相机 + 深度图查看**
```bash
终端1: ros2 launch orbbec_camera gemini305.launch.py
终端2: ros2 run yahboomcar_visual astra_depth_image
```

**链 3：相机 + 颜色识别**
```bash
终端1: ros2 launch orbbec_camera gemini305.launch.py
终端2: ros2 run yahboomcar_astra colorHSV
```

**链 4：USB 摄像头 + KCF 跟踪**
```bash
ros2 launch yahboomcar_KCFTracker KCFTracker_X3.launch.py   # 需先装 ros-humble-usb-cam
```

**链 5：手势识别**
```bash
终端1: ros2 launch orbbec_camera gemini305.launch.py
终端2: ros2 run yahboomcar_mediapipe 01_HandDetector
```

**调试辅助**：
```bash
ros2 run orbbec_camera list_devices_node    # 插上相机先列设备
ros2 topic list                              # 确认 /camera/... 话题
ros2 topic echo /camera/color/camera_info    # 看相机参数
```

## 注意事项

| 项 | 说明 |
|---|---|
| `yahboomcar_astra` launch | 依赖外部 `yahboomcar_bringup`（不在本工作空间），只能 `ros2 run` 单节点 |
| `yahboomcar_KCFTracker` launch | 依赖 `usb_cam`（`sudo apt install ros-humble-usb-cam`），配 USB 摄像头非 Orbbec |
| `yahboomcar_mediapipe` launch | 依赖外部 `yahboomcar_point`，只能 `ros2 run` 节点；mediapipe 需 pip 装 |
| `yahboomcar_slam` | 多数 launch 依赖未构建的 `ros2_orbslam`，当前搁置 |
| `ros2_orbslam` | 被 `COLCON_IGNORE` 跳过，需外部 ORB_SLAM2 库（详见下） |

## 本工作空间做过的修复（相对 Yahboom 原版）

1. **清理失效构建产物**：原 `build/install` 的 symlink 指向 `/home/yahboom/`，与当前 `/home/wyi/` 不符，已清理重建。
2. **补 apt 依赖**：`ros-humble-backward-ros`、`ros-humble-pangolin`、`ros-humble-image-publisher`。
3. **修 KCFTracker 源码缺陷**：`package.xml`/`CMakeLists.txt` 补 `image_transport` 依赖声明；取消注释 `target_link_libraries(... ${OpenCV_LIBRARIES})`（原被注释致 highgui 符号未链接）。
4. **消除 setup.cfg 警告**：3 个 Python 包 `script-dir`→`script_dir`、`install-scripts`→`install_scripts`。
5. **修 5 处写死绝对路径**：原厂从 `/home/yahboom`、`/home/nx-ros2` 拷贝的路径在 `/home/wyi` 下跑不通，改用 `get_package_share_directory()` + setup.py `data_files` 装资源到 share；顺手修正 `05_FaceEyeDetection.py` 的 faceDetect 原厂 bug（误指 haarcascade_eye.xml，改回 haarcascade_frontalface_default.xml）。

## 相机 color 流形态（Gemini 305，重要：旧结论已过时）

`/camera/color/image_raw`（1280×800）**当前是正常对位画面**，用户用 viewer 直看话题已确认。

- 上一轮（2026-09-04）曾判定为"固件双目拼图、512 分界、左右放反"，并在 `astra_rgb_image.py` 加 `np.concatenate` 交换两半对位；本轮（2026-09-05）发现该交换反而把正确画面搞反，已**回退**该交换与 `numpy` import，`astra_rgb_image.py` 恢复原版（imgmsg→resize→显示）。
- 推断：固件/驱动/相机配置已变化，或旧结论对场景/分界高度敏感。后续判断 color 流形态前，先 `rqt_image_view` 直看话题本身，别盲信旧结论。
- 影响：下游基于 color 的节点（colorHSV、simple_AR、QRcode_Parsing、深度对齐等）当前应在正常画面上运行；若哪天又出现画面割裂/识别异常，再按需排查 color 流形态是否再变。

## 待办：ros2_orbslam（SLAM）

当前被 `COLCON_IGNORE` 跳过。补全路线：
1. clone `raulmur/ORB_SLAM2` 源码；
2. 打自带 `docker/scripts/orbslam.patch`（补 unistd.h + install target）；
3. 解决 OpenCV4 兼容（原版面向 OpenCV3，最大坑）；
4. `bash docker/scripts/build.sh` 编 Thirdparty(DBoW2/g2o) + 本体 + `make install`；
5. `export ORB_SLAM2_ROOT_DIR=~/ORB_SLAM2`；
6. `rm src/ros2-ORB_SLAM2/COLCON_IGNORE`；
7. `colcon build --packages-select ros2_orbslam`。

注：自带 docker 基于 ubuntu18.04+Foxy+OpenCV3，不能直接复用，仅作蓝本。
