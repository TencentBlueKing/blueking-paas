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
} as const;

/** 判断一个异常是否为指定业务错误码的接口错误。 */
export const isApiError = (error: unknown, code: string): boolean => (
  error instanceof RequestError && error.code === code
);
