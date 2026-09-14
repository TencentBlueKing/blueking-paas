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
| `APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS` | 否 | 空闲秒数，从进程启动起算，每次 `POST /runs` 结束后重置；从未收到 `/runs` 也会到期退出。缺省 `1800`，到期以退出码 0 退出。`GET /health` 不续命。`<= 0` 关闭空闲退出 |
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

已知缺口：冷启动只恢复上下文，不恢复 workspace 源码；旧 Runtime 的 `run_id` 也不会在空状态
目录中参与重放检测。控制面应先恢复源码，并始终为每轮生成新的 UUID。

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
