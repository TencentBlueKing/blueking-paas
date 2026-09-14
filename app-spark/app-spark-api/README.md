# app-spark-api

## 开发指南

在 `manage.py` 文件同目录下创建 `settings_local.yaml`，添加必要的配置内容：

```yaml
# 必选：统一登录页面地址
LOGIN_FULL: ...

# 必选：BKAUTH 用户认证相关配置（具体值请参考当前开发环境）
BKAUTH_BACKEND_TYPE: ...
BKAUTH_TOKEN_APP_CODE: ...
BKAUTH_TOKEN_SECRET_KEY: ...
BKAUTH_TOKEN_USER_INFO_ENDPOINT: ...
BKAUTH_USER_COOKIE_VERIFY_URL: ...

# 必选：数据库配置，必须使用 MySQL 8.X 版本以上数据库
DATABASE_NAME: ...
DATABASE_USER: ...
DATABASE_PASSWORD: ...
DATABASE_HOST: ...
DATABASE_PORT: ...
```

### 启动服务

使用 uvicorn 启动 ASGI 开发服务：

```bash
uv run uvicorn app_spark_api.asgi:application --reload
```

必须用 ASGI 服务器（uvicorn）启动。会话接口要把 Agent 的 SSE 事件流边收边转发，
在 WSGI 下这个流会被缓冲到结束才吐出来，等于失去流式的意义。

### 运行测试

```bash
uv run pytest --reuse-db tests/
```

会话相关的测试不 mock agent，而是真的 spawn agent 进程、走真实 HTTP。

## 驱动 Agent

一个会话（conversation）对应一个 Agent Runtime 进程。API 负责建会话、按需拉起 Runtime、
把用户消息发过去，并把 Runtime 返回的 AG-UI 事件流原样透传给前端。

local_process provider 会为每个 Runtime 生成独立的随机 Bearer token，随进程环境注入，并由
`AgentRuntimeClient` 自动附加到 `/health`、`/runs`、状态读取与冷恢复请求；token 不进入配置文件。

### 配置

```yaml
## Agent Runtime 的驱动方式，目前只有 local_process（在本机 spawn 进程）
AGENT_RUNTIME_PROVIDER: local_process
AGENT_RUNTIME_PROVIDER_CONFIG:
  ## agent 项目目录，`uv run --project` 指向它
  agent_project_dir: ../agent
  ## 每个 Project 的 workspace 建在这下面
  workspace_root: /tmp/app-spark/workspaces
  ## 每个会话的持久化状态（log.jsonl / ui_events.jsonl / context.json）建在这下面。
  ## 必须在 workspace_root 之外，否则 agent 自己的文件工具能改掉自己的历史。
  ## 这份状态是可丢弃的本地缓冲，权威副本在本服务的库里，见下面「会话状态的权威副本」。
  state_root: /tmp/app-spark/agent-state
  ## Runtime 回写状态时访问本服务用的地址。spawn 时会拼上会话前缀注入进去
  callback_base_url: http://127.0.0.1:8000
  ## 可选，留空则用 agent 自己的默认值
  # model: deepseek:deepseek-v4-flash
  # model_api_key: ...
  ## 可选，追加传给 agent 进程的 APP_SPARK_AGENT_* 环境变量
  # extra_env:
  #   APP_SPARK_AGENT_FAKE_DELAY_SECONDS: "3"

## 会话上下文文档存哪儿，字段见 ContextStorageConfig
AGENT_CONTEXT_STORAGE:
  backend: host_tmp_path
  root: /tmp/app-spark/agent-contexts
```

**前置条件**：local_process 用 `uv run --project <agent_project_dir> --no-sync` 拉起 Runtime，
`--no-sync` 意味着它不会在请求路径上解析依赖，所以 agent 的虚拟环境必须提前备好：

```bash
cd ../agent && uv sync
```

本地想不花钱跑通整条链路时，把 `model` 设成 `fake:write-file`——
这是 agent 内置的确定性假模型，不发起任何网络请求，
细节见 [agent/README.md](../agent/README.md) 的「假模型」一节。

### 会话状态的权威副本

Runtime 是可丢弃的，所以会话历史的权威副本在本服务这边。Runtime 在后台把三类状态推过来，
本服务只在**推进**会话时才需要 Runtime，**查看**会话从不需要：

| 数据 | 存在哪 | 谁来读 |
| --- | --- | --- |
| 原始对话记录 | `ConversationMessage` 表 | 暂无对外读接口 |
| AG-UI 事件历史 | `ConversationUiEvent` 表 | `GET .../ui-events/`，直接读库、不起容器 |
| 会话上下文 | 制品库 blob + `ConversationContextSnapshot` 行 | 冷启动时注入回 Runtime |

**一致性是最终一致的**：Runtime 是在把 AG-UI 事件流全部发完之后才 flush 的，所以客户端收到
`RUN_FINISHED` 的那一刻，本服务的库可能还差几十毫秒。要等一轮真正落定，看
`GET .../conversations/<n>/` 的 `running` 与 `replication_pending` 是否**都**回到 `false`。

只看 `running` 不够。Runtime 确实是先 flush 再释放 run guard，但 flush 超时不会让这一轮失败——
数据还在 Runtime 的本地文件里、后台任务会继续重试——run guard 照样会释放。于是完全可能出现
「Runtime 空闲，但库里还差一截」。`replication_pending` 报的就是那一截，落后到什么程度可以从
Runtime 的 `/health` 的 `pushed_*` 游标看。

**已知缺口**：冷启动不恢复 workspace 源码。恢复出来的上下文会引用一堆不存在的文件，所以
「换一个全新 Runtime 继续对话」目前只在讨论层面成立，不在继续编码层面成立。衔接点是
`ProjectSourceStorage`：注入 context 之前先把源码 `get()` 回来。

### 会话的生命周期

一个会话只有两种状态，由 `Conversation.closed_at` 一个字段决定：`null` 表示还活着（live，还能
继续推进），有值表示已经结束。`POST .../conversations/<n>/close/` 是唯一的结束入口，重复调用
返回 409。

**live 说的不是「此刻有没有 Runtime 在跑」**，这点容易搞混。Runtime 是可丢弃的，会被反复回收和
重新拉起，而且它的进程句柄只在内存里、本服务一重启就全没了——拿它当会话状态的话，同一个会话会
因为一次无关的重启从 live 变成非 live，下一轮对话又把它变回来。要看某个会话此刻的运行情况，看
`GET .../conversations/<n>/` 的 `running` 与 `replication_pending`；会话列表刻意不报这些，否则
一页 20 条就是 20 次 `/health` 请求。

结束会话同时也是 Runtime 唯一的对外回收入口，走的就是 `terminate_runtime()`：先把上面那套
`state_epoch` 吊销机制真正用上，让之前签发的回写 token 全部作废，**然后**才去停进程。这个顺序
是有讲究的：停进程是尽力而为（进程可能已经没了、可能不理信号、也可能本服务早就跟丢了），吊销
token 才是「不会再有东西以这个会话的名义写进来」的保证——所以停不掉只记日志，而不是把吊销挡在
后面。停掉之后它占着的 Project workspace 被交还，同一个 Project 的下一个会话才能开起来（一个
workspace 同时只容得下一个 Runtime）。如果此刻正有一轮对话在跑，它会被打断，客户端那条 SSE 流
上会收到一个 AG-UI `RUN_ERROR` 事件。

会话结束后历史仍然可读，只是不能再发起新的一轮对话——`start_run` 里有闸门拦着，否则「结束」
只是杀掉了一个进程，下一轮对话会照常把 Runtime 重新拉起来。闸门有两道，因为拉起 Runtime 要花
好几秒，够另一个请求在这中间把会话结束掉：进来时看一次，Runtime 拉起来之后再回库确认一次，
确认没过就把刚拉起来的 Runtime 收掉并返回 409（见 `_reject_if_closed_meanwhile()`）。

## 部署相关

### 镜像构建

项目提供 [Dockerfile](Dockerfile)，以父目录 `app-spark/` 为构建上下文，
包含 API 和 Agent 各自的生产依赖。**镜像中包含 Agent 是为了支持当前的 `local_process` 驱动。**
