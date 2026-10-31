# 架构与接口

本阶段终点是相机光学坐标系下的目标位置，不包含手眼标定、底盘、机械臂控制和自动抓取。

## 模块边界

- `citrus_vision` 是普通 Python 包，既不导入 ROS，也不依赖相机驱动。离线检测和 ROS 检测节点调用同一推理接口。
- `citrus_interfaces` 定义 2D 检测与 3D 结果，不复用 `frame_id` 存类别名。
- `citrus_detector` 订阅图像并推理，原样保留输入 Header。深度为 1 的输入队列减少慢推理时旧帧积压，不承诺固定帧率。
- `citrus_localizer` 按采集时间近似同步检测与深度；缓存彩色 CameraInfo，校验分辨率与坐标系。内参不必每帧参与同步，启动及标定变化后必须获取有效信息。
- `citrus_bringup` 组合相机、检测、定位；模型缺失时先报错，业务节点退出时关闭整个启动链。

公共检测结果为 `Detection(class_id, class_name, confidence, xyxy)`，中心点由原始图像框计算。推理后端负责撤销缩放和 letterbox，定位层不关心模型家族。
公共模块的 ROS 包装通过仓库内相对符号链接复用源代码，避免 pip 与 ROS 维护两份实现。
当前后端实现为 `ultralytics`。`rknn` 是明确报未实现的预留接口，不能用于生产运行。

## 消息

| 话题 | 类型 | 语义 |
| --- | --- | --- |
| `/citrus/detections` | `citrus_interfaces/Detection2DArray` | 彩色采集 Header、原始宽高、全部检测框及类别 |
| `/citrus/targets_3d` | `citrus_interfaces/Target3DArray` | 彩色采集 Header、匹配深度时间戳、各目标位置和有效性 |
| `/citrus/annotated_image` | `sensor_msgs/Image` | 可选显示图，保留原 Header，默认关闭 |

`detection_index` 只标识本帧中的检测序号，不是跨帧跟踪 ID。
`depth_valid=false` 时必须忽略坐标，NaN 防止误当成原点。整帧缺少有效标定或尺寸不匹配时不发布三维结果，并节流输出警告。
输入图像和深度使用 SensorData QoS；输出目标数组使用默认 reliable QoS。

## 几何前提

深度必须已经对齐到彩色图，三者宽高一致；仅分辨率相等不足以证明对齐正确。启用 `depth_registration`，拿到硬件后需检查重投影。
`16UC1` 按配置深度比例转换为米；当前驱动启用 `enable_depth_scale`，默认比例 0.001，仍需实机核对。
`32FC1` 按 ROS 浮点深度约定直接视为米，不再次乘 0.001。

深度取框中心邻域的有效值中位数，剔除零、NaN、Inf 和范围外的值。非零畸变使用 K/D 与 OpenCV 反畸变求射线；分箱或局部 ROI 标定暂不支持。
无畸变情况下：`x=(u-cx)*z/fx`，`y=(v-cy)*z/fy`。
结果代表中心邻域可见表面位置，不等于物体几何中心或可直接执行的抓取点。叶片边缘、背景混入和遮挡需要后续实测评估。

同步窗口默认 0.04 秒、缓存 30 帧，可在运行配置调整。它约束采集时间差，不能消除运动误差；推理延迟超过缓存保留时间会导致匹配失败。
