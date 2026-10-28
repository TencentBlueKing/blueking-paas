import { nextTick, onBeforeUnmount, ref } from 'vue';

const DEFAULT_CLOSE_DELAY = 120;
const DEFAULT_ITEM_SELECTOR = '[role="menuitem"]';

interface HoverSubmenuOptions {
  onOpen?: () => void | Promise<void>;
  closeDelay?: number;
  itemSelector?: string;
}

/**
 * 管理由 hover、点击和键盘共同驱动的二级菜单。
 *
 * 延迟关闭让鼠标能跨过父菜单与子菜单之间的间隙；键盘展开则等待数据加载完成后再把焦点
 * 移到第一项，避免焦点落在加载状态上。
 */
export const useHoverSubmenu = ({
  onOpen,
  closeDelay = DEFAULT_CLOSE_DELAY,
  itemSelector = DEFAULT_ITEM_SELECTOR,
}: HoverSubmenuOptions = {}) => {
  const triggerRef = ref<HTMLButtonElement>();
  const panelRef = ref<HTMLElement>();
  const visible = ref(false);
  let closeTimer = 0;
  let generation = 0;
  let openPromise: Promise<void> | null = null;

  const cancelClose = () => {
    window.clearTimeout(closeTimer);
    closeTimer = 0;
  };

  const close = (restoreFocus = false) => {
    cancelClose();
    generation += 1;
    visible.value = false;
    openPromise = null;
    if (restoreFocus) nextTick(() => triggerRef.value?.focus());
  };

  const show = async (focusFirst = false) => {
    cancelClose();
    if (!visible.value) {
      visible.value = true;
      generation += 1;
      openPromise = Promise.resolve(onOpen?.());
    }

    const expectedGeneration = generation;
    if (openPromise) await openPromise;
    if (!focusFirst || !visible.value || expectedGeneration !== generation) return;

    await nextTick();
    panelRef.value?.querySelector<HTMLButtonElement>(itemSelector)?.focus();
  };

  const toggle = () => {
    if (visible.value) close();
    else void show();
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer = window.setTimeout(() => close(), closeDelay);
  };

  onBeforeUnmount(() => {
    cancelClose();
    generation += 1;
  });

  return {
    triggerRef,
    panelRef,
    visible,
    show,
    close,
    toggle,
    scheduleClose,
    cancelClose,
  };
};
