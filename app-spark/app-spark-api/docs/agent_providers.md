# Agent Runtime provider

`AGENT_RUNTIME_PROVIDER` 决定怎么为会话拉起 Runtime，不配时是 `local_process`。各自的字段写在
`AGENT_RUNTIME_PROVIDER_CONFIG`，每个字段的说明和默认值见 [conf.yaml.tpl](../conf.yaml.tpl)「Agent Runtime provider」。
Runtime 调哪个模型与 provider 无关，见 [Agent 的模型](agent_llm.md)。

| provider | Runtime 跑在哪 | 预览怎么打开 | 用途 |
| --- | --- | --- | --- |
| `local_process` | 本机进程 | 经本服务反代 | 开发和测试 |
| `e2b` | 每个会话一个沙箱 | 浏览器直接打开 `get_host` 的地址 | 生产和预发布 |

在 Chart 里怎么填见 [charts/app-spark-api/README.md](../charts/app-spark-api/README.md)。

## 共同约定

- **访问 Runtime 的凭据**：每个 Runtime 有独立的随机 Bearer token，随环境注入，并由 `AgentRuntimeClient`
  自动附加到 `/health`、`/runs`、状态读取与冷恢复请求；token 不进入配置文件。
- **透传 agent 配置**：`extra_env` 只收 `APP_SPARK_AGENT_*`，模型相关的变量不收，它们由
  `AGENT_MODEL_SOURCE` 决定。
- **状态目录**：必须在 workspace 之外，否则 agent 自己的文件工具能改掉自己的历史。这份状态是可丢弃的
  本地缓冲，权威副本在本服务的库里，见[权威副本](conversation.md#权威副本)。

## local_process

### 前置条件

local_process 用 `uv run --project <agent_project_dir> --no-sync` 拉起 Runtime，`--no-sync` 意味着它不会在
请求路径上解析依赖，所以 agent 的虚拟环境必须提前备好：

```bash
cd ../agent && uv sync
```

### 配置

- 必填：`AGENT_RUNTIME_PROVIDER_CONFIG` 的 `agent_project_dir`、`workspace_root`、`state_root`
- 可选：`AGENT_RUNTIME_PROVIDER`（默认就是 `local_process`）；`AGENT_RUNTIME_PROVIDER_CONFIG` 的 `callback_base_url`、
  `startup_timeout_seconds`、`extra_env`

### Runtime 的环境变量

local_process 不把本服务的环境整份交给 Runtime，只按白名单继承 `PATH`、`HOME`、语言、时区、临时目录、
TLS 根证书、出站代理和 uv 的缓存与解释器路径（见 `INHERITED_ENV_NAMES`），再加上 provider 自己注入的
`APP_SPARK_AGENT_*`。

本服务的 `APP_SPARK_API_*` 配置（含 `app_secret`、数据库密码）一律不进 Runtime，因为 Runtime 又会把环境
交给模型写的应用。

## e2b

### 配置

- 必填：`AGENT_RUNTIME_PROVIDER`（设为 `e2b`）；`AGENT_RUNTIME_PROVIDER_CONFIG` 的 `api_key`、`api_url`、
  `callback_base_url`、`template`
- 可选：`AGENT_RUNTIME_PROVIDER_CONFIG` 的 `idle_timeout_seconds`、`max_lifetime_seconds`（见下面「沙箱生命周期」）、
  `runtime_port`、`preview_port`、`port_scheme`（见下面「端口与预览」），以及 `domain`、`agent_user` 等，
  全部字段见 [conf.yaml.tpl](../conf.yaml.tpl)。

模板由 agent 镜像添加而来，见[本地镜像](../../agent/docs/dev_guide.md#本地镜像)。

### 启动 Agent

每个会话创建一个沙箱，通过 envd 执行 `agent_command` 启动模板里预装的 Agent，等 `/health` 通过后才记下
进程号并返回。启动失败时带上 `agent_log_path`（默认 `/tmp/app-spark-agent.log`）末尾报错，并销毁沙箱。

Agent 的配置全部经这次启动的环境变量注入，不继承本服务的环境。状态回写地址是 `callback_base_url` 加上
保留 FORCE_SCRIPT_NAME 前缀的回写路径，因为沙箱经 Ingress 回调本服务。

已建好沙箱但还没有进程号的记录处于启动中，不会交给任何请求：其他请求看到项目忙，`peek` 和预览看到没有
Runtime。启动它的 worker 若死在半路，超过 `startup_timeout_seconds` 加 60 秒后，下一个请求会杀掉该沙箱
并重建。

### 沙箱生命周期

沙箱的生命周期跟着对话走：

- **续期**：只有对话算活动。每轮开始和结束时，把沙箱存活期续为 `idle_timeout_seconds`；预览、打开会话、
  查询状态都不续期。同一个值也作为 Agent 的空闲退出时间。
- **复用前检查**：新一轮开始时先对 Agent 做健康检查。进程已不在就立即销毁旧沙箱并重建；进程还在但不
  应答，隔一秒再探，共探 3 次仍不应答才重建。不在旧沙箱里重新拉起 Agent。
- **存活上限**：沙箱存活满 `max_lifetime_seconds` 后，在下一轮开始前重建；有一轮正在跑时不动它。这个值
  必须比 E2B 平台自己的沙箱存活上限小，至少留出最长一轮的时间。
- **结束会话**：先吊销状态回写凭证，再给 Agent 发 SIGTERM 让它推送，连同重连在内最多等 25 秒，然后销毁
  沙箱；请求中途被断开也照样销毁并释放占用。销毁旧沙箱以便重建时也走同样的优雅停止。

会话状态接口的 `runtime_ready` 表示下一轮能否直接复用现有沙箱，前端据此显示「正在准备运行环境」。

### 端口与预览

Runtime 和预览分别走 `get_host(runtime_port)`、`get_host(preview_port)`，端口所有沙箱相同：Agent 听前者，
用户应用听后者。`get_host()` 返回的地址必须能从 API 服务访问。

新建沙箱允许公开流量，预览端口不带令牌就能打开，浏览器直接访问。Runtime 客户端访问 Agent 端口时仍附带
沙箱访问令牌。预览接口的行为和安全取舍见[工作区应用的预览](misc.md#工作区应用的预览)。

### 自建 E2B 的已回收沙箱

自建 E2B 的入口网关对已被回收的沙箱主机名回 `401 unauthorized`，而不是 404 或 502。重连时 envd 回 401，
provider 会再向控制面查一次（`get_info`）：控制面确认沙箱不存在，就按到期（`expired`）处理并释放占位；
否则照旧报错，不会放掉一个可能还活着的沙箱。

### 集成测试

怎么跑、什么时候跳过，见[开发指南](dev_guide.md#真实-e2b)。
