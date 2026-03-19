# Project

## 愿景

`nanoclaw-mini` 将长期聚焦于人工智能基础设施的建设和发展。

这里的“基础设施”不是单指模型接入，而是指一个可以长期演进的、本地优先、可组合、可扩展的 agent runtime：

- 身份与上下文管理
- 文件与命令能力
- 记忆与会话持久化
- 技能系统
- 子代理协作
- 后台调度与 heartbeat

## 当前定位

`nanoclaw-mini` 当前是一个：

- Python 项目
- CLI-first agent runtime
- Codex OAuth-only provider 方案
- 面向本地工作区和自动化任务的基础设施底座

它不是：

- 多渠道聊天机器人平台
- 通用 SaaS 控制台
- 以网页搜索、信息聚合为核心的产品

## 设计原则

### 1. 先保留核心，再做扩展

优先保留真正影响 agent runtime 的基础设施能力，而不是先做外围渠道和接入层。

### 2. 本地优先

围绕本地 workspace、文件系统、命令执行与持续记忆构建核心体验。

### 3. 接口尽量少

减少 provider、channel、bridge 等表面积，避免让项目在接入层上过度膨胀。

### 4. 组合优于堆叠

通过 `subagent`、`cron` 这些可组合模块来增强能力，而不是不断叠加分散入口。

### 5. 以长期维护为前提

保持代码结构可以被继续瘦身、重构和演化，不追求一次性的大而全。

## 当前保留范围

- OpenAI Codex OAuth 登录
- CLI 直接交互
- 文件工具
- Shell 工具与安全防护
- Session / Memory
- Subagent
- Cron
- Heartbeat

## 当前主动裁剪的范围

- 所有外部聊天渠道
- Telegram 集成
- 网页搜索与网页抓取
- 多 provider 支持
- 对外暴露网络端口的 gateway

## 中长期方向

- 继续打磨本地 agent runtime 的稳定性
- 继续收紧无用耦合和历史兼容层
- 让 workspace、memory 的协同更清晰
- 提升调度与子代理的组合能力
- 保持文档、安装体验和公开仓库形态更清楚

## 非目标

至少在当前阶段，`nanoclaw-mini` 不以这些方向为优先目标：

- 做成多平台消息聚合器
- 为各种模型厂商维护大量 provider 适配
- 以浏览器端产品体验为中心
- 追求“大而全”的通用 agent 平台叙事
