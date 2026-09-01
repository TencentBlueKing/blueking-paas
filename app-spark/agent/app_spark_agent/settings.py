"""Agent 服务可配置项。"""

from __future__ import annotations

import hmac

from environs import Env, EnvError
from marshmallow.validate import Length, Range

# 所有配置项共用的环境变量前缀。接入层与本地开发都只下这一套。
ENV_PREFIX = "APP_SPARK_AGENT_"

DEFAULT_AGENT_PORT = 8090
DEFAULT_APP_PORT = 8000
DEFAULT_WORKSPACE = "/data/workspace"
DEFAULT_STATE_DIR = "/data/state"
DEFAULT_IDLE_TIMEOUT_SECONDS = 1800
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 1

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

# 用户应用约定端口。本组件只读入并留给后续子进程，不拉起应用，也不因不是 8000
# 而拒绝启动——数值由接入层锁定，端口是否在听属于应用管理。
APP_PORT = env.int("APP_PORT", DEFAULT_APP_PORT)

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

# 对话使用的模型，格式是 pydantic-ai 的 ``<provider>:<model>``。
#
# 另外支持 ``fake:<scenario>``：一个不发起任何网络请求的确定性假模型，供集成测试把 Runtime
# 真正启动起来，场景清单见 ``fake_model.py``。
MODEL = env.str("MODEL", "deepseek:deepseek-v4-flash", validate=Length(min=1))

# 模型密钥，同时交给 provider。缺失时 health 报 model_ready=false，POST /runs 返回 503。
# 这是唯一的就绪门闩：模型名或网关地址缺失不让 Runtime 报未就绪。
MODEL_API_KEY = env.str("MODEL_API_KEY", "") or None

# 网关目标，读入是为了契约落在同一处。当前还不拿它们去拨号：模型客户端仍由
# ``MODEL`` 与 ``MODEL_API_KEY`` 构造。
MODEL_NAME = env.str("MODEL_NAME", "")
MODEL_BASE_URL = env.str("MODEL_BASE_URL", "")

# ``fake:slow`` 场景挂起的秒数。它存在的意义是让「run 正在进行中」成为一个能被外部观察到的
# 稳定状态，从而可以真实地触发 Runtime 的 409，而不是靠 sleep 去猜时序。
FAKE_DELAY_SECONDS = env.float("FAKE_DELAY_SECONDS", 2.0, validate=Range(min=0))

# Agent 的系统提示词。它和 ``agent.py`` 里挂载的能力是配套的——提示词里提到的「file 工具」
# 「shell 工具」「AGENTS.md」分别对应 FileSystem、Shell、RepoContext 三个能力。
#
# TODO：当前仅做调试功能后，后续再调，以及增加更多 SKILL。
INSTRUCTIONS = """
You are a coding agent working inside the provided workspace.

Complete the user's task autonomously. Inspect the workspace before changing it, make the
smallest coherent change that solves the request, and verify the result when useful. Follow all
AGENTS.md instructions. Preserve existing user changes and report what changed, what you
verified, and anything that remains blocked.

Use file tools for reading and editing and shell tools for commands. Treat paths as relative to the
workspace. Never expose credentials or intentionally inspect secret files.
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

# 单条消息 part 的 token 上限，超过就截断。跑飞的生成表现为**一个**超大 part 而不是总量
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
# ``http://api/api/internal/conversations/<uuid>/state/``。
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
# 重试——但 ``/health`` 的复制游标会显示落后。
PUSH_FLUSH_TIMEOUT_SECONDS = env.float("PUSH_FLUSH_TIMEOUT_SECONDS", 30.0, validate=Range(min=0))

if CONTROL_PLANE_URL and not CONTROL_PLANE_TOKEN:
    raise EnvError(f"{ENV_PREFIX}CONTROL_PLANE_TOKEN must be set whenever {ENV_PREFIX}CONTROL_PLANE_URL is")

# -----------------------------------------------------------------------
# HTTP 接口
# -----------------------------------------------------------------------

# 两条日志游标接口 ``limit`` 参数的默认值和上限。
DEFAULT_DRAIN_LIMIT = env.int("DEFAULT_DRAIN_LIMIT", 200, validate=Range(min=1))
MAX_DRAIN_LIMIT = env.int("MAX_DRAIN_LIMIT", 1_000, validate=Range(min=1))

if DEFAULT_DRAIN_LIMIT > MAX_DRAIN_LIMIT:
    raise EnvError(
        f"{ENV_PREFIX}DEFAULT_DRAIN_LIMIT ({DEFAULT_DRAIN_LIMIT}) must not be greater than "
        f"{ENV_PREFIX}MAX_DRAIN_LIMIT ({MAX_DRAIN_LIMIT})"
    )


def is_model_ready() -> bool:
    """模型是否无需外部凭据，或已注入 ``APP_SPARK_AGENT_MODEL_API_KEY``。"""
    return MODEL.startswith("fake:") or MODEL_API_KEY is not None


def _tokens_match(expected: str, actual: str) -> bool:
    """恒定时间比较；期望值为空时永不匹配。

    先拒绝长度不一致，避免 ``compare_digest`` 把 401 变成 500。
    """
    if not expected or not actual or len(expected) != len(actual):
        return False
    return hmac.compare_digest(expected, actual)


def matches_runtime_token(token: str) -> bool:
    """``token`` 是否等于 ``APP_SPARK_AGENT_RUNTIME_TOKEN``。"""
    return _tokens_match(RUNTIME_TOKEN, token)


def matches_bearer(authorization: str | None) -> bool:
    """Authorization 是否为 ``Bearer <APP_SPARK_AGENT_RUNTIME_TOKEN>``。"""
    if not authorization:
        return False
    scheme, _, credential = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credential:
        return False
    return matches_runtime_token(credential.strip())
