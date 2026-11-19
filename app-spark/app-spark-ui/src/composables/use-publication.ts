import { computed, onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import {
  clearPublicationUnseenResult,
  createPublicationDeployment,
  getPublication,
} from '@/http/api';
import type { PublicationResponse } from '@/http/types';
import { ApiErrorCode, isApiError } from '@/http/error-codes';
import {
  createLatestDeploymentRequest,
  hasNewPublicationVersion,
} from '@/common/publication';
import { usePageVisibility } from './use-page-visibility';

const POLL_INTERVAL_MS = 6000;

const errorMessage = (error: unknown, fallback: string) => (
  error instanceof Error && error.message ? error.message : fallback
);

/**
 * 当前项目的真实发布状态。
 *
 * 进入项目先查询一次；后端返回 task 后每 6 秒继续查询，面板关闭也不停，确保工具栏按钮能及时从
 * 「发布中」切换为结果。页面进入后台时暂停，恢复后先查询最新状态再决定是否继续。每个请求带顺序号，
 * 较早发出的 GET 即使比 POST 晚回来，也不能覆盖新任务。
 */
export const usePublication = (projectId: Ref<string>) => {
  const pageVisible = usePageVisibility();
  const publication = ref<PublicationResponse | null>(null);
  const loading = ref(false);
  const refreshing = ref(false);
  const submitting = ref(false);
  const loadError = ref('');
  const actionError = ref('');
  // 首次发布时被开发者中心判为重名的名称；面板据此回到改名状态，不当成一般的发布失败展示。
  const conflictedAppName = ref<string | null>(null);

  let timer = 0;
  let generation = 0;
  let requestSequence = 0;
  let appliedSequence = 0;
  let pullPromise: Promise<PublicationResponse | null> | null = null;

  const stopPolling = () => {
    if (!timer) return;
    window.clearTimeout(timer);
    timer = 0;
  };

  const schedulePolling = () => {
    stopPolling();
    if (!pageVisible.value || !publication.value?.task || !projectId.value) return;
    timer = window.setTimeout(() => {
      timer = 0;
      void pull(true);
    }, POLL_INTERVAL_MS);
  };

  const applyResponse = (
    data: PublicationResponse,
    requestGeneration: number,
    sequence: number,
  ) => {
    if (requestGeneration !== generation || sequence < appliedSequence) return false;
    appliedSequence = sequence;
    publication.value = data;
    loadError.value = '';
    actionError.value = '';
    schedulePolling();
    return true;
  };

  async function pull(silent = false): Promise<PublicationResponse | null> {
    const id = projectId.value;
    if (!id || !pageVisible.value) return null;
    if (pullPromise) return pullPromise;

    const requestGeneration = generation;
    const sequence = ++requestSequence;
    if (!silent && !publication.value) loading.value = true;
    else refreshing.value = true;

    const promise = getPublication(id)
      .then((data) => {
        applyResponse(data, requestGeneration, sequence);
        return data;
      })
      .catch((error) => {
        if (requestGeneration !== generation) return null;
        loadError.value = errorMessage(error, '获取发布状态失败');
        // 任务可能仍在后端继续，临时网络失败不能让轮询永久停止。
        schedulePolling();
        return null;
      })
      .finally(() => {
        if (requestGeneration === generation) {
          loading.value = false;
          refreshing.value = false;
        }
        if (pullPromise === promise) pullPromise = null;
      });

    pullPromise = promise;
    return promise;
  }

  const deployLatest = async (appName?: string) => {
    const id = projectId.value;
    const current = publication.value;
    if (!id || !current?.latest_version_id || current.task || submitting.value) return false;

    const requestGeneration = generation;
    const barrierSequence = ++requestSequence;
    // 这一刻之后，发得更早的状态查询即使晚回来，也不能把即将开始的任务覆盖掉。
    appliedSequence = barrierSequence;
    const name = appName?.trim();
    actionError.value = '';
    conflictedAppName.value = null;
    submitting.value = true;
    stopPolling();

    try {
      const data = await createPublicationDeployment(
        id,
        createLatestDeploymentRequest(current, name),
      );
      // POST 进行期间可能因面板打开或页面恢复触发了 GET。发布响应是本次操作的权威结果，
      // 在返回时重新取序号，确保这些中途发出的旧快照不能盖掉已经创建好的任务。
      if (requestGeneration !== generation || projectId.value !== id) return false;
      const responseSequence = ++requestSequence;
      if (!applyResponse(data, requestGeneration, responseSequence)) return false;

      // 等掉 POST 之前已经在路上的 GET，再主动取一次完整快照。这样即使发布响应与「确认已读」
      // 同时发生，任务状态和后续轮询也会按服务端最新结果恢复。
      if (pullPromise) await pullPromise;
      if (
        requestGeneration === generation
        && projectId.value === id
        && pageVisible.value
      ) {
        await pull(true);
      }
      return true;
    } catch (error) {
      if (requestGeneration !== generation) return false;
      if (isApiError(error, ApiErrorCode.PUBLICATION_TASK_IN_PROGRESS)) {
        if (pullPromise) await pullPromise;
        await pull(true);
        return false;
      }
      if (isApiError(error, ApiErrorCode.PUBLICATION_NO_VERSION) && publication.value) {
        publication.value = { ...publication.value, latest_version_id: null };
      } else if (isApiError(error, ApiErrorCode.PUBLICATION_APP_NAME_CONFLICT) && name) {
        // 重名时后端没有建任务，用户改个名字再发即可，提示交给名称输入框。
        conflictedAppName.value = name;
      } else {
        actionError.value = errorMessage(error, '发布失败，请稍后重试');
      }
      schedulePolling();
      return false;
    } finally {
      if (requestGeneration === generation) submitting.value = false;
    }
  };

  const acknowledgeResult = async () => {
    const id = projectId.value;
    const current = publication.value;
    if (!id || !current?.unseen_result) return;
    const requestGeneration = generation;
    try {
      await clearPublicationUnseenResult(id);
      if (
        requestGeneration === generation
        && projectId.value === id
        && publication.value?.unseen_result
      ) {
        publication.value = { ...publication.value, unseen_result: null };
      }
    } catch (error) {
      // 关闭结果页不应被错误提示打断；保留 unseen_result，下次打开仍可看到并再次确认。
      console.error('[project] 确认发布结果已读失败', error);
    }
  };

  watch(projectId, (id) => {
    generation += 1;
    requestSequence = 0;
    appliedSequence = 0;
    pullPromise = null;
    stopPolling();
    publication.value = null;
    loadError.value = '';
    actionError.value = '';
    conflictedAppName.value = null;
    loading.value = Boolean(id);
    refreshing.value = false;
    submitting.value = false;
    if (id) void pull();
  }, { immediate: true });

  watch(pageVisible, (visible) => {
    stopPolling();
    if (!visible || !projectId.value) return;
    const id = projectId.value;
    const pending = pullPromise;
    void Promise.resolve(pending).then(() => {
      if (pageVisible.value && projectId.value === id) void pull(true);
    });
  });

  onScopeDispose(() => {
    generation += 1;
    stopPolling();
  });

  const isFirstPublication = computed(() => publication.value?.app_code === null);
  const hasNewVersion = computed(() => hasNewPublicationVersion(publication.value));

  return {
    publication,
    loading,
    refreshing,
    submitting,
    loadError,
    actionError,
    conflictedAppName,
    isFirstPublication,
    hasNewVersion,
    pull,
    deployLatest,
    acknowledgeResult,
    clearActionError: () => {
      actionError.value = '';
    },
  };
};
