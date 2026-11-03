# Agent 的模型

Runtime 调模型走哪条路由 `AGENT_MODEL_SOURCE` 决定，不配时是 `bkaidev`。本服务在拉起 Runtime 时把模型配置
转成环境变量注入，Runtime 启动后不再读这些配置。各配置项的说明和默认值见 [conf.yaml.tpl](../conf.yaml.tpl)「Agent 的模型」。

| 来源 | 配置 | 凭据 | 可选模型 |
| --- | --- | --- | --- |
| 假模型 | `direct`，模型写 `fake:<场景>` | 不需要 | 一个 |
| 直连厂商 | `direct` | 配置里固定的 `api_key` | 一个 |
| bkaidev 网关 | `bkaidev` | 用当前用户登录态换来的 access_token | 网关对换票应用开放的模型 |

本服务自己调模型（给项目起名）用的是另一套配置 `LLM_*`，见[本服务调用的模型](misc.md#本服务调用的模型)。

## 使用 direct 和 fake 模型

`direct` 只有一个固定模型，每个用户都一样，不换票也不访问网关。

### 直连厂商

- 必填：`AGENT_MODEL_SOURCE`（设为 `direct`）；`AGENT_DIRECT_MODEL_CONFIG` 的 `model`、`api_key`
- 可选：`AGENT_DIRECT_MODEL_CONFIG` 的 `name`、`context_window`，只用于模型列表展示

### 假模型

本地想不花钱跑通整条链路时用。这是 agent 内置的确定性假模型，不需要 `api_key`，不发起任何网络请求：

- 必填：`AGENT_MODEL_SOURCE`（设为 `direct`）；`AGENT_DIRECT_MODEL_CONFIG` 的 `model`（设为 `fake:write-file`）

场景清单和细节见 [agent 开发指南](../../agent/docs/dev_guide.md#本地跑起来)。

### 模型列表

`GET /api/models/` 只读 `AGENT_DIRECT_MODEL_CONFIG`，返回那一个模型，`allow_user_switch` 为 false，
`api_key` 不出现在响应里。模型 ID 取 `model` 冒号后的部分，例如 `deepseek-v4-flash`、`write-file`。

## 使用 bkaidev 模型

### 配置

- 必填：`BK_API_URL_TMPL`、`TOKEN_AUTH_ENDPOINT`、`SANDBOX_APP_CODE` / `SANDBOX_APP_SECRET`（见下面「换票应用」）
- 可选：`AGENT_MODEL_SOURCE`（默认就是 `bkaidev`）、`BKAIDEV_APIGW_ENVIRONMENT`、`AUTH_ENV_NAME`、`BKAUTH_BACKEND_TYPE`
  （见下面「换取 access_token」）、`BKAIDEV_MODEL_CONFIG`（见下面「模型列表」）

必填项缺失时，拉起 Runtime 和模型列表都返回 503 `MODEL_ACCESS_CONFIGURATION_ERROR`。

LLM 基址是 `{BK_API_URL_TMPL:bkaidev}/{BKAIDEV_APIGW_ENVIRONMENT}/openapi/aidev/gateway/llm/v1`，
不要在别处再配一份。

### 换取 access_token

provider 在确定要新起 Runtime 的那一刻（持锁、确认没有活着的 Runtime 之后），用当前用户的登录态加上
换票应用的 `SANDBOX_APP_CODE` / `SANDBOX_APP_SECRET` 向 `TOKEN_AUTH_ENDPOINT` 换一张用户态 access_token。
已在跑的 Runtime 继续对话时不会再换票。

只有这个 Runtime 拿到下面三项，拿不到 `app_secret`，也拿不到直连用的固定 key：

| 环境变量 | 值 |
| --- | --- |
| `APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN` | 换来的 access_token |
| `APP_SPARK_AGENT_MODEL_BASE_URL` | LLM 基址 |
| `APP_SPARK_AGENT_MODEL_ID` | 模型列表的默认模型 |

- **换票 backend** 由 `BKAUTH_BACKEND_TYPE` 选择：`bk_token` 用 `SsmBackend`，其余用 `AuthApiBackend`，
  后者请求体另带 `AUTH_ENV_NAME` 作为 `env_name`。
- **不落库也不缓存 token**：签发服务在现有 token 仍有效时原样返回，所以新开会话不会把用户已在用的
  token 废掉。
- **失败**：拿不到用户登录态返回 401 `MODEL_CREDENTIAL_MISSING`，签发服务给不出 token 返回 502
  `MODEL_ACCESS_TOKEN_UNAVAILABLE`。

### 换票应用

换票不用本服务的 `APP_CODE`，而是另一个专用应用（如 app-spark-pub），没配时也不回落到 `APP_CODE`。网关按
签发 token 的应用决定这张票能调什么，用 `APP_CODE` 换出来的票会带着本服务调开发者中心（创建应用、发布）的
授权进 Runtime。

- 换票应用在网关上只申请 bkaidev LLM 的 `models` 和 `chat/completions`，不申请开发者中心，并在 bkaidev 里
  给它开通要用的模型。
- Runtime 里的票仍有这个应用被授权的全部资源，以后给它多批一个接口，这张票立刻就能用。
- 开发者中心客户端和登录态校验仍用 `APP_CODE` / `APP_SECRET`。
- 部署时先完成换票应用的注册、授权和模型开通，再切配置，否则换票和模型列表都会失败。

### 模型列表

可选模型由网关和本服务配置共同决定，本服务这边是可选的 `BKAIDEV_MODEL_CONFIG` 的 `default_model_id`、
`available_models`。

用当前用户换票，调网关 `GET .../llm/v1/models` 取换票应用可用的模型，然后：

1. 剔除网关明确标记不能调工具的；个别读不了的模型卡片跳过并记 warning。
2. 按 `available_models` 过滤和排序，顺序即展示顺序；为空时不过滤。
3. 确定默认模型：`default_model_id` 不在列表里时取列表第一个，列表为空时返回 503
   `MODEL_ACCESS_CONFIGURATION_ERROR`。

每轮校验和新起 Runtime 的默认模型都用这份列表，三者不会不一致。

网关的列表只跟换票应用有关，按换票应用在进程内缓存 5 分钟、所有用户共用，命中时不换票也不调网关；网关新开通
或下线的模型最迟 5 分钟后可见。网关拿不到列表时返回 502 `MODEL_CATALOG_UNAVAILABLE`，不返回空列表，
失败也不缓存。

每个模型只给 ID、名称、上下文窗口和是否支持图像输入：网关卡片只有这些，名称用 ID 代替。

### thinking

网关模型的 thinking 走人工维护的白名单，见[bkaidev 网关的 thinking 支持](misc.md#bkaidev-网关的-thinking-支持)。

## 选择模型

`GET /api/models/` 告诉前端可选哪些模型、不指定时用哪个（`default_model_id`）、平台是否允许用户切换
（`allow_user_switch`）。

发起一轮对话时可以带列表里的 `model_id`，Runtime 用它跑这一轮；不带时用 Runtime 启动时的默认模型。

- 校验对照的就是模型列表接口返回的那份列表：bkaidev 和列表共用 5 分钟缓存，direct 只接受那一个模型的 ID。
- 不接受时返回 422 `MODEL_NOT_AVAILABLE`，不会悄悄换成默认模型。
- 校验通过但网关不认这个模型时（列表有缓存，模型可能刚下线），本轮以 AG-UI `RUN_ERROR` 结束。
