# nanoclaw-mini

<p align="center">
  <img src="./nanoclaw_mini.png" alt="nanoclaw-mini" width="360">
</p>

`nanoclaw-mini` 是一个基于 Python 的、`CLI-first` 的 AI 基础设施项目。

它来自对 [nanobot](https://github.com/HKUDS/nanobot) 和 [openclaw](https://github.com/openclaw/openclaw) 思路与代码的持续精简与重组，当前版本聚焦在一个更小、更直接、更适合本地工作流的方向上：

- 只保留 `OpenAI Codex OAuth` 授权登录
- 只保留本地 `CLI` 交互
- 保留文件、Shell、记忆、子代理、定时任务与 heartbeat 等核心基础设施能力
- 移除多渠道接入、网页搜索/抓取、API Key provider、网络暴露式 gateway 等外围能力

## 项目定位

`nanoclaw-mini` 不是一个“全渠道聊天机器人平台”，而是一个围绕本地工作区和 agent runtime 构建的 AI 基础设施底座。

它当前更适合这些场景：

- 本地代码与文档协作
- 基于工作区文件的长期 AI 助手
- 通过 `cron` 和 `heartbeat` 承载长期运行任务
- 持续沉淀可复用的 memory 与 agent workflow

## 核心能力

- `Codex OAuth only`：唯一 provider 为 OpenAI Codex 网页授权登录
- `CLI chat`：支持单次调用和交互式对话
- `Filesystem tools`：读、写、编辑、列目录
- `Shell tool`：带基础安全防护的命令执行
- `Memory + Session`：会话持久化与记忆整合
- `Subagents`：支持后台子代理执行
- `Gateway`：支持 cron 与 heartbeat 后台运行

## 当前不包含

- Telegram / Discord / WhatsApp / Slack 等聊天渠道
- 网页搜索与网页抓取
- OpenAI API Key / LiteLLM / 多 provider 适配层
- 对外监听端口的网关服务

## 快速开始

```powershell
cd C:\Users\LAB\Downloads\new\nanoclaw-mini
python -m pip install -e .
nanoclaw-mini onboard
nanoclaw-mini provider login codex
nanoclaw-mini status
nanoclaw-mini agent -m "Hello!"
```

如果 `nanoclaw-mini` 没有进入 `PATH`，可以使用模块方式：

```powershell
python -m nanoclaw_mini onboard
python -m nanoclaw_mini provider login codex
python -m nanoclaw_mini agent -m "Hello!"
```

## 最小配置

默认配置文件路径是：

- `~/.nanoclaw-mini/config.json`

最小可用配置示例：

```json
{
  "agents": {
    "defaults": {
      "model": "openai-codex/gpt-5.1-codex"
    }
  }
}
```

运行 `onboard` 后，默认 workspace 位于：

- `~/.nanoclaw-mini/workspace`

其中会自动同步这些基础文件：

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md`
- `HEARTBEAT.md`
- `memory/MEMORY.md`

## 常用命令

```powershell
nanoclaw-mini onboard
nanoclaw-mini provider login codex
nanoclaw-mini models list
nanoclaw-mini models choose
nanoclaw-mini models set gpt-5.4-mini
nanoclaw-mini status
nanoclaw-mini agent
nanoclaw-mini agent -m "Summarize this project"
nanoclaw-mini gateway
```

## 文档导航

- [USAGE.md](./USAGE.md): 安装、登录、配置、命令与常见问题
- [PROJECT.md](./PROJECT.md): 项目定位、设计原则、当前边界与长期方向
- [ACKNOWLEDGEMENTS.md](./ACKNOWLEDGEMENTS.md): 上游来源、关系说明与致谢
- [CONTRIBUTING.md](./CONTRIBUTING.md): 提交 issue / PR 与本地检查建议
- [nanoclaw-mini-desktop/README.md](./nanoclaw-mini-desktop/README.md): Rust 桌面安装器 / 更新器

## 说明

- 当前公开项目名是 `nanoclaw-mini`
- 当前 Python 包目录是 `nanoclaw_mini`
- 默认运行数据目录是 `~/.nanoclaw-mini/`
- 如果你之前已经在本机执行过 `pip install -e .`，改名后请重新执行一次安装以刷新命令入口

## License

本仓库当前使用根目录中的 [LICENSE](./LICENSE)。
