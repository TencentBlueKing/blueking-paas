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
  created: string;
  updated: string;
}

export type PagedProjectResponse = PagedResponse<ProjectResponse>;

export interface ListConversationsQuery extends PageQuery {
  is_live?: boolean | null;
}

export interface ConversationResponse {
  number: number;
  conversation_id: string;
  is_live: boolean;
  created: string;
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
