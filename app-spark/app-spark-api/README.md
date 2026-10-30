# app-spark-api

## 开发指南

在 `manage.py` 文件同目录下创建 `settings_local.yaml`，添加必要的配置内容：

```yaml
# 必选：统一登录页面地址
LOGIN_FULL: ...

# 必选：本服务在蓝鲸的应用身份，调用蓝鲸各服务都用这一对
APP_CODE: ...
APP_SECRET: ...

# 必选：BKAUTH 用户认证相关配置（具体值请参考当前开发环境）
BKAUTH_BACKEND_TYPE: ...
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

日志默认以 `INFO` 级别写到控制台。可用 `LOG_LEVEL` 调整级别。

### 运行测试

```bash
uv run pytest --reuse-db tests/
```

会话相关的测试不 mock agent，而是真的 spawn agent 进程、走真实 HTTP。

## API 错误响应

所有已匹配 API 路由的失败响应使用 `blue_krill.web.std_error` 的 `APIError`，保留原有 HTTP
状态语义，响应包含稳定的 `code` 和可展示的 `detail`：

```json
{"code": "PROJECT_ID_TAKEN", "detail": "Project id `demo` is already taken."}
```

## 驱动 Agent

一个会话（conversation）对应一个 Agent Runtime 进程。API 负责建会话、按需拉起 Runtime、
把用户消息发过去，并把 Runtime 返回的 AG-UI 事件流原样透传给前端。

local_process provider 会为每个 Runtime 生成独立的随机 Bearer token，随进程环境注入，并由
`AgentRuntimeClient` 自动附加到 `/health`、`/runs`、状态读取与冷恢复请求；token 不进入配置文件。

### 配置

```yaml
## Agent Runtime 的驱动方式；local_process 在本机 spawn 进程
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
  ## 可选，追加传给 agent 进程的 APP_SPARK_AGENT_* 环境变量（模型相关的变量不收）
  # extra_env:
  #   APP_SPARK_AGENT_FAKE_DELAY_SECONDS: "3"

## 会话上下文文档存哪儿，字段见 ContextStorageConfig
AGENT_CONTEXT_STORAGE:
  backend: host_tmp_path
  root: /tmp/app-spark/agent-contexts

## 调模型走哪条路：bkaidev（默认）或 direct（直连厂商）
AGENT_MODEL_SOURCE: bkaidev
## AGENT_MODEL_SOURCE 为 bkaidev 时必填：换票地址，按版本填（见下文）
# TOKEN_AUTH_ENDPOINT: ...
## AGENT_MODEL_SOURCE 为 bkaidev 时可选。LLM 基址由 BK_API_URL_TMPL + APIGW_ENVIRONMENT 拼接；
## app 身份用 APP_CODE / APP_SECRET。
## default_model_name 注入为 Runtime 的 MODEL_NAME，默认 deepseek-v4-flash。
# BKAIDEV_MODEL_CONFIG:
#   default_model_name: deepseek-v4-flash
## AGENT_MODEL_SOURCE 为 direct 时必填，字段见 DirectModelAccess
# AGENT_DIRECT_MODEL_CONFIG:
#   model: deepseek:deepseek-v4-flash
#   api_key: ...
```

**Runtime 的环境变量**：local_process 不把本服务的环境整份交给 Runtime，只按白名单继承 `PATH`、
`HOME`、语言、时区、临时目录、TLS 根证书、出站代理和 uv 的缓存与解释器路径（见 `INHERITED_ENV_NAMES`），
再加上 provider 自己注入的 `APP_SPARK_AGENT_*`。本服务的 `APP_SPARK_API_*` 配置（含 `app_secret`、
数据库密码）一律不进 Runtime，因为 Runtime 又会把环境交给模型写的应用。

**模型的 access_token**：走 bkaidev 时，provider 在确定要新起 Runtime 的那一刻（持锁、确认没有
活着的 Runtime 之后）用当前用户的登录态加上本服务的 `APP_CODE` / `APP_SECRET`，向
`TOKEN_AUTH_ENDPOINT` 换一张用户态 access_token，只注入该 Runtime 的
`APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN`，并把
`{BK_API_URL_TMPL:bkaidev}/{APIGW_ENVIRONMENT}/openapi/aidev/gateway/llm/v1` 注入为
`APP_SPARK_AGENT_MODEL_BASE_URL`，`default_model_name`（默认 `deepseek-v4-flash`）注入为
`APP_SPARK_AGENT_MODEL_NAME`。

换票支持直连 auth api 或 SSM 两种 backend，由 `BKAUTH_BACKEND_TYPE` 选择：`bk_token` 用
`SsmBackend`，其余用 `AuthApiBackend`，
后者请求体另带 `AUTH_ENV_NAME`（默认 `prod`）作为 `env_name`。本服务不落库也不缓存 token：签发
服务在现有 token 仍有效时原样返回，所以新开会话不会把用户已在用的 token 废掉。已在跑的 Runtime
继续对话时不会再换票。bkaidev 的 Runtime 拿不到 `app_secret`，也拿不到直连用的固定 key。

**前置条件**：local_process 用 `uv run --project <agent_project_dir> --no-sync` 拉起 Runtime，
`--no-sync` 意味着它不会在请求路径上解析依赖，所以 agent 的虚拟环境必须提前备好：

```bash
cd ../agent && uv sync
```

本地想不花钱跑通整条链路时，把 `AGENT_MODEL_SOURCE` 设成 `direct`，`AGENT_DIRECT_MODEL_CONFIG.model`
设成 `fake:write-file`——这是 agent 内置的确定性假模型，不发起任何网络请求，
细节见 [agent/README.md](../agent/README.md) 的「假模型」一节。

`e2b` provider 为每个会话创建一个沙箱，通过 envd 执行 `agent_command` 启动模板里预装的 Agent，
等 `/health` 通过后才记下进程号并返回；启动失败时带上 `agent_log_path`（默认
`/tmp/app-spark-agent.log`）末尾报错，并销毁沙箱。Agent 的
配置全部经这次启动的环境变量注入，不继承本服务的环境；状态回写地址是 `callback_base_url` 加上
保留 FORCE_SCRIPT_NAME 前缀的回写路径，因为沙箱经 Ingress 回调本服务。

已建好沙箱但还没有进程号的记录处于启动中，不会交给任何请求：其他请求看到项目忙，`peek` 和预览
看到没有 Runtime。启动它的 worker 若死在半路，超过 `startup_timeout_seconds` 加 60 秒后，下一个
请求会杀掉该沙箱并重建。Runtime 和预览分别走 `get_host(runtime_port)`、`get_host(preview_port)`
（默认 `8000` 和 `9000`，所有沙箱相同）：Agent 听前者，用户应用听后者。

沙箱的生命周期跟着对话走：

- 只有对话算活动。每轮开始和结束时，把沙箱存活期续为 `idle_timeout_seconds`
  （默认 1800）；预览、打开会话、查询状态都不续期。同一个值也作为 Agent 的空闲退出时间。
- 新一轮开始时先对 Agent 做健康检查。进程已不在就立即销毁旧沙箱并重建；进程还在但不应答，隔一秒
  再探，共探 3 次仍不应答才重建。不在旧沙箱里重新拉起 Agent。
- 沙箱存活满 `max_lifetime_seconds`（默认 86400）后，在下一轮开始前重建；有一轮正在跑时不动它。
  这个值必须比 E2B 平台自己的沙箱存活上限小，至少留出最长一轮的时间。
- 结束会话时先吊销状态回写凭证，再给 Agent 发 SIGTERM 让它推送，连同重连在内最多等 20 秒，然后
  销毁沙箱；请求中途被断开也照样销毁并释放占用。销毁旧沙箱以便重建时也走同样的优雅停止。

会话状态接口的 `runtime_ready` 表示下一轮能否直接复用现有沙箱，前端据此显示「正在准备运行环境」。

```yaml
AGENT_RUNTIME_PROVIDER: e2b
AGENT_RUNTIME_PROVIDER_CONFIG:
  ## 必填：自建 E2B 服务的凭据与管理 API 地址
  api_key: <your-api-key>
  api_url: https://example.com/e2b
  ## 必填：本服务的对外地址，沙箱内的 Agent 用它回写会话状态
  callback_base_url: https://app-spark.example.com
  ## 必填：预装了 Agent 的沙箱模板，由 agent 镜像添加而来（见 agent/README.md「本地镜像」）
  template: <agent-template>
  ## 可选：在沙箱内启动、停止、探测 Agent 所用的用户，默认 user
  # agent_user: user
  ## 可选：API 未返回 sandbox_domain 时使用的域名后缀
  # domain: sandbox.example.com
  ## 可选：Agent 监听端口与用户应用端口，默认 8000 / 9000，所有沙箱相同
  # runtime_port: 8000
  # preview_port: 9000
```

`get_host()` 返回的端口地址必须能从 API 服务访问。新建沙箱允许公开流量，预览端口不带令牌就能
打开，浏览器直接访问。Runtime 客户端访问 Agent 端口时仍附带沙箱访问令牌。

自建 E2B 的入口网关对已被回收的沙箱主机名回 `401 unauthorized`，而不是 404 或 502。重连时
envd 回 401，provider 会再向控制面查一次（`get_info`）：控制面确认沙箱不存在，就按到期（`expired`）
处理并释放占位；否则照旧报错，不会放掉一个可能还活着的沙箱。

有有效 E2B 配置时，运行
`APP_SPARK_API_FORCE_SCRIPT_NAME='@none' uv run pytest -s tests/agent/runtime/test_e2b_integration.py tests/api/live_e2b/`，
没有配置、或配置里没有 `template` 时跳过。`template` 必须是由 agent 镜像添加的模板，测试直接用
生产的 provider 启动模板里的 Agent，不往沙箱里装任何东西；空闲超时设为 300 秒，每一轮会续期，
`max_lifetime_seconds` 仍用配置值，结束时主动销毁。
不验证沙箱内的 Git 持久化和状态回写。

### 会话状态的权威副本

Runtime 是可丢弃的，所以会话历史的权威副本在本服务这边。Runtime 在后台把三类状态推过来，
本服务只在**推进**会话时才需要 Runtime，**查看**会话从不需要：

| 数据 | 存在哪 | 谁来读 |
| --- | --- | --- |
| 原始对话记录 | `ConversationMessage` 表 | 暂无对外读接口 |
| 用户发送的原文 | `ConversationUserMessage` 表 | `GET .../history/`，与 AG-UI 事件一起恢复 |
| AG-UI 事件历史 | `ConversationUiEvent` 表 | `GET .../ui-events/`，直接读库、不起容器 |
| 会话上下文 | blob + `ConversationContextVersion` 行（一版一行） | 冷启动时注入回 Runtime |
| 可恢复检查点 | `ConversationCheckpoint` 行 | 冷启动时先据此把文件放回去 |

上下文 blob 的后端由 `AGENT_CONTEXT_STORAGE.backend` 决定。本地和 Chart 默认是 `host_tmp_path`；
`bk_repo` 是制品库，多副本 e2b 用它，因为上下文不能只留在单个 Pod 的磁盘上。

**一致性是最终一致的**：Runtime 是在把 AG-UI 事件流全部发完之后才 flush 的，所以客户端收到
`RUN_FINISHED` 的那一刻，本服务的库可能还差几十毫秒。要等一轮真正落定，看
`GET .../conversations/<n>/` 的 `running` 与 `replication_pending` 是否**都**回到 `false`。

只看 `running` 不够。Runtime 确实是先 flush 再释放 run guard，但 flush 超时不会让这一轮失败——
数据还在 Runtime 的本地文件里、后台任务会继续重试——run guard 照样会释放。于是完全可能出现
「Runtime 空闲，但库里还差一截」。`replication_pending` 报的就是那一截，落后到什么程度可以从
Runtime 的 `/health` 的 `pushed_*` 游标看。

#### 冷恢复：文件跟 Project，上下文跟会话

冷启动要恢复两样东西，它们的归属不同，所以各取各的最新，不要求描述同一个时刻：

- **工作区文件属于 Project。** 一个 Project 会被多个会话接着开发，工作分支又只能快进，所以文件
  最终落在远端分支的最新提交上。本服务拿这个会话**最新的检查点**（它推过的最后一个提交，连同
  钉住它的远端 tag）去调 Runtime 的 `restore_workspace`：远端已经在检查点之后（被别的会话或这
  个会话中断的那一轮推进过），Runtime 保留较新的工作并回 `superseded`，不会被旧检查点回滚掉；
  复用的旧 workspace 落后于远端时，会被带到远端最新。恢复前会先 fetch，避免本地旧 workspace
  把已经推进的远端分支误判成“就在检查点”。
- **会话上下文属于会话。** 冷启动总是注入最新归档的那一版；新 Runtime 的日志游标取「现在库里
  存到哪」，不取检查点上记的游标。
- **日志游标无论如何都要续上。** Runtime 先推日志、后推上下文，第一轮里丢掉的 Runtime 会留下
  「有记录、没有任何一版上下文」。这时没有记忆可注入，但仍用 `PUT /cursors` 把两个游标交给新
  Runtime；否则它从 seq 1 重新编号，ingest 把撞号当重发丢掉，实时输出和历史就对不上了。

没改文件的轮次（问答、读文件、与工作区无关的文档工作）不产生检查点，所以上下文领先于检查点是
常态；某一轮的提交已上报、但它的最终上下文没来得及归档时，文件也会领先于上下文。两种情况都照
常恢复，差异交给 Agent 自行感知——它每一轮都是从磁盘读文件的。曾经要求两者版本严格配对，结果
是纯对话轮次之后冷启动一律被拒，Project 永久卡死。检查点上的 `context_version` 现在只记录
「这次提交是在会话的哪个位置做的」，供排查。冷启动日志会同时打出检查点版本和注入的上下文版本。
「最新的检查点」和回收时保留的「最近 N 个」都按登记先后算，不按 `context_version`：上下文没归档
就丢了 Runtime 时，新 Runtime 从版本 0 重新计数，版本号会回退。

从未推过检查点的会话不调 `restore_workspace`，只恢复最新上下文；全新沙箱里 Runtime 启动时就
已经检出了远端分支的最新提交。

恢复顺序是**先文件、后上下文、最后才接受新 run**（`_resume_if_cold`）。反过来会留下一个窗口：
Runtime 记得自己写过一些还没落盘的代码，这时进来一轮 run，模型就会基于这个错位行动。

只有「没有会话、`context_version` 为 0、两个通道都没有记录」的 Runtime 才算冷的。通道这一条
不能省：第一轮在提交上下文之前失败的 Runtime 仍报版本 0，但它已经有了自己的编号，再播种只会
被拒（409），而它接着的本来就是自己的历史。

远端不可用，或检查点提交不在远端分支历史里时，`restore_workspace` **显式失败**，不静默从空
工作区开始。

#### 上下文版本与检查点的保留

每一版上下文单独存一份 blob（key 里带版本号）。这样归档不用加锁、也不用维护一个「最新」指针：
每一版有自己的 key 和行，「最新」就是版本号最大的那一行。代价是版本会累积，所以要有保留上限：

```yaml
AGENT_CONTEXT_VERSIONS_KEPT: 5   # 一个会话保留的最近上下文版本数
AGENT_CHECKPOINTS_KEPT: 3        # 一个会话保留的最近检查点数
```

两者各自只留最近 N 个，互不牵制：检查点不钉住任何上下文版本。冷启动只用最新的那一版上下文和
最新的那一个检查点，多留的是排障和人工恢复的余量。两个值都会被抬到至少 1，配成 0 等于关掉冷
启动。

回收在归档新版本之后顺带做，删版本时**先删行、再删 blob**。反过来的话，一次失败的远端删除会留
下一行指向已经不存在的文档，而那正好是冷启动最没法处理的状态——行说有，读出来没有。孤儿 blob
只是占空间。被淘汰的检查点在远端留下的 tag 不跟着删：删远端引用是一次可能失败的网络操作，不该
让本地回收依赖它，而一个没人引用的 tag 只占几十字节。

### Git 源码仓库

每个 Project 对应组织下的一个**私有**仓库、一条工作分支。API 负责建仓和签发仓库范围的长期
读写 token。源码持久化已由 Git 承担；会话冷恢复按上方「冷恢复：先文件，后上下文」使用检查点。

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

#### 发布用的源码包

发布时把某个 commit 的源码打成 tgz 传到蓝鲸制品库，再签一个预签名地址交给发布流程去下载，
见 `repository/git/source_packages.py`。

包就是 Forgejo 对该 commit 的 `tar.gz` 归档，原样上传，不解压重打。源码在包里套着一层以仓库名
命名的目录（`{repo}/...`），开发者中心支持源码位于单个子目录内，所以不必把文件提到包根目录。

每次上传记一行 `ProjectSourcePackage`，以「Project + commit SHA」唯一：主分支会被反复发布，只有
SHA 能区分版本；同一个 SHA 不论经由主分支还是 tag 选中都只上传一次，后来者复用已有记录。

包不会永久保存。上传、复用和签地址都会刷新行上的 `last_used_at`，长期没人用的包由命令回收，建议
用定时任务每天跑一次：

```bash
python manage.py delete_unused_source_packages            # 删除 15 天未被使用的包
python manage.py delete_unused_source_packages --days 30  # 自定义天数
python manage.py delete_unused_source_packages --dry-run  # 只列出，不删除
```

回收先删行再删制品库对象。对象已不存在（制品库错误码 `251010`）算删除成功；其余删不掉的情况
（网络错误、鉴权失败、仓库不存在等）会列出对象 key 并让命令以失败退出，以便有人去手工清理。

删除项目时（Project 只是软删除，外键级联不会触发），在删完 Git 仓库之后用同一套逻辑删掉该项目的
全部源码包，不看 `last_used_at`。删不掉的对象只记日志，不让项目删除失败：行已经没了，重试也找不回它。

因为预签名地址只有制品库能给，`BLOBSTORE_BKREPO_CONFIG` 是必填配置，缺了在第一次打包时就报
`ImproperlyConfigured`，不会先去下载归档。包所在的通用仓库由 `BLOBSTORE_BUCKET_SOURCE_PACKAGES`
指定（默认 `app-spark-source-packages`），需事先建好。测试里制品库默认是内存假实现（`fake_bkrepo`
fixture），真实 Forgejo 测试会检查推送的提交和 tag 打出来的内容。

`tests/repository/git/test_source_packages_live_bkrepo.py`（`bkrepo` marker）对真实制品库走一遍
「打包上传 → 签地址并匿名下载 → 回收删除」，只在 `BLOBSTORE_BKREPO_CONFIG` 配齐（如写在
`settings_local.yaml`）时执行，否则跳过；测试结束会删掉自己上传的包：

```bash
uv run pytest --reuse-db -m bkrepo tests/repository/git/
```

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
`AGENT_BUSY` 与 `AGENT_WORKSPACE_SAVE_PENDING` 两个错误码及不同提示——把它们合并会在 Agent 明明
空闲、只是存不上的时候告诉用户「正忙」。Agent 侧的逃生口（`?allow_unsaved=true`）目前不透传给
终端用户：要不要提供「本轮不保存也继续」是产品决定。

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

### 工作区应用的预览

预览是三件事，分开看才对：**平台签发能打开的地址**、**agent 保证约定端口在听**、**前端决定什么时候
摆给人看**。沙箱只管中间那件——它不知道自己被外面怎么寻址，`app.launched` 里也就没有 url。

`GET .../conversations/<n>/preview/` 返回 `origin`、`direct` 和 `dev_server_status`，前端拿 `origin`
当 iframe 的 `src`，地址不落库，每次现查。provider 的 `preview_target` 标了 `public`（E2B）时，
`origin` 是沙箱用 `get_host` 给出的暴露域名，`direct` 为 true，浏览器直接打开，沙箱创建时已允许不带
令牌访问；沙箱重建后主机会变。其余情况 `origin` 是本服务自己的一条路径 `.../preview/app/`，由请求
推导，会话一建好就有。此刻有没有东西可看要看 `dev_server_status`：`not_started` / `starting` /
`ready` / `stopped`，`null` 表示问不到。只有 `ready` 才挂 iframe；`starting` 是「进程在跑，还没答出来」，
继续等就好，Runtime 那边不会因此重启它。

E2B 直连意味着暴露域名本身就能打开预览，不经过平台登录；`allow_public_traffic` 是整个沙箱的开关。
Agent Runtime 的业务路由另有 Bearer token 保护，交互文档和 OpenAPI 不对外提供。平台页面是 https 时
`port_scheme` 必须是 https。

`.../preview/app/<任意路径>` 是反向代理，鉴权与 `.../ui-events/` 一致：平台登录加项目归属复查，所以
预览 URL 不是凭据。转发时摘掉 `Cookie` / `Authorization`，反方向摘掉 `Set-Cookie`。上游由 provider 的
`preview_target` 一次给出（地址、端口代理要的首部、能否发 `X-Forwarded-Host`），local_process 为每个
Runtime 分一个应用端口，于是多个会话能同时预览。没有 Runtime 是 503，应用没起来是 502。转发时按本服务
看到的事实重写 `X-Forwarded-For` / `-Proto` / `-Prefix`；`X-Forwarded-Host` 由 provider 的
`send_forwarded_host` 决定：本地 provider 发送，E2B 因端口代理按 host 路由而不发送。
客户端自己带的那份不透传；读 `X-Forwarded-Prefix` 的框架能靠它把自己生成的链接
拼对。

**反代路径上，同源是最大的妥协。** 走 `.../preview/app/` 时，应用是模型写的代码，却和控制面共享
origin，它的 JS 一句 `fetch("/api/...")` 就能带着用户登录态调平台。HTML 响应因此带一条 CSP，把
`connect-src` / `form-action` 锁在预览前缀下，代价是应用不能从浏览器直连第三方。上游路径怎么拼、
响应头怎么改，都写在 `conversations/preview.py` 里。直连的沙箱主机和平台不是同一个源，这段 CSP
打不到直连响应上，下面列的反代缺口在直连上也不存在。

反代地址的两个部署前提：在 Ingress 上终结 TLS 时要配 `SECURE_PROXY_SSL_HEADER`，否则 `origin` 签成
`http://`，前端是 https 就按 mixed content 拦掉；前端与本服务不同源时，`X-Frame-Options:
SAMEORIGIN` 要换成 `frame-ancestors`。直连地址的协议来自 `port_scheme`，不走这个签发。

反代的已知缺口：不支持 WebSocket（`Upgrade` 属逐跳首部，且 Django 的 `StreamingHttpResponse`
代理不了）；请求体整份进内存，没有流式上传；HTML 正文里的根绝对路径（`/static/app.css`）仍会
404——重定向那一类已经在响应里改写了，正文没有改写。

## 部署相关

### 镜像构建

项目提供 [Dockerfile](Dockerfile)，在本目录构建，只包含 API 的生产依赖与源码。
生产和预发布使用 `e2b` provider，镜像里没有 Agent 项目；即使误配成 `local_process`，
也无法在 API 容器里拉起 Runtime。

本地开发和测试若需要在 API 容器里使用 `local_process`，必须显式选择
[Dockerfile.dev](Dockerfile.dev)，并以父目录 `app-spark/` 为构建上下文。
这个镜像同时包含 API、Agent 及双方的虚拟环境，不得用于生产或预发布，也不得推送为正式
app-spark-api 镜像。

```bash
docker build -t app-spark-api:production .
docker build -f Dockerfile.dev -t app-spark-api:dev ..
```

`e2b` 跑的是由 [agent 镜像](../agent/README.md) 做成的沙箱模板。API 镜像负责创建沙箱、注入环境，
再经 envd 启动模板里的 Agent。两种运行方式在 Chart 里怎么填、e2b 什么时候能多副本，见
[charts/app-spark-api/README.md](charts/app-spark-api/README.md)。
