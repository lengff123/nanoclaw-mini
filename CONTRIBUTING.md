# Contributing

欢迎提交 issue、文档改进和代码改进。

## 建议的贡献方向

- 改进 CLI 体验
- 改进 workspace / memory 协同
- 改进 cron、heartbeat 等基础设施能力
- 改进文档、安装流程与公开仓库说明
- 清理历史兼容层和死代码

## 提交前建议

由于当前仓库已经不是完整上游开发形态，提交前建议至少完成这些检查：

```powershell
python -m compileall nanoclaw_mini
python -m nanoclaw_mini --help
python -m nanoclaw_mini agent --help
```

如果你的修改涉及文档，请确认：

- README 中的命令与当前代码一致
- 示例配置与当前 `schema.py` 一致
- 不要把已经删除的能力重新写回文档

## 风格建议

- 优先做小而清晰的改动
- 优先删除无用复杂度，而不是增加新的兼容层
- 文档请尽量与代码现状保持一致
- 新增能力时，尽量说明它在整体基础设施中的位置

## Issue / PR 说明建议

提交问题或改动时，建议写清：

- 背景与目标
- 期望行为
- 当前行为
- 影响范围
- 是否涉及公开接口或配置结构变化
