# 协作约定

修改公共检测或几何行为时，同时检查离线入口和 ROS 适配。类别字段、时间戳、像素坐标、深度单位和光学坐标系约定见 [架构](docs/ARCHITECTURE.md)。
目录职责与开发导航见 [仓库结构说明](docs/REPOSITORY_GUIDE.md)。

不要提交数据集、权重、第三方 SDK、venv 或构建产物。相机依赖通过固定提交加补丁管理。

| 修改类型 | 本地校验 |
| --- | --- |
| 文档、SVG、Issue/PR 模板 | 静态检查与 `git diff --check` |
| 公共算法、配置或 CLI | 静态检查及相关核心测试 |
| ROS 消息、节点或启动 | 构建项目包并运行完整 ROS 测试 |
| 训练、导出或依赖 | 实际小规模训练与导出检查、相关回归 |

```bash
python .github/scripts/check_repository.py
git diff --check
```

核心测试使用 `CITRUS_FAIL_ON_SKIP=1 python -m pytest -q --ignore=tests/ros`；完整测试需先构建并加载 ROS overlay，再执行 `CITRUS_FAIL_ON_SKIP=1 python -m pytest -q`。

涉及 ROS 消息或节点时还需构建并执行合成 ROS 测试，见 [验证说明](docs/VALIDATION.md)。没有相机或板卡时如实标记待实测，不将合成测试当成硬件通过。
训练实验保留数据版本、随机种子、超参数、代码提交与结果。依赖升级需要记录实际验证的版本组合。
提交说明写清触发条件、改变后的行为、实际验证和剩余边界。
