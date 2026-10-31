# 本地数据

数据不提交 Git。原始配对数据放在 `raw/<dataset>/images` 与 `raw/<dataset>/labels`，划分结果可放在 `citrus_mini/`。
训练数据配置位于 `configs/datasets/citrus.yaml`。
使用 `citrus-prepare-data --help` 查看参数。输出目录存在时拒绝执行，选择新目录可保留旧数据。
