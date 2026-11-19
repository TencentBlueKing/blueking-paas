import RequestError from './fetch/request-error';

/**
 * app-spark-api 的业务错误码。
 *
 * 后端返回的 `code` 是一个稳定的字符串标识（见 app-spark-api 的 `error_codes.py`），HTTP 状态码
 * 只是它的表现形式：好几种互不相干的错误共用同一个 409，只有 code 能把它们区分开。所以判断
 * 「是哪一种错」必须比对这里的常量，而不是状态码。
 */
export const ApiErrorCode = {
  /** 会话已结束：既不能再推进，也不能再被结束一次。 */
  CONVERSATION_CLOSED: 'CONVERSATION_CLOSED',
  /** 同项目里已有别的会话占着 workspace，新会话拉不起自己的 Agent Runtime。 */
  AGENT_WORKSPACE_BUSY: 'AGENT_WORKSPACE_BUSY',
  /** 工作区应用的端口被不是 Runtime 拉起的进程占着，预览拉不起来。 */
  PREVIEW_PORT_TAKEN: 'PREVIEW_PORT_TAKEN',
  /** 要停的那一轮已经结束，或它所在的 Runtime 已经不在了。 */
  RUN_NOT_RUNNING: 'RUN_NOT_RUNNING',
  /** 用户选择的模型已经不在当前推荐目录中，需要刷新目录并重新选择。 */
  MODEL_NOT_AVAILABLE: 'MODEL_NOT_AVAILABLE',
  /** 当前模型不支持图片输入，本轮不会开始。 */
  MODEL_IMAGE_INPUT_UNSUPPORTED: 'MODEL_IMAGE_INPUT_UNSUPPORTED',
  /** 附件超过后端允许的 5MB。 */
  ATTACHMENT_TOO_LARGE: 'ATTACHMENT_TOO_LARGE',
  /** 附件存储暂时不可用，可以用同一份原始文件重试。 */
  ATTACHMENT_STORAGE_UNAVAILABLE: 'ATTACHMENT_STORAGE_UNAVAILABLE',
  /** 提交给本轮的附件不属于当前会话或已经不可用。 */
  ATTACHMENT_NOT_FOUND: 'ATTACHMENT_NOT_FOUND',
  /** 附件已经随另一轮对话发出，不能重复使用。 */
  ATTACHMENT_ALREADY_USED: 'ATTACHMENT_ALREADY_USED',
  /** 请求字段未通过后端校验。 */
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  /** 当前项目还没有可发布的代码检查点。 */
  PUBLICATION_NO_VERSION: 'PUBLICATION_NO_VERSION',
  /** 首次发布时填写的应用名称过滤后为空。 */
  PUBLICATION_APP_NAME_INVALID: 'PUBLICATION_APP_NAME_INVALID',
  /** 首次发布时的应用名称已被开发者中心的其他应用使用，换一个名称再发布。 */
  PUBLICATION_APP_NAME_CONFLICT: 'PUBLICATION_APP_NAME_CONFLICT',
  /** 开发者中心拒绝创建应用或提交部署。 */
  PUBLICATION_SUBMIT_FAILED: 'PUBLICATION_SUBMIT_FAILED',
  /** 当前项目已经有发布任务进行中，需要重新查询任务状态。 */
  PUBLICATION_TASK_IN_PROGRESS: 'PUBLICATION_TASK_IN_PROGRESS',
} as const;

/** 判断一个异常是否为指定业务错误码的接口错误。 */
export const isApiError = (error: unknown, code: string): boolean => (
  error instanceof RequestError && error.code === code
);
