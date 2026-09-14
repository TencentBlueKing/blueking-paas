# App-Spark Agent Runtime

沙箱内编码 Agent：一个进程绑定一个会话和一个 workspace，通过 AG-UI HTTP/SSE 接收新消息，
并在 workspace 外持久化会话状态。本组件与 `app-spark-api` 平级，不引入 Django。

## 安装与启动

需要 Python 3.14+ 与 [uv](https://docs.astral.sh/uv/)。

```bash
cd app-spark/agent
uv sync
```

可用命令见 `make help`。

### 启动所需环境变量

文档只用占位符，不要填真实密钥。

生产环境的 `APP_SPARK_AGENT_*` 由接入层创建沙箱时注入；本地开发也可以通过 `.env` 提供。
键名与端口数值已锁定。

| 变量 | 必需 | 说明 |
|------|------|------|
| `APP_SPARK_AGENT_RUNTIME_TOKEN` | 是 | 所有 HTTP 接口的 Bearer（含 `GET /health`、`POST /runs`、控制面） |
| `APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN` | 调用真实模型时是 | 用户态 access_token。app-spark 创建 bkaidev 空间和单个智能体后注入；出站只放进 `X-Bkapi-Authorization`。`fake:*` 不需要 |
| `APP_SPARK_AGENT_MODEL_API_KEY` | 调用真实模型时是 | 兼容回落。未注入上面的 token 时当作 access_token 用。`fake:*` 不需要 |
| `APP_SPARK_AGENT_MODEL_NAME` | 调用真实模型时是 | 不带 vendor 前缀，必须落在对照表（本期 `deepseek-v4-flash`） |
| `APP_SPARK_AGENT_MODEL_BASE_URL` | 调用真实模型时是 | bkaidev LLM 网关 v1 入口，不要带 `/chat/completions` |
| `APP_SPARK_AGENT_APP_PORT` | 是 | 用户应用约定端口，锁定 `8000`；本组件只读入，不拉起应用也不校验 |
| `APP_SPARK_AGENT_PORT` | 否 | 监听端口，缺省 `8090` |
| `APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS` | 否 | 空闲秒数，从进程启动起算，每次 `POST /runs` 结束后重置；从未收到 `/runs` 也会到期退出。缺省 `1800`。到期发 SIGTERM 走有序关停（见下面的「关停时多等一步」），而不是直接 `os._exit`；有序关停在 `IDLE_EXIT_DEADLINE_SECONDS`（20s）内走不完才硬退。`GET /health` 不续命。`<= 0` 关闭空闲退出 |
| `APP_SPARK_AGENT_SESSION_ID` | 否 | 只进日志与指标 |
| `APP_SPARK_AGENT_TENANT_ID` | 否 | 只进日志与指标，不做业务分支 |
| `APP_SPARK_AGENT_WORKSPACE` | 本地是；容器缺省 `/data/workspace` | Agent 工具可见目录 |
| `APP_SPARK_AGENT_STATE_DIR` | 本地是；容器缺省 `/data/state` | 必须在 workspace 外 |
| `APP_SPARK_AGENT_APP_LOG_PATH` | 否 | 本会话约定应用日志，缺省 `/data/app.log`。必须在 workspace / state 外；日志工具只读这一条 |
| `APP_SPARK_AGENT_MODEL` | 否 | 缺省 `deepseek:deepseek-v4-flash` |

就绪门闩：`fake:*` 直接就绪；真实模型要 access_token 非空 **且** `MODEL_BASE_URL` 非空 **且** `MODEL_NAME` 在对照表。
access_token 取值：`APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN` → `APP_SPARK_AGENT_MODEL_API_KEY`。
bkaidev 鉴权是 `X-Bkapi-Authorization: {"access_token":"..."}`，不是 `Authorization: Bearer`。
沙箱不注入 `bk_app_code` / `bk_app_secret`。

示例：

```bash
export APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me
export APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN=replace-me
export APP_SPARK_AGENT_MODEL_NAME=deepseek-v4-flash
export APP_SPARK_AGENT_MODEL_BASE_URL=https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1
export APP_SPARK_AGENT_WORKSPACE=/tmp/app-spark-workspace
export APP_SPARK_AGENT_STATE_DIR=/tmp/app-spark-state
make run
```

其余压缩策略、游标 limit 等配置见 `app_spark_agent/settings.py`（`APP_SPARK_AGENT_*`）。

## 假模型

`MODEL` 除了 `<provider>:<model>`，还接受 `fake:<scenario>`——一个不发起任何网络请求的确定性
模型。它让外部控制面可以零成本启动真实进程，覆盖真实 HTTP、SSE 与文件写入，而不必 mock 整个 Agent。

```bash
APP_SPARK_AGENT_MODEL=fake:write-file uv run uvicorn app_spark_agent.server.asgi:app --port 8765
```

目前支持的假模型场景详情可查看 `fake_model.py`。

## 调用 HTTP

`GET /health` 必须带 Bearer，缺或错误返回 401，且不返回状态字段：

```bash
curl -sS -H "Authorization: Bearer ${APP_SPARK_AGENT_RUNTIME_TOKEN}" \
  http://127.0.0.1:8090/health
```

成功时 JSON 含锁定四字段 `version`、`model_ready`、`running`、`app_status`，以及会话游标
`conversation_id`、`context_version`、`log_seq`、`ui_event_seq`。kube 探针用同一接口，走 `httpHeaders`。

`POST /runs` 为 AG-UI over SSE，同样必须 `Authorization: Bearer <APP_SPARK_AGENT_RUNTIME_TOKEN>`：

```bash
curl -sS -N -H "Authorization: Bearer ${APP_SPARK_AGENT_RUNTIME_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "demo-conversation",
    "runId": "4c1889a5-0500-4c7d-877a-d933a5a28e51",
    "state": {},
    "messages": [{
      "id": "cb39dbbf-a3db-46ff-bb1d-e15a9003c658",
      "role": "user",
      "content": "Create only index.html containing Hello World."
    }],
    "tools": [],
    "context": [],
    "forwardedProps": {"contextVersion": 0}
  }' \
  http://127.0.0.1:8090/runs
```

错误码：401（Token 缺失或错误）、409（已有运行中 run）、503（模型未就绪）、422（非法 AG-UI 请求）。
没有独立取消接口；客户端断开 SSE 即取消。

请求只需携带最新一条用户消息，展示历史会被丢弃，只使用 Runtime 自己的可信上下文；第一次
运行的 `contextVersion` 是 `0`。

`/log`、`/ui-events`、`GET/PUT /context` 同样需要 Bearer，供控制面读取或迁移会话状态。

以下接口是提供给外部访问会话状态的通道：`/health` 报三份状态的当前游标、运行标志，以及
`pushed_*` 复制游标与 `replication_pending`（都只在配了控制面时才有意义），`/log` 与
`/ui-events` 按游标增量读取两条日志，`/context` 导出当前上下文（也可向空 Runtime 注入冷会话
上下文并播种 seq）。

## 凭据屏蔽

两层。第二层存在的理由是**第一层静默失效**：新增一个密钥键却忘了登记、或 harness 升级改了名单语义，
测试全绿、功能正常，密钥却已经进了模型能读的环境。

**一、密钥不进子进程**：harness `Shell` 从继承环境里剥掉 `APP_SPARK_AGENT_*` 及各 provider 密钥变量（`agent.py`）。

**二、出站文本脱敏**（`masking.py`），匹配值而非键名，多个密钥按长度降序替换：

| 出口 | 实现位置 |
|---|---|
| AG-UI **落盘**事件 | `ui_events.py` |
| HTTP 错误响应体（401 / 409 / 422 / 503 及异常文本） | `server/errors.py` |
| 进程日志（含 uvicorn） | `observability.py` |

**实时 SSE 不脱敏**，是有意的：逐 delta 匹配要在每个 token 上跑，而它要防的值只有在第一层已经失效时才可能出现；
且模型把密钥切成两个 chunk 时它照样漏。落盘副本按消息合并后才脱敏，拿到的是完整字符串，且它才是审计要看的那份。
客户端在自己的流里看到凭据，本来就是个已经持有凭据的客户端。

第二层是**兜底而非控制措施**，两条限制得清楚：只匹配精确的配置值（变形过的——重编码、截断、拆分——一律穿过）；
只匹配值不匹配键名（否则 `APP_SPARK_AGENT_MODEL_API_KEY` 这种名字在日志里就没法读了）。

日志每条带 `session_id` / `tenant_id`（缺省 `-`），`POST /runs` 在开始和流结束各打一条。

## 会话状态

会话状态按「怎么变」分成三类，都由 `app_spark_agent/state/` 下的类型实现：

| 数据         | 文件                | 形态                                 | 实现类型                                                       | 单测                            |
|------------|-------------------|------------------------------------|------------------------------------------------------------|-------------------------------|
| 原始对话记录     | `log.jsonl`       | append-only，`seq` 连续递增             | `AppendLog` / `LogRecord`（`state/log.py`）                  | `tests/state/test_log.py`     |
| AG-UI 事件历史 | `ui_events.jsonl` | append-only，`seq` 连续递增             | `AppendLog`（同上）                                            | `tests/state/test_log.py`     |
| 会话上下文      | `context.json`    | 可变 blob，原子整体替换，带 `context_version` | `ContextStore` / `ConversationContext`（`state/context.py`） | `tests/state/test_context.py` |

关键点：

- 压缩发生在每轮 run 的中间（每次模型请求之前）并把结果写回历史，因此原始记录必须在消息
  产生的瞬间抄走、不能等 run 结束再导出——由最外层的 `TranscriptRecorder` capability 负责
  （`recorder.py`）。
- `context_version` 不等于轮次：一轮里压缩触发几次就提交几次，控制面不要假设两者同步。
- `SummarizingCompaction` 是一次不可重放的真实 LLM 调用，冷启动重建上下文的唯一来源是
  `context.json`，绝不能从 `log.jsonl` 拼出来。
- bkaidev 对话中间层（`app_spark_agent/bkaidev/session.py`）只从 `context.json` 取发给
  网关的历史，并读取三份游标；不改写 context，也不往 transcript 写 OpenAI 原始报文。
- `read_app_log` 只读 `APP_LOG_PATH`（缺省 `/data/app.log`），不接受路径，单次最多尾部
  8192 字节；文件工具看不见它。

## 远程持久化

配置了控制面地址之后，上面三份文件不再是唯一副本：`app_spark_agent/replication/` 下的后台任务
会把它们复制到控制面，状态目录退化成一个可以丢弃的本地缓冲。

| 配置项 | 作用 |
| --- | --- |
| `CONTROL_PLANE_URL` | 已带会话前缀的完整地址；Runtime 不需要认识「会话」 |
| `CONTROL_PLANE_TOKEN` | spawn 时注入、只授权这一个会话的 Bearer token |
| `PUSH_BATCH_SIZE` | 单次 ingest 调用最多携带的记录数 |
| `PUSH_RETRY_BACKOFF_SECONDS` | 单轮推送失败后的重试间隔 |
| `PUSH_FLUSH_TIMEOUT_SECONDS` | run 收尾时等待控制面追平的上限 |

- **run 结束时有一道屏障，但它不是保证**：先 flush、再释放 `run_guard`。flush 超时不会让 run
  失败，数据仍在本地且后台任务会继续重试；`/health` 的 `replication_pending` 和 `pushed_*`
  用于判断 Runtime 是否真的可以回收。
- **flush 判断的是控制面是否真正追平**，不是单次调用有没有报错。发现缺口时会继续补齐并重新
  触发后台任务。
- **冷启动必须播种 seq**：`PUT /context?log_seq=40&ui_event_seq=55` 会让新记录从 41 和 56
  继续，避免与控制面已有记录撞号。

已知缺口：旧 Runtime 的 `run_id` 不会在空状态目录中参与重放检测，控制面应始终为每轮生成新的
UUID。workspace 源码的持久化见下一节。

## workspace 的 Git 持久化

状态目录之外，workspace 里的源码由 `app_spark_agent/git/` 存进 Project 的私有 Git 仓库。

| 配置项 | 作用 |
| --- | --- |
| `GIT_REMOTE_URL` | Project 私有仓库的 clone 地址。必须是**沙箱能解析的**地址：控制面自己用的 `localhost` 拿到这里只会打到沙箱自己。留空即关闭 Git 持久化 |
| `GIT_TOKEN` | 仓库范围的读写 token |
| `GIT_USERNAME` | HTTP Basic 的用户名，对 Forgejo 是签发 token 的服务账号 |
| `GIT_BRANCH` | 唯一的工作分支，缺省 `main` |
| `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` | 提交身份。是机器人不是终端用户 |
| `GIT_COMMAND_TIMEOUT_SECONDS` | 单条 git 命令超时，缺省 120 |
| `GIT_MAX_FILE_BYTES` / `GIT_MAX_TOTAL_BYTES` | 文件策略的硬性体积上限，缺省 10MiB / 200MiB |
| `GIT_PUSH_RETRY_BACKOFF_SECONDS` | push 失败后的重试间隔，缺省 5 |
| `GIT_SAVE_WAIT_TIMEOUT_SECONDS` | 开始下一轮前等待上一轮推送落地的上限，缺省 10。见下面的逃生口 |
| `PROJECT_ID` | 只写进 commit trailer 便于追溯，留空不影响保存 |

### 凭据只在一个进程的环境里

token 走 `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` 交给 git，**不进命令行**。
常见写法 `git -c http.extraHeader=...` 会把凭据放进 `argv`，而同一个容器里、同一个用户下的
任何进程都能从 `/proc` 读到它——包括模型通过 Shell 能力跑起来的每一条命令。第一层的
「密钥不进子进程」会因此被一个 `ps` 抵消掉。

配套的三条：header 按 URL 限定（`http.<remote>.extraHeader`），重定向到别处不会带上；
`.git/config` 里只有不含凭据的 remote URL；系统与用户级 git 配置、以及任何继承来的
credential helper 全部关掉——helper 有权把凭据写到磁盘上，那正好是上面所有选择要避免的。

### 文件策略（本阶段定稿）

- **保留**：源码、配置、静态资源、锁文件，**包含隐藏文件**（`.env`、`.python-version` 一类）。
  仓库是每个 Project 私有的，恢复时悄悄丢掉应用配置比存下来更糟。
- **默认忽略**：语言相关的构建产物与依赖目录（`.venv`、`node_modules`、`__pycache__` 等），来自
  vendored 的 [github/gitignore](https://github.com/github/gitignore) 模板，目前覆盖 Python 与
  Node，更新模板：`make update-gitignore-assets`。
- **二进制**原样提交；**符号链接**按链接本身提交（git 存的是链接文本，不是目标内容），恢复
  时重建的也是链接。
- **体积上限**：单文件 10MiB、总量 200MiB。超限时提交明确失败并报出是哪些路径，而不是安静地
  把几百 MB 推上去。检查发生在 `git add` 之前，所以失败不会留下半个暂存区。

### 不变量

- **一个远端、一条分支**。推送目标固定是 `origin` 的 `refs/heads/<branch>`。
- **永不强推**。远端有本地没有的提交时，推送报 `GitDivergedError` 交给上层，不会加 `--force`。
  仓库 token 是长期有效的，所以拦住一个跟丢的旧 Runtime 的唯一防线就是服务端拒绝非快进推送；
  这里留一个 force 开关等于给那道防线开后门。
- **工作区有文件、远端也有历史时拒绝合并**。两种做法都会丢数据（覆盖工作区丢未推送的工作，
  在远端 tip 上提交则把远端有、本地没有的文件记成删除），所以这个选择留给调用方。

### 每轮 run 怎么保存

拆成两半，位置不同：

- **屏障内**（`_hold_run_stream` 的 `finally`）只做**本地 commit**。纯本地、快、确定性强。
  它跑在工作线程上，而线程不可取消，所以即使这个 `finally` 是在一个已被取消的任务里执行的，
  commit 也能落地。
- **屏障外**由后台任务做 **push**，自带重试。

为什么 push 不能放屏障里：那个 `finally` 在客户端断开时同样会执行，而 uvicorn 的
`GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS` 是 1 秒、会主动切断 SSE——相当大一部分保存动作发生在
已取消的任务里，一次网络往返在那个位置没法保证做完。何况它还会把一轮对话挂在网络上，用户
看到的就是「卡住了」。

由此得到一条必须说清楚的结论：**一轮 run 的流结束，只代表代码已在本地提交，不代表已经存到
远端。** 两者是不同的状态，`/health` 分别报：

| 字段 | 含义 |
| --- | --- |
| `workspace_persisted` | 这个 Runtime 是否配了仓库。没配和「已保存」必须能区分开 |
| `workspace_save_pending` | 是否还有本地有、远端没有的提交 |
| `workspace.state` | `idle` / `pending` / `pushing` / `saved` / `failed` |
| `workspace.local_sha` / `workspace.pushed_sha` | 本地提交与远端确认的提交 |
| `workspace.unsaved_seconds` | **最早**一个未保存提交等了多久，不是最近那个 |
| `workspace.push_failures` | 连续失败次数，成功即清零 |
| `workspace.needs_attention` | 重试也过不去的失败：分叉、token 被拒、超出体积上限 |

一轮 run 无论成败都会 commit：客户端中途断开时写了一半的文件也值得留着，但 commit message
会写成 `(interrupted)` 且带 `Turn-Status: interrupted`，不会被后来的人误当成完整产出。

### 关停时多等一步

普通路径从不在屏障里等 push——那是后台任务的事。关停是唯一的例外：进程一走，workspace 盘和
状态目录一起没了，只存在本地的 commit 就等于用户丢了一轮。所以 lifespan 在收尾时会调
`ConversationRuntime.drain()`，在一个有界窗口里把未推送的 commit 和未回写的状态送出去：

### 未保存时的下一轮：有界等待与逃生口

第一版只允许一份改动在途：上一轮还没推上去时，`POST /runs` 会先等，等满
`GIT_SAVE_WAIT_TIMEOUT_SECONDS` 仍未落地就由 **Agent 侧的路由**拒绝，返回 **409**，
`detail.code` 为 `workspace_save_pending`（与 `RunGuard` 的 409 靠 `code` 区分）。

**必须有逃生口**：网络断了 push 可能永远落不了地，无限等待等于把用户锁在自己的会话外面。
客户端可以显式选择继续：

```
POST /runs?allow_unsaved=true
```

这一轮的改动会叠在未保存的改动上；这是要让用户明确做的选择，而不是替他做的选择。选择继续
之后 `/health` 依然报 `workspace_save_pending`——继续不等于假装已经存好了。

### 检查点：commit 必须配一个 tag

push 成功之后，这一轮的提交会被打上一个**不可移动的远端 tag**
（`app-spark/checkpoint/<run_id>`），然后才上报给控制面。

为什么不能只存一个 SHA：分支保护挡的是强推，挡不住「这个提交曾经存在、后来被回收了」。
一个没有任何 ref 指向的提交是可回收对象，等到真要恢复的时候，检查点指向的可能已经什么都不是
了。tag 是让它永远可达的那个 ref，一个检查点一个。

上报的内容是 `commit` + `tag` + `run_id` + `context_version`。其中 `context_version` 取自
**做 commit 的那一刻**，不是 push 落地的那一刻：push 可能几秒后才回来，那时会话可能已经是下
一轮了，拿那个版本配这一轮的文件就是错的配对。

控制面的回答 `restorable=false` **不是错误**，它表示「代码到了、配套上下文还没到」这个正常的
中间态；上下文到了之后控制面自己会认。相对地，只要检查点还没上报成功，这一轮就仍然算
`outstanding`——「已保存」的含义是**可恢复**，不只是**已落盘**。上报失败时重试的是**同一个检
查点**，绝不重新 commit 一次：代码已经在远端了，再提交只会多出一个内容相同的 SHA。

### 恢复：先文件，后上下文

`POST /workspace/restore?commit=<sha>`（需要 bearer token，且会拿 `run_guard.exclusive()`）
把工作区放回某个检查点。三种结果：

| `outcome` | 含义 |
| --- | --- |
| `already_there` | 工作区已经在这个提交上，什么都不用做 |
| `superseded` | 工作区在这个提交**之后**，保留较新的工作，**不回滚** |
| `restored` | 工作区落后或分叉，移到这个提交上 |

`superseded` 是有意为之：检查点记录的是**那个会话**把文件写到了哪，不是 Project 现在在哪。
换会话时把工作区回滚到旧会话的检查点，会删掉另一个会话的成果——这比「模型看到一些它不记得写
过的文件」严重得多。

提交在远端找不到时抛 `GitError`，由控制面转成显式失败。**不会**静默地从一个空工作区开始：
那样模型会以为自己从没写过任何东西，然后把已经存在的文件重写一遍。

### 测试

`tests/git/` 用真实 git 进程和真实仓库跑，不 mock 命令输出，覆盖提交、推送、打 tag 上报和上面
那三种恢复结果。`tests/api/test_workspace_save.py` 用真实 Runtime + fake 模型驱动完整一轮，验
证提交、状态上报和上面那个逃生口。认证与传输是本地裸仓库假不出来的部分（tag 走的是另一个 ref
命名空间，权限可能和分支不同），放在 `tests/live_forgejo/`，需要真实 Forgejo：

```bash
APP_SPARK_FORGEJO_LIVE=1 uv run pytest tests/live_forgejo
```

未设置该变量时这个目录不会被收集；一旦设置，测试自己会去 `repo-server/forgejo` 起实例，
Forgejo 起不来就失败，不会 skip。

## 本地镜像

```bash
make docker-build
docker run --rm -p 8090:8090 \
  -e APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me \
  -e APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN=replace-me \
  -e APP_SPARK_AGENT_MODEL_NAME=deepseek-v4-flash \
  -e APP_SPARK_AGENT_MODEL_BASE_URL=https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1 \
  app-spark-agent:dev
```

入口为 tini（PID 1）。`make docker-build` 使用 `--load` 写入本地 daemon。镜像内 workspace / state 锁定为 `/data/workspace` 与
`/data/state`，二者必须是独立路径，文件工具只能看见 `/data/workspace`。

## 开发指南

### 单元测试

默认的测试命令不请求真实模型、不需要 API Key：

```bash
make test
```

`tests/api/` 跑在进程内注入的假模型上，完整覆盖 HTTP 接口的正确与错误分支；状态原语、Agent
组装、压缩、事件合并在 `tests/` 其余模块。`tests/replication/` 用 `httpx.MockTransport` 在进程
内伪造控制面，但状态文件、游标、字节偏移全是真的——整套设计就架在「文件即 outbox」上。

`tests/live/` 用 uvicorn 拉起**真实进程**，但模型是 `fake:` 场景，所以默认就跑。它覆盖
的是进程内测试结构上够不到的那一段：Runtime 由 `create_app_from_settings()` 只凭环境变量装配
起来——这正是任何外部控制面启动它的方式，而一个只能进程内注入的假模型对它们毫无用处。
`test_replication.py` 是同一个道理：它在环回端口上跑一个假控制面，验证「跑完一轮 → 换一个状态
目录全空的新进程 → 对话接着上一轮继续」，并且两代 Runtime 的 seq 拼成一条不重号的平坦序列。

### E2E 测试

`tests/e2e/` 会用 uvicorn 拉起真实 Runtime 去基于真实 DeepSeek 执行 Agent 任务，和部署方式完全一致，所有断言
都走 HTTP。设置好有效配置后：

```bash
export APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN=replace-me
export APP_SPARK_AGENT_MODEL_NAME=deepseek-v4-flash
export APP_SPARK_AGENT_MODEL_BASE_URL=https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1
export APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me
uv run pytest tests/e2e -s
```
