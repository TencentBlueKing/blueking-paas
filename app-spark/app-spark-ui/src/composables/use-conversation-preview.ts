import { computed, onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import { storeToRefs } from 'pinia';
import type { PreviewPhase } from '@/components/project/workspace/types';
import { getConversationPreview } from '@/http/api';
import type { DevServerStatus } from '@/http/types';
import { useProjectStore } from '@/store/project';

/** 应用拉起要几十秒，更密也不会更快看到页面；每次请求都会再问一次 Runtime。 */
const POLL_INTERVAL_MS = 5000;

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
 * iframe 要和当前页面同源，否则响应里的 `frame-ancestors 'self'` 会拦住。
 *
 * 接口按它自己看到的 Host 签发绝对地址。本地页面在另一台主机上时，只留路径，
 * 请求仍走页面上的 `/api-svc` 代理。路径本身不改。
 */
export const previewFrameUrl = (origin: string, pageOrigin: string): string => {
  if (!origin) return '';
  let url: URL;
  try {
    url = new URL(origin, pageOrigin);
  } catch {
    return origin;
  }
  if (url.origin === pageOrigin) return url.href;
  return `${pageOrigin}${url.pathname}${url.search}${url.hash}`;
};

/**
 * 当前打开的预览面板要画的地址和状态。
 *
 * 没有推送。`app.launched` 只落库，不进正在进行的 `/runs` SSE，对话流里等不到「可以预览了」。
 * 面板开着就自己打 `GET .../preview/`：进来立刻一次，之后每 5 秒一次，iframe 挂上之后也不停
 * ——进程会自己退出，没有事件通知。离开这个面板，或会话已结束，停掉。不要在后台对每个会话一直打。
 *
 * `origin` 第一次拿到就留下，后面只看 `dev_server_status` 变不变。地址有了不等于页面能开，
 * 只有 `ready` 才把 origin 交给 iframe。
 */
export const useConversationPreview = (panelOpen: Ref<boolean>) => {
  const { projectId, conversationNumber, isLive } = storeToRefs(useProjectStore());

  const origin = ref('');
  const devServerStatus = ref<DevServerStatus | null>(null);
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

  const conversationKey = () => (
    projectId.value && conversationNumber.value != null
      ? `${projectId.value}:${conversationNumber.value}`
      : ''
  );

  const stop = () => {
    if (!timer) return;
    window.clearInterval(timer);
    timer = 0;
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
      // 同一会话里 origin 不变。后面的响应只用来更新状态，避免 iframe 因 src 抖动重载。
      if (!origin.value && data.origin) origin.value = data.origin;
      devServerStatus.value = asDevServerStatus(data.dev_server_status);
      pending.value = false;
    } catch (error) {
      if (gen !== generation) return;
      console.error('[project] 预览状态获取失败', error);
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
      devServerStatus.value = null;
      pending.value = true;
    }

    stop();
    if (!panelOpen.value || nextKey === '' || !isLive.value) {
      // 离开面板时摘掉 iframe。origin 留下，下次进来问到 ready 再挂，避免把上次的 502 页留在里面。
      if (!panelOpen.value && nextKey !== '' && isLive.value) pending.value = true;
      return;
    }

    void pull();
    timer = window.setInterval(() => {
      void pull();
    }, POLL_INTERVAL_MS);
  };

  watch([panelOpen, projectId, conversationNumber, isLive], sync, { immediate: true });

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
      ? previewFrameUrl(origin.value, window.location.origin)
      : ''
  ));

  const waiting = computed(() => phase.value === 'pending' || phase.value === 'starting');

  return { phase, frameSrc, waiting };
};
