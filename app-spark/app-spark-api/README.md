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

# 必选：EncryptField 使用的 Fernet key，必须自己生成且保持稳定
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
BKKRILL_ENCRYPT_SECRET_KEY: ...
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
| 会话上下文 | 制品库 blob + `ConversationContextVersion` 行（一版一行） | 冷启动时注入回 Runtime |
| 可恢复检查点 | `ConversationCheckpoint` 行 | 冷启动时先据此把文件放回去 |

**一致性是最终一致的**：Runtime 是在把 AG-UI 事件流全部发完之后才 flush 的，所以客户端收到
`RUN_FINISHED` 的那一刻，本服务的库可能还差几十毫秒。要等一轮真正落定，看
`GET .../conversations/<n>/` 的 `running` 与 `replication_pending` 是否**都**回到 `false`。

只看 `running` 不够。Runtime 确实是先 flush 再释放 run guard，但 flush 超时不会让这一轮失败——
数据还在 Runtime 的本地文件里、后台任务会继续重试——run guard 照样会释放。于是完全可能出现
「Runtime 空闲，但库里还差一截」。`replication_pending` 报的就是那一截，落后到什么程度可以从
Runtime 的 `/health` 的 `pushed_*` 游标看。

#### 冷恢复：先文件，后上下文

冷启动恢复的依据是**检查点**，不是「最新的上下文」。一个检查点由一个仓库提交（连同钉住它的
远端 tag）和一个上下文版本组成，两者必须描述**同一个时刻**。

两半从两条路、按不确定的先后到达本服务：提交由 Runtime 的后台 push 上报，上下文由复制通道推
过来。所以「可恢复」不做成一个由某条路径去置位的字段，而是一个查询——检查点行在、且它引用的那
一版上下文行也在。字段要两条路径都记得置位，还要防住两者交错到达；查询没有这个时序问题。

由此，**「代码已推送、上下文尚未保存」和反过来的情况都不算恢复点**。这不是保守，是必要的：文
件和记忆描述的不是同一个时刻时，恢复出来的 Runtime 不会崩，它只会拿着记得别的文件的模型接着
写代码，而错误要到好几轮之后才看得出来。碰到半成品状态时宁可退回「只恢复上下文」，也不拿一份
对不上的配对去继续。

恢复顺序是**先文件、后上下文、最后才接受新 run**（`_resume_if_cold`）。反过来会留下一个窗口：
Runtime 记得自己写过一些还没落盘的代码，这时进来一轮 run，模型就会基于这个错位行动。

- **同一会话**冷恢复用它自己配套的那个检查点，游标也取自检查点，而不是「现在库里存到哪」。
- **换会话**继承 Project 最新的代码：Agent 侧发现工作区已经在检查点**之后**，会保留较新的工作
  并回 `superseded`，不会被旧会话的检查点回滚掉。
- 远端不可用、提交找不到、或检查点引用的上下文版本读不出来时**显式失败**，不静默从空工作区开
  始。

#### 上下文版本的保留与回收

每一版上下文单独存一份 blob（key 里带版本号），否则检查点够不到「和它的提交配套的那一版」——
就地覆盖的 blob 只能回答「最新是什么」。普通冷启动要的「最新一版」不另记指针，就是版本号最大
的那一行。代价是版本会累积，所以保留策略是硬性配套的：

```yaml
AGENT_CONTEXT_VERSIONS_KEPT: 5   # 除被检查点引用的版本外，额外保留的最近版本数
AGENT_CHECKPOINTS_KEPT: 3        # 一个会话保留的最近检查点数
```

两个数缺一不可。检查点会钉住它引用的那一版不让回收，所以只限版本数、不限检查点数的话，blob
仍然会无上限增长——真正兜底的是检查点这一侧。留 3 个是余量：实际能被用上的只有「和最新上下文
版本配套」的那一个，多留两个是为了容忍提交上报与上下文归档之间的乱序。两个值都会被抬到至少
1，配成 0 等于关掉冷启动。

回收在归档新版本之后顺带做，顺序是**先淘汰检查点、再删版本**（先删检查点，被它钉住的版本才能
在同一次回收里一起走），删版本时**先删行、再删 blob**。反过来的话，一次失败的远端删除会留下一
行指向已经不存在的文档，而那正好是冷启动最没法处理的状态——行说有，读出来没有。孤儿 blob 只是
占空间。被淘汰的检查点在远端留下的 tag 不跟着删：删远端引用是一次可能失败的网络操作，不该让本
地回收依赖它，而一个没人引用的 tag 只占几十字节。

### Git 源码仓库

每个 Project 对应组织下的一个**私有**仓库、一条工作分支。API 负责建仓和签发仓库范围的长期
读写 token。

本地 Forgejo 见 [repo-server/forgejo](../repo-server/forgejo/README.md)。配置示例：

```yaml
BKKRILL_ENCRYPT_SECRET_KEY: ''  # Fernet key；进程启动必须配置，不要留空
REPO_SERVER:
  type: forgejo
  base_url: http://127.0.0.1:3000   # 本服务调 Forgejo API
  clone_url: http://127.0.0.1:3000  # Agent/git 看到的地址，可以和 base_url 不同
  org: app-spark
  service_account: app-spark-bot
  service_account_password: ...     # 不要提交；init 写在 secrets/
  default_branch: main
  commit_author_name: App-Spark
  commit_author_email: app-spark@localhost.invalid
```

真实 Forgejo 测试不在默认 `pytest tests/` 里。CI 或本地验收由本项目驱动（会 `just test-up` 拉起
`repo-server/forgejo` 测试实例，和会话测试拉起 Agent 同一模式）：

```bash
APP_SPARK_FORGEJO_LIVE=1 .venv/bin/pytest tests/api/live_forgejo
```

未设置 `APP_SPARK_FORGEJO_LIVE=1` 时该目录不会被收集；一旦设置，缺少 Forgejo 会失败而不是跳过。

#### Runtime 怎么拿到仓库

起 Runtime 时把 `GitRemote`（clone 地址、分支、服务账号、写 token）交给 provider，由它写进子进程
环境。传的是 `clone_url` 而不是 `base_url`——两者只在「所有东西都在同一台机器上」时相同，一旦不
是，用本进程自己的地址会把每个 Runtime 指向它自己。

和状态回写 token 不同，**仓库 token 不会在 Runtime 停止时吊销**：它长期有效、被这个 Project 的
每个 Runtime 共用。拦住一个被替换掉的旧 Runtime 推送的，是服务端拒绝非快进推送，不是收回凭据。

没有仓库时不下发这几个变量，Runtime 的 workspace 就只留在本地磁盘，并在 `/health` 上如实报出来，
而不是假装文件已经存好了。

#### 未保存时下一轮被拒

Runtime 会用 409 拒绝两种完全不同的情况：正在跑另一轮（`AgentBusyError`），和上一轮的文件还没
推到仓库（`AgentWorkspaceSavePendingError`）。两者靠 Runtime 返回的 `detail.code` 区分，对外也是
两条不同的提示——把它们合并会在 Agent 明明空闲、只是存不上的时候告诉用户「正忙」。Agent 侧的
逃生口（`?allow_unsaved=true`）目前不透传给终端用户：要不要提供「本轮不保存也继续」是产品决定。

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
