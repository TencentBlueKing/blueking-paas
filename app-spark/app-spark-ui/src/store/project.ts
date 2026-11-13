import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';
import Message from '@/common/message';
import { createStartRunRequest } from '@/common/model-catalog';
import type { ChatImage, ChatMessage } from '@/components/project/interaction/types';
import { usePageVisibility } from '@/composables/use-page-visibility';
import {
  closeConversation,
  createConversation,
  getConversation,
  getProjectIntRenaming,
  listConversations,
  listHistory,
  listUiEvents,
  startConversationPreview,
  startConversationRun,
  stopConversationRun,
} from '@/http/api';
import type {
  ConversationHistoryRecord,
  ConversationResponse,
  ProjectIntRenamingResponse,
  RuntimeStateResponse,
} from '@/http/types';
import { ApiErrorCode, isApiError } from '@/http/error-codes';
import RequestError from '@/http/fetch/request-error';
import type { AgUiApplyContext } from '@/services/agent/ag-ui';
import {
  appendRunError,
  appendUserMessage,
  applyAgUiEvent,
  createApplyContext,
  createWelcomeMessage,
  currentTurnAssistant,
  getRecordSeq,
  hasConversationContent,
  markRunStopped,
  readSseEvents,
} from '@/services/agent/ag-ui';
import { useModelCatalogStore } from '@/store/model-catalog';

export type ProjectStatus = 'idle' | 'thinking' | 'streaming';
export type ProjectIntRenamingStatus = 'idle' | ProjectIntRenamingResponse['status'];

type VisibilityRecovery = {
  kind: 'incremental';
} | {
  kind: 'interrupted-run';
  projectId: string;
  conversationNumber: number;
  runGeneration: number;
  seqBeforeRun: number;
};

const PREPARING_RUNTIME_TEXT = '正在准备运行环境…';
/** 回复进行中，历史是分批入库的。两秒补一次，能跟上已经写进来的字，又不会把接口打满。 */
const CATCH_UP_INTERVAL_MS = 2000;
/** 追赶接口连续失败这么多次就停，并把输入框放开。成功一次就重新计数。 */
const MAX_CATCH_UP_FAILURES = 3;
const INT_RENAMING_POLL_INTERVAL_MS = 2000;
const INT_RENAMING_MAX_DURATION_MS = 30000;

const createId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const useProjectStore = defineStore('project', () => {
  const modelCatalogStore = useModelCatalogStore();
  const pageVisible = usePageVisibility();
  const projectId = ref('');
  const projectName = ref('');
  const intRenamingStatus = ref<ProjectIntRenamingStatus>('idle');
  const conversationNumber = ref<number | null>(null);
  const conversationId = ref('');
  const isLive = ref(true);
  // 项目当前活跃会话的编号，与「正在看的会话」是两件事：翻看归档时后者会变，前者不变，
  // 于是才有地方可回。
  const liveNumber = ref<number | null>(null);
  const uiEventSeq = ref(0);
  const running = ref(false);
  /** 正在跑的那一轮的 ID，停止时要点名它。直播时取自 RUN_STARTED，其余时候取自会话状态。 */
  const runId = ref<string | null>(null);
  /** 本页发出的这一轮还没被 Runtime 接受（多半在准备运行环境），这时还没有 run ID 可点名。 */
  const awaitingRunStart = ref(false);
  /** 已经请求停止，等这一轮收尾。回到空闲就清掉，见下面对 status 的 watch。 */
  const stopping = ref(false);
  /**
   * 按停止时这一轮还没有 run ID（还没被 Runtime 接受），停止请求还没发出去。哪条路先拿到 run ID
   * 就由哪条路补发：直播的 RUN_STARTED，或者 SSE 中断后按会话状态恢复时的 applyState。
   * 回到空闲就清掉：要么这一轮已经结束，要么换了会话。
   */
  let pendingStop: { projectId: string; number: number } | null = null;
  const replicationPending = ref(false);
  // 下一轮能不能直接用现有运行环境；不能时，发消息后要先等运行环境准备好。
  const runtimeReady = ref(false);
  const entering = ref(false);
  /** 进入会话时发出的「拉起预览」请求还没回来。要先拉 Runtime、恢复工作区，可能要几十秒。 */
  const previewStarting = ref(false);
  /** 每回来一次「拉起预览」就加一。预览面板据此重新问状态：之前那次可能在 Runtime 起来前就问完停了。 */
  const previewStartSeq = ref(0);
  const messages = ref<ChatMessage[]>([createWelcomeMessage()]);
  const status = ref<ProjectStatus>('idle');
  // 首页创建项目时暂存首条需求。只允许目标项目消费一次，避免刷新或切项目后误发。
  const pendingInitialMessage = ref<{
    projectId: string;
    conversationNumber: number;
    content: string;
    modelId?: string;
  } | null>(null);
  // 取更早一页历史用的游标，null 表示已经翻到会话开头（或者还没拉过第一页）。
  const historyCursor = ref<string | null>(null);
  const loadingEarlier = ref(false);
  const busy = computed(() => status.value !== 'idle' || entering.value);
  /**
   * 眼前这一轮能不能停。只剩回写（`replication_pending`）时这一轮已经跑完，没有可停的。
   * 还在等 Runtime 接受时也算能停：先记下，拿到 run ID 再发，见 :func:`stopRun`。
   */
  const canStop = computed(() => (
    status.value !== 'idle'
    && !entering.value
    && isLive.value
    && !stopping.value
    && (runId.value != null || awaitingRunStart.value)
  ));
  /** 还有更早的历史可以往前翻。 */
  const hasEarlierHistory = computed(() => historyCursor.value !== null);
  /** 正在翻看归档：会话已经结束，只能读，发不出新的一轮对话。 */
  const viewingArchive = computed(() => conversationNumber.value != null && !isLive.value);
  /** 归档看完之后能不能回到当前对话——上一次新建失败过的话，项目里可能根本没有活跃会话。 */
  const canReturnToLive = computed(() => (
    liveNumber.value != null && liveNumber.value !== conversationNumber.value
  ));

  const applyCtx = createApplyContext(messages.value);

  // 停下的一轮和正常结束的一轮走同一条收尾路线，最后都回到空闲；切走、重置也都会先回到空闲。
  // 用 sync：同一个 tick 里 idle 之后紧接着又进了下一轮时，不能漏掉这一次。
  watch(status, (value) => {
    if (value === 'idle') {
      stopping.value = false;
      pendingStop = null;
    }
  }, { flush: 'sync' });

  let enterToken = 0;
  // 只认最后一次「拉起预览」：换了会话再回来的旧请求，不能把新会话的标记清掉。
  let previewStartGeneration = 0;
  // 还没返回的那次「拉起预览」请求。和代数分开记：切走再回来时界面已经不认它，但它在后端还在
  // 拉 Runtime，发消息照样要等它。
  let previewStartInFlight: { projectId: string; number: number; done: Promise<void> } | null = null;
  // 正在读的那一轮 SSE。切项目、换会话都会把消息列表换掉，不中断的话后续事件会写进新列表。
  // 后端这一轮不靠这条连接：abort、刷新页面、网络中断都只让当前页面停止读取，这一轮在 Runtime 里
  // 照常跑完；切回来靠轮询补已入库的内容。
  let liveRunAbort: AbortController | null = null;
  let liveRunGeneration = 0;
  // 切进一个正在回复的会话时，靠轮询把已经入库的新内容补上。离开或这一轮落定后必须停。
  let catchUpTimer: ReturnType<typeof setTimeout> | null = null;
  let catchUpGeneration = 0;
  // 从定时器等待开始，到状态及事件请求全部结束为止都算活跃，避免请求在途时因 timer 为空而漏记恢复。
  let catchUpActive = false;
  // 普通追赶可以从当前游标继续；中断的 SSE 必须按历史重画，否则会把已经展示的增量再追加一次。
  let visibilityRecovery: VisibilityRecovery | null = null;
  let intRenamingGeneration = 0;

  const pauseIncrementalCatchUp = () => {
    // 中断 SSE 的全量恢复优先级更高，不能被普通追赶覆盖。
    if (visibilityRecovery?.kind !== 'interrupted-run') {
      visibilityRecovery = { kind: 'incremental' };
    }
  };

  const stopCatchUp = () => {
    catchUpGeneration += 1;
    catchUpActive = false;
    if (catchUpTimer != null) {
      clearTimeout(catchUpTimer);
      catchUpTimer = null;
    }
  };

  const cancelLiveRun = () => {
    liveRunGeneration += 1;
    liveRunAbort?.abort();
    liveRunAbort = null;
    awaitingRunStart.value = false;
  };

  const syncApplyCtx = () => {
    applyCtx.messages = messages.value;
  };

  /** 换了一段要渲染的消息，事件里那些认 id 的索引（消息、工具调用、思考）得跟着清掉。 */
  const resetApplyCtx = () => {
    applyCtx.messages = messages.value;
    applyCtx.byId = new Map();
    applyCtx.toolCalls = new Map();
    applyCtx.reasonings = new Map();
  };

  const queueInitialMessage = (
    id: string,
    number: number,
    content: string,
    modelId?: string,
  ) => {
    const text = content.trim();
    pendingInitialMessage.value = id && Number.isInteger(number) && number > 0 && text
      ? {
        projectId: id,
        conversationNumber: number,
        content: text,
        modelId,
      }
      : null;
  };

  const consumeInitialMessage = (id: string) => {
    const pending = pendingInitialMessage.value;
    pendingInitialMessage.value = null;
    return pending?.projectId === id ? pending : null;
  };

  const setProjectName = (id: string, name: string) => {
    if (id === projectId.value && name) projectName.value = name;
  };

  /**
   * 仅在「从第一句话创建项目」后调用。任务结束或 30 秒后静默停止；
   * 用户已手动改名时，页面上的名称不再是占位项目 ID，因此不会被 AI 结果覆盖。
   */
  const pollProjectIntRenaming = async (id: string) => {
    const generation = intRenamingGeneration;
    const deadline = Date.now() + INT_RENAMING_MAX_DURATION_MS;
    intRenamingStatus.value = 'pending';
    while (Date.now() < deadline) {
      if (generation !== intRenamingGeneration || projectId.value !== id) return;
      let result: ProjectIntRenamingResponse;
      try {
        result = await getProjectIntRenaming(id);
      } catch {
        if (generation === intRenamingGeneration && projectId.value === id) {
          intRenamingStatus.value = 'idle';
        }
        return;
      }
      if (generation !== intRenamingGeneration || projectId.value !== id) return;
      if (result.status === 'completed') {
        if (
          result.name
          && (!projectName.value || projectName.value === id || projectName.value === result.name)
        ) {
          projectName.value = result.name;
          intRenamingStatus.value = 'completed';
        } else {
          intRenamingStatus.value = 'idle';
        }
        return;
      }
      if (result.status === 'failed') {
        intRenamingStatus.value = 'failed';
        return;
      }
      const remaining = deadline - Date.now();
      if (remaining <= 0) {
        intRenamingStatus.value = 'idle';
        return;
      }
      await new Promise(resolve => setTimeout(
        resolve,
        Math.min(INT_RENAMING_POLL_INTERVAL_MS, remaining),
      ));
    }
    if (generation === intRenamingGeneration && projectId.value === id) {
      intRenamingStatus.value = 'idle';
    }
  };

  /**
   * 请求停止给定的一轮。失败时把按钮放开，好让用户再试；这一轮已经结束则不算失败。
   */
  const requestStop = async (targetRunId: string) => {
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    if (!targetProjectId || targetNumber == null) return;
    const stillThisRun = () => (
      projectId.value === targetProjectId
      && conversationNumber.value === targetNumber
      && runId.value === targetRunId
    );
    try {
      await stopConversationRun(targetProjectId, targetNumber, targetRunId);
    } catch (error) {
      // 已经跑完了，要的本来就是它不再跑。收尾照常交给 SSE 或轮询。
      if (isApiError(error, ApiErrorCode.RUN_NOT_RUNNING) || !stillThisRun()) return;
      stopping.value = false;
      Message({ theme: 'error', message: error instanceof Error ? error.message : '停止失败' });
    }
  };

  /** 有待补发的停止、并且已经知道这一轮的 run ID 时，把停止请求发出去。 */
  const flushPendingStop = () => {
    const pending = pendingStop;
    if (!pending || !runId.value) return;
    pendingStop = null;
    // 换过会话的话，记下的停止属于上一段会话，眼前这一轮不是用户要停的那一轮。
    if (pending.projectId !== projectId.value || pending.number !== conversationNumber.value) return;
    void requestStop(runId.value);
  };

  const applyState = (state: RuntimeStateResponse, options?: { syncEventSeq?: boolean }) => {
    conversationNumber.value = state.number;
    conversationId.value = state.conversation_id;
    isLive.value = state.is_live;
    running.value = state.running;
    runId.value = state.run_id ?? null;
    replicationPending.value = state.replication_pending;
    runtimeReady.value = state.runtime_ready;
    // 直播的 SSE 在 RUN_STARTED 之前断了，按停止时没能点名的那一轮要靠这里拿到的 run ID 补发。
    flushPendingStop();
    // 顺手校准「哪个会话是活跃的」。反过来那一支同样重要：我们记着的那个会话被读出来是已结束
    // 的，说明它在别处（另一个标签页、后端回收）被归档了，这里必须忘掉它，否则「返回当前会话」
    // 会指向一个只读的归档。
    if (state.is_live) {
      liveNumber.value = state.number;
    } else if (liveNumber.value === state.number) {
      liveNumber.value = null;
    }
    // 追赶进行中的回复时不能在这里把游标拨到最新：后面还要按旧游标把新事件补进对话框。
    if (options?.syncEventSeq !== false && state.ui_event_seq > uiEventSeq.value) {
      uiEventSeq.value = state.ui_event_seq;
    }
  };

  const reset = () => {
    stopCatchUp();
    visibilityRecovery = null;
    cancelLiveRun();
    intRenamingGeneration += 1;
    enterToken += 1;
    projectId.value = '';
    projectName.value = '';
    intRenamingStatus.value = 'idle';
    conversationNumber.value = null;
    conversationId.value = '';
    isLive.value = true;
    liveNumber.value = null;
    uiEventSeq.value = 0;
    running.value = false;
    runId.value = null;
    awaitingRunStart.value = false;
    replicationPending.value = false;
    runtimeReady.value = false;
    entering.value = false;
    previewStartGeneration += 1;
    previewStarting.value = false;
    status.value = 'idle';
    historyCursor.value = null;
    loadingEarlier.value = false;
    messages.value = [createWelcomeMessage()];
    resetApplyCtx();
  };

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
   * `progress` / `errorText` 都是接在「这一段最后一轮的助手消息」上的，认错 ctx 就会把更早那一页
   * 的进度文字写到当前这一轮的气泡里。
   */
  const applyResult = (
    ctx: AgUiApplyContext,
    result: ReturnType<typeof applyAgUiEvent>,
    { trackStatus = true }: { trackStatus?: boolean } = {},
  ) => {
    if (trackStatus && result.status) status.value = result.status;
    const assistant = currentTurnAssistant(ctx.messages);
    if (assistant && result.progress !== undefined) {
      assistant.progress = result.progress;
    }
    if (result.errorText) appendRunError(ctx, result.errorText);
    if (result.stopped) markRunStopped(ctx);
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
  const pullHistory = async (still?: () => boolean): Promise<boolean> => {
    if (!projectId.value || conversationNumber.value == null) return false;
    const project = projectId.value;
    const number = conversationNumber.value;
    const data = await listHistory(project, number);
    // 请求在路上时可能已经切到别的项目，或同一项目又打开了一次。这份历史属于上一段，不能写进去。
    if (projectId.value !== project || conversationNumber.value !== number) return false;
    if (still && !still()) return false;
    syncApplyCtx();
    replayHistoryPage(applyCtx, data.records || []);

    // 水位取响应里的 `last_seq`，而不是本页最后一条事件的 seq：本页一定读到了频道末尾（它没有上
    // 界），而「频道到哪了」是频道自己的事，一并给出来就省掉一次额外的状态查询。
    advanceUiEventSeq(data.last_seq);
    historyCursor.value = data.next_cursor;
    fallbackToWelcome();
    return true;
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
  const pullUiEvents = async (stillCurrent?: () => boolean) => {
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    const generation = liveRunGeneration;
    if (!targetProjectId || targetNumber == null) return;
    let since = uiEventSeq.value;

    const stillThisConversation = () => (
      liveRunGeneration === generation
      && projectId.value === targetProjectId
      && conversationNumber.value === targetNumber
      && (!stillCurrent || stillCurrent())
    );

    for (let page = 0; page < UI_EVENT_PAGE_LIMIT; page++) {
      const data = await listUiEvents(targetProjectId, targetNumber, {
        since,
        limit: 200,
      }, { globalError: false });
      // 这一页在路上时可能已经切走了。事件属于上一段对话，不能补进眼前这段。
      if (!stillThisConversation()) return;
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
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    const generation = liveRunGeneration;
    if (!targetProjectId || targetNumber == null) return;
    const state = await getConversation(targetProjectId, targetNumber);
    if (
      liveRunGeneration !== generation
      || projectId.value !== targetProjectId
      || conversationNumber.value !== targetNumber
    ) return;
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
   * 本页读的 SSE 没读到 `RUN_FINISHED` 就结束了，把这一段会话对齐到服务端。
   *
   * 流断了不等于这一轮结束：网络中断、本服务重启都会让流提前断开，而这一轮仍在 Runtime 里跑，
   * 甚至已经跑完存好了。眼前画出来的只是断开之前的那一截，所以：
   *
   * - 服务端比发送前多存了事件，或这一轮还在跑、还没回写完：整段按历史重画，再按
   *   `running || replication_pending` 轮询补齐，和进入一个正在回复的会话走同一条路。不在原地
   *   续补：读 SSE 时游标不前进，从本轮开头再拉入库事件，会把已经画出来的字再接一遍；
   * - 服务端什么都没多存（请求没到、一轮没开始就失败）：没有可补的，留着眼前的报错。
   *
   * 服务端明确拒绝的一轮（比如别的标签页正在跑而回 409）不走这里，调用方直接按原样收尾。
   *
   * 状态没问到之前不算这一轮结束：让流断开的那次故障，往往也让紧接着的这一问失败。所以有界
   * 重试，期间输入框一直锁着；离开会话就不再问；连续失败到上限才放开并提示。
   *
   * @param stillCurrent 这一轮所在的会话是否还在眼前
   * @param seqBeforeRun 发送这一轮之前本地的事件游标；读 SSE 时它不前进，服务端超过它说明这一轮有入库的内容
   */
  const settleAfterInterruptedRun = async (stillCurrent: () => boolean, seqBeforeRun: number) => {
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    const runGeneration = liveRunGeneration;
    if (!targetProjectId || targetNumber == null) {
      status.value = 'idle';
      return;
    }
    const pauseInterruptedRun = () => {
      visibilityRecovery = {
        kind: 'interrupted-run',
        projectId: targetProjectId,
        conversationNumber: targetNumber,
        runGeneration,
        seqBeforeRun,
      };
    };
    status.value = 'thinking';
    if (!pageVisible.value) {
      pauseInterruptedRun();
      return;
    }

    let state: RuntimeStateResponse | null = null;
    for (let attempt = 1; attempt <= MAX_CATCH_UP_FAILURES; attempt++) {
      try {
        state = await getConversation(targetProjectId, targetNumber, { globalError: false });
        break;
      } catch {
        if (!stillCurrent()) return;
        if (!pageVisible.value) {
          pauseInterruptedRun();
          return;
        }
        if (attempt === MAX_CATCH_UP_FAILURES) {
          status.value = 'idle';
          Message({ theme: 'error', message: '回复同步失败，刷新页面可重试。' });
          return;
        }
        await new Promise(resolve => setTimeout(resolve, CATCH_UP_INTERVAL_MS));
        if (!stillCurrent()) return;
        if (!pageVisible.value) {
          pauseInterruptedRun();
          return;
        }
      }
    }
    // 问的路上切走了：状态属于上一段会话。
    if (!state || !stillCurrent()) return;
    if (!pageVisible.value) {
      applyState(state, { syncEventSeq: false });
      pauseInterruptedRun();
      return;
    }

    if (state.running || state.replication_pending || state.ui_event_seq > seqBeforeRun) {
      await bindConversation(state);
      return;
    }
    applyState(state);
    status.value = 'idle';
  };

  /**
   * 把已经入库、但眼前这页还没画出来的事件补上。
   *
   * 不在这里把游标直接拨到会话状态上的最新值：拨过去之后再拉，就会从最新处开始，新字被跳过。
   */
  const catchUpOnce = async (still: () => boolean) => {
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    if (!targetProjectId || targetNumber == null || !still()) return null;
    const prevSeq = uiEventSeq.value;
    const state = await getConversation(targetProjectId, targetNumber, { globalError: false });
    if (!still()) return null;
    applyState(state, { syncEventSeq: false });
    if (state.ui_event_seq > prevSeq) {
      await pullUiEvents(still);
    }
    if (!still()) return null;
    return {
      settled: !state.running && !state.replication_pending,
      targetSeq: state.ui_event_seq,
    };
  };

  /**
   * 这一轮还在跑、或者最后一批还没写完时，隔一段时间补一次历史。
   *
   * 本页自己正在读 SSE 时不轮询，两边一起写会把同一段字接两遍。
   * 停的条件是这轮已经落定，并且本地序号已经追上这次问到的水位。只看到落定还不够：
   * 紧接着的增量请求失败时，最后一批还在库里，下一拍还要再试。
   * 连续失败达到上限就停，并把输入框放开。状态接口正常返回且仍在跑时，继续问。
   * 离开这个会话或页面进入后台也会停；恢复可见时先按最新状态追一次，不在后台追别的项目。
   */
  const scheduleCatchUp = (
    lockComposer: boolean,
    { immediate = false, force = false }: { immediate?: boolean; force?: boolean } = {},
  ) => {
    stopCatchUp();
    if (liveRunAbort) return;
    if (!projectId.value || conversationNumber.value == null) return;
    if (!force && !running.value && !replicationPending.value) return;
    if (!pageVisible.value) {
      pauseIncrementalCatchUp();
      return;
    }

    const generation = catchUpGeneration;
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    let consecutiveFailures = 0;
    catchUpActive = true;
    if (lockComposer) status.value = 'thinking';

    const still = () => (
      generation === catchUpGeneration
      && !liveRunAbort
      && pageVisible.value
      && projectId.value === targetProjectId
      && conversationNumber.value === targetNumber
    );

    const tick = async () => {
      catchUpTimer = null;
      if (!still()) return;
      const seqBefore = uiEventSeq.value;
      try {
        const outcome = await catchUpOnce(still);
        if (!still() || !outcome) return;
        consecutiveFailures = 0;
        const caughtUp = uiEventSeq.value >= outcome.targetSeq;
        // 已经落定，这一拍却没再拉到新事件：水位不会自己涨了，再问也是同一份。
        const stalled = outcome.settled && !caughtUp && uiEventSeq.value === seqBefore;
        const done = outcome.settled && (caughtUp || stalled);
        if (lockComposer) status.value = done ? 'idle' : 'thinking';
        if (done) {
          catchUpActive = false;
          return;
        }
      } catch {
        if (!still()) return;
        consecutiveFailures += 1;
        if (consecutiveFailures >= MAX_CATCH_UP_FAILURES) {
          catchUpActive = false;
          status.value = 'idle';
          Message({ theme: 'error', message: '回复同步失败，刷新页面可重试。' });
          return;
        }
      }
      if (!still()) return;
      catchUpTimer = setTimeout(() => {
        void tick();
      }, CATCH_UP_INTERVAL_MS);
    };

    if (immediate) void tick();
    else {
      catchUpTimer = setTimeout(() => {
        void tick();
      }, CATCH_UP_INTERVAL_MS);
    }
  };

  const handlePageVisibility = (visible: boolean) => {
    if (!visible) {
      if (
        !liveRunAbort
        && (
          catchUpActive
          || catchUpTimer != null
          || running.value
          || replicationPending.value
        )
      ) {
        pauseIncrementalCatchUp();
      }
      stopCatchUp();
      return;
    }
    const recovery = visibilityRecovery;
    visibilityRecovery = null;
    if (!recovery) return;
    if (recovery.kind === 'incremental') {
      // 后台期间状态可能已经结束，先立即按服务端最新状态追一次，再决定是否继续每 2 秒补齐。
      scheduleCatchUp(true, { immediate: true, force: true });
      return;
    }

    const stillCurrent = () => (
      liveRunGeneration === recovery.runGeneration
      && projectId.value === recovery.projectId
      && conversationNumber.value === recovery.conversationNumber
    );
    if (!stillCurrent()) return;
    // SSE 的部分内容已经画过，但事件游标仍停在本轮之前。复用前台中断后的历史重画流程，
    // 不能从旧游标增量追赶，否则恢复可见时会把已画出的回复再追加一遍。
    void settleAfterInterruptedRun(stillCurrent, recovery.seqBeforeRun).catch(() => undefined);
  };

  watch(pageVisible, handlePageVisibility);

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
    // 换一段要渲染的历史之前先停掉上一轮直播和补历史。两边都属于上一段会话。
    stopCatchUp();
    cancelLiveRun();
    const token = enterToken;
    const stillBound = () => enterToken === token;
    applyState(state);
    uiEventSeq.value = 0;
    // 清在拉第一页之前：这一页失败的话，游标就该是「不知道能往前翻到哪」，而不是上一个会话的。
    historyCursor.value = null;
    messages.value = [];
    resetApplyCtx();
    let historyLoaded = false;
    try {
      if (!stillBound()) return;
      historyLoaded = await pullHistory(stillBound);
    } catch (error) {
      // 切走之后这段历史已经不属于眼前的项目，错误不能写到新对话上，也不再往外抛。
      if (!stillBound()) return;
      console.error('[project] 会话历史加载失败', error);
      messages.value.push(createHistoryErrorMessage());
      // 回放到一半断掉的话，byId / toolCalls 里攒着的是半条消息、半次工具调用。清掉，免得后面
      // 直播来的事件按 id 认回这些残骸，续写到一个根本没画完的块上。
      resetApplyCtx();
      // 继续往外抛：调用方那句 toast 才是「刚刚这一下失败了」的即时反馈，两者不重复。
      throw error;
    } finally {
      // 回放会带上历史里的中间态，这里用进来时问到的 running 盖回去。后面的轮询再按新的状态改。
      // 这段绑定已经过期时不能写：会把后一个空闲项目的输入框留在「正在回复」。
      if (stillBound()) status.value = state.running ? 'thinking' : 'idle';
    }
    // 历史没拉回来，或这次绑定已经过期，都不要在眼前这段上接着补事件。
    if (historyLoaded && stillBound()) scheduleCatchUp(true);
  };

  /**
   * 进入一个活跃会话时，在后台把它的工作区应用拉起来，不等。
   *
   * 查看会话不会拉 Runtime，没有一轮对话模型也不会去启动应用，进入一个已有代码的项目时预览就会
   * 一直空着。和拉历史并行发：要先拉 Runtime、恢复工作区，比拉历史慢得多。应用已在跑后端不会动它，
   * 每次进入都发也安全。失败只记日志，预览面板照常按状态显示，不影响对话。
   *
   * 对话要等它：两者都会去拉同一个 Runtime，E2B 多 worker 下后到的那个会被 AGENT_WORKSPACE_BUSY
   * 拒掉，见 sendMessage。
   */
  const startPreviewInBackground = (state: RuntimeStateResponse) => {
    if (!state.is_live || !projectId.value) return;
    const id = projectId.value;
    previewStartGeneration += 1;
    const generation = previewStartGeneration;
    const stillHere = () => (
      generation === previewStartGeneration
      && projectId.value === id
      && conversationNumber.value === state.number
    );
    previewStarting.value = true;
    const done = startConversationPreview(id, state.number)
      .then(() => {
        if (!stillHere()) return;
        // 后端已经把 Runtime 拉起来了，下一轮不用再等准备运行环境。
        runtimeReady.value = true;
      })
      .catch((error) => {
        if (!stillHere()) return;
        console.warn('[project] 拉起预览失败', error);
      })
      .finally(() => {
        if (previewStartInFlight?.done === done) previewStartInFlight = null;
        if (generation !== previewStartGeneration) return;
        previewStarting.value = false;
        previewStartSeq.value += 1;
      });
    previewStartInFlight = { projectId: id, number: state.number, done };
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

  /**
   * 会话状态接口失败时仍把已经入库的对话画出来。
   *
   * 列表接口已经给出了会话编号。历史只读库，不依赖这次状态查询。状态里的运行信息拿不到，
   * 这一轮就不轮询补字，输入框保持可发送。
   */
  const showStoredConversation = async (summary: ConversationResponse) => {
    stopCatchUp();
    cancelLiveRun();
    conversationNumber.value = summary.number;
    conversationId.value = summary.conversation_id;
    isLive.value = summary.is_live;
    if (summary.is_live) {
      liveNumber.value = summary.number;
    } else if (liveNumber.value === summary.number) {
      liveNumber.value = null;
    }
    running.value = false;
    runId.value = null;
    replicationPending.value = false;
    runtimeReady.value = false;
    uiEventSeq.value = 0;
    historyCursor.value = null;
    messages.value = [];
    resetApplyCtx();
    status.value = 'idle';
    const token = enterToken;
    try {
      await pullHistory(() => enterToken === token);
    } catch (error) {
      if (enterToken !== token) return;
      console.error('[project] 会话历史加载失败', error);
      messages.value.push(createHistoryErrorMessage());
      resetApplyCtx();
    }
  };

  const enterProject = async (id: string, preferredNumber?: number) => {
    reset();
    const token = enterToken;
    projectId.value = id;
    entering.value = true;
    try {
      if (preferredNumber != null) {
        const state = await getConversation(id, preferredNumber);
        if (token !== enterToken) return;
        await bindConversation(state);
        return;
      }
      const live = await findLiveConversation(id);
      if (token !== enterToken) return;
      if (!live) {
        const state = await startNewConversation(id);
        if (token !== enterToken) return;
        // 项目可能是旧的：没有活跃会话时新建一个，workspace 里照样是之前写好的代码。
        // bindConversation 先把会话编号定下来，这里不 await 它的历史，才能和拉历史并行。
        const bound = bindConversation(state);
        startPreviewInBackground(state);
        await bound;
        return;
      }
      let state: RuntimeStateResponse;
      try {
        state = await getConversation(id, live.number);
      } catch (error) {
        if (token !== enterToken) return;
        console.error('[project] 会话状态加载失败，改为只拉历史', error);
        await showStoredConversation(live);
        return;
      }
      if (token !== enterToken) return;
      const bound = bindConversation(state);
      startPreviewInBackground(state);
      await bound;
    } finally {
      if (token === enterToken) entering.value = false;
    }
  };

  const openConversation = async (number: number) => {
    if (!projectId.value) return;
    // 先停掉正在读的那一轮。bindConversation 里还会再停一次，这里要盖住等接口的这段时间。
    cancelLiveRun();
    enterToken += 1;
    const token = enterToken;
    const project = projectId.value;
    entering.value = true;
    status.value = 'idle';
    try {
      const state = await getConversation(project, number);
      if (token !== enterToken || projectId.value !== project) return;
      // 归档只读，不拉；回到活跃会话时拉，它的 Runtime 可能在翻归档期间被空闲回收了。
      const bound = bindConversation(state);
      startPreviewInBackground(state);
      await bound;
    } finally {
      if (token === enterToken) entering.value = false;
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
    const token = enterToken;
    try {
      const number = (await findLiveConversation(id))?.number ?? fallbackNumber;
      if (number == null || token !== enterToken || projectId.value !== id) return;
      const state = await getConversation(id, number);
      if (token !== enterToken || projectId.value !== id) return;
      await bindConversation(state);
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
    enterToken += 1;
    const token = enterToken;
    const stillHere = () => token === enterToken && projectId.value === id;
    status.value = 'idle';
    try {
      await archiveLiveConversation(id);
      if (!stillHere()) return;
      const created = await createConversation(id);
      if (!stillHere()) return;
      const bound = bindConversation(created);
      startPreviewInBackground(created);
      await bound;
    } catch (error) {
      if (!stillHere()) return;
      await recoverConversationView(id, viewedNumber);
      throw error;
    } finally {
      if (token === enterToken) entering.value = false;
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

  /**
   * 停下眼前正在跑的那一轮。
   *
   * 只发请求，不改 status：被停下的一轮照常收尾，直播的 SSE 以 RUN_FINISHED 结束，补历史的轮询
   * 看到 `running` 变回 false，界面沿原路回到空闲。这一轮还没被 Runtime 接受时没有 run ID，只先
   * 记下，拿到 run ID 时补发，见 `pendingStop`；不能 abort 本页的请求代替，那只会让本页不再读，
   * Runtime 照样会接下这一轮。
   */
  const stopRun = async () => {
    if (!canStop.value) return;
    stopping.value = true;
    if (runId.value) {
      await requestStop(runId.value);
    } else if (projectId.value && conversationNumber.value != null) {
      pendingStop = { projectId: projectId.value, number: conversationNumber.value };
    }
  };

  // TODO: 项目对话暂不上传图片，后续再接入
  const sendMessage = async (text: string, images: ChatImage[] = [], modelId?: string) => {
    void images;
    const content = text.trim();
    if (!content || busy.value || !projectId.value || conversationNumber.value == null || !isLive.value) {
      return;
    }

    // 自己发消息就改由这条 SSE 来画。补历史如果还在飞，不能再写进同一条消息。
    stopCatchUp();
    liveRunGeneration += 1;

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
    const runProjectId = projectId.value;
    const runNumber = conversationNumber.value;
    const runGeneration = liveRunGeneration;
    // 读 SSE 时游标不前进，所以它一直是「这一轮之前」的位置。
    const seqBeforeRun = uiEventSeq.value;
    // 只有读到 RUN_FINISHED 才算这一轮完整画出来了。RUN_ERROR 不算：本服务和 Runtime 之间断开时，
    // 本服务会自己补一个 RUN_ERROR，而这一轮在 Runtime 里还在跑。
    let sawRunFinished = false;
    // 服务端明确拒绝了这一轮（4xx/5xx 响应）：没有一轮在跑，眼前的报错就是结果，不用去对齐。
    let refused = false;
    const controller = new AbortController();
    liveRunAbort = controller;
    // 代数在取消时立刻加一，比项目号、会话号变得更早：openConversation 还在等接口时，
    // 消息列表仍是上一段，不能靠「当前会话号已经变了」来判断。
    const stillCurrent = () => (
      liveRunGeneration === runGeneration
      && projectId.value === runProjectId
      && conversationNumber.value === runNumber
    );

    messages.value.push(userMessage, assistantMessage);
    syncApplyCtx();
    status.value = 'thinking';
    runId.value = null;
    awaitingRunStart.value = true;

    // 经响应式代理改 progress：直接改 assistantMessage 这个原始对象，界面不会跟着变。
    const liveAssistant = messages.value[messages.value.length - 1];
    // 本轮开始输出或已经失败后就不再提示：迟到的状态查询不能把提示又盖回去。
    let preparingOver = false;
    const showPreparingRuntime = () => {
      if (!preparingOver && stillCurrent()) liveAssistant.progress = PREPARING_RUNTIME_TEXT;
    };

    // 已知没有可用运行环境：这一轮要先准备环境，可能要几十秒，先说清楚在等什么。
    if (!runtimeReady.value) showPreparingRuntime();

    // 手里的状态可能早已过期（离开半小时回来，运行环境已被回收），所以和发消息并行再问一次。
    // 只看 runtime_ready，不走 applyState：它会按 running=false 把「正在回复」改回空闲。
    // 失败不弹窗，最多是少一句提示。
    getConversation(runProjectId, runNumber, { globalError: false })
      .then((state) => {
        if (!state.runtime_ready) showPreparingRuntime();
      })
      .catch(() => undefined);

    try {
      // 「拉起预览」还在拉这个会话的 Runtime 时先等它回来，失败也照常发。两边同时拉，跨 worker 时
      // 后到的这一轮会被 AGENT_WORKSPACE_BUSY 拒掉。它回来时 Runtime 已经起来并恢复好，这一轮
      // 本来也要做这些，几乎不多等。
      const pendingPreview = previewStartInFlight;
      if (pendingPreview?.projectId === runProjectId && pendingPreview.number === runNumber) {
        await pendingPreview.done;
        if (!stillCurrent()) return;
      }
      const response = await startConversationRun(
        runProjectId,
        runNumber,
        createStartRunRequest(content, modelId),
        controller.signal,
      );
      if (!stillCurrent()) return;
      for await (const event of readSseEvents(response)) {
        // 读到的是上一轮的事件。列表已经换成别的项目或会话，不能再 syncApplyCtx 跟着写过去。
        if (!stillCurrent()) break;
        if (!preparingOver) {
          preparingOver = true;
          // 开始输出，运行环境已就绪。只清自己设的那句，事件带来的进度留给 applyResult。
          if (liveAssistant.progress === PREPARING_RUNTIME_TEXT) liveAssistant.progress = '';
        }
        if (event.type === 'RUN_STARTED' && awaitingRunStart.value) {
          awaitingRunStart.value = false;
          if (typeof event.runId === 'string' && event.runId) {
            runId.value = event.runId;
            // 准备运行环境期间就按了停止。
            flushPendingStop();
          }
        }
        if (event.type === 'RUN_FINISHED') sawRunFinished = true;
        syncApplyCtx();
        applyResult(applyCtx, applyAgUiEvent(applyCtx, event, { ignoreUser: true }));
      }
    } catch (error) {
      // 切走时 abort 会落到这里。那条助手消息已经不在眼前的列表里，错误不能写到新对话上。
      if (!stillCurrent()) return;
      refused = error instanceof RequestError;
      const modelUnavailable = isApiError(error, ApiErrorCode.MODEL_NOT_AVAILABLE);
      const textBlock = liveAssistant.blocks.find(block => block.type === 'text');
      const detail = modelUnavailable
        ? '该模型已不可用，请重新选择后重试。'
        : error instanceof Error ? error.message : '发起对话失败';
      liveAssistant.tone = 'error';
      if (textBlock && !textBlock.text) {
        textBlock.text = detail;
      } else {
        liveAssistant.blocks.push({ type: 'text', text: detail });
      }
      if (modelUnavailable) {
        Message({ theme: 'warning', message: '该模型已不可用' });
        await modelCatalogStore.recoverFromUnavailableModel();
      }
    } finally {
      preparingOver = true;
      if (liveRunAbort === controller) liveRunAbort = null;
      if (stillCurrent()) {
        awaitingRunStart.value = false;
        assistantMessage.progress = '';
        const textBlock = assistantMessage.blocks.find(block => block.type === 'text');
        // 被停下的一轮自己会标「已停止」，不用再补这一句。
        if (textBlock && !textBlock.text && !assistantMessage.stopped) {
          textBlock.text = '本轮对话已结束。';
        }
        if (!sawRunFinished && !refused) {
          try {
            await settleAfterInterruptedRun(stillCurrent, seqBeforeRun);
          } catch {
            // 只有按历史重画失败会到这里，bindConversation 已在对话区留了报错；它也已把状态改对。
          }
        } else {
          status.value = 'idle';
          if (projectId.value && conversationNumber.value != null) {
            try {
              // 这一轮已经完整画出来了：游标直接拨到最新，不再把本轮入库的事件接一遍。
              await syncConversationOnce();
            } catch {
              // 发送结果已展示，追赶失败不覆盖当前消息
            }
          }
        }
      }
    }
  };

  return {
    projectId,
    projectName,
    intRenamingStatus,
    conversationNumber,
    conversationId,
    isLive,
    liveNumber,
    uiEventSeq,
    running,
    runId,
    stopping,
    canStop,
    replicationPending,
    entering,
    previewStarting,
    previewStartSeq,
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
    queueInitialMessage,
    consumeInitialMessage,
    setProjectName,
    pollProjectIntRenaming,
    sendMessage,
    stopRun,
  };
});
