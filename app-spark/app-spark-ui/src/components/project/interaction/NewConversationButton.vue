<template>
  <bk-popover
    ref="popoverRef"
    trigger="click"
    placement="bottom-end"
    theme="light"
    :arrow="false"
    :disabled="disabled"
    :padding="0"
    @after-show="onAfterShow"
    @after-hidden="onAfterHidden"
  >
    <span
      class="icon-btn"
      :class="{ 'is-disabled': disabled }"
      v-bk-tooltips="{ content: '新建会话', placement: 'top', disabled: visible || disabled }"
    >
      <Plus class="icon-btn__icon" />
    </span>
    <template #content>
      <div class="new-conversation">
        <p class="new-conversation__title">新建会话</p>
        <p class="new-conversation__text">
          新会话将使用全新上下文，继承工作区文件的最新改动；当前会话历史将被归档（仅供查看）
        </p>
        <div class="new-conversation__actions">
          <bk-button size="small" @click="close">取消</bk-button>
          <bk-button
            size="small"
            theme="primary"
            @click="handleConfirm"
          >
            确认新建
          </bk-button>
        </div>
      </div>
    </template>
  </bk-popover>
</template>

<script setup lang="ts">
import { Message } from 'bkui-vue';
import { Plus } from 'bkui-vue/lib/icon';
import { usePopoverVisible } from '@/composables/use-popover-visible';
import { useProjectStore } from '@/store/project';

defineProps<{
  disabled?: boolean;
}>();

const projectStore = useProjectStore();
const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();

const handleConfirm = async () => {
  close();
  try {
    await projectStore.startFreshConversation();
  } catch (error) {
    // 失败必须说出来：归档那一步可能已经生效，否则用户只会看到对话忽然变成只读，不知道为什么。
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '新建会话失败',
    });
  }
};
</script>

<style lang="postcss" scoped>
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: var(--muted, #5c6573);
  cursor: pointer;
  border-radius: 8px;
}

.icon-btn:hover:not(.is-disabled) {
  color: var(--ink, #12141a);
  background: #e8ecf3;
}

.icon-btn.is-disabled {
  color: #c4c6cc;
  cursor: not-allowed;
}

.icon-btn__icon {
  font-size: 16px;
}

.new-conversation {
  width: 280px;
  padding: 14px 14px 12px;
}

.new-conversation__title {
  margin: 0;
  color: var(--ink, #12141a);
  font-size: 13px;
  font-weight: 600;
}

.new-conversation__text {
  margin: 6px 0 0;
  color: var(--muted, #5c6573);
  font-size: 12px;
  line-height: 1.6;
}

.new-conversation__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
