# 运行与配置切换

所有示例从仓库根目录执行，先安装公共包。权重相对路径均相对 `--weights-dir` / `weights_dir`，默认当前工作目录的 `weights`。
从其他目录启动时，传绝对的配置路径和模型目录；不依赖 `/home/wyi`。

## 离线检测

```bash
citrus-detect --config configs/runtime/generic.yaml --weights-dir weights --source /absolute/path/image.jpg --output runs/detect-001 --save-images
citrus-detect --config configs/runtime/citrus.yaml --weights-dir weights --source data/citrus_mini/images/val --output runs/citrus-detect
```

支持单图、图片目录、视频路径和摄像头编号；只有 ROS 管线使用 Gemini 305 的对齐深度。离线检测仅输出 2D 像素，不能凭单张彩色图生成实测三维坐标。
输出为每帧一行的 JSONL，含类别 ID/名称、置信度、原图尺寸、框和中心。可选保存标注帧。输出目录存在时拒绝执行，避免覆盖已有 JSONL 和图片；每次运行需选择新目录。

## 模型配置

| 配置 | 权重位置 | 用途 |
| --- | --- | --- |
| `configs/runtime/generic.yaml` | `weights/yolov8n.pt` | 使用日常物体测试坐标通路 |
| `configs/runtime/citrus.yaml` | `weights/citrus/best.pt` | 最终病害模型 |

`target_classes: []` 表示不过滤。可填模型内的完整类别名，如 `[bottle]`；名称不存在时启动报错，避免切换模型后静默无结果。
`device`、置信度、IoU、输入尺寸和 `publish_annotated` 均可配置。
训练类别顺序保持原 GitHub 配置，不能把旧 HLB 权重默认为相同标签或相同模型结构。

## 相机管线

准备驱动、构建并 source 后：

```bash
ros2 launch citrus_bringup pipeline.launch.py profile:=generic weights_dir:="$PWD/weights"
ros2 launch citrus_bringup pipeline.launch.py profile:=citrus weights_dir:="$PWD/weights"
ros2 topic echo /citrus/targets_3d
```

使用自定义配置：

```bash
ros2 launch citrus_bringup pipeline.launch.py profile_file:="$PWD/configs/runtime/generic.yaml" camera_file:="$PWD/configs/cameras/gemini305.yaml" weights_dir:="$PWD/weights"
```

相机配置是传给驱动 launch 的参数，不是 ROS 节点参数文件。默认使用设备自动分辨率与帧率，具体可用 profile 待实机核对；模型输入 640 不代表相机必须输出 640。
启动文件默认显式启用深度对齐到 COLOR、帧同步与深度尺度归一，关闭点云和额外的 1.5 米截断过滤。

外部相机或回放已有图像/深度/内参时：

```bash
ros2 launch citrus_bringup pipeline.launch.py start_camera:=false weights_dir:="$PWD/weights"
```

外部数据必须满足 [几何与消息约定](ARCHITECTURE.md)，话题可在运行配置的 `topics` 中调整。
启动时没有模型会报错退出；有模型但没有相机或外部数据时节点等待输入，不会伪造检测或位置。

检测、内参和深度帧必须使用相同的彩色光学坐标系；仅尺寸相同的原始深度帧会被拒绝。业务进程异常退出时，启动命令返回非零状态；正常 Ctrl+C 停止保持正常退出。
