# 开发指南

## 本地配置

所有配置项的说明、默认值和是否必填都在 [conf.yaml.tpl](../conf.yaml.tpl)。以它为起点：

```bash
cp conf.yaml.tpl settings_local.yaml
```

取消注释并填写下面的项，其余保持注释即用默认值。这是不连真实模型、不发布的最小配置：

- 必填：
  - `DATABASE_NAME`、`DATABASE_USER`、`DATABASE_PASSWORD`、`DATABASE_HOST`、`DATABASE_PORT`（MySQL 8.0 以上）
  - `BKKRILL_ENCRYPT_SECRET_KEY`
  - `LOGIN_FULL`、`APP_CODE` / `APP_SECRET`，以及 `BKAUTH_USER_INFO_APIGW_URL` 或 `BKAUTH_USER_COOKIE_VERIFY_URL`
    其中一项，具体值参考当前开发环境
  - `REPO_SERVER`，本地 Forgejo 见 [repo-server/forgejo](../../repo-server/forgejo/README.md)
  - `AGENT_RUNTIME_PROVIDER_CONFIG` 的 `agent_project_dir`、`workspace_root`、`state_root`（local_process）
  - `AGENT_MODEL_SOURCE` 设为 `direct`，`AGENT_DIRECT_MODEL_CONFIG.model` 设为 `fake:write-file`（假模型）
- 可选：
  - `LLM_SOURCE`：设为 `fake`，否则项目自动命名会因为没配 bkaidev 而失败
  - `RABBITMQ_*`：要跑自动命名、发布这些 Celery 任务时必填
  - `BK_API_URL_TMPL`、`TOKEN_AUTH_ENDPOINT`、`USER_ACCESS_TOKEN_APP_CODE` / `USER_ACCESS_TOKEN_APP_SECRET`：改用 bkaidev 模型时必填，见[使用 bkaidev 模型](agent_llm.md#使用-bkaidev-模型)
  - `BLOBSTORE_BKREPO_CONFIG`：要发布到开发者中心时必填
  - `LOG_LEVEL`、`DEBUG`

各配置项也可以用加了 `APP_SPARK_API_` 前缀的环境变量覆盖。

## 启动服务

```bash
uv run uvicorn app_spark_api.asgi:application --reload
```

必须用 ASGI 服务器（uvicorn）启动。会话接口要把 Agent 的事件流边收边转发，在 WSGI 下这个流会被缓冲到结束才吐出来，
等于失去流式的意义。日志默认以 `INFO` 级别写到控制台，可用 `LOG_LEVEL` 调整。

另开一个进程跑 Celery worker，项目自动命名、发布都在这里执行：

```bash
uv run celery -A app_spark_api.celery worker --loglevel=INFO
```

`RABBITMQ_*` 都没配时用占位默认值，worker 能起来、启动时不探测队列，但任务投递不出去。

## 调用接口

服务起来之后，先用不需要登录的接口确认它在应答：

```bash
curl -s http://127.0.0.1:8000/api/accounts/userinfo/
# 未登录时返回 401：{"authenticated": false, "login_url": "..."}
```

其余接口都要蓝鲸登录态。从浏览器里登录蓝鲸后，把 Cookie 带上（`BKAUTH_BACKEND_TYPE` 为 `bk_token` 时 Cookie 名是
`bk_token`，`bk_ticket` 时是 `bk_ticket`）：

```bash
curl -s -b "bk_token=<浏览器里的值>" http://127.0.0.1:8000/api/projects/
```

失败的响应统一是 `{"code": ..., "detail": ...}`，`code` 稳定、可以拿来分支，`detail` 可以直接展示给用户。配了
`FORCE_SCRIPT_NAME` 时，路径前要加上这个前缀。

框架错误的原始信息一律不回显，只有请求参数校验失败（`VALIDATION_ERROR`，422）例外：它只描述调用方
自己提交的内容。这时 `detail` 摘要前 3 条，`data` 列出全部：

```json
{
  "code": "VALIDATION_ERROR",
  "detail": "Request validation failed: body.content: Field required",
  "data": [{"loc": ["body", "content"], "msg": "Field required", "type": "missing"}]
}
```

`loc` 是调用方发送时的位置：整个请求体就是一个 Schema 参数时，不含视图的参数名（ninja 默认会报
`["body", "payload", "content"]`）。实现见 `utils/api_errors/hooks.py`。

## 测试

```bash
uv run pytest --reuse-db tests/
```

平时优先指定测试文件，全量跑比较慢。测试库建在 `settings_local.yaml` 配的 MySQL 上，`--reuse-db` 让多次运行
共用同一个测试库。

测试按依赖从少到多分成下面几层。默认命令会收集除真实 Forgejo 外的所有层，缺依赖的自动跳过，所以「全部通过」
不代表后几层真的跑过，看一眼 skip 的原因：

| 层 | 依赖 | marker | 没有依赖时 |
| --- | --- | --- | --- |
| [单元测试](#单元测试) | 只有数据库 | — | — |
| [真实 Agent 进程](#真实-agent-进程) | agent 的虚拟环境 | — | 跳过 |
| [真实模型](#真实模型) | 模型凭据 | `live_llm` | 跳过 |
| [真实制品库](#真实制品库) | `BLOBSTORE_BKREPO_CONFIG` | `bkrepo` | 跳过 |
| [真实 E2B](#真实-e2b) | E2B 配置和沙箱模板 | `e2b` | 跳过 |
| [真实 Forgejo](#真实-forgejo) | `just`、Docker | `forgejo` | 默认不收集；开启后**失败** |

### 单元测试

外部服务默认都换成假实现，不联网：

- **Forgejo**：内存假实现，autouse fixture `fake_forgejo` 自动生效，标了 `forgejo` 的用例除外。
- **制品库**：内存假实现，需要的用例显式用 `fake_bkrepo` fixture。
- **模型**：`infras/llm` 与项目自动命名的测试用假模型和 MockTransport。

Chart 渲染测试（`tests/test_helm_*.py`）需要 PATH 上有 `helm`，没有时跳过。

### 真实 Agent 进程

会话相关的测试（`tests/api/test_conversations.py`）不 mock Agent，而是真的 spawn agent 进程、走真实 HTTP，
所以要先备好 agent 的虚拟环境，没有时跳过：

```bash
cd ../agent && uv sync
```

- 用的是 `live_server` 而不是进程内的测试客户端：spawn 出来的 Runtime 要经真实 socket 回写状态。
- 状态回写在一轮的事件流发完**之后**才落库，所以读库的断言要轮询（`wait_for_replication`），不能假设库里已经
  是最新的。

### 真实模型

标了 `live_llm` 的用例会对每个配了凭据的真实模型各跑一遍（同一份用例，靠 `live_llm` fixture 参数化），哪个
没配就跳过哪个：

| 目标 | 需要的环境变量 |
| --- | --- |
| 直连 DeepSeek | `DEEPSEEK_API_KEY`；`APP_SPARK_LIVE_LLM_MODEL` 可换模型，默认 `deepseek:deepseek-v4-flash` |
| bkaidev 网关 | `APP_SPARK_LIVE_BKAIDEV_ACCESS_TOKEN`（用户态 token）、`APP_SPARK_LIVE_BKAIDEV_BASE_URL`（v1 地址） |

bkaidev 要测的模型用 `APP_SPARK_LIVE_BKAIDEV_MODEL_IDS` 逗号分隔，默认 `deepseek-v4-flash`，每个模型一组用例。

```bash
set -a; . ~/.app-spark-live-bkaidev.env; set +a
uv run pytest --reuse-db -m live_llm tests/infras/llm tests/ext/llm
```

网关有调用频率限制（超了返回 429 `RATE_LIMIT_RESTRICTION`），一次别测太多模型。

给网关模型适配 thinking 时，最后一步也是跑这一层，完整步骤见[为网关模型适配 thinking](misc.md#为网关模型适配-thinking)。

### 真实制品库

`bkrepo` 用例对真实制品库走一遍「打包上传 → 签地址并匿名下载 → 回收删除」，只在 `BLOBSTORE_BKREPO_CONFIG`
配齐（如写在 `settings_local.yaml`）时执行，结束时删掉自己上传的包：

```bash
uv run pytest --reuse-db -m bkrepo tests/repository/git/
```

### 真实 E2B

```bash
APP_SPARK_API_FORCE_SCRIPT_NAME='@none' uv run pytest -s tests/agent/runtime/test_e2b_integration.py tests/api/live_e2b/
```

`AGENT_RUNTIME_PROVIDER` 不是 `e2b`、E2B 配置无效或配置里没有 `template` 时跳过。

- `template` 必须是由 agent 镜像添加的模板，测试直接用生产的 provider 启动模板里的 Agent，不往沙箱里装任何东西。
- 模型固定用假模型。空闲超时设为 300 秒，每一轮会续期，`max_lifetime_seconds` 仍用配置值，结束时主动销毁。
- 不验证沙箱内的 Git 持久化和状态回写。

### 真实 Forgejo

`tests/api/live_forgejo/` 只在设置 `APP_SPARK_FORGEJO_LIVE=1` 时才被收集。它会用 `just test-up` 拉起
`repo-server/forgejo` 的测试实例，和会话测试拉起 Agent 是同一个模式，所以 PATH 上要有 `just` 和 Docker：

```bash
APP_SPARK_FORGEJO_LIVE=1 uv run pytest --reuse-db tests/api/live_forgejo
```

一旦设置了这个变量，缺少 Forgejo 就会失败而不是跳过。除了 API 流程，它还检查推送的提交和 tag 打出来的源码包
内容。

## 部署

### 镜像构建

项目提供 [Dockerfile](../Dockerfile)，在本目录构建，只包含 API 的生产依赖与源码。
生产和预发布使用 `e2b` provider，镜像里没有 Agent 项目；即使误配成 `local_process`，
也无法在 API 容器里拉起 Runtime。

本地开发和测试若需要在 API 容器里使用 `local_process`，必须显式选择
[Dockerfile.dev](../Dockerfile.dev)，并以父目录 `app-spark/` 为构建上下文。
这个镜像同时包含 API、Agent 及双方的虚拟环境，不得用于生产或预发布，也不得推送为正式
app-spark-api 镜像。

```bash
docker build -t app-spark-api:production .
docker build -f Dockerfile.dev -t app-spark-api:dev ..
```

`e2b` 跑的是由 [agent 镜像](../../agent/docs/dev_guide.md#本地镜像) 做成的沙箱模板。API 镜像负责创建沙箱、注入环境，
再经 envd 启动模板里的 Agent。两种运行方式在 Chart 里怎么填、e2b 什么时候能多副本，见
[charts/app-spark-api/README.md](../charts/app-spark-api/README.md)。
