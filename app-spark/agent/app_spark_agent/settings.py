"""Agent 服务可配置项。"""

from __future__ import annotations

import hmac
from pathlib import Path

from environs import Env, EnvError
from marshmallow.validate import Length, Range
from pydantic_ai.profiles.openai import OpenAIModelProfile

# 所有配置项共用的环境变量前缀。接入层与本地开发都只下这一套。
ENV_PREFIX = "APP_SPARK_AGENT_"

DEFAULT_AGENT_PORT = 8090
DEFAULT_APP_PORT = 8000
DEFAULT_WORKSPACE = "/data/workspace"
DEFAULT_STATE_DIR = "/data/state"
DEFAULT_IDLE_TIMEOUT_SECONDS = 1800
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 1

# 关停时 lifespan 允许为「把东西送出去」花掉的总墙钟秒数：workspace 的 push 和状态回写的
# flush 共用它，先 push 后 flush。见 ``ConversationRuntime.drain``。
#
# 这个值不能自己定。控制面停 Runtime 时给的是 ``SHUTDOWN_GRACE_SECONDS``（见 app-spark-api 的
# local_process provider），超时就 SIGKILL，而关停要按顺序花掉：
#   uvicorn 掐连接 1s + 本值 + 停应用子进程 5s = 14s < 20s
# 改这里必须回头看那个常量，否则 drain 会被杀在半路，等于一点没送出去。
SHUTDOWN_DRAIN_TIMEOUT_SECONDS = 8.0

# 空闲退出发出 SIGTERM 后，等有序关停走完的上限；到点无条件 ``os._exit``。
# 比上面那串 14s 留出余量：它是兜底，不是正常路径的预算。
IDLE_EXIT_DEADLINE_SECONDS = 20.0

env = Env(prefix=ENV_PREFIX)
env.read_env(".env")

# -----------------------------------------------------------------------
# 运行目标
# -----------------------------------------------------------------------

# 暴露给编码工具的 workspace 目录，Agent 只能读写这里面的内容。
WORKSPACE = env.path("WORKSPACE", None)

# 会话持久化状态的存放目录，必须位于 WORKSPACE 之外，否则会被 Agent 自己的文件和
# Shell 工具读到、甚至改坏自己的历史。这一点在构建应用时强制检查。
STATE_DIR = env.path("STATE_DIR", None)

# GET /health、POST /runs 和控制面接口共用的 Bearer。
RUNTIME_TOKEN = env.str("RUNTIME_TOKEN", "")

PORT = env.int("PORT", DEFAULT_AGENT_PORT)

# 用户应用约定端口。拉起时注入 APP_SPARK_AGENT_APP_PORT；不是 8000 也不拒绝启动。
APP_PORT = env.int("APP_PORT", DEFAULT_APP_PORT)

# 平台给这个沙箱预览入口的基址，带 scheme，不含 path。例如
# https://preview-session.example.com 。拼进 app.launched.url，不改变本机监听端口。
# 未注入时本机联调用 http://127.0.0.1:<APP_PORT>。
PREVIEW_BASE_URL = env.str("PREVIEW_BASE_URL", "")

# 空闲秒数从进程启动起算，POST /runs 结束后重置。缺省 1800；<= 0 关闭空闲退出。
# 从未收到 /runs 也会到期退出。
IDLE_TIMEOUT_SECONDS = env.int("IDLE_TIMEOUT_SECONDS", DEFAULT_IDLE_TIMEOUT_SECONDS)

# 只进日志与指标。不做业务分支：一个沙箱服务一个租户，这里按租户分流等于多造一套
# 别处没有的策略。
SESSION_ID = env.str("SESSION_ID", "")
TENANT_ID = env.str("TENANT_ID", "")

# -----------------------------------------------------------------------
# 模型
# -----------------------------------------------------------------------

# 对话使用的模型，格式是 pydantic-ai 的 <provider>:<model>。
#
# 另外支持 fake:<scenario>：一个不发起任何网络请求的确定性假模型，供集成测试把 Runtime
# 真正启动起来，场景清单见 fake_model.py。
MODEL = env.str("MODEL", "deepseek:deepseek-v4-flash", validate=Length(min=1))

# 一把钥匙，两条路，不是两套并行生产配置。
#
# 网关：未注入 BK_AIDEV_ACCESS_TOKEN 时，把它当作 bkaidev 的 access_token 回落，
# 以免已入库的 SPARK_MODEL_API_KEY 立刻失效。
# 直连：没有网关意图时，交给 pydantic-ai 按 MODEL 的 <provider>:<model> 推断，
# 走官网 Bearer。/runs 只认网关三件套或 fake；只配这把钥匙走直连时 HTTP 仍 503。
MODEL_API_KEY = env.str("MODEL_API_KEY", "") or None

# 用户态 access_token。app-spark 在 bkaidev 建好该沙箱的空间和单个智能体后注入。
# 出站只放进 X-Bkapi-Authorization 的 access_token 字段，不带 bk_app_code /
# bk_app_secret。本组件不调创建空间 / 智能体的 API。
BK_AIDEV_ACCESS_TOKEN = env.str("BK_AIDEV_ACCESS_TOKEN", "") or None

# 不带 vendor 前缀的模型名（如 deepseek-v4-flash），必须落在 MODEL_PROFILES。
MODEL_NAME = env.str("MODEL_NAME", "")

# bkaidev LLM 网关 OpenAI 兼容入口，注入到 v1 这一层，不要带 /chat/completions。
# prod 示例：https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1。
MODEL_BASE_URL = env.str("MODEL_BASE_URL", "")

# MODEL_NAME → 能力档。表外名称不得走「按名字猜测」的保守档，否则工具调用会静默关掉。
# 值是档位标识，不是拼进请求的 vendor 前缀。
MODEL_PROFILES: dict[str, str] = {
    "deepseek-v4-flash": "deepseek",
}

# 对照表内每一档都必须显式打开工具调用和结构化输出，禁止落到 pydantic-ai 的保守推断。
_TOOL_AND_STRUCTURED_PROFILE = OpenAIModelProfile(
    supports_tools=True,
    supports_json_schema_output=True,
    supports_json_object_output=True,
    supports_tool_return_schema=True,
)

# -----------------------------------------------------------------------
# 应用日志
# -----------------------------------------------------------------------

# 本会话约定应用日志。位于 workspace / state 之外；日志工具只读这一条，不接受路径参数。
# 后续会把用户应用 stdout/stderr 接到同一文件。缺省与容器数据盘对齐。
DEFAULT_APP_LOG_PATH = "/data/app.log"
APP_LOG_PATH = env.path("APP_LOG_PATH", Path(DEFAULT_APP_LOG_PATH))

# 单次返回正文的字节上限。按需求锁定，不是部署旋钮。
APP_LOG_MAX_BYTES = 8192

# fake:slow 场景挂起的秒数。它存在的意义是让「run 正在进行中」成为一个能被外部观察到的
# 稳定状态，从而可以真实地触发 Runtime 的 409，而不是靠 sleep 去猜时序。
FAKE_DELAY_SECONDS = env.float("FAKE_DELAY_SECONDS", 2.0, validate=Range(min=0))

# Agent 的系统提示词。它和 agent.py 里挂载的能力是配套的——提示词里提到的「file 工具」
# 「shell 工具」「AGENTS.md」分别对应 FileSystem、Shell、RepoContext 三个能力。
#
# App Framework 一节里的 main:app 与 app_supervisor 里构造的启动命令是一对：那边启的就是这个
# 导入路径，模型写成别的入口名，launch 一定失败。两处要一起改，不要只动一边。
#
# TODO：当前仅做调试功能后，后续再调。真出现多套技术栈时把「怎么写应用」抽成可切换的档，
# 而不是再挂一个指向本包安装目录的 RepoContext。
INSTRUCTIONS = """
You are a coding agent working inside the provided workspace.

### Task

- Complete the user's task autonomously;
- Inspect the workspace before changing it;
- Make the smallest coherent change that solves the request, and verify the result when useful;
- Follow all AGENTS.md instructions;
- Preserve existing user changes;
- Report what changed, what you verified, and anything that remains blocked.

### Tools

- Use file tools to read and edit, and shell tools to run commands;
- Treat paths as relative to the workspace;
- Use `read_app_log` to diagnose the running application; it takes no path argument;
- NEVER expose credentials, and NEVER intentionally inspect secret files.

### App Framework

- ALWAYS write the user-facing application as a FastAPI app;
- ALWAYS export it from `main.py` as `app`, that is the import path `main:app`. The launcher
  starts that import path and no other, so an application exported under a different name
  cannot be started at all;
- NEVER listen on a port yourself, and NEVER hard-code one. The launcher decides the port and
  passes it to the server on the command line, so the application has no say in it;
- Do NOT align this application with the BlueKing or PaaS application framework in this
  period. A plain FastAPI HTTP app is enough.

### Launch App

- Once the code can run, use the `launch_app` tool to start or restart the application;
- ALWAYS launch through `launch_app`. NEVER host a long-running server with the shell, and
  NEVER start the application any other way;
- When `launch_app` reports a failure, read the log with `read_app_log`, fix the cause, and
  launch once more;
- The tool refuses a third attempt in the same turn. Report the failure at that point rather
  than keep retrying.
""".strip()

# -----------------------------------------------------------------------
# 上下文压缩
# -----------------------------------------------------------------------

# 压缩要把输入压回到的 token 预算。
#
# DeepSeek V4 Flash 的上下文窗口是 1,000,000 token，
# 但输入和生成共用这一个信封，而模型最多能输出 384,000 token。压回 480,000 就给一次
# 满长度生成留出了余量（480K + 384K = 864K），而不是让一段长历史把回复的空间挤掉。
# 用绝对值而不是窗口比例：这样触发点固定在测试能够到的地方，也不会随计价表变动而漂移。
COMPACTION_TARGET_TOKENS = env.int("COMPACTION_TARGET_TOKENS", 480_000, validate=Range(min=1))

# 单条消息 part 的 token 上限，超过就截断。跑飞的生成表现为一个超大 part 而不是总量
# 偏大，所以任何基于总量的策略都碰不到它；把超限的部分截掉才能保证下一次请求还发得出去。
COMPACTION_MAX_PART_TOKENS = env.int("COMPACTION_MAX_PART_TOKENS", 50_000, validate=Range(min=1))

# 摘要层原样保留的对话尾部长度。它同时也是摘要层的下限：短于这个长度的历史会被原样返回，
# 因为没有足够旧的内容值得总结。
COMPACTION_KEEP_MESSAGES = env.int("COMPACTION_KEEP_MESSAGES", 20, validate=Range(min=0))

# 清空工具结果时，最近多少组「工具调用 / 工具结果」保持完整。刚发生的工具结果往往正是模型
# 下一步要用的，清掉它们省下的 token 换不回这个代价。
COMPACTION_KEEP_TOOL_RESULT_PAIRS = env.int("COMPACTION_KEEP_TOOL_RESULT_PAIRS", 3, validate=Range(min=0))

# -----------------------------------------------------------------------
# 状态回写（复制到控制面）
# -----------------------------------------------------------------------

# 控制面的会话级状态写入地址，例如
# http://api/api/internal/conversations/<uuid>/state/。
#
# 留空即关闭回写：此时 Runtime 完全独立，状态只存在于 STATE_DIR，也就是本地开发和单测的形态。
# 地址由控制面在拉起 Runtime 时给出，且已经带上会话路径，所以 Runtime 自己不需要知道
# 「会话」是什么，也不需要在启动时就知道自己的 conversation_id。
CONTROL_PLANE_URL = env.str("CONTROL_PLANE_URL", None)

# 访问上述地址用的 Bearer token，由控制面签发。配了 URL 就必须配它。
CONTROL_PLANE_TOKEN = env.str("CONTROL_PLANE_TOKEN", None)

# 单次状态写入调用的超时秒数。给得比较宽松是因为一份 context 文档可能有好几 MB，但必须有限：
# 一轮 run 结束时的 flush 会等它。
CONTROL_PLANE_TIMEOUT_SECONDS = env.float("CONTROL_PLANE_TIMEOUT_SECONDS", 30.0, validate=Range(min=0))

# 每次推送最多带多少条日志记录。
PUSH_BATCH_SIZE = env.int("PUSH_BATCH_SIZE", 50, validate=Range(min=1))

# 一次推送失败后等多久重试，避免控制面挂掉时空转。
PUSH_RETRY_BACKOFF_SECONDS = env.float("PUSH_RETRY_BACKOFF_SECONDS", 2.0, validate=Range(min=0))

# 一轮 run 结束时等待推送追平的秒数。超时不会让这一轮失败——数据还在本地文件里、后台任务会继续
# 重试——但 /health 的复制游标会显示落后。
PUSH_FLUSH_TIMEOUT_SECONDS = env.float("PUSH_FLUSH_TIMEOUT_SECONDS", 30.0, validate=Range(min=0))

if CONTROL_PLANE_URL and not CONTROL_PLANE_TOKEN:
    raise EnvError(f"{ENV_PREFIX}CONTROL_PLANE_TOKEN must be set whenever {ENV_PREFIX}CONTROL_PLANE_URL is")

# -----------------------------------------------------------------------
# Workspace 工作区持久化（基于 Git）
# -----------------------------------------------------------------------

# Project 私有仓库的 HTTP clone 地址，由控制面在拉起 Runtime 时注入，且必须是**沙箱能解析的**
# 地址：控制面自己用的 `localhost` 拿到这里只会打到沙箱自己。
#
# 留空即关闭 Git 持久化：此时 workspace 只存在于本地磁盘，也就是单测与本地开发的形态。
GIT_REMOTE_URL = env.str("GIT_REMOTE_URL", "")

# 仓库范围的读写 token，作为 HTTP Basic 的密码。长期有效、不随 Runtime 代次轮换，因此它
# 只在受控的 git 子进程环境里出现，不进命令行、不写进 .git/config、不进提交内容。
GIT_TOKEN = env.str("GIT_TOKEN", "")

# Basic 认证的用户名，对 Forgejo 是签发 token 的那个服务账号。
GIT_USERNAME = env.str("GIT_USERNAME", "")

# 唯一的工作分支。推送与恢复都只认它。
GIT_BRANCH = env.str("GIT_BRANCH", "main")

# 提交身份。是机器人而不是终端用户：提交发生在 Agent 里，而蓝鲸用户未必有 Git 能接受的邮箱。
# Git 在缺少这两项时直接拒绝提交，所以它们有缺省值而不是留空。
GIT_AUTHOR_NAME = env.str("GIT_AUTHOR_NAME", "App-Spark")
GIT_AUTHOR_EMAIL = env.str("GIT_AUTHOR_EMAIL", "app-spark@localhost.invalid")

# 单条 git 命令的超时秒数。必须有限：本地提交发生在 run 收尾屏障里，一条挂住的命令等于挂住
# 这一轮对话。给到 120 秒是因为首次 clone 要走网络。
GIT_COMMAND_TIMEOUT_SECONDS = env.float("GIT_COMMAND_TIMEOUT_SECONDS", 120.0, validate=Range(min=0))

# 文件策略的硬性体积上限，超限时提交明确失败并报出是哪些路径。见 ``git/policy.py``。
GIT_MAX_FILE_BYTES = env.int("GIT_MAX_FILE_BYTES", 10 * 1024 * 1024, validate=Range(min=1))
GIT_MAX_TOTAL_BYTES = env.int("GIT_MAX_TOTAL_BYTES", 200 * 1024 * 1024, validate=Range(min=1))

# push 失败后重试的间隔秒数。网络分区可能持续很久，退避太短只是把失败刷进日志。
GIT_PUSH_RETRY_BACKOFF_SECONDS = env.float("GIT_PUSH_RETRY_BACKOFF_SECONDS", 5.0, validate=Range(min=0))

# 开始下一轮前，等待上一轮文件推送到远端的时间上限。这是逃生口的那个「有界」：网络断了时
# push 可能永远落不了地，无限等待等于把用户锁在自己的会话外面。超时后接口返回 409，客户端
# 可以带 ``?allow_unsaved=true`` 明确选择继续。
GIT_SAVE_WAIT_TIMEOUT_SECONDS = env.float("GIT_SAVE_WAIT_TIMEOUT_SECONDS", 10.0, validate=Range(min=0))

# 这个 Runtime 属于哪个 Project，仅用于写进 commit trailer 便于追溯。留空不影响保存。
PROJECT_ID = env.str("PROJECT_ID", "")

if GIT_REMOTE_URL and not GIT_TOKEN:
    raise EnvError(f"{ENV_PREFIX}GIT_TOKEN must be set whenever {ENV_PREFIX}GIT_REMOTE_URL is")

# -----------------------------------------------------------------------
# HTTP 接口
# -----------------------------------------------------------------------

# 两条日志游标接口 limit 参数的默认值和上限。
DEFAULT_DRAIN_LIMIT = env.int("DEFAULT_DRAIN_LIMIT", 200, validate=Range(min=1))
MAX_DRAIN_LIMIT = env.int("MAX_DRAIN_LIMIT", 1_000, validate=Range(min=1))

if DEFAULT_DRAIN_LIMIT > MAX_DRAIN_LIMIT:
    raise EnvError(
        f"{ENV_PREFIX}DEFAULT_DRAIN_LIMIT ({DEFAULT_DRAIN_LIMIT}) must not be greater than "
        f"{ENV_PREFIX}MAX_DRAIN_LIMIT ({MAX_DRAIN_LIMIT})"
    )


def preview_base_url() -> str:
    """平台预览基址；未注入时用本机 APP_PORT。"""
    stripped = PREVIEW_BASE_URL.strip().rstrip("/")
    if stripped:
        return stripped
    return f"http://127.0.0.1:{APP_PORT}"


def _stripped(value: str | None) -> str | None:
    """空白和未注入都当成没有。"""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def gateway_access_token() -> str | None:
    """bkaidev 出站使用的用户态 access_token。

    优先 BK_AIDEV_ACCESS_TOKEN；未注入时回落到 MODEL_API_KEY。
    两侧都先 strip，空白值不能挡住回落，也不能把就绪门闩打成真。
    """
    return _stripped(BK_AIDEV_ACCESS_TOKEN) or _stripped(MODEL_API_KEY)


def uses_direct_provider() -> bool:
    """没有网关意图时，才允许 MODEL_API_KEY 走官网 provider。

    注入了 BK_AIDEV_ACCESS_TOKEN 或 MODEL_BASE_URL 就表示要走 bkaidev，
    缺项不得回落到公网 api.deepseek.com。
    """
    return (
        _stripped(BK_AIDEV_ACCESS_TOKEN) is None
        and not MODEL_BASE_URL.strip()
        and _stripped(MODEL_API_KEY) is not None
    )


def resolved_model_name() -> str:
    """去掉首尾空白后的 MODEL_NAME。"""
    return MODEL_NAME.strip()


def model_profile(name: str | None = None) -> str | None:
    """对照表中的能力档；表外名称返回 None，调用方必须当成未就绪。"""
    return MODEL_PROFILES.get(name if name is not None else resolved_model_name())


def openai_capability_profile(name: str | None = None) -> OpenAIModelProfile | None:
    """列出模型对应的显式 OpenAI 能力档；表外名称返回 None，不得猜测。"""
    if model_profile(name) is None:
        return None
    return _TOOL_AND_STRUCTURED_PROFILE


def is_model_ready() -> bool:
    """fake: 无需凭据；真实模型要 access_token、网关地址、对照表内模型名。"""
    if MODEL.startswith("fake:"):
        return True
    return gateway_access_token() is not None and bool(MODEL_BASE_URL.strip()) and model_profile() is not None


def is_git_configured() -> bool:
    """是否给了远端仓库地址和凭据。为假时 workspace 只存在于本地磁盘。"""
    return bool(GIT_REMOTE_URL and GIT_TOKEN)


def _tokens_match(expected: str, actual: str) -> bool:
    """恒定时间比较；期望值为空时永不匹配。

    先拒绝长度不一致，避免 compare_digest 把 401 变成 500。
    """
    if not expected or not actual or len(expected) != len(actual):
        return False
    return hmac.compare_digest(expected, actual)


def matches_runtime_token(token: str) -> bool:
    """token 是否等于 APP_SPARK_AGENT_RUNTIME_TOKEN。"""
    return _tokens_match(RUNTIME_TOKEN, token)


def matches_bearer(authorization: str | None) -> bool:
    """Authorization 是否为 Bearer <APP_SPARK_AGENT_RUNTIME_TOKEN>。"""
    if not authorization:
        return False
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credential:
        return False
    return matches_runtime_token(credential.strip())
