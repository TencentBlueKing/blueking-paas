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

另一个缺口是目前没有任何对外接口会终止 Runtime，所以上面那套吊销机制装好了但还没有调用点；
真正开始回收 Runtime（尤其换成沙箱之后）时，回收路径必须走 `terminate_runtime()`。
