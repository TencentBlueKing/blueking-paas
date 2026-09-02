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

| 变量 | 必需 | 说明 |
|------|------|------|
| `APP_SPARK_AGENT_RUNTIME_TOKEN` | 是 | `GET /health` 的 query `token`，以及 `POST /runs` / 控制面接口的 Bearer |
| `APP_SPARK_AGENT_MODEL_API_KEY` | 调用 `/runs` 时是 | 模型密钥。缺失则 `model_ready=false`，`POST /runs` 返回 503 |
| `APP_SPARK_AGENT_PORT` | 否 | 监听端口，缺省 `8090` |
| `APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS` | 否 | 空闲秒数，从进程启动起算，每次 `POST /runs` 结束后重置；从未收到 `/runs` 也会到期退出。缺省 `1800`，到期以退出码 0 退出。`GET /health` 不续命。`<= 0` 关闭空闲退出 |
| `APP_SPARK_AGENT_WORKSPACE` | 本地是；容器缺省 `/workspace` | Agent 工具可见目录 |
| `APP_SPARK_AGENT_STATE_DIR` | 本地是；容器缺省 `/state` | 必须在 workspace 外 |
| `APP_SPARK_AGENT_MODEL` | 否 | 缺省 `deepseek:deepseek-v4-flash` |

示例：

```bash
export APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me
export APP_SPARK_AGENT_MODEL_API_KEY=replace-me
export APP_SPARK_AGENT_WORKSPACE=/tmp/app-spark-workspace
export APP_SPARK_AGENT_STATE_DIR=/tmp/app-spark-state
make run
```

其余压缩策略、游标 limit 等配置见 `app_spark_agent/settings.py`（`APP_SPARK_AGENT_*`）。

## 调用 HTTP

`GET /health` 必须带 query token，缺或错误返回 401，且不返回状态字段：

```bash
curl -sS "http://127.0.0.1:8090/health?token=${APP_SPARK_AGENT_RUNTIME_TOKEN}"
```

成功时 JSON 含锁定四字段 `version`、`model_ready`、`running`、`app_status`，以及会话游标
`conversation_id`、`context_version`、`log_seq`、`ui_event_seq`。kube / 接入层探针使用同一 URL。

`POST /runs` 为 AG-UI over SSE，必须 `Authorization: Bearer <APP_SPARK_AGENT_RUNTIME_TOKEN>`：

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

## 会话状态

会话状态按「怎么变」分成三类，都由 `app_spark_agent/state/` 下的类型实现：

| 数据 | 文件 | 形态 | 实现类型 | 单测 |
| --- | --- | --- | --- | --- |
| 原始对话记录 | `log.jsonl` | append-only，`seq` 连续递增 | `AppendLog` / `LogRecord`（`state/log.py`） | `tests/state/test_log.py` |
| AG-UI 事件历史 | `ui_events.jsonl` | append-only，`seq` 连续递增 | `AppendLog`（同上） | `tests/state/test_log.py` |
| 会话上下文 | `context.json` | 可变 blob，原子整体替换，带 `context_version` | `ContextStore` / `ConversationContext`（`state/context.py`） | `tests/state/test_context.py` |

关键点：

- 压缩发生在每轮 run 的中间（每次模型请求之前）并把结果写回历史，因此原始记录必须在消息
  产生的瞬间抄走、不能等 run 结束再导出——由最外层的 `TranscriptRecorder` capability 负责
  （`recorder.py`）。
- `context_version` 不等于轮次：一轮里压缩触发几次就提交几次，控制面不要假设两者同步。
- `SummarizingCompaction` 是一次不可重放的真实 LLM 调用，冷启动重建上下文的唯一来源是
  `context.json`，绝不能从 `log.jsonl` 拼出来。

## 本地镜像

```bash
make docker-build
docker run --rm -p 8090:8090 \
  -e APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me \
  -e APP_SPARK_AGENT_MODEL_API_KEY=replace-me \
  app-spark-agent:dev
```

入口为 tini（PID 1）。`make docker-build` 使用 `--load` 写入本地 daemon。镜像内 workspace / state 锁定为 `/workspace` 与 `/state`，二者必须是独立路径，文件工具只能看见 `/workspace`。

## 开发指南

### 单元测试

普通测试不请求模型、不需要真实 API Key、也不需要起进程：

```bash
make test
```

`tests/api/` 跑在假模型上完整覆盖 HTTP 接口的正确与错误分支；状态原语、Agent 组装、压缩、
事件合并在 `tests/` 其余模块。

### E2E 测试

`tests/e2e/` 会用 uvicorn 拉起真实 Runtime 去基于真实 DeepSeek 执行 Agent 任务，和部署方式完全一致，所有断言
都走 HTTP。设置好有效配置后：

```bash
export APP_SPARK_AGENT_MODEL_API_KEY=sk-...
export APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me
uv run pytest tests/e2e -s
```
