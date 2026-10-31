# depth_estimation 工程总结

> 更新日期 2026-09-07。本文件汇总：工程结构、底层包→上层 bringup 的参数接口、底层包漏洞隐患、近期修正记录。

## 1. 工程结构

```
depth_estimation/
├── models/                          # yolov8n.pt（验证）+ HLB_ABC/ABCD/ABCDE.pt（待换黄龙病模型）
├── src/
│   ├── OrbbecSDK_ROS2-2-main/       # 第三方相机驱动（未纳入 git）
│   ├── yahboomcar_msgs/             # 消息包：Target / TargetArray
│   ├── vision_yolo_detector/        # 下层：YOLO 2D 检测节点 + 单节点调试 launch
│   ├── vision_target_locator/       # 下层：3D 定位节点
│   └── vision_bringup/              # 上层：编排 + 参数固化（all.launch.py）
├── build/ install/ log/
└── summary.md                       # 本文件
```

**分层原则**：下层节点包只管自己的节点逻辑（声明参数、订阅/发布），上层 `vision_bringup` 集中拉起相机+检测+定位，固化运行时参数（分辨率、模型路径、类别等）。下层两包靠话题 `/yolo/targets` 解耦，互不声明依赖。

**启动**：`ros2 launch vision_bringup all.launch.py`

## 2. 底层包 → 上层 bringup 的常用参数接口

### 2.1 相机（Orbbec gemini305.launch.py，bringup 通过 launch_arguments 传）

| 参数 | 含义 | 当前值 |
|---|---|---|
| `depth_registration` | 深度对齐到 color 的开关（true=align 原位替换 depth） | `true` |
| `color_width` / `color_height` | 彩色取流分辨率 | `640` / `480` |
| `depth_width` / `depth_height` | 深度取流分辨率（=对齐后深度分辨率） | `640` / `480` |
| `color_fps` / `depth_fps` | 帧率（0=设备默认，~20Hz） | `0` |

### 2.2 vision_yolo_detector 节点（bringup 通过 Node parameters 传）

| 参数 | 含义 | 节点默认 | bringup 固化 |
|---|---|---|---|
| `model_path` | 模型权重路径 | `''`（空转等模型） | `/home/wyi/depth_estimation/models/yolov8n.pt` |
| `conf_thres` | 置信度阈值 | `0.1` | 不传（继承 0.1） |
| `target_class` | 过滤类别（空=不过滤） | `''` | `''` |
| `image_topic` | 输入图像话题 | `/camera/color/image_raw` | 不传（继承） |

### 2.3 vision_target_locator 节点（bringup 当前不传参，全用节点默认）

| 参数 | 含义 | 节点默认 |
|---|---|---|
| `depth_topic` | 深度话题（对齐版） | `/camera/depth/image_raw` |
| `depth_scale` | 深度值→米缩放（16UC1 毫米→米） | `0.001` |
| `max_depth` | 有效深度上界（米） | `10.0` |
| `min_depth` | 有效深度下界（米） | `0.1` |

> 参数优先级：命令行 `-p` > launch parameters > 节点 `declare_parameter` 默认值。

## 3. 底层包漏洞隐患排查（非参数类）

### 3.1 vision_yolo_detector

| # | 隐患 | 影响 | 建议 |
|---|---|---|---|
| D1 | **QoS 用默认 keep_last 10 reliable**，非 SensorDataQoS | 高频相机流下队列满/丢帧 | 订阅加 `qos_profile=SensorDataQoS` |
| D2 | 推理无 try/except | ultralytics 抛异常会冒泡反复 log | image_cb 推理段包 try/except，异常吞掉+warn |
| D3 | 无背压控制 | 换大模型推理慢于取流（如 imgsz=1280=10fps<20Hz）时回调堆积内存涨 | 加跳帧或队列长度监控；当前 yolov8n@640=38fps 有余量暂不爆 |
| D4 | `/yolo/annotated_image` 每帧发布 | cv2_to_imgmsg+画框占 CPU | 加 `publish_annotated` 参数，生产关闭 |
| D5 | `target_class` 推理后过滤 | 全图先检测再筛浪费算力 | 可传 ultralytics `classes=[id]` 预过滤；yolov8n 无妨 |

### 3.2 vision_target_locator

| # | 隐患 | 影响 | 建议 |
|---|---|---|---|
| L1 | **三路订阅无时间同步** | 框(t1)用最新深度(t2)，运动目标错位 | 用 `message_filters.ApproximateTimeSynchronizer` 同步 targets/depth/camera_info |
| L2 | **PointStamped stamp 用 `now()` 非检测时间** | 未来 tf2 查询按 stamp 插值会错位 | 用 Target.stamp 或深度图时间戳 |
| L3 | depth_cb 持续转换占 CPU | 高频深度流即使无目标也在 imgmsg_to_cv2 | lazy 转换：targets_cb 到来时才转当前深度帧 |
| L4 | 单线程 executor 三回调 | depth_cb 高频可能延迟 targets_cb | 换 MultiThreadedExecutor 或 lazy 转换降负 |
| L5 | `_sample_depth` 注释"3×3"但 half=5 实为稀疏9点跨10像素 | 命名误导 | 改注释为"稀疏 9 点采样"或调 half=1 |
| L6 | 中值偶数点取上中位 | 边缘裁剪后偶数点不精确 | 用 `np.median` 或补真中值 |
| L7 | 多目标只取 `msg.data[0]` | 多目标丢余 | 已知 TODO，后续扩展 |

### 3.3 优先级建议

**抓取前必处理**：L1（时间同步）、L2（stamp）——直接影响 3D 坐标准确性，且与后续 tf2 手眼标定耦合。
**稳定性**：D1（QoS）、D3（背压）、L3/L4（CPU）——长时运行稳定。
**可观察**：D4（annotated 开关）、D2（异常吞掉）。
**小修**：L5、L6、D5。

## 4. 近期修正记录

### 2026-09-07 参数穿透对齐（3 处）
1. `yolo_detector.launch.py` `conf_thres` 0.5→0.1，与节点默认及 all.launch.py 统一。
2. `yolo_detector.py` 节点 `target_class` 默认 `'cell phone'`→`''`，消除"不传参=只报手机"的隐式分裂。
3. `target_locator.py` 深度解码 `'32FC1'`→`'16UC1'`，与驱动实际编码一致（原跨编码转换能跑但不严谨）。

### 2026-09-07 工程结构重构
- 新建 `vision_bringup` 顶层包，`all.launch.py` 从 `vision_yolo_detector` 迁入，依赖在 package.xml 显式声明。
- 清理 `vision_target_locator/setup.py` 匹配空的 launch glob 冗余。
- 取流分辨率 1280×800→640×480（YOLO imgsz=640，取流高于此对检测无增益；待实机验证 profile）。

## 5. 待办（按优先级）
1. 换 HLB 模型：改 `vision_bringup/launch/all.launch.py` detector 的 `model_path`/`target_class`。
2. tf2 手眼标定：相机光学系→机械臂 base 系（locator 已留 TODO，tf2 依赖已声明）。
3. 处理 L1/L2（时间同步+stamp），为 tf2 铺路。
4. 多目标扩展（L7）。
