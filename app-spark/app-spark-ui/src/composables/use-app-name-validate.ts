import { onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import { validatePublicationAppName } from '@/http/api';
import type { PublicationAppNameValidateResponse } from '@/http/types';

const CHECK_DEBOUNCE_MS = 1000;

/**
 * 首次发布时检查蓝鲸应用名能否使用。
 *
 * 名称在开发者中心租户内唯一，打开发布面板和改名时都要问一次。检查只是提前提示：接口失败时不拦发布，
 * 由发布接口的校验兜底；发布时报重名，用 markTaken 记下，界面照样回到改名状态。
 */
export const useAppNameValidate = (projectId: Ref<string>) => {
  // 结果只对它检查过的那个输入有效，输入一变就作废，以免旧结果放行新名字。
  const result = ref<PublicationAppNameValidateResponse | null>(null);
  const checkedInput = ref('');
  const pendingInput = ref<string | null>(null);

  let timer = 0;
  let sequence = 0;
  let inflight: AbortController | null = null;

  const clearTimer = () => {
    if (!timer) return;
    window.clearTimeout(timer);
    timer = 0;
  };

  // 输入还在变时，上一次检查的结果用不上。取消它，避免返回后占掉这次输入的结论。
  const dropInflight = () => {
    sequence += 1;
    inflight?.abort();
    inflight = null;
  };

  const run = async (input: string) => {
    const id = projectId.value;
    const current = ++sequence;
    const controller = new AbortController();
    inflight = controller;
    try {
      const data = await validatePublicationAppName(id, input, controller.signal);
      // 更晚发出的检查、或切换了项目之后，这次的结果已经不算数。
      if (current !== sequence || projectId.value !== id) return;
      result.value = data;
      checkedInput.value = input;
    } catch (error) {
      if (controller.signal.aborted || current !== sequence || projectId.value !== id) return;
      // 问不到开发者中心时不给结论，发布时后端会再校验一次。
      console.error('[publication] 检查应用名称失败', error);
      result.value = null;
      checkedInput.value = input;
    } finally {
      if (inflight === controller) inflight = null;
      // 请求在路上时用户可能已经改了名，新名字还在等防抖：只清掉属于这次输入的等待。
      if (current === sequence && pendingInput.value === input) pendingInput.value = null;
    }
  };

  /** 检查 input；immediate 为 false 时等用户停止输入 1 秒再问。 */
  const validate = (input: string, immediate = false) => {
    clearTimer();
    dropInflight();
    const trimmed = input.trim();
    if (!trimmed || !projectId.value) {
      pendingInput.value = null;
      result.value = null;
      checkedInput.value = '';
      return;
    }

    pendingInput.value = trimmed;
    if (immediate) {
      void run(trimmed);
      return;
    }

    timer = window.setTimeout(() => {
      timer = 0;
      void run(trimmed);
    }, CHECK_DEBOUNCE_MS);
  };

  /** 发布时开发者中心报了重名：不等下一次检查，直接按重名展示。 */
  const markTaken = (input: string) => {
    clearTimer();
    dropInflight();
    pendingInput.value = null;
    const trimmed = input.trim();
    result.value = { name: trimmed, is_available: false, problem: 'taken', message: null };
    checkedInput.value = trimmed;
  };

  /** 当前输入是否还在等检查结果。 */
  const isPending = (input: string) => pendingInput.value !== null && pendingInput.value === input.trim();

  /** 当前输入的检查结果；输入改过、还没检查或检查失败时为 null。 */
  const resultFor = (input: string) => (
    result.value && checkedInput.value === input.trim() ? result.value : null
  );

  const reset = () => {
    clearTimer();
    dropInflight();
    pendingInput.value = null;
    result.value = null;
    checkedInput.value = '';
  };

  watch(projectId, reset);
  onScopeDispose(() => {
    clearTimer();
    dropInflight();
  });

  return {
    validate,
    markTaken,
    reset,
    isPending,
    resultFor,
  };
};
