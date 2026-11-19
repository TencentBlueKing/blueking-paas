# 配置项参考

权威来源是 `app_spark_agent/settings.py`，本文只与它保持同步，两边不一致时以代码为准。

所有环境变量共用前缀 `APP_SPARK_AGENT_`，接入层与本地开发都只下这一套；启动时还会读取当前目录的 `.env`。
文档只用占位符，不要填真实密钥。

## 运行目标

### `APP_SPARK_AGENT_WORKSPACE`

缺省 `/data/workspace`。

暴露给编码工具的 workspace 目录，Agent 只能读写这里面的内容。

### `APP_SPARK_AGENT_STATE_DIR`

缺省 `/data/state`。

会话持久化状态的存放目录，必须位于 `WORKSPACE` 之外，否则会被 Agent 自己的文件和 Shell 工具读到、甚至改坏自己的历史。
这一点在构建应用时强制检查。

### `APP_SPARK_AGENT_RUNTIME_TOKEN`

缺省为空。

`GET /health`、`POST /runs` 和控制面接口共用的 Bearer。为空时任何 token 都不匹配。

### `APP_SPARK_AGENT_PORT`

缺省 `8090`。

Agent 进程的监听端口。

### `APP_SPARK_AGENT_APP_PORT`

缺省 `8000`。

用户应用约定端口。拉起时注入 `APP_SPARK_AGENT_APP_PORT`；不是 `8000` 也不拒绝启动。

### `APP_SPARK_AGENT_PACKAGE_INDEX_URL`

缺省 `https://mirrors.cloud.tencent.com/pypi/simple`。必须是 http(s) 地址，且不得带凭据。

用户项目装依赖用的 PyPI 包源，以 `UV_DEFAULT_INDEX` 交给 uv。这个地址会被 uv 写进用户仓库里的 `uv.lock`，
也在模型的 shell 环境变量里，带凭据等于泄露。

模板的 `uv.lock` 是对着缺省值锁的（`make lock-app-template`）：换了包源，uv 会认为锁文件过期，新项目首次启动就要联网重新解析。

### `APP_SPARK_AGENT_IDLE_TIMEOUT_SECONDS`

缺省 `1800`；`<= 0` 关闭空闲退出。

空闲秒数从进程启动起算，`POST /runs` 结束后重置。从未收到 `/runs` 也会到期退出。

### `APP_SPARK_AGENT_SESSION_ID`

缺省为空。

只进日志与指标。

### `APP_SPARK_AGENT_TENANT_ID`

缺省为空。

只进日志与指标。不做业务分支：一个沙箱服务一个租户，这里按租户分流等于多造一套别处没有的策略。

## 模型

三种互斥的模型配置，凭据不要混用：

- fake：`MODEL=fake:<scenario>`，不需要任何凭据。
- 直连：只提供 `MODEL_API_KEY`，和 `MODEL` 的 `<provider>:<model>` 一起走官网 Bearer。
- 网关：`BK_AIDEV_ACCESS_TOKEN`、`MODEL_ID`、`MODEL_BASE_URL` 三者齐全，走 bkaidev。

网关三项只要出现一项，就不把 `MODEL_API_KEY` 当成直连钥匙；缺项保持未就绪（`/runs` 返回 503）。
两者同时配齐时走网关，`MODEL_API_KEY` 不参与鉴权。各项的空白和未注入都当成没有。

网关下不管模型 ID 是什么都用同一份能力档（工具调用、JSON schema / JSON object 输出、工具返回 schema 全开），
不交给 pydantic-ai 按 ID 推断：推断出的档会关掉 `supports_tool_return_schema`，保守档甚至会把工具调用静默关掉。

### `APP_SPARK_AGENT_MODEL`

缺省 `deepseek:deepseek-v4-flash`，不能为空。

对话使用的模型，格式是 pydantic-ai 的 `<provider>:<model>`。

另外支持 `fake:<scenario>`：一个不发起任何网络请求的确定性假模型，供集成测试把 Runtime 真正启动起来，
场景清单见 `fake_model.py`。fake 不看凭据。

### `APP_SPARK_AGENT_MODEL_API_KEY`

缺省为空。

官网直连的钥匙，见上面的三种模式。

### `APP_SPARK_AGENT_BK_AIDEV_ACCESS_TOKEN`

缺省为空。

用户态 access_token。app-spark 在 bkaidev 建好该沙箱的空间和单个智能体后注入。出站只放进
`X-Bkapi-Authorization` 的 `access_token` 字段，不带 `bk_app_code` / `bk_app_secret`。
本组件不调创建空间 / 智能体的 API。

### `APP_SPARK_AGENT_MODEL_ID`

缺省为空。

沙箱默认模型，不带 vendor 前缀（如 `deepseek-v4-flash`）。没指定模型的一轮和上下文压缩都用它；
每轮可以用 `forwardedProps.modelId` 换成别的模型，能不能调由网关按用户 token 裁决。

### `APP_SPARK_AGENT_MODEL_BASE_URL`

缺省为空。

bkaidev LLM 网关 OpenAI 兼容入口，注入到 v1 这一层，不要带 `/chat/completions`。
prod 示例：`https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1`。

### `APP_SPARK_AGENT_FAKE_DELAY_SECONDS`

缺省 `2.0`，`>= 0`。

`fake:slow` 场景挂起的秒数。它存在的意义是让「run 正在进行中」成为一个能被外部观察到的稳定状态，
从而可以真实地触发 Runtime 的 409，而不是靠 sleep 去猜时序。

## 应用日志

### `APP_SPARK_AGENT_APP_LOG_PATH`

缺省 `/data/app.log`，与容器数据盘对齐。

本会话约定应用日志。位于 workspace / state 之外；日志工具只读这一条，不接受路径参数。
launch 把用户应用的 stdout/stderr 和 `uv sync` 的输出都追加到这个文件。

## 上下文压缩

### `APP_SPARK_AGENT_COMPACTION_TARGET_TOKENS`

缺省 `480000`，`>= 1`。

压缩要把输入压回到的 token 预算。

DeepSeek V4 Flash 的上下文窗口是 1,000,000 token，但输入和生成共用这一个信封，而模型最多能输出 384,000 token。
压回 480,000 就给一次满长度生成留出了余量（480K + 384K = 864K），而不是让一段长历史把回复的空间挤掉。
用绝对值而不是窗口比例：这样触发点固定在测试能够到的地方，也不会随计价表变动而漂移。

### `APP_SPARK_AGENT_COMPACTION_MAX_PART_TOKENS`

缺省 `50000`，`>= 1`。

单条消息 part 的 token 上限，超过就截断。跑飞的生成表现为一个超大 part 而不是总量偏大，所以任何基于总量的策略都碰不到它；
把超限的部分截掉才能保证下一次请求还发得出去。

### `APP_SPARK_AGENT_COMPACTION_KEEP_MESSAGES`

缺省 `20`，`>= 0`。

摘要层原样保留的对话尾部长度。它同时也是摘要层的下限：短于这个长度的历史会被原样返回，因为没有足够旧的内容值得总结。

### `APP_SPARK_AGENT_COMPACTION_KEEP_TOOL_RESULT_PAIRS`

缺省 `3`，`>= 0`。

清空工具结果时，最近多少组「工具调用 / 工具结果」保持完整。刚发生的工具结果往往正是模型下一步要用的，清掉它们省下的 token 换不回这个代价。

## 状态回写（复制到控制面）

### `APP_SPARK_AGENT_CONTROL_PLANE_URL`

缺省为空。

控制面的会话级状态写入地址，例如 `http://api/api/internal/conversations/<uuid>/state/`。

留空即关闭回写：此时 Runtime 完全独立，状态只存在于 `STATE_DIR`，也就是本地开发和单测的形态。
地址由控制面在拉起 Runtime 时给出，且已经带上会话路径，所以 Runtime 自己不需要知道「会话」是什么，
也不需要在启动时就知道自己的 conversation_id。

### `APP_SPARK_AGENT_CONTROL_PLANE_TOKEN`

缺省为空。配了 `CONTROL_PLANE_URL` 就必须配它，否则启动报错。

访问上述地址用的 Bearer token，由控制面签发。

### `APP_SPARK_AGENT_CONTROL_PLANE_TIMEOUT_SECONDS`

缺省 `30.0`，`>= 0`。

单次状态写入调用的超时秒数。给得比较宽松是因为一份 context 文档可能有好几 MB，但必须有限：一轮 run 结束时的 flush 会等它。

### `APP_SPARK_AGENT_PUSH_BATCH_SIZE`

缺省 `50`，`>= 1`。

每次推送最多带多少条日志记录。

### `APP_SPARK_AGENT_PUSH_RETRY_BACKOFF_SECONDS`

缺省 `2.0`，`>= 0`。

一次推送失败后等多久重试，避免控制面挂掉时空转。

### `APP_SPARK_AGENT_PUSH_FLUSH_TIMEOUT_SECONDS`

缺省 `30.0`，`>= 0`。

一轮 run 结束时等待推送追平的秒数。超时不会让这一轮失败——数据还在本地文件里、后台任务会继续重试——但 `/health` 的复制游标会显示落后。

## Workspace 工作区持久化（基于 Git）

### `APP_SPARK_AGENT_GIT_REMOTE_URL`

缺省为空。

Project 私有仓库的 HTTP clone 地址，由控制面在拉起 Runtime 时注入，且必须是**沙箱能解析的**地址：
控制面自己用的 `localhost` 拿到这里只会打到沙箱自己。

留空即关闭 Git 持久化：此时 workspace 只存在于本地磁盘，也就是单测与本地开发的形态。

### `APP_SPARK_AGENT_GIT_TOKEN`

缺省为空。配了 `GIT_REMOTE_URL` 就必须配它，否则启动报错。

仓库范围的读写 token，作为 HTTP Basic 的密码。长期有效、不随 Runtime 代次轮换，因此它只在受控的 git 子进程环境里出现，
不进命令行、不写进 `.git/config`、不进提交内容。

### `APP_SPARK_AGENT_GIT_USERNAME`

缺省为空。

Basic 认证的用户名，对 Forgejo 是签发 token 的那个服务账号。

### `APP_SPARK_AGENT_GIT_BRANCH`

缺省 `main`。

唯一的工作分支。推送与恢复都只认它。

### `APP_SPARK_AGENT_GIT_AUTHOR_NAME` / `APP_SPARK_AGENT_GIT_AUTHOR_EMAIL`

缺省 `App-Spark` / `app-spark@localhost.invalid`。

提交身份。是机器人而不是终端用户：提交发生在 Agent 里，而蓝鲸用户未必有 Git 能接受的邮箱。
Git 在缺少这两项时直接拒绝提交，所以它们有缺省值而不是留空。

### `APP_SPARK_AGENT_GIT_COMMAND_TIMEOUT_SECONDS`

缺省 `120.0`，`>= 0`。

单条 git 命令的超时秒数。必须有限：本地提交发生在 run 收尾屏障里，一条挂住的命令等于挂住这一轮对话。
给到 120 秒是因为首次 clone 要走网络。

### `APP_SPARK_AGENT_GIT_MAX_FILE_BYTES` / `APP_SPARK_AGENT_GIT_MAX_TOTAL_BYTES`

缺省 10MiB / 200MiB，`>= 1`。

文件策略的硬性体积上限，超限时提交明确失败并报出是哪些路径。见 `git/policy.py`。

### `APP_SPARK_AGENT_GIT_PUSH_RETRY_BACKOFF_SECONDS`

缺省 `5.0`，`>= 0`。

push 失败后重试的间隔秒数。网络分区可能持续很久，退避太短只是把失败刷进日志。

### `APP_SPARK_AGENT_GIT_SAVE_WAIT_TIMEOUT_SECONDS`

缺省 `10.0`，`>= 0`。

开始下一轮前，等待上一轮文件推送到远端的时间上限。这是逃生口的那个「有界」：网络断了时 push 可能永远落不了地，
无限等待等于把用户锁在自己的会话外面。超时后接口返回 409，客户端可以带 `?allow_unsaved=true` 明确选择继续。

### `APP_SPARK_AGENT_PROJECT_ID`

缺省为空。

这个 Runtime 属于哪个 Project，仅用于写进 commit trailer 便于追溯。留空不影响保存。

## HTTP 接口

### `APP_SPARK_AGENT_DEFAULT_DRAIN_LIMIT` / `APP_SPARK_AGENT_MAX_DRAIN_LIMIT`

缺省 `200` / `1000`，`>= 1`，且 `DEFAULT_DRAIN_LIMIT` 不得大于 `MAX_DRAIN_LIMIT`，否则启动报错。

两条日志游标接口 `limit` 参数的默认值和上限。

## 代码常量

以下不能通过环境变量修改，改动要改 `settings.py`。

### `SHUTDOWN_DRAIN_TIMEOUT_SECONDS`

关停时 lifespan 允许为「把东西送出去」花掉的总墙钟秒数：workspace 的 push 和状态回写的 flush 共用它，先 push 后 flush。
见 `ConversationRuntime.drain`。

这个值不能自己定。控制面停 Runtime 时给的是 `SHUTDOWN_GRACE_SECONDS`（local_process provider）或 `STOP_GRACE_SECONDS`（e2b provider），
超时就 SIGKILL，而关停要按顺序花掉一串预算。具体秒数和合计只写在 `settings.py` 这个常量的注释里，改这里必须回头看那个常量，
否则 drain 会被杀在半路，等于一点没送出去。

### `RUN_STOP_TIMEOUT_SECONDS`

关停时给进行中的一轮多少秒按「停止」收尾（提交上下文、本地提交文件）；到点直接取消任务，文件照样提交，只是这一轮的上下文不再提交。
一轮不随连接断开而结束，所以这一步只能在这里做。计入关停预算。

### `RUN_CANCEL_WIND_DOWN_SECONDS`

取消之后再等这一轮收尾（本地提交文件）多少秒。取消只打断一次，收尾里的本地 commit 要排在后台 saver 正在进行的 push 后面拿 Git 锁，
push 卡在网络上时可以等上几分钟。到点不再等，直接进 drain：那个 commit 自己带 shield 并持锁，没人等也不会登记错乱；
而此时 push 反正也拿不到锁，drain 真正还能送出去的是不需要 Git 锁的状态回写。计入关停预算。

### `IDLE_EXIT_DEADLINE_SECONDS`

空闲退出发出 SIGTERM 后，等有序关停走完的上限；到点无条件 `os._exit`。比关停预算留出余量：它是兜底，不是正常路径的预算。

### `GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS`

uvicorn 掐连接的秒数（`timeout_graceful_shutdown`），计入关停预算。

### `APP_TEMPLATE_DIR`

新项目的模板（`app-template/`）：模型调 `init_project` 时，workspace 里没有 `pyproject.toml` 才按它写出 `pyproject.toml` 与 `uv.lock`（只改项目名），
只剩一个 `uv.lock` 时连它一起重写。之后它们就是用户项目的一部分，随代码保存和下载。

### `APP_LOG_MAX_BYTES`

`read_app_log` 单次返回正文的字节上限，`8192`。按需求锁定，不是部署旋钮。

### `INSTRUCTIONS`

Agent 的系统提示词。它和 `agent.py` 里挂载的能力是配套的，其中几处和代码成对，必须一起改：

- App Framework 一节里的 `main:app` 与 `app_arch/python.py` 的 `APP_IMPORT_PATH`：预览和部署启的都是这个导入路径，模型写成别的入口名，launch 一定失败。
- Dependencies 一节列出的起始包与 `app-template/pyproject.toml` 的依赖：模型以为新项目里有什么，模板里就得有什么。
  uvicorn 那条也和启动命令是一对：启动器用的是项目环境里的 uvicorn，模型把它删了或改了版本，launch 就不再可靠。
- `init_project` 这个名字与 `tools/init_project.py` 注册的工具，`project_env.NO_PROJECT_DETAIL` 里也写着它。
