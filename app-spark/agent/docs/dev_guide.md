# 开发指南

## 环境准备

需要 Python 3.14+、[uv](https://docs.astral.sh/uv/) 和 git（Git 持久化的测试要用真实 git）。

```bash
cd app-spark/agent
uv sync
```

常用命令见 `make help`：`make run` 启动服务，`make test` 跑测试，`make lint` / `make typecheck` / `make fmt` 做检查和格式化。

## 本地跑起来

最快的方式是用假模型：不需要任何模型凭据，也不发网络请求，但走的是真实的 HTTP、SSE 和文件写入。
本地必须给的只有四项：

```bash
mkdir -p /tmp/app-spark-workspace
export APP_SPARK_AGENT_RUNTIME_TOKEN=dev               # 所有接口的 Bearer；留空时任何请求都是 401
export APP_SPARK_AGENT_MODEL=fake:write-file           # 假模型场景，清单见 app_spark_agent/fake_model.py
export APP_SPARK_AGENT_WORKSPACE=/tmp/app-spark-workspace  # 必须已存在
export APP_SPARK_AGENT_STATE_DIR=/tmp/app-spark-state      # 必须在 workspace 外，不存在会自动创建
make run
```

- `WORKSPACE` / `STATE_DIR` 缺省是容器里的 `/data/...`，本地一般不存在，所以要显式给。
- 应用日志缺省也在 `/data/app.log`。本地要试 `launch_app` 时把 `APP_SPARK_AGENT_APP_LOG_PATH` 指到一个可写路径，
  否则应用照样能起来，但模型读不到日志。
- 启动时会读取当前目录的 `.env`，上面这些也可以写在里面。
- 换成真实模型：去掉 `MODEL=fake:*`，改配 bkaidev 网关三项（`BK_AIDEV_ACCESS_TOKEN`、`MODEL_ID`、`MODEL_BASE_URL`），
  或只配 `MODEL_API_KEY` 直连官网。两种不能混用，判定规则和其余配置项见 [ref_settings.md](ref_settings.md)。

## 调用 HTTP

所有接口都要带 `Authorization: Bearer <RUNTIME_TOKEN>`，没有交互文档和 OpenAPI。接口、参数和错误码见
`app_spark_agent/server/routes.py`。

```bash
curl -sS -H "Authorization: Bearer dev" http://127.0.0.1:8090/health
```

发起一轮对话（AG-UI over SSE）：

```bash
curl -sS -N -H "Authorization: Bearer dev" -H "Content-Type: application/json" \
  -d '{
    "threadId": "demo-conversation",
    "runId": "4c1889a5-0500-4c7d-877a-d933a5a28e51",
    "state": {}, "tools": [], "context": [],
    "messages": [{"id": "m1", "role": "user", "content": "Create index.html containing Hello World."}],
    "forwardedProps": {"contextVersion": 0}
  }' \
  http://127.0.0.1:8090/runs
```

调用时容易踩的几点：

- `runId` 每轮都要是新的 UUID，用过的会被当成重放拒掉。
- 请求只需带最新一条用户消息，其余历史会被丢弃，Runtime 只用自己的上下文。第一轮的 `contextVersion` 是 `0`。
- 客户端断开 SSE 不会中断这一轮。判断一轮是否结束看 `/health` 的 `running` 变回 false，不要看 SSE 有没有收到结尾事件。

## 本地镜像

镜像就是 e2b 沙箱模板。容器里只常驻 envd，Agent 由 app-spark-api 拿到凭据后经 envd 启动，所以镜像不设 CMD：
设了 CMD，Agent 会在还没有任何凭据时就起来。

构建时必须指定 envd 的来源镜像，tag 与平台的 `ENVD_REF` 一致。这一项没有缺省值，免得构建悄悄用上平台没验证过的 envd：

```bash
make docker-build CUBE_BASE_ENVD_IMAGE=mirrors.tencent.com/bcs/cube-base-envd:2026.16
```

本地调试时显式带上启动命令，不带的话容器只起 envd，8090 没人监听：

```bash
docker run --rm -p 8090:8090 \
  -e APP_SPARK_AGENT_RUNTIME_TOKEN=dev \
  -e APP_SPARK_AGENT_MODEL=fake:write-file \
  app-spark-agent:dev python -m app_spark_agent
```

升级 envd：平台 `ENVD_REF` 变更后，换成对应 tag 的 cube-base-envd 重新构建，再更新模板。

### cube 约定

镜像从 Python 官方镜像自建，只从 cube-base-envd 复制 envd 和入口脚本，其余照 cube 底座的约定：

- **就绪探测走 envd**：平台探的是 envd 的 `:49983/health`，要求约 1 秒内通过，不是 Agent 的 `/health`。
- **`user` 账户**：app-spark-api 以它的身份启动 Agent，整个 `/data` 归它，包括 workspace、state 和应用日志。
- **envd 不继承镜像 ENV**：envd 启动的进程拿到的是 envd 自己的默认 `PATH`，所以 app-spark-api 用绝对路径
  `/app/.venv/bin/python -m app_spark_agent` 启动 Agent。镜像里的 `APP_SPARK_AGENT_*` 也只对本地 `docker run` 生效，
  沙箱里 Agent 听接入层注入的 `runtime_port`，用户应用听 `preview_port`。
- **进沙箱排查**：镜像带了 `ps`、vim、curl。正常时只有 envd 一个进程，Agent 由 app-spark-api 启动后才出现。
  Agent 自己的日志在 `/data/agent.log`，启动命令重定向的 stdout/stderr 在 `/tmp/app-spark-agent.log`；
  前者不存在说明进程没走到 `main()`，这时看后者。启动失败时 app-spark-api 回带的也是后者的末尾。

## 测试

`make test` 跑默认的测试集：不请求真实模型、不需要 API Key、不联网，半分钟左右。平时只改一处时，优先跑单个文件：

```bash
uv run pytest tests/api/test_health.py
```

测试按依赖从轻到重分成下面几类。写新测试时放进依赖最轻、又能覆盖到问题的那一类。

### 纯单元

不起 Runtime，也不依赖外部程序：状态原语（`tests/state/`）、模型工具（`tests/tools/`）、应用架构（`tests/app_arch/`）、
bkaidev 客户端（`tests/bkaidev/`），以及 `tests/` 根目录下的模块级测试。

- `tests/replication/` 用 `httpx2.MockTransport` 在进程内伪造控制面，但状态文件、游标、字节偏移全是真的：
  整套复制的设计就架在「本地文件即 outbox」上。
- 涉及 `uv sync` 的测试用 PATH 上的一个假 uv 脚本：要验的是真子进程的超时、退出码和输出去向，而真 uv 不是要联网，
  就是要依赖本机缓存里恰好有什么。真 uv 的路径在镜像里端到端验。

### 进程内 Runtime

`tests/api/` 用 `TestClient` 驱动完整的 Runtime，模型是进程内注入的假模型，覆盖 HTTP 接口的正确和错误分支。
`launch_app` 相关的测试会拉起真实的子进程。

### 真实 git

`tests/git/`、`tests/api/test_workspace_save.py`、`tests/server/test_shutdown.py` 跑真实 git 进程，用本地裸仓库充当远端，
不 mock 命令输出：分叉推送、空远端、重命名这些情形都能原样复现。缺 git 时 `tests/git/` 直接失败而不是跳过。
`Dockerfile.unittest` 就是为此装了 git 的测试镜像。

### 真实进程 + 假模型

`tests/live/` 用 uvicorn 拉起真实进程，模型是 `fake:` 场景，所以默认就跑。它覆盖进程内测试结构上够不到的一段：
Runtime 只凭环境变量装配起来，这正是外部控制面启动它的方式。

`test_replication.py` 在环回端口上跑一个假控制面，验证「跑完一轮 → 换一个状态目录全空的新进程 → 对话接着上一轮继续」，
并且两代 Runtime 的 `seq` 拼成一条不重号的序列。

### 真实 Forgejo（需显式开启）

认证与传输是本地裸仓库假不出来的部分（tag 走另一个 ref 命名空间，权限可能和分支不同），放在 `tests/live_forgejo/`：

```bash
APP_SPARK_FORGEJO_LIVE=1 uv run pytest tests/live_forgejo
```

不设这个变量时这个目录不会被收集。一旦设置，测试会自己用 `just` 去 `repo-server/forgejo` 起实例，起不来就失败，
不会跳过：CI 里这是 Git 持久化唯一的端到端覆盖，悄悄跳过比没有更糟。

### 真实模型（E2E）

`tests/e2e/` 用 uvicorn 拉起真实 Runtime，基于真实模型跑 Agent 任务，所有断言都走 HTTP。不在 `make test` 里，
没有完整的模型配置时跳过：它花钱也花时间。

```bash
export APP_SPARK_AGENT_RUNTIME_TOKEN=replace-me
export APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN=replace-me
export APP_SPARK_AGENT_MODEL_ID=deepseek-v4-flash
export APP_SPARK_AGENT_MODEL_BASE_URL=https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1
uv run pytest tests/e2e -s
```
