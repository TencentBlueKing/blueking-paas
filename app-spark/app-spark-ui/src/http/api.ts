import http, { resolveApiUrl } from './fetch';
import type { IFetchConfig } from './fetch';
import RequestError from './fetch/request-error';
import type {
  AuthenticatedUserResponse,
  ConversationHistoryResponse,
  ConversationResponse,
  GitRepositoryResponse,
  ListConversationsQuery,
  ListHistoryQuery,
  ListUiEventsQuery,
  ModelCatalogResponse,
  PagedConversationResponse,
  PagedProjectResponse,
  PageQuery,
  PreviewResponse,
  PreviewStartResponse,
  PublicationAppNameValidateResponse,
  PublicationDeploymentRequest,
  PublicationResponse,
  ProjectFromPromptRequest,
  ProjectFromPromptResponse,
  ProjectIntRenamingResponse,
  ProjectRenameRequest,
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
  DevServerStatus,
  ErrorResponse,
  GitCommitIdentity,
  GitRepositoryResponse,
  GitRepositoryStatus,
  ListConversationsQuery,
  ListHistoryQuery,
  ListUiEventsQuery,
  ModelCatalogItem,
  ModelCatalogResponse,
  ModelCatalogSource,
  PagedConversationResponse,
  PagedProjectResponse,
  PagedResponse,
  PageQuery,
  PreviewResponse,
  PreviewStartResponse,
  PublicationAppNameValidateResponse,
  PublicationDeploymentRequest,
  PublicationDevCenterLinks,
  PublicationFailure,
  PublicationOnlineVersion,
  PublicationResponse,
  PublicationTask,
  PublicationTaskStage,
  PublicationUnseenResult,
  ProjectFromPromptRequest,
  ProjectFromPromptResponse,
  ProjectIntRenamingResponse,
  ProjectRenameRequest,
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

/** 当前用户可用的模型目录。失败时由调用方降级到沙箱默认模型，不弹全局错误。 */
export const listModels = (): Promise<ModelCatalogResponse> => (
  http.get(`${apiPrefix}/models/`, {}, { globalError: false })
);

export const listProjects = (query: PageQuery = {}): Promise<PagedProjectResponse> => (
  http.get(`${apiPrefix}/projects/`, query)
);

/** 用用户的第一句话创建项目及承接首轮消息的会话。 */
export const createProjectFromPrompt = (
  payload: ProjectFromPromptRequest,
): Promise<ProjectFromPromptResponse> => (
  http.post(`${apiPrefix}/projects/-/create-from-prompt/`, payload, { globalError: false })
);

/** 查询从第一句话创建项目后触发的后台智能命名任务。 */
export const getProjectIntRenaming = (
  projectId: string,
): Promise<ProjectIntRenamingResponse> => (
  http.get(
    `${apiPrefix}/projects/${projectId}/int-renaming/`,
    {},
    { globalError: false },
  )
);

/** 修改当前用户自己的项目名称；名称不要求唯一。 */
export const renameProject = (
  projectId: string,
  payload: ProjectRenameRequest,
): Promise<ProjectResponse> => (
  http.post(`${apiPrefix}/projects/${projectId}/rename/`, payload, { globalError: false })
);

/** 删除项目。无请求体；成功后列表不再返回该项目。失败文案由确认框展示。 */
export const deleteProject = (projectId: string): Promise<void> => (
  http.delete(`${apiPrefix}/projects/${projectId}/`, {}, { globalError: false })
);

/** 项目在开发者中心的发布状态；发布进行中时由调用方每 3 秒轮询。 */
export const getPublication = (projectId: string): Promise<PublicationResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/publication/`, {}, { globalError: false })
);

/** 发布当前工作区最新版本。已发布项目调用同一接口即为更新版本。 */
export const createPublicationDeployment = (
  projectId: string,
  payload: PublicationDeploymentRequest = {},
): Promise<PublicationResponse> => (
  http.post(
    `${apiPrefix}/projects/${projectId}/publication/deployments/`,
    payload,
    { globalError: false },
  )
);

/** 首次发布前检查蓝鲸应用名能否使用；只是提示，发布时后端会再校验一次。 */
export const validatePublicationAppName = (
  projectId: string,
  name: string,
  signal?: AbortSignal,
): Promise<PublicationAppNameValidateResponse> => (
  http.get(
    `${apiPrefix}/projects/${projectId}/publication/app-name-validate/`,
    { name },
    { globalError: false, signal },
  )
);

/** 结果页展示并关闭后确认已读，之后不会再次展示一次性结果。 */
export const clearPublicationUnseenResult = (projectId: string): Promise<void> => (
  http.delete(
    `${apiPrefix}/projects/${projectId}/publication/unseen-result/`,
    {},
    { globalError: false },
  )
);

/**
 * 项目的 Git 仓库状态，其中 `archive_url` 是源码下载地址。项目尚未建仓时 404。
 */
export const getGitRepository = (projectId: string): Promise<GitRepositoryResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/git-repository/`, {}, { globalError: false })
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
  config: IFetchConfig = {},
): Promise<RuntimeStateResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/`, {}, config)
);

/**
 * 这个会话的工作区应用该去哪儿打开，以及此刻打不打得开。
 *
 * 会话一创建就可以问。`origin` 末尾带斜杠；`direct` 为 false 时先折回当前页面再当 iframe 的
 * src，为 true 时原样使用。能不能看只看 `dev_server_status`。Runtime 联系不上时仍是 200，
 * 地址照常返回，所以这里关掉全局报错：
 * 预览面板会每 5 秒打一次，一句 toast 不该跟着响。
 */
export const getConversationPreview = (
  projectId: string,
  number: number,
): Promise<PreviewResponse> => (
  http.get(
    `${apiPrefix}/projects/${projectId}/conversations/${number}/preview/`,
    {},
    { globalError: false },
  )
);

/**
 * 把会话的工作区应用拉起来，不等就绪就返回。
 *
 * 进入已有代码的项目时用：没有一轮对话，模型不会去拉起应用，预览会一直空着。会按需拉起 Agent
 * Runtime 并恢复工作区，可能要几秒到几十秒。应用已在跑就不动它，重复调用安全。是否起来了照常看
 * `getConversationPreview` 的 `dev_server_status`。失败不影响对话，所以关掉全局报错。
 */
export const startConversationPreview = (
  projectId: string,
  number: number,
): Promise<PreviewStartResponse> => (
  http.post(
    `${apiPrefix}/projects/${projectId}/conversations/${number}/preview/start/`,
    {},
    { globalError: false },
  )
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
  config: IFetchConfig = {},
): Promise<UiEventPageResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/ui-events/`, query, config)
);

/**
 * 拉取一页展示历史（用户输入 + AG-UI 事件）。
 *
 * 不带游标时给的是**最新**的若干轮，往更早翻就一直用上一页的 `next_cursor`，直到它为 null。
 */
export const listHistory = (
  projectId: string,
  number: number,
  query: ListHistoryQuery = {},
): Promise<ConversationHistoryResponse> => (
  http.get(`${apiPrefix}/projects/${projectId}/conversations/${number}/history/`, query)
);

/** 发起一轮对话，返回 AG-UI SSE Response，调用方自行读流 */
export const startConversationRun = async (
  projectId: string,
  number: number,
  payload: StartRunRequest,
  signal?: AbortSignal,
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
    signal,
  });

  if (!response.ok) {
    let detail = response.statusText || '发起对话失败';
    let data: any = null;
    try {
      data = await response.json();
      detail = data.detail || data.message || detail;
    } catch {
      // 保持 statusText
    }
    throw new RequestError(data?.code ?? response.status, detail, data);
  }

  return response;
};
