# App-Spark Agent Runtime

这是一个独立的、有状态的编码 Agent 服务。一个进程绑定一个 Chat 会话和一个 workspace，
通过 AG-UI HTTP/SSE 接收新消息，并在 workspace 外持久化会话状态。

## TODO

- 支持对 api 主控端回写持久化内容
- 改造为可以基于独立容器启动
- 支持在沙箱环境中启动
- 增加开发蓝鲸 SaaS 相关 SKILL

## 安装与启动

需要 Python 3.14 与 uv。本地运行只需三个配置：workspace、状态目录和模型 API Key，然后启动：

```bash
uv sync
export APP_SPARK_AGENT_WORKSPACE=/tmp/app-spark-workspace
export APP_SPARK_AGENT_STATE_DIR=/tmp/app-spark-state
export APP_SPARK_AGENT_API_KEY="..."

uv run uvicorn app_spark_agent.server.asgi:app --port 8765
```

接口没有鉴权，请保持 uvicorn 默认的回环地址，不要监听 `0.0.0.0`；需要对外暴露时由外层
基础设施负责鉴权和网络隔离。

## 配置

全部配置项集中在 `app_spark_agent/settings.py`，由 environs 在导入时从 `APP_SPARK_AGENT_*`
环境变量解析并校验（`.env` 文件也会自动读取），完整清单以该文件为准。其中 `WORKSPACE` 与
`STATE_DIR` 没有默认值、真正建应用时才检查；其余项（模型、压缩策略、游标 limit 等）都有
合理默认值。

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

## 发起会话

`POST /runs` 接收 AG-UI 请求体，返回一段 SSE 事件流，里面全部是可以直接转发给前端的 AG-UI
事件：

```bash
curl -N http://127.0.0.1:8765/runs \
  -H 'Accept: text/event-stream' \
  -H 'Content-Type: application/json' \
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
  }'
```

请求只需携带最新一条用户消息，展示历史会被丢弃，只使用 Runtime 自己的可信上下文；第一次
运行的 `contextVersion` 是 `0`。流结束即本轮完成，之后访问 `/health` 确认会话成功：
`running` 回到 `false`，且 `context_version`、`log_seq`、`ui_event_seq` 都已经前进。

## 游标接口

以下接口是提供给外部访问会话状态的通道：`/health` 报三份状态的当前游标与运行标志，
`/log` 与 `/ui-events` 按游标增量读取两条日志，`/context` 导出当前上下文（也可向空 Runtime
注入冷会话上下文）。

> 具体参数与返回结构以代码实现为准。

## 开发指南

### 单元测试

普通测试不请求模型、不需要 API Key、也不需要起进程：

```bash
uv run pytest
```

`tests/api/` 跑在假模型上完整覆盖 HTTP 接口的正确与错误分支；状态原语、Agent 组装、压缩、
事件合并在 `tests/` 其余模块。

### E2E 测试

`tests/e2e/` 会用 uvicorn 拉起真实 Runtime 去基于真实 DeepSeek 执行 Agent 任务，和部署方式完全一致，所有断言
都走 HTTP。设置好有效配置后：

```bash
echo 'APP_SPARK_AGENT_API_KEY=sk-...' > .env   # 已在 .gitignore 中
uv run pytest tests/e2e -s
```

`-s` 作用：每次模型调用都会实时打到控制台——请求与响应、工具调用与结果、逐 token 出现
的回答。挑一个 `tests/e2e/test_coding_session.py` 跑起来，看 Agent 读文件、写文件、执行命令、
流式输出，再配合回读 `/log`、`/ui-events`、`/context`，是掌握这套 Runtime 工作过程最快的方式。
