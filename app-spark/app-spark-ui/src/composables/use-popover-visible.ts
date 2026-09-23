import { ref } from 'vue';

interface PopoverInstance {
  hide?: () => void;
}

/**
 * 让 `bk-popover` 能被外面主动关掉，并且知道它此刻是开着还是关着。
 *
 * 两件事都不能照直觉写：
 *
 * - `isShow` 名义上支持 `v-model`，实际是单向的：组件自己被点开时不会 emit `update:isShow`，外面
 *   那个 ref 一直停在 false。于是「点完就收起来」写成 `visible.value = false` 等于什么都没做——值
 *   没变，组件内部的 `watch(() => props.isShow)` 不会触发，气泡赖在原地不动。
 * - 而且那个 watch 只在 setup 时 `disabled` 为 false 才注册。我们这两个气泡挂载时项目还在加载
 *   （`busy` 为真），watch 压根不存在，靠 `isShow` 关就更不可能成。
 *
 * 所以关闭走组件暴露的 `hide()`，它直接改内部状态，不受上面两条影响；开合状态则由 `afterShow` /
 * `afterHidden` 回填，供「气泡开着时别再弹 tooltip」这类判断使用。
 */
export const usePopoverVisible = () => {
  const popoverRef = ref<PopoverInstance | null>(null);
  const visible = ref(false);

  return {
    popoverRef,
    visible,
    onAfterShow: () => {
      visible.value = true;
    },
    onAfterHidden: () => {
      visible.value = false;
    },
    close: () => {
      popoverRef.value?.hide?.();
      // hide() 之后 `afterHidden` 会把它置回 false，这里再写一次是为了万一气泡实例还没建起来，
      // 状态也不至于卡在「开着」上。
      visible.value = false;
    },
  };
};
