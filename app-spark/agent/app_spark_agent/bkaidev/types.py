"""bkaidev LLM 网关 OpenAPI 结构体。

字段对齐 bk-aidev 的 aidev_gateway/protocols/openai.py，以及网关资源
POST {BASE_URL}/chat/completions（aidev_llm_gateway_chat_completion）和
GET {BASE_URL}/models（aidev_llm_gateway_models）。

BASE_URL 注入到 v1 层，例如
https://bkaidev.apigw.example.com/prod/openapi/aidev/gateway/llm/v1。
网关 resources.yaml 不展开请求体，所以字段以协议层为准。

Python 属性避开 id / type / object / property 这些内置名，JSON 仍走协议字段。
"""

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


def _wire(python_name: str, json_name: str, **kwargs: Any) -> Any:
    """Python 属性避开内置名，出站 / 入站 JSON 仍用协议字段。"""
    return Field(
        validation_alias=AliasChoices(python_name, json_name),
        serialization_alias=json_name,
        **kwargs,
    )


class FunctionDefinition(BaseModel):
    """OpenAI function 定义，挂在 tools[].function 上。

    :param name: 函数名，模型回传的 tool_calls[].function.name 用这个。
    :param description: 给模型看的说明，可空。
    :param parameters: JSON Schema 对象；网关原样转给上游。
    """

    name: str
    description: str | None = None
    parameters: dict[str, object] | None = None


class FunctionTool(BaseModel):
    """Chat Completions 的 tools 数组元素。本期只发 type=function。"""

    tool_type: Literal["function"] = _wire("tool_type", "type", default="function")
    function: FunctionDefinition


class FunctionCall(BaseModel):
    """一次已选定的 function 调用。

    :param name: 要调用的函数名。
    :param arguments: 参数的 JSON 字符串（不是对象），与 OpenAI 一致。
    """

    name: str
    arguments: str


class ChatMessageToolCall(BaseModel):
    """assistant 消息里的一条 tool call。

    :param tool_call_id: 本次调用 id，后续 role=tool 的 tool_call_id 必须对上。
    :param function: 函数名和参数。
    :param tool_type: 固定 function。
    """

    tool_call_id: str = _wire("tool_call_id", "id")
    function: FunctionCall
    tool_type: Literal["function"] = _wire("tool_type", "type", default="function")


class ChatCompletionMessage(BaseModel):
    """Chat Completions 的一条 messages[] / 响应 choices[].message。

    请求侧常见 role：system / user / assistant / tool。
    响应侧可能多带 reasoning_content（思考模型）。

    :param role: 说话角色。
    :param content: 文本正文；纯 tool_calls 时可为 None。
    :param name: 可选发言者名，OpenAI 兼容字段。
    :param tool_call_id: role=tool 时对应的 ChatMessageToolCall.tool_call_id。
    :param tool_calls: assistant 发起的工具调用列表。
    :param function_call: 旧版单函数调用字段，新路径用 tool_calls。
    :param reasoning_content: 思考链正文，部分模型会回。
    """

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ChatMessageToolCall] | None = None
    function_call: FunctionCall | None = None
    reasoning_content: str | None = None


class ChatCompletionRequest(BaseModel):
    """POST /chat/completions 请求体（aidev_llm_gateway_chat_completion）。

    网关 extra="allow"，未列字段原样转发。本期不用流式：流式由 pydantic-ai
    的 OpenAI 客户端走同一地址。

    :param model: llm_code，必须与 GET /models 返回的 llm_code 一致。
    :param messages: 对话消息，含历史与本轮增量。
    :param temperature: 采样温度，协议默认 0.7。
    :param top_p: nucleus sampling。
    :param n: 生成几条 completion。
    :param max_tokens: 生成上限；不设则走上游默认。
    :param stop: 停止序列。
    :param stream: 是否 SSE 流式。ApiClient 默认 False。
    :param presence_penalty: 话题新鲜度惩罚。
    :param frequency_penalty: 重复惩罚。
    :param response_format: 结构化输出约定，字符串或 {"type": ...}。
    :param user: 调用方用户标识，网关不校验用户认证，此字段仅透传。
    :param tools: 可供模型调用的函数列表。
    :param tool_choice: none / auto / required，或指定某个 function。
    :param parallel_tool_calls: 是否允许并行 tool calls。
    :param functions: 旧版 functions 字段，优先用 tools。
    :param function_call: 旧版 function_call 字段，优先用 tool_choice。
    """

    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[ChatCompletionMessage]
    temperature: float | None = 0.7
    top_p: float | None = 1.0
    n: int | None = 1
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    stream: bool | None = False
    presence_penalty: float | None = 0.0
    frequency_penalty: float | None = 0.0
    response_format: str | dict[str, Any] | None = None
    user: str | None = None
    tools: list[FunctionTool] | None = None
    tool_choice: Literal["none", "auto", "required"] | dict[str, Any] | None = None
    parallel_tool_calls: bool | None = None
    functions: list[FunctionDefinition] | None = None
    function_call: Literal["none", "auto"] | dict[str, Any] | None = None


class PromptTokensDetails(BaseModel):
    """prompt 侧的细项用量，含缓存命中。"""

    audio_tokens: int | None = None
    cached_tokens: int | None = None
    cache_write_tokens: int | None = None


class UsageInfo(BaseModel):
    """一次 completion 的 token 用量。

    :param prompt_tokens: 输入 token。
    :param total_tokens: 输入 + 输出。
    :param completion_tokens: 输出 token。
    :param prompt_tokens_details: 缓存等细项。
    """

    model_config = ConfigDict(extra="allow")

    prompt_tokens: int = 0
    total_tokens: int = 0
    completion_tokens: int | None = 0
    prompt_tokens_details: PromptTokensDetails | None = None


class ChatCompletionResponseChoice(BaseModel):
    """非流式响应的一条 choice。

    :param index: 在 choices 中的位置。
    :param message: 模型回复（文本和/或 tool_calls）。
    :param finish_reason: stop / length / content_filter /
        tool_calls / function_call。
    """

    index: int
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "content_filter", "tool_calls", "function_call"]


class ChatCompletionResponse(BaseModel):
    """POST /chat/completions 非流式响应。

    :param completion_id: 网关生成的 completion id，形如 chatcmpl-...。
    :param object_type: 固定 chat.completion。
    :param created: Unix 秒。
    :param model: 实际使用的 llm_code。
    :param choices: 生成结果；n=1 时通常只有一条。
    :param usage: token 用量。
    """

    model_config = ConfigDict(extra="allow")

    completion_id: str = _wire("completion_id", "id")
    object_type: str = _wire("object_type", "object", default="chat.completion")
    created: int
    model: str
    choices: list[ChatCompletionResponseChoice]
    usage: UsageInfo


class ModelPermission(BaseModel):
    """GET /models 里一张模型卡上的权限描述，OpenAI 兼容字段。"""

    model_config = ConfigDict(extra="allow")

    permission_id: str = _wire("permission_id", "id")
    object_type: str = _wire("object_type", "object", default="model_permission")
    created: int
    allow_create_engine: bool = False
    allow_sampling: bool = True
    allow_logprobs: bool = True
    allow_search_indices: bool = True
    allow_view: bool = True
    allow_fine_tuning: bool = False
    organization: str = "*"
    group: str | None = None
    is_blocking: bool = False


class ModelCard(BaseModel):
    """一张可用模型。

    :param llm_code: 应对 MODEL_NAME / 请求里的 model。
    :param object_type: 固定 model。
    :param created: Unix 秒。
    :param owned_by: 协议默认 aidev。
    :param root: 根模型 id，可空。
    :param parent: 父模型 id，可空。
    :param permission: 权限列表。
    :param extra_properties: 网关扩展属性，JSON 字段仍是 property。
    """

    model_config = ConfigDict(extra="allow")

    llm_code: str = _wire("llm_code", "id")
    object_type: str = _wire("object_type", "object", default="model")
    created: int
    owned_by: str = "aidev"
    root: str | None = None
    parent: str | None = None
    permission: list[ModelPermission] = Field(default_factory=list)
    extra_properties: dict[str, Any] | None = _wire("extra_properties", "property", default=None)


class ModelList(BaseModel):
    """GET /models 响应（aidev_llm_gateway_models）。

    网关按应用身份过滤；未开通的 llm_code 不会出现在 data 里，
    直接用也会被拒绝为「该应用无访问该模型的权限」。
    """

    object_type: str = _wire("object_type", "object", default="list")
    data: list[ModelCard] = Field(default_factory=list)


class ErrorResponseDetail(BaseModel):
    """OpenAI 风格错误体里的 error 对象。"""

    message: str
    code: int
    error_type: str = _wire("error_type", "type", default="invalid_request_error")


class ErrorResponse(BaseModel):
    """网关错误响应。"""

    error: ErrorResponseDetail
