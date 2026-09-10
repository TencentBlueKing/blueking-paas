import http from './fetch';
import RequestError from './fetch/request-error';
import type {
  AuthenticatedUserResponse,
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
} from './types';

const API_PATH = '/api-svc/api';

const getApiPrefix = () => {
  const raw = (typeof window !== 'undefined' && window.BK_API_URL) || process.env.BK_API_URL || '';
  const base = String(raw).trim().replace(/\/$/, '');
  // 绝对地址只作为本地代理目标，页面始终打同源 /api-svc，避免跨域
  if (!base || /^https?:\/\//.test(base)) {
    return API_PATH;
  }
  return `${base}${API_PATH}`;
};

const apiPrefix = getApiPrefix();

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

export const listUiEvents = (
  projectId: string,
  number: number,
  query: ListUiEventsQuery = {},
): Promise<UiEventPageResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/ui-events/`, query)
);

const resolveApiUrl = (path: string) => {
  if (/^https?:\/\//.test(path)) return path;
  const site = String(window.SITE_URL || '').replace(/\/$/, '');
  const ajax = String(process.env.BK_AJAX_URL_PREFIX || '').replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${location.origin}${site}${ajax}${normalized}`;
};

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
