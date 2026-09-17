import http, { resolveApiUrl } from './fetch';
import RequestError from './fetch/request-error';
import type {
  AuthenticatedUserResponse,
  ConversationHistoryResponse,
  ConversationResponse,
  ListConversationsQuery,
  ListUiEventsQuery,
  PagedConversationResponse,
  PagedProjectResponse,
  PageQuery,
  ProjectCreateRequest,
  ProjectResponse,
  RuntimeStateResponse,
  StartRunRequest,
  UiEventPageResponse,
} from './types';

export type {
  AgUiEvent,
  AnonymousUserResponse,
  AuthenticatedUserResponse,
  ConversationHistoryRecord,
  ConversationHistoryResponse,
  ConversationResponse,
  ErrorResponse,
  ListConversationsQuery,
  ListUiEventsQuery,
  PagedConversationResponse,
  PagedProjectResponse,
  PagedResponse,
  PageQuery,
  ProjectCreateRequest,
  ProjectResponse,
  RuntimeStateResponse,
  StartRunRequest,
  UiEventPageResponse,
  UserInfoResponse,
  UserMessageRecord,
} from './types';

// 业务 API 前缀，不含 SITE_URL。绝对 BK_API_URL 只给本地 webpack 代理用
const apiPrefix = '/api-svc/api';

export const getUserInfo = (): Promise<AuthenticatedUserResponse> => (
  http.get(`${apiPrefix}/accounts/userinfo/`, {}, { globalError: false })
);

export const listProjects = (query: PageQuery = {}): Promise<PagedProjectResponse> => (
  http.get(`${apiPrefix}/projects/`, query)
);

export const createProject = (payload: ProjectCreateRequest): Promise<ProjectResponse> => (
  http.post(`${apiPrefix}/projects/`, payload)
);

export const listConversations = (
  projectId: string,
  query: ListConversationsQuery = {},
): Promise<PagedConversationResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/`, query)
);

export const createConversation = (projectId: string): Promise<RuntimeStateResponse> => (
  http.post(`${apiPrefix}/projects/${projectId}/conversations/`)
);

export const getConversation = (
  projectId: string,
  number: number,
): Promise<RuntimeStateResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/`)
);

export const closeConversation = (
  projectId: string,
  number: number,
): Promise<ConversationResponse> => (
  http.post(`${apiPrefix}/projects/${projectId}/conversations/${number}/close/`)
);

/** 拉取已入库的 AG-UI 事件，用于 SSE 意外中断后从 `since` 处追赶；完整历史请用 `listHistory` */
export const listUiEvents = (
  projectId: string,
  number: number,
  query: ListUiEventsQuery = {},
): Promise<UiEventPageResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/ui-events/`, query)
);

/** 拉取会话的完整展示历史（用户输入 + AG-UI 事件），不分页，一次全量返回 */
export const listHistory = (
  projectId: string,
  number: number,
): Promise<ConversationHistoryResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/history/`)
);

/** 发起一轮对话，返回 AG-UI SSE Response，调用方自行读流 */
export const startConversationRun = async (
  projectId: string,
  number: number,
  payload: StartRunRequest,
): Promise<Response> => {
  const response = await fetch(resolveApiUrl(
    `${apiPrefix}/projects/${projectId}/conversations/${number}/runs/`,
  ), {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = response.statusText || '发起对话失败';
    try {
      const data = await response.json();
      detail = data.detail || data.message || detail;
    } catch {
      // 保持 statusText
    }
    throw new RequestError(response.status, detail);
  }

  return response;
};
