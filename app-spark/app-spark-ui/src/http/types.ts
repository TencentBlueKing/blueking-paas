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

/** Agent 提交代码时用的机器身份，不是终端用户。 */
export interface GitCommitIdentity {
  author_name: string;
  author_email: string;
}

/** 建仓进度：`pending` 等待初始化，`ready` 初始化完成，`failed` 初始化失败。 */
export type GitRepositoryStatus = 'pending' | 'ready' | 'failed';

/** GET /projects/{id}/git-repository/ 仓库状态，不含凭据明文。 */
export interface GitRepositoryResponse {
  owner: string;
  name: string;
  default_branch: string;
  status: GitRepositoryStatus;
  status_detail: string;
  clone_url: string;
  created_at: string;
  updated_at: string;
  commit: GitCommitIdentity;
  /**
   * 下载已保存源码（zip）的地址；远端仓库还没建起来时为 null。
   *
   * 可能是站内路径（含后端 `FORCE_SCRIPT_NAME` 前缀），也可能是带协议的绝对地址，交给
   * `resolveApiUrl` 分辨即可。
   *
   * 下到的是 Agent **最后一次成功保存**的那一版，不是运行中 Runtime 工作区的实时状态；文件名里
   * 带 commit 短 SHA，据此可分辨拿到的是哪一版。
   */
  archive_url: string | null;
}

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

export interface ListHistoryQuery {
  /** 上一页返回的 `next_cursor`；不传则读最新一页 */
  cursor?: string;
  /** 本页覆盖几轮对话，默认由后端决定 */
  runs?: number;
}

/**
 * 一页展示历史。
 *
 * 分页是往**更早**的方向翻的：不带游标拿到的是最新的若干轮，之后一直用上一页的 `next_cursor`
 * 往前取。页内记录始终是对话正序。
 *
 * 一页是若干个**完整的 run**，不是固定条数，所以 `records` 的长度是浮动的。页边界卡在 run 边界
 * 上，是因为回放事件流要靠一个有状态的 reducer（见 `services/agent/ag-ui.ts`）：切在一次工具调用
 * 中间，那次调用在界面上就永远停在「正在执行」。
 */
export interface ConversationHistoryResponse {
  records: ConversationHistoryRecord[];
  /** 取更早一页时原样回传；null 表示已经到会话开头，没有更早的内容了 */
  next_cursor: string | null;
  /** AG-UI 事件频道当前的最后一个游标，可直接当 ui-events 的 `since` 用 */
  last_seq: number;
}
