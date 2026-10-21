import { computed, onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import { storeToRefs } from 'pinia';
import type { PreviewPhase } from '@/components/project/workspace/types';
import { getConversationPreview } from '@/http/api';
import type { DevServerStatus } from '@/http/types';
import { useProjectStore } from '@/store/project';

import { previewFrameUrl } from './preview-frame-url';

/** 应用拉起要几十秒，更密也不会更快看到页面；每次请求都会再问一次 Runtime。 */
const POLL_INTERVAL_MS = 5000;
/** 连续这么多次都失败，就当这个接口坏了，不再每 5 秒打一遍。中间成功一次就重新计数。 */
const MAX_CONSECUTIVE_FAILURES = 3;

const KNOWN_STATUSES: ReadonlySet<string> = new Set([
  'not_started',
  'starting',
  'ready',
  'stopped',
]);

const asDevServerStatus = (value: string | null | undefined): DevServerStatus | null => (
  value && KNOWN_STATUSES.has(value) ? value as DevServerStatus : null
);

/**
 * 当前打开的预览面板要画的地址和状态。
 *
 * 没有推送。`app.launched` 只落库，不进正在进行的 `/runs` SSE，对话流里等不到「可以预览了」。
 * 面板开着、会话还活着时，进来先问一次。之后是否每 5 秒继续问，要同时看会话和预览：
 * 这一轮还在回复（`running`、页面上的回复中、或 `replication_pending`），或者预览还在
 * `starting`，才继续。会话已经闲下来，并且页面已经 `ready`、没启动、已停止或问不到，就停。
 * 离开这个面板，或会话已结束，也停。一次都还没成功时，失败一次就停，不再空转。
 * 已经成功过之后，偶尔失败一次不停，连续失败 3 次再停，上次的地址和状态留着。
 * 停掉之后，对话框里出现新的回复，或重新进入这个会话，计数回到 0 再问。
 * 不要在后台对每个会话一直打。
 *
 * 地址有了不等于页面能开，只有 `ready` 才把 origin 交给 iframe。沙箱重建后主机名会变，
 * 变了才换 src，同一地址的轮询不重载 iframe。
 *
 * 接口只报地址和状态，模型改了代码这两样都不变，轮询看不出页面该刷新了。所以另给一个 `frameKey`，
 * 一轮对话结束就递增，让 iframe 重新挂一次。
 */
export const useConversationPreview = (panelOpen: Ref<boolean>) => {
  const {
    projectId,
    conversationNumber,
    isLive,
    status,
    running,
    replicationPending,
    messages,
  } = storeToRefs(useProjectStore());

  const origin = ref('');
  /** direct 为 true 时，origin 是沙箱暴露的主机，不是本服务的反代路径。 */
  const direct = ref(false);
  const devServerStatus = ref<DevServerStatus | null>(null);
  /** 作为 iframe 的 key，变了就重新挂载、重新请求页面。 */
  const frameKey = ref(0);
  /**
   * 这次打开面板后还没问到 preview。离开面板、换会话都会重新置上，
   * 这样回来时先占位，问到 ready 再挂 iframe。
   */
  const pending = ref(true);

  let timer = 0;
  /** 换会话或离开页面时递增，用来丢掉还在路上的旧响应。 */
  let generation = 0;
  /** 同一代里已经有请求在飞时，这一拍不再打。慢响应不会被下一拍顶掉。 */
  let inFlightGeneration = -1;
  let trackedKey = '';
  let consecutiveFailures = 0;
  /** 这次打开这个会话后，preview 已经成功过。没有的话失败一次就停，不按 3 次空转。 */
  let resolved = false;
  /** 最近一条助手回复的正文。变了说明对话框有新内容，失败计数要回到 0。 */
  let replyMark = '';

  const conversationKey = () => (
    projectId.value && conversationNumber.value != null
      ? `${projectId.value}:${conversationNumber.value}`
      : ''
  );

  /** 只看最后一条真正的助手回复，往前翻历史不会被当成新回复。 */
  const latestReplyMark = () => {
    const list = messages.value;
    for (let index = list.length - 1; index >= 0; index -= 1) {
      const message = list[index];
      if (message.role !== 'assistant') continue;
      if (message.id === 'welcome' || message.id === 'history-error') continue;
      return message.blocks.map((block) => {
        if (block.type === 'text') return block.text || '';
        if (block.type === 'tool') return `${block.tool?.id || ''}:${block.tool?.state || ''}`;
        return '';
      }).join('\n');
    }
    return '';
  };

  const stop = () => {
    if (!timer) return;
    window.clearInterval(timer);
    timer = 0;
  };

  /**
   * 还要不要每 5 秒问一次。
   *
   * 会话还在回复或收尾没写完时，应用可能被拉起或关掉，预览现在显示没启动也要继续问。
   * 会话已经闲下来之后，只有还在启动、结果没出来时才继续。已经 ready 的完成页不再每 5 秒问。
   */
  const shouldKeepPolling = () => {
    if (!panelOpen.value || conversationKey() === '' || !isLive.value) return false;
    if (status.value !== 'idle' || running.value || replicationPending.value) return true;
    return devServerStatus.value === 'starting';
  };

  const start = () => {
    stop();
    if (!panelOpen.value || conversationKey() === '' || !isLive.value) return;
    consecutiveFailures = 0;
    void pull();
    timer = window.setInterval(() => {
      void pull();
    }, POLL_INTERVAL_MS);
  };

  const pull = async () => {
    const id = projectId.value;
    const number = conversationNumber.value;
    if (!panelOpen.value || !id || number == null || !isLive.value) return;
    if (inFlightGeneration === generation) return;

    const gen = generation;
    inFlightGeneration = gen;
    try {
      const data = await getConversationPreview(id, number);
      if (gen !== generation) return;
      // 面板已经合上，或会话已经换过、结束了：这包响应不属于眼前这块预览。
      if (
        !panelOpen.value
        || projectId.value !== id
        || conversationNumber.value !== number
        || !isLive.value
      ) {
        return;
      }
      // 同一地址不换 src。远程沙箱重建后 get_host 会变成另一个主机，那时才重载。
      if (data.origin && data.origin !== origin.value) {
        origin.value = data.origin;
        direct.value = data.direct;
      }
      devServerStatus.value = asDevServerStatus(data.dev_server_status);
      pending.value = false;
      resolved = true;
      consecutiveFailures = 0;
      if (!shouldKeepPolling()) stop();
    } catch (error) {
      if (gen !== generation) return;
      if (
        !panelOpen.value
        || projectId.value !== id
        || conversationNumber.value !== number
        || !isLive.value
      ) {
        return;
      }
      consecutiveFailures += 1;
      console.error('[project] 预览状态获取失败', error);
      // 一次都没成功过：没有上次的状态可留，停在「正在获取」里空等没有意义。
      // 计数直接记满，会话状态随后变化也不会把这次失败又打开。
      if (!resolved) consecutiveFailures = MAX_CONSECUTIVE_FAILURES;
      // 已经成功过：地址和状态不动，偶尔失败继续问，连续 3 次再停。
      if (consecutiveFailures < MAX_CONSECUTIVE_FAILURES) return;
      if (pending.value) pending.value = false;
      stop();
    } finally {
      if (inFlightGeneration === gen) inFlightGeneration = -1;
    }
  };

  const sync = () => {
    const nextKey = conversationKey();
    if (nextKey !== trackedKey) {
      trackedKey = nextKey;
      generation += 1;
      origin.value = '';
      direct.value = false;
      devServerStatus.value = null;
      pending.value = true;
      resolved = false;
      consecutiveFailures = 0;
    }

    stop();
    if (!panelOpen.value || nextKey === '' || !isLive.value) {
      // 离开面板时摘掉 iframe。origin 留下，下次进来问到 ready 再挂，避免把上次的 502 页留在里面。
      if (!panelOpen.value && nextKey !== '' && isLive.value) pending.value = true;
      return;
    }

    start();
  };

  watch([panelOpen, projectId, conversationNumber, isLive], sync, { immediate: true });

  // 预览已经停了，对话框里又写出新回复：从 0 再给 3 次。
  // 正在输出时内容会一直变，计数跟着回到 0，不会在回复过程中被偶发失败停掉。
  watch(messages, () => {
    const next = latestReplyMark();
    if (!next || next === replyMark) {
      replyMark = next;
      return;
    }
    replyMark = next;
    consecutiveFailures = 0;
    if (timer || !panelOpen.value || conversationKey() === '' || !isLive.value) return;
    if (!origin.value && devServerStatus.value == null) pending.value = true;
    start();
  }, { deep: true });

  // 文件是在一轮对话里写的，回到 idle 时通常已经写完。不能指望状态变化来触发：只改文件时进程不
  // 重启，状态一直是 ready；就算重启了，5 秒一拍的轮询也未必赶得上中间那段 starting。
  watch(status, (next, prev) => {
    if (next === 'idle' && prev !== 'idle') frameKey.value += 1;
  });

  // 连续失败停掉的，要等新回复把计数清零，这里不重新打开。
  // 还没问到第一次结果时也不停，避免把「进来先问一次」取消掉。
  watch([status, running, replicationPending], () => {
    if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES || pending.value) return;
    if (shouldKeepPolling()) {
      if (!timer) start();
      return;
    }
    stop();
  });

  onScopeDispose(() => {
    stop();
    generation += 1;
  });

  const phase = computed<PreviewPhase>(() => {
    if (conversationNumber.value == null) return 'no-conversation';
    if (!isLive.value) return 'ended';
    if (pending.value) return 'pending';
    switch (devServerStatus.value) {
      case 'not_started':
      case 'starting':
      case 'stopped':
      case 'ready':
        return devServerStatus.value;
      default:
        return 'unavailable';
    }
  });

  /** 只有 ready 才有 src。空串表示摘掉 iframe，回到占位。 */
  const frameSrc = computed(() => (
    phase.value === 'ready' && origin.value
      ? previewFrameUrl(origin.value, direct.value, window.location.origin)
      : ''
  ));

  const waiting = computed(() => phase.value === 'pending' || phase.value === 'starting');

  return { phase, frameSrc, frameKey, waiting };
};
