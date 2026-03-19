# Acknowledgements

`nanoclaw-mini` 是一个持续演化中的精简项目。

它与以下上游项目存在明确的来源关系与思想继承：

- [HKUDS/nanobot](https://github.com/HKUDS/nanobot)
- [openclaw/openclaw](https://github.com/openclaw/openclaw)

## 关系说明

当前仓库并不是对上游项目的原样镜像，而是在其基础上做了持续裁剪、保留与重组，形成了一个更聚焦于以下方向的 Python 版本：

- 本地 CLI 交互
- Codex OAuth 登录
- 文件 / Shell / memory / cron / heartbeat 等基础设施能力

同时，这个仓库主动移除了大量外围能力，例如：

- 多聊天渠道接入
- Web 搜索与抓取
- 多 provider 适配层
- 面向公网接入的网关形态

## 致谢

感谢上游项目的作者与贡献者为 agent runtime、tooling、交互模式与工程组织方式提供的启发与基础。

## License / Notice

本仓库当前使用根目录中的 `LICENSE`。

如果你需要进一步追溯来源、复用边界或上游通知信息，请直接查看对应上游仓库中的 license / notice / readme 文件。
