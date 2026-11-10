# app-spark-api

AppSpark 的控制面服务：管理 Project 和会话，为每个会话按需拉起 Agent Runtime，把用户消息转给它，再把它返回的
AG-UI 事件流原样转给前端。

**上手开发**从[开发指南](docs/dev_guide.md)开始，里面有本地最小配置、怎么启动和调用接口、测试怎么分层，以及镜像
构建。第一次本地跑通，先 `cd ../agent && uv sync` 备好 agent 的虚拟环境，再按最小配置用假模型，不需要任何模型凭据。
所有配置项的说明、默认值和是否必填，以 [conf.yaml.tpl](conf.yaml.tpl) 为准。

**会话**是用户和 Agent 围绕一个 Project 的一段连续对话。Runtime 可以随时丢弃，会话历史以本服务的库为准，新
Runtime 靠冷恢复接上之前的历史；生命周期、一轮对话、结束会话和冷恢复见[会话](docs/conversation.md)。

**驱动 Agent** 有两套互相独立的配置：Runtime 跑在哪由 [Agent Runtime provider](docs/agent_providers.md) 决定，
本地开发用 `local_process`，生产用 `e2b`；Runtime 调哪个模型由 [Agent 的模型](docs/agent_llm.md) 决定，可以直连厂商、
用假模型，或者走 bkaidev 网关。

**源码和发布**：每个 Project 的源码存在自己的 Git 仓库里，Agent 每轮提交并推送，见[源码仓库](docs/repo_server.md)；
项目所有者可以把某个版本发布到蓝鲸开发者中心，见[发布到开发者中心](docs/publish.md)。

**其他**：本服务自己调用的模型（给项目起名）、bkaidev 网关的 thinking 白名单，以及工作区应用的预览，见
[其他](docs/misc.md)。

## 文档索引

- [开发指南](docs/dev_guide.md)
  - [本地配置](docs/dev_guide.md#本地配置)
  - [启动服务](docs/dev_guide.md#启动服务)
  - [调用接口](docs/dev_guide.md#调用接口)
  - [测试](docs/dev_guide.md#测试)
  - [部署](docs/dev_guide.md#部署)
- [配置模板 conf.yaml.tpl](conf.yaml.tpl)
- [会话](docs/conversation.md)
  - [生命周期](docs/conversation.md#生命周期)
  - [一轮对话](docs/conversation.md#一轮对话)
  - [结束会话](docs/conversation.md#结束会话)
  - [权威副本](docs/conversation.md#权威副本)
  - [冷恢复](docs/conversation.md#冷恢复)
  - [归档数据维护](docs/conversation.md#归档数据维护)
- [Agent Runtime provider](docs/agent_providers.md)
  - [local_process](docs/agent_providers.md#local_process)
  - [e2b](docs/agent_providers.md#e2b)
- [Agent 的模型](docs/agent_llm.md)
  - [使用 direct 和 fake 模型](docs/agent_llm.md#使用-direct-和-fake-模型)
  - [使用 bkaidev 模型](docs/agent_llm.md#使用-bkaidev-模型)
  - [选择模型](docs/agent_llm.md#选择模型)
- [源码仓库](docs/repo_server.md)
  - [源码怎么保存](docs/repo_server.md#源码怎么保存)
  - [Runtime 怎么拿到仓库](docs/repo_server.md#runtime-怎么拿到仓库)
  - [源码生命周期管理](docs/repo_server.md#源码生命周期管理)
- [发布到开发者中心](docs/publish.md)
  - [前置要求](docs/publish.md#前置要求)
  - [怎么工作](docs/publish.md#怎么工作)
  - [关键设计决策](docs/publish.md#关键设计决策)
- [其他](docs/misc.md)
  - [本服务调用的模型](docs/misc.md#本服务调用的模型)
  - [bkaidev 网关的 thinking 支持](docs/misc.md#bkaidev-网关的-thinking-支持)
  - [工作区应用的预览](docs/misc.md#工作区应用的预览)
