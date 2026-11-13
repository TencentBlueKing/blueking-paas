/**
 * 测试里顶替 `@/http/api`，见 scripts/test-hooks.mjs。
 *
 * 每个接口都转给 `handlers` 里的同名函数，由测试按场景填；没填的接口被调到就失败，免得一个
 * 意料之外的请求悄悄返回 undefined。
 */
type Handler = (...args: any[]) => unknown;

export const handlers: Record<string, Handler> = {};
export const calls: { name: string; args: unknown[] }[] = [];

export const resetApi = () => {
  for (const name of Object.keys(handlers)) delete handlers[name];
  calls.length = 0;
};

export const callsOf = (name: string) => calls.filter(call => call.name === name).map(call => call.args);

const route = (name: string) => async (...args: unknown[]) => {
  calls.push({ name, args });
  const handler = handlers[name];
  if (!handler) throw new Error(`unexpected API call: ${name}`);
  return handler(...args);
};

export const closeConversation = route('closeConversation');
export const createConversation = route('createConversation');
export const getConversation = route('getConversation');
export const getProjectIntRenaming = route('getProjectIntRenaming');
export const listConversations = route('listConversations');
export const listHistory = route('listHistory');
export const listModels = route('listModels');
export const listUiEvents = route('listUiEvents');
export const startConversationPreview = route('startConversationPreview');
export const startConversationRun = route('startConversationRun');
export const stopConversationRun = route('stopConversationRun');
