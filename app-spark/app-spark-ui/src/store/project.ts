import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { ChatImage, ChatMessage } from '@/components/project/interaction/types';
import {
  createConversation,
  getConversation,
  listConversations,
  listUiEvents,
  startConversationRun,
} from '@/http/api';
import type { ConversationResponse, RuntimeStateResponse } from '@/http/types';
import RequestError from '@/http/fetch/request-error';
import {
  applyAgUiEvent,
  createWelcomeMessage,
  getRecordSeq,
  hasConversationContent,
  readSseEvents,
  type AgUiApplyContext,
} from '@/services/agent/ag-ui';

export type ProjectStatus = 'idle' | 'thinking' | 'streaming';

const createId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const useProjectStore = defineStore('project', () => {
  const projectId = ref('');
  const conversationNumber = ref<number | null>(null);
  const conversationId = ref('');
  const isLive = ref(true);
  const uiEventSeq = ref(0);
  const running = ref(false);
  const replicationPending = ref(false);
  const entering = ref(false);
  const messages = ref<ChatMessage[]>([createWelcomeMessage()]);
  const status = ref<ProjectStatus>('idle');
  const busy = computed(() => status.value !== 'idle' || entering.value);

  const applyCtx: AgUiApplyContext = {
    messages: messages.value,
    byId: new Map(),
  };

  let enterToken = 0;

  const syncApplyCtx = () => {
    applyCtx.messages = messages.value;
  };

  const applyState = (state: RuntimeStateResponse) => {
    conversationNumber.value = state.number;
    conversationId.value = state.conversation_id;
    isLive.value = state.is_live;
    running.value = state.running;
    replicationPending.value = state.replication_pending;
    if (state.ui_event_seq > uiEventSeq.value) {
      uiEventSeq.value = state.ui_event_seq;
    }
  };

  const reset = () => {
    enterToken += 1;
    projectId.value = '';
    conversationNumber.value = null;
    conversationId.value = '';
    isLive.value = true;
    uiEventSeq.value = 0;
    running.value = false;
    replicationPending.value = false;
    entering.value = false;
    status.value = 'idle';
    messages.value = [createWelcomeMessage()];
    applyCtx.messages = messages.value;
    applyCtx.byId = new Map();
  };

  const latestAssistant = () => (
    [...applyCtx.messages].reverse().find(item => item.role === 'assistant')
  );

  const applyResult = (result: ReturnType<typeof applyAgUiEvent>) => {
    if (result.status) status.value = result.status;
    const assistant = latestAssistant();
    if (assistant && result.progress !== undefined) {
      assistant.progress = result.progress;
    }
    if (result.errorText && assistant) {
      const textBlock = assistant.blocks.find(block => block.type === 'text');
      if (textBlock && !textBlock.text) {
        textBlock.text = result.errorText;
      } else if (!assistant.blocks.some(block => block.type === 'text' && block.text === result.errorText)) {
        assistant.blocks.push({ type: 'text', text: result.errorText });
      }
      assistant.progress = '';
    }
  };

  const advanceUiEventSeq = (seq: number | null | undefined) => {
    const value = Number(seq);
    if (Number.isFinite(value) && value > uiEventSeq.value) {
      uiEventSeq.value = value;
    }
  };

  const UI_EVENT_PAGE_LIMIT = 30;

  const pullUiEvents = async (ignoreUser = false) => {
    if (!projectId.value || conversationNumber.value == null) return;
    let since = uiEventSeq.value;

    for (let page = 0; page < UI_EVENT_PAGE_LIMIT; page++) {
      const data = await listUiEvents(projectId.value, conversationNumber.value, {
        since,
        limit: 200,
      });
      const records = data.records || [];
      syncApplyCtx();
      for (const record of records) {
        applyResult(applyAgUiEvent(applyCtx, record, { ignoreUser }));
        advanceUiEventSeq(getRecordSeq(record));
      }
      advanceUiEventSeq(data.last_seq);

      if (data.exhausted || !records.length) break;
      const lastRecordSeq = getRecordSeq(records[records.length - 1]);
      const nextSince = Math.max(lastRecordSeq ?? 0, Number(data.last_seq) || 0);
      if (nextSince <= since) break;
      if (page === UI_EVENT_PAGE_LIMIT - 1) {
        console.warn(`[project] ui-events 已拉取 ${UI_EVENT_PAGE_LIMIT} 页仍未结束，停止追赶`);
        break;
      }
      since = nextSince;
    }

    if (!hasConversationContent(messages.value) && !messages.value.some(item => item.role === 'user')) {
      messages.value = [createWelcomeMessage()];
      applyCtx.messages = messages.value;
      applyCtx.byId = new Map();
    }
  };

  const syncConversationOnce = async () => {
    if (!projectId.value || conversationNumber.value == null) return;
    const state = await getConversation(projectId.value, conversationNumber.value);
    const prevSeq = uiEventSeq.value;
    applyState(state);
    if (prevSeq === 0 && hasConversationContent(messages.value)) {
      uiEventSeq.value = state.ui_event_seq;
      return;
    }
    if (state.ui_event_seq > prevSeq) {
      await pullUiEvents(true);
    }
  };

  const bindConversation = async (state: RuntimeStateResponse) => {
    applyState(state);
    uiEventSeq.value = 0;
    messages.value = [];
    applyCtx.messages = messages.value;
    applyCtx.byId = new Map();
    await pullUiEvents(false);
  };

  const startNewConversation = async (id: string) => {
    try {
      return await createConversation(id);
    } catch (error) {
      if (error instanceof RequestError && error.code === 409) {
        const again = await listConversations(id, {
          is_live: true,
          page: 1,
          page_size: 1,
        });
        if (again.items?.[0]) {
          return getConversation(id, again.items[0].number);
        }
      }
      throw error;
    }
  };

  const resolveLiveConversation = async (id: string) => {
    const listed = await listConversations(id, {
      is_live: true,
      page: 1,
      page_size: 1,
    });
    if (listed.items?.[0]) {
      return getConversation(id, listed.items[0].number);
    }
    return startNewConversation(id);
  };

  const enterProject = async (id: string) => {
    reset();
    const token = enterToken;
    projectId.value = id;
    entering.value = true;
    try {
      const state = await resolveLiveConversation(id);
      if (token !== enterToken) return;
      await bindConversation(state);
    } finally {
      if (token === enterToken) entering.value = false;
    }
  };

  const openConversation = async (number: number) => {
    if (!projectId.value) return;
    entering.value = true;
    status.value = 'idle';
    try {
      const state = await getConversation(projectId.value, number);
      await bindConversation(state);
    } finally {
      entering.value = false;
    }
  };

  const createNewConversation = async () => {
    if (!projectId.value || busy.value) return;
    const previousNumber = conversationNumber.value;
    const id = projectId.value;

    status.value = 'idle';
    conversationNumber.value = null;
    isLive.value = true;
    uiEventSeq.value = 0;
    messages.value = [createWelcomeMessage()];
    applyCtx.messages = messages.value;
    applyCtx.byId = new Map();

    try {
      const state = await createConversation(id);
      applyState(state);
      uiEventSeq.value = 0;
      messages.value = [createWelcomeMessage()];
      applyCtx.messages = messages.value;
      applyCtx.byId = new Map();
    } catch (error) {
      if (previousNumber != null) {
        try {
          const previous = await getConversation(id, previousNumber);
          await bindConversation(previous);
        } catch {
          // 切回失败时仍提示新建失败
        }
      }
      throw error;
    }
  };

  const fetchConversationList = async (page = 1, pageSize = 10) => {
    if (!projectId.value) {
      return { items: [] as ConversationResponse[], count: 0 };
    }
    return listConversations(projectId.value, {
      page,
      page_size: pageSize,
    });
  };

  // TODO: 项目对话暂不上传图片，后续再接入
  const sendMessage = async (text: string, images: ChatImage[] = []) => {
    void images;
    const content = text.trim();
    if (!content || busy.value || !projectId.value || conversationNumber.value == null || !isLive.value) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      blocks: [{ type: 'text', text: content }],
    };
    const assistantMessage: ChatMessage = {
      id: createId(),
      role: 'assistant',
      blocks: [{ type: 'text', text: '' }],
    };
    messages.value.push(userMessage, assistantMessage);
    syncApplyCtx();
    status.value = 'thinking';

    try {
      const response = await startConversationRun(
        projectId.value,
        conversationNumber.value,
        { content },
      );
      for await (const event of readSseEvents(response)) {
        syncApplyCtx();
        applyResult(applyAgUiEvent(applyCtx, event, { ignoreUser: true }));
      }
    } catch (error) {
      const textBlock = assistantMessage.blocks.find(block => block.type === 'text');
      const detail = error instanceof Error ? error.message : '发起对话失败';
      assistantMessage.tone = 'error';
      if (textBlock && !textBlock.text) {
        textBlock.text = detail;
      } else {
        assistantMessage.blocks.push({ type: 'text', text: detail });
      }
    } finally {
      assistantMessage.progress = '';
      const textBlock = assistantMessage.blocks.find(block => block.type === 'text');
      if (textBlock && !textBlock.text) {
        textBlock.text = '本轮对话已结束。';
      }
      status.value = 'idle';
      if (projectId.value && conversationNumber.value != null) {
        try {
          await syncConversationOnce();
        } catch {
          // 发送结果已展示，追赶失败不覆盖当前消息
        }
      }
    }
  };

  return {
    projectId,
    conversationNumber,
    conversationId,
    isLive,
    uiEventSeq,
    running,
    entering,
    messages,
    status,
    busy,
    reset,
    enterProject,
    openConversation,
    createNewConversation,
    fetchConversationList,
    sendMessage,
  };
});
