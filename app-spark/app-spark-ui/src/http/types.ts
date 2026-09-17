/** 分页查询 */
export interface PageQuery {
  page?: number;
  page_size?: number | null;
}

export interface PagedResponse<T> {
  items: T[];
  count: number;
}

export interface ErrorResponse {
  detail: string;
}

/** GET /accounts/userinfo/ 已登录 */
export interface AuthenticatedUserResponse {
  authenticated: true;
  username: string;
  display_name: string;
  tenant_id: string | null;
}

/** GET /accounts/userinfo/ 未登录（401） */
export interface AnonymousUserResponse {
  authenticated: false;
  login_url: string;
}

export type UserInfoResponse = AuthenticatedUserResponse | AnonymousUserResponse;

export interface ProjectCreateRequest {
  /** 全局唯一，2-20 个字符，小写字母开头，仅含小写字母、数字与连字符 */
  id: string;
  /** 同租户内唯一，1-20 个字符 */
  name: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export type PagedProjectResponse = PagedResponse<ProjectResponse>;

export interface ListConversationsQuery extends PageQuery {
  is_live?: boolean | null;
}

export interface ConversationResponse {
  number: number;
  conversation_id: string;
  is_live: boolean;
  created_at: string;
  closed_at: string | null;
}

export type PagedConversationResponse = PagedResponse<ConversationResponse>;

export interface RuntimeStateResponse {
  number: number;
  conversation_id: string;
  is_live: boolean;
  closed_at: string | null;
  model: string | null;
  context_version: number;
  log_seq: number;
  ui_event_seq: number;
  running: boolean;
  replication_pending: boolean;
}

export interface StartRunRequest {
  content: string;
}

export interface ListUiEventsQuery {
  since?: number;
  limit?: number | null;
}

export type AgUiEvent = Record<string, unknown>;

export interface UiEventPageResponse {
  since: number;
  last_seq: number;
  exhausted: boolean;
  records: AgUiEvent[];
}

/**
 * 历史里的一条用户输入。
 *
 * AG-UI 事件流里没有它：Runtime 只回写自己产生的事件，用户发过什么由后端单独存一张表，只有
 * history 接口会把两者按对话顺序合在一起交回来。
 */
export interface UserMessageRecord {
  /** 后端的消息 ID，可用于去重 */
  id: number;
  run_id: string | null;
  /** 插在该 UI event 序号之后，0 表示所有事件之前 */
  after_seq: number;
  created_at: string;
  content: string;
}

/** 一条展示历史，两个字段恰好一个非空。 */
export interface ConversationHistoryRecord {
  ui_event: AgUiEvent | null;
  user_message: UserMessageRecord | null;
}

/** 会话的完整展示历史，接口不分页，一次全量返回。 */
export interface ConversationHistoryResponse {
  records: ConversationHistoryRecord[];
}
