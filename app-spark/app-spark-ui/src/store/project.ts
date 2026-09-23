import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { ChatImage, ChatMessage } from '@/components/project/interaction/types';
import {
  closeConversation,
  createConversation,
  getConversation,
  listConversations,
  listHistory,
  listUiEvents,
  startConversationRun,
} from '@/http/api';
import type {
  ConversationHistoryRecord,
  ConversationResponse,
  RuntimeStateResponse,
} from '@/http/types';
import { ApiErrorCode, isApiError } from '@/http/error-codes';
import type { AgUiApplyContext } from '@/services/agent/ag-ui';
import {
  appendUserMessage,
  applyAgUiEvent,
  createApplyContext,
  createWelcomeMessage,
  getRecordSeq,
  hasConversationContent,
  readSseEvents,
} from '@/services/agent/ag-ui';

export type ProjectStatus = 'idle' | 'thinking' | 'streaming';

const createId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const useProjectStore = defineStore('project', () => {
  const projectId = ref('');
  const conversationNumber = ref<number | null>(null);
  const conversationId = ref('');
  const isLive = ref(true);
  // 项目当前活跃会话的编号，与「正在看的会话」是两件事：翻看归档时后者会变，前者不变，
  // 于是才有地方可回。
  const liveNumber = ref<number | null>(null);
  const uiEventSeq = ref(0);
  const running = ref(false);
  const replicationPending = ref(false);
  const entering = ref(false);
  const messages = ref<ChatMessage[]>([createWelcomeMessage()]);
  const status = ref<ProjectStatus>('idle');
  // 取更早一页历史用的游标，null 表示已经翻到会话开头（或者还没拉过第一页）。
  const historyCursor = ref<string | null>(null);
  const loadingEarlier = ref(false);
  const busy = computed(() => status.value !== 'idle' || entering.value);
  /** 还有更早的历史可以往前翻。 */
  const hasEarlierHistory = computed(() => historyCursor.value !== null);
  /** 正在翻看归档：会话已经结束，只能读，发不出新的一轮对话。 */
  const viewingArchive = computed(() => conversationNumber.value != null && !isLive.value);
  /** 归档看完之后能不能回到当前对话——上一次新建失败过的话，项目里可能根本没有活跃会话。 */
  const canReturnToLive = computed(() => (
    liveNumber.value != null && liveNumber.value !== conversationNumber.value
  ));

  const applyCtx = createApplyContext(messages.value);

  let enterToken = 0;

  const syncApplyCtx = () => {
    applyCtx.messages = messages.value;
  };

  /** 换了一段要渲染的消息，事件里那些认 id 的索引（消息、工具调用）得跟着清掉。 */
  const resetApplyCtx = () => {
    applyCtx.messages = messages.value;
    applyCtx.byId = new Map();
    applyCtx.toolCalls = new Map();
  };

  const applyState = (state: RuntimeStateResponse) => {
    conversationNumber.value = state.number;
    conversationId.value = state.conversation_id;
    isLive.value = state.is_live;
    running.value = state.running;
    replicationPending.value = state.replication_pending;
    // 顺手校准「哪个会话是活跃的」。反过来那一支同样重要：我们记着的那个会话被读出来是已结束
    // 的，说明它在别处（另一个标签页、后端回收）被归档了，这里必须忘掉它，否则「返回当前会话」
    // 会指向一个只读的归档。
    if (state.is_live) {
      liveNumber.value = state.number;
    } else if (liveNumber.value === state.number) {
      liveNumber.value = null;
    }
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
    liveNumber.value = null;
    uiEventSeq.value = 0;
    running.value = false;
    replicationPending.value = false;
    entering.value = false;
    status.value = 'idle';
    historyCursor.value = null;
    loadingEarlier.value = false;
    messages.value = [createWelcomeMessage()];
    resetApplyCtx();
  };

  const latestAssistant = (ctx: AgUiApplyContext) => (
    [...ctx.messages].reverse().find(item => item.role === 'assistant')
  );

  /**
   * 把一条事件的作用落到界面上。
   *
   * `trackStatus` 只在直播（一轮对话的 SSE 流）时为真。回放历史必须传 false：入库的事件是「发生
   * 过什么」的记录，不是「此刻在发生什么」，用它推 `status` 会让一条尾巴不完整的历史（Runtime
   * 还没回写最后一批事件、进程被回收、上一轮被打断）把界面永久钉在「正在回复」上，输入框和右上
   * 角两个按钮跟着一起灰掉，刷新也没用——因为回放的还是同一段历史。眼下这一刻到底有没有在跑，
   * 由会话状态里的 `running` 说，见 :func:`bindConversation`。
   *
   * `ctx` 必须显式传：回放更早的一页历史用的是一个独立的 ctx（见 `replayHistoryPage`），而
   * `progress` / `errorText` 都是接在「这一段的最后一条助手消息」上的，认错 ctx 就会把更早那一页
   * 的进度文字写到当前这一轮的气泡里。
   */
  const applyResult = (
    ctx: AgUiApplyContext,
    result: ReturnType<typeof applyAgUiEvent>,
    { trackStatus = true }: { trackStatus?: boolean } = {},
  ) => {
    if (trackStatus && result.status) status.value = result.status;
    const assistant = latestAssistant(ctx);
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

  /** 一条能显示的东西都没回放出来，就把欢迎语放回去，别把界面留成一片空白。 */
  const fallbackToWelcome = () => {
    if (hasConversationContent(messages.value) || messages.value.some(item => item.role === 'user')) {
      return;
    }
    messages.value = [createWelcomeMessage()];
    resetApplyCtx();
  };

  /**
   * 把一页展示历史回放成消息，落到给定的 ctx 上。
   *
   * 事件一律按 `ignoreUser` 处理：用户那一侧已经由 `user_message` 记录负责，事件流里万一也混进
   * 用户消息，渲染出来就是重复的一条。
   */
  const replayHistoryPage = (ctx: AgUiApplyContext, records: ConversationHistoryRecord[]) => {
    for (const record of records) {
      if (record.user_message) {
        appendUserMessage(ctx, record.user_message);
        continue;
      }
      if (!record.ui_event) continue;
      applyResult(
        ctx,
        applyAgUiEvent(ctx, record.ui_event, { ignoreUser: true }),
        { trackStatus: false },
      );
    }
  };

  /**
   * 回放会话**最新**的一页展示历史。
   *
   * 走 history 而不是 ui-events：用户发过什么不在 AG-UI 事件流里——Runtime 只回写自己产生的事
   * 件，用户输入由后端单独存着——只有 history 会把两者按对话顺序合成一条流交回来。
   *
   * 只拉一页，更早的由 `loadEarlierHistory` 按需往前取：一个长会话里 `TOOL_CALL_ARGS` 事件带着完
   * 整的工具参数（write_file 的参数就是整份文件），全量拉的代价跟对话长度成正比，而用户一打开只
   * 看得到最后几轮。
   *
   * 这一页用的是共享的 `applyCtx`，不是独立的：接下来直播过来的事件要按 id 认回这一页尾巴上那条
   * 还没说完的助手消息。
   */
  const pullHistory = async () => {
    if (!projectId.value || conversationNumber.value == null) return;
    const data = await listHistory(projectId.value, conversationNumber.value);
    syncApplyCtx();
    replayHistoryPage(applyCtx, data.records || []);

    // 水位取响应里的 `last_seq`，而不是本页最后一条事件的 seq：本页一定读到了频道末尾（它没有上
    // 界），而「频道到哪了」是频道自己的事，一并给出来就省掉一次额外的状态查询。
    advanceUiEventSeq(data.last_seq);
    historyCursor.value = data.next_cursor;
    fallbackToWelcome();
  };

  /**
   * 往列表头部接上更早的一页历史。
   *
   * 每页一个独立的 ctx：`byId` / `toolCalls` 是按事件自带的 id 认人的索引，而一页就是若干个完整
   * 的 run（页边界由后端卡在 run 边界上），所以页内自洽，不需要跨页共享。反过来也必须独立——更早
   * 的页是**后**拉的，混进当前 ctx 的话，一次工具调用会按 id 认回别的页里那一行，续写到一个根本
   * 不属于它的气泡上。
   *
   * 用 `unshift` 原地改而不是 `messages.value = [...earlier, ...messages.value]`：后者换掉了数组
   * 本身，而 `applyCtx.messages` 指着的是原来那个，直播事件会写进一个已经没人渲染的数组里。
   */
  const loadEarlierHistory = async () => {
    const cursor = historyCursor.value;
    const target = conversationNumber.value;
    if (!cursor || loadingEarlier.value || !projectId.value || target == null) return;

    loadingEarlier.value = true;
    try {
      const data = await listHistory(projectId.value, target, { cursor });
      // 这一页在路上时可能已经切走了（打开归档、新建会话），那它属于上一段对话，不能接到眼前这
      // 段的头上。游标也一并核对：`bindConversation` 会把它清掉，那同样意味着换了一段历史。
      if (conversationNumber.value !== target || historyCursor.value !== cursor) return;

      const earlier: ChatMessage[] = [];
      replayHistoryPage(createApplyContext(earlier), data.records || []);
      messages.value.unshift(...earlier);
      historyCursor.value = data.next_cursor;
    } finally {
      loadingEarlier.value = false;
    }
  };

  /**
   * 从 `uiEventSeq` 起把已落库的 AG-UI 事件追上来，用于一轮 SSE 走完之后补齐尾巴。
   *
   * 与 `pullHistory` 的分工：这里补的是增量，用户本轮发的内容在调用它之前就已经在界面上了，所以
   * 只认事件，不碰用户输入。
   */
  const pullUiEvents = async () => {
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
        applyResult(
          applyCtx,
          applyAgUiEvent(applyCtx, record, { ignoreUser: true }),
          { trackStatus: false },
        );
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
      await pullUiEvents();
    }
  };

  /**
   * 历史没拉回来时摆进对话区的那一条。
   *
   * 不能只靠调用方那句 toast：它几秒就消失了，剩下的是一片空白，而空白跟「这是个刚开的新会
   * 话」长得一模一样。用户会以为对话真的是空的，接着在这段自己都不知道残缺的历史上往下发。
   */
  const createHistoryErrorMessage = (): ChatMessage => ({
    id: 'history-error',
    role: 'assistant',
    tone: 'error',
    blocks: [{ type: 'text', text: '会话历史加载失败，这里显示的不是完整对话，刷新页面可重试。' }],
  });

  const bindConversation = async (state: RuntimeStateResponse) => {
    applyState(state);
    uiEventSeq.value = 0;
    // 清在拉第一页之前：这一页失败的话，游标就该是「不知道能往前翻到哪」，而不是上一个会话的。
    historyCursor.value = null;
    messages.value = [];
    resetApplyCtx();
    try {
      await pullHistory();
    } catch (error) {
      console.error('[project] 会话历史加载失败', error);
      messages.value.push(createHistoryErrorMessage());
      // 回放到一半断掉的话，byId / toolCalls 里攒着的是半条消息、半次工具调用。清掉，免得后面
      // 直播来的事件按 id 认回这些残骸，续写到一个根本没画完的块上。
      resetApplyCtx();
      // 继续往外抛：调用方那句 toast 才是「刚刚这一下失败了」的即时反馈，两者不重复。
      throw error;
    } finally {
      // 唯一有资格决定「此刻是不是在回复中」的地方：`running` 是后端现问 Runtime 拿到的，历史事件
      // 只能告诉我们过去发生过什么。放在回放之后，保证它不会被回放出来的中间态盖掉。
      status.value = state.running ? 'thinking' : 'idle';
    }
  };

  /** 项目里还活着的那个会话，一个都没有则返回 null。 */
  const findLiveConversation = async (id: string): Promise<ConversationResponse | null> => {
    const listed = await listConversations(id, {
      is_live: true,
      page: 1,
      page_size: 1,
    });
    return listed.items?.[0] ?? null;
  };

  const startNewConversation = async (id: string) => {
    try {
      return await createConversation(id);
    } catch (error) {
      // 别人（另一个标签页）在我们查完与建之间抢先建好了活跃会话，接回它就是了。
      if (isApiError(error, ApiErrorCode.AGENT_WORKSPACE_BUSY)) {
        const live = await findLiveConversation(id);
        if (live) {
          return getConversation(id, live.number);
        }
      }
      throw error;
    }
  };

  const resolveLiveConversation = async (id: string) => {
    const live = await findLiveConversation(id);
    if (live) {
      return getConversation(id, live.number);
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

  /** 归档项目当前的活跃会话。已经被结束过则视作成功——想要的结果本就是「它不再活跃」。 */
  const archiveLiveConversation = async (id: string) => {
    const target = liveNumber.value;
    if (target == null) return;
    try {
      await closeConversation(id, target);
    } catch (error) {
      if (!isApiError(error, ApiErrorCode.CONVERSATION_CLOSED)) throw error;
    }
    liveNumber.value = null;
  };

  /**
   * 把视图落回一个真实存在的会话，用于新建失败之后收场。
   *
   * 先问项目里还有没有活跃会话，而不是直接回退：新建失败可能是「会话行已建好、Agent Runtime
   * 没拉起来」这种半成功（AGENT_WORKSPACE_BUSY 就是如此），那条会话是活着的，接回它比退回归档
   * 更接近用户按下按钮时想要的东西。
   */
  const recoverConversationView = async (id: string, fallbackNumber: number | null) => {
    try {
      const number = (await findLiveConversation(id))?.number ?? fallbackNumber;
      if (number == null) return;
      await bindConversation(await getConversation(id, number));
    } catch {
      // 收场也失败就维持现状，真正的失败原因由调用方报给用户
    }
  };

  /**
   * 归档当前会话，并用一个全新的会话取代它。
   *
   * 顺序不能反：一个项目的 workspace 同时只容得下一个 Agent Runtime，活跃会话不先让位，新会话
   * 就会被后端以 AGENT_WORKSPACE_BUSY 拒绝。
   */
  const startFreshConversation = async () => {
    if (!projectId.value || busy.value) return;
    const id = projectId.value;
    const viewedNumber = conversationNumber.value;

    entering.value = true;
    status.value = 'idle';
    try {
      await archiveLiveConversation(id);
      await bindConversation(await createConversation(id));
    } catch (error) {
      await recoverConversationView(id, viewedNumber);
      throw error;
    } finally {
      entering.value = false;
    }
  };

  /** 从归档回到项目当前的活跃会话。 */
  const returnToLiveConversation = async () => {
    const target = liveNumber.value;
    if (target == null || target === conversationNumber.value) return;
    await openConversation(target);
  };

  /**
   * 当前活跃会话的概要（编号、会话 ID、创建时间），没有活跃会话则返回 null。
   *
   * 现查而不是拿 store 里的 `conversationId`：后者说的是「正在看的那个会话」，翻看归档时它恰好
   * 就不是活跃的那个。
   */
  const fetchLiveConversation = async () => (
    projectId.value ? findLiveConversation(projectId.value) : null
  );

  /** 列出已归档的会话。活跃的那个不在其中：它就是眼下这段对话本身，不该出现在归档里。 */
  const fetchArchivedConversations = async (page = 1, pageSize = 20) => {
    if (!projectId.value) {
      return { items: [] as ConversationResponse[], count: 0 };
    }
    return listConversations(projectId.value, {
      is_live: false,
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
        applyResult(applyCtx, applyAgUiEvent(applyCtx, event, { ignoreUser: true }));
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
    liveNumber,
    uiEventSeq,
    running,
    entering,
    messages,
    status,
    busy,
    loadingEarlier,
    hasEarlierHistory,
    viewingArchive,
    canReturnToLive,
    reset,
    enterProject,
    loadEarlierHistory,
    openConversation,
    startFreshConversation,
    returnToLiveConversation,
    fetchLiveConversation,
    fetchArchivedConversations,
    sendMessage,
  };
});
