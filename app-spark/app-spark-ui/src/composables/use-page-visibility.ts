import { onScopeDispose, readonly, ref } from 'vue';

const pageVisible = ref(true);
let consumers = 0;

const syncVisibility = () => {
  pageVisible.value = document.visibilityState !== 'hidden';
};

/**
 * 共享页面可见状态。首个使用方挂载时监听，最后一个使用方销毁时释放，
 * 避免每个轮询逻辑各自维护一套 visibilitychange 监听。
 */
export const usePageVisibility = () => {
  consumers += 1;
  if (consumers === 1 && typeof document !== 'undefined') {
    syncVisibility();
    document.addEventListener('visibilitychange', syncVisibility);
  }

  let active = true;
  onScopeDispose(() => {
    if (!active) return;
    active = false;
    consumers -= 1;
    if (consumers === 0 && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', syncVisibility);
    }
  });

  return readonly(pageVisible);
};
