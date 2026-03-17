# Usage Guide

本文档基于当前 `nanoclaw-mini` 代码状态编写，适用于本仓库现在这版 `CLI-only + Codex OAuth-only` 运行方式。

## 1. 环境要求

- Python `3.11+`
- 可用的 OpenAI Codex 网页授权登录环境
- 本地可执行 `pip`

## 2. 安装

```powershell
cd C:\Users\LAB\Downloads\new\nanoclaw-mini
python -m pip install -e .
```

安装后建议先初始化：

```powershell
nanoclaw-mini onboard
```

如果脚本命令不可用，可以使用：

```powershell
python -m nanoclaw_mini onboard
```

## 3. 登录

当前只支持一种 provider：

- `OpenAI Codex OAuth`

登录命令：

```powershell
nanoclaw-mini provider login codex
```

你也可以使用等价名称：

```powershell
nanoclaw-mini provider login openai-codex
```

登录完成后建议检查状态：

```powershell
nanoclaw-mini status
```

## 4. 配置文件

默认配置文件路径：

- `~/.nanoclaw-mini/config.json`

当前默认配置与运行数据目录位于 `~/.nanoclaw-mini/`。
为了兼容旧环境，运行时仍会尝试读取旧的 `~/.nanobot/config.json`。

配置支持 `camelCase` 和 `snake_case` 两种写法。

### 最小配置

```json
{
  "agents": {
    "defaults": {
      "model": "openai-codex/gpt-5.1-codex"
    }
  }
}
```

### 推荐配置示例

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.nanoclaw-mini/workspace",
      "model": "openai-codex/gpt-5.1-codex",
      "provider": "openai_codex",
      "maxTokens": 8192,
      "contextWindowTokens": 65536,
      "temperature": 0.1,
      "maxToolIterations": 40
    }
  },
  "interaction": {
    "sendProgress": true,
    "sendToolHints": false
  },
  "gateway": {
    "heartbeat": {
      "enabled": true,
      "intervalS": 1800
    }
  },
  "tools": {
    "restrictToWorkspace": false,
    "exec": {
      "timeout": 60,
      "pathAppend": ""
    },
    "mcpServers": {}
  }
}
```

## 5. 常用命令

### 单次调用

```powershell
nanoclaw-mini agent -m "Hello!"
```

### 交互式对话

```powershell
nanoclaw-mini agent
```

### 指定 session

```powershell
nanoclaw-mini agent -s "cli:project-a"
```

### 指定 workspace

```powershell
nanoclaw-mini agent -w "D:\\work\\repo"
```

### 指定 config 文件

```powershell
nanoclaw-mini agent -c "D:\\configs\\nanoclaw-mini.json" -m "Check this workspace"
```

### 查看状态

```powershell
nanoclaw-mini status
```

### 启动后台 gateway

```powershell
nanoclaw-mini gateway
```

这里的 `gateway` 不再监听网络端口，它当前只负责：

- 运行 `cron`
- 运行 `heartbeat`
- 驱动后台 agent loop

## 6. Workspace 结构

执行 `onboard` 后，默认会准备 `~/.nanoclaw-mini/workspace`。

其中重要文件和目录包括：

- `AGENTS.md`：agent 行为与团队约束
- `SOUL.md`：长期身份与风格补充
- `USER.md`：用户相关偏好
- `TOOLS.md`：工具约束说明
- `HEARTBEAT.md`：heartbeat 检查任务来源
- `memory/MEMORY.md`：长期记忆
- `skills/<name>/SKILL.md`：自定义技能

## 7. 文件与命令能力

当前默认工具集包括：

- `read_file`
- `write_file`
- `edit_file`
- `list_dir`
- `exec`
- `message`
- `spawn`
- `cron`

说明：

- `exec` 带有基础安全拦截，危险命令和内网 URL 会被阻止
- 当 `tools.restrictToWorkspace=true` 时，文件和命令能力会更严格地限制在 workspace 内
- `cron` 工具需要通过 agent 使用，不是单独的 CLI 子命令

## 8. MCP 配置示例

如果你要接 MCP server，可以在配置里补 `tools.mcpServers`。

示例：

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "toolTimeout": 30,
        "enabledTools": ["*"]
      }
    }
  }
}
```

支持的 MCP transport：

- `stdio`
- `sse`
- `streamableHttp`

## 9. 定时任务与 Heartbeat

`gateway` 模式下会启用：

- `CronService`
- `HeartbeatService`

行为说明：

- `cron` 负责计划任务和提醒
- `heartbeat` 会周期性读取 workspace 下的 `HEARTBEAT.md`
- 当 heartbeat 判断存在待执行任务时，会将任务送入完整 agent loop

## 10. 常见问题

### 1. `nanoclaw-mini` 命令不可用

改用：

```powershell
python -m nanoclaw_mini <command>
```

### 2. `status` 显示 not logged in

重新执行：

```powershell
nanoclaw-mini provider login codex
```

### 3. `gateway` 启动后看起来“没反应”

这是正常现象。当前 `gateway` 不是聊天入口，它会常驻等待：

- cron 触发
- heartbeat 周期唤醒
- 后台任务执行

### 4. shell 命令被拦截

这是 `exec` 工具的安全保护。典型原因包括：

- 命令包含危险删除模式
- 命令访问了内网 / 私网 / `localhost` URL
- 开启了 workspace 限制后，命令访问了外部路径

### 5. 配置文件编码问题

当前加载器已经兼容 `UTF-8 BOM`，但仍建议把 `config.json` 保存为标准 `UTF-8`。
