<template>
  <bk-popover
    ref="popoverRef"
    trigger="click"
    :placement="placement"
    theme="light"
    :arrow="false"
    :padding="0"
    :offset="6"
    ext-cls="project-actions-popover"
    @after-show="handleAfterShow"
    @after-hidden="handleAfterHidden"
  >
    <button
      ref="triggerRef"
      type="button"
      class="project-actions-menu__trigger"
      :class="{ 'is-open': visible }"
      aria-label="更多操作"
      aria-haspopup="menu"
      :aria-expanded="visible"
    >
      <AppIcon name="more" />
    </button>
    <template #content>
      <div class="project-actions-menu" role="menu">
        <button type="button" role="menuitem" @click="select('rename')">
          <AppIcon name="pencil" />
          <span>重命名</span>
        </button>
        <button type="button" role="menuitem" class="is-danger" @click="select('delete')">
          <AppIcon name="trash" />
          <span>删除</span>
        </button>
      </div>
    </template>
  </bk-popover>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';
import AppIcon from '@/components/AppIcon.vue';
import { usePopoverVisible } from '@/composables/use-popover-visible';

withDefaults(defineProps<{
  placement?: 'top-end' | 'bottom-end';
}>(), {
  placement: 'bottom-end',
});

const emit = defineEmits<{
  (e: 'rename'): void;
  (e: 'delete'): void;
}>();

const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();
const triggerRef = ref<HTMLButtonElement>();
let triggerObserver: IntersectionObserver | null = null;

const stopObservingTrigger = () => {
  triggerObserver?.disconnect();
  triggerObserver = null;
};

const handleAfterShow = () => {
  onAfterShow();
  if (!triggerRef.value || typeof IntersectionObserver === 'undefined') return;
  stopObservingTrigger();
  triggerObserver = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) return;
    stopObservingTrigger();
    close();
  });
  triggerObserver.observe(triggerRef.value);
};

const handleAfterHidden = () => {
  stopObservingTrigger();
  onAfterHidden();
};

const select = (action: 'rename' | 'delete') => {
  close();
  emit(action);
};

onBeforeUnmount(stopObservingTrigger);
</script>

<style lang="postcss" scoped>
.project-actions-menu__trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--faint);
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.project-actions-menu__trigger:hover,
.project-actions-menu__trigger.is-open {
  color: var(--ink);
  background: var(--subtle-bg);
}

.project-actions-menu__trigger :deep(.app-icon) {
  font-size: 18px;
}

.project-actions-menu {
  box-sizing: border-box;
  min-width: 168px;
  padding: 6px;
  background: #fff;
  border-radius: 12px;
}

:global(.project-actions-popover),
:global(.project-actions-popover.bk-popover),
:global(.project-actions-popover .bk-pop2-content) {
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}

:global(.project-actions-popover) {
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(16, 22, 34, 0.14), 0 0 0 1px rgba(16, 22, 34, 0.05);
}

.project-actions-menu > button {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  color: var(--ink);
  font-size: 13px;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.project-actions-menu > button:hover,
.project-actions-menu > button:focus-visible {
  background: var(--subtle-bg);
  outline: none;
}

.project-actions-menu > button :deep(.app-icon) {
  flex: 0 0 15px;
  width: 15px;
  height: 15px;
  margin-top: 2px;
  color: var(--faint);
}

.project-actions-menu > button.is-danger,
.project-actions-menu > button.is-danger :deep(.app-icon) {
  color: var(--danger);
}

.project-actions-menu > button.is-danger:hover,
.project-actions-menu > button.is-danger:focus-visible {
  background: var(--danger-soft);
}

.project-actions-menu__trigger:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}
</style>
