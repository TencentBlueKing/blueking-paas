<template>
  <bk-popover
    v-model:isShow="visible"
    trigger="click"
    placement="bottom-end"
    theme="light"
    :arrow="false"
    :disabled="disabled"
    :padding="0"
    @after-show="fetchList"
  >
    <span
      class="icon-btn"
      :class="{ 'is-disabled': disabled }"
      v-bk-tooltips="{ content: '会话历史', placement: 'top', disabled: visible || disabled }"
    >
      <TextFile class="icon-btn__icon" />
    </span>
    <template #content>
      <div class="history-dropdown">
        <bk-loading :loading="loading">
          <div v-if="!loading && !conversations.length" class="history-dropdown__empty">
            暂无会话
          </div>
          <ul v-else class="history-dropdown__list">
            <li
              v-for="row in conversations"
              :key="row.number"
              :class="[
                'history-dropdown__item',
                { 'is-current': row.number === currentNumber },
              ]"
              @click="handleOpen(row)"
            >
              <div class="history-dropdown__row">
                <span class="history-dropdown__name">会话 #{{ row.number }}</span>
                <bk-tag :theme="row.is_live ? 'success' : ''" size="small">
                  {{ row.is_live ? '进行中' : '已结束' }}
                </bk-tag>
              </div>
              <p class="history-dropdown__time">{{ timeFormatter(row.created) }}</p>
            </li>
          </ul>
        </bk-loading>
      </div>
    </template>
  </bk-popover>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Message } from 'bkui-vue';
import { TextFile } from 'bkui-vue/lib/icon';
import type { ConversationResponse } from '@/http/types';
import { useProjectStore } from '@/store/project';
import { timeFormatter } from '@/common/util';

defineProps<{
  disabled?: boolean;
  currentNumber: number | null;
}>();

const projectStore = useProjectStore();
const loading = ref(false);
const visible = ref(false);
const conversations = ref<ConversationResponse[]>([]);

const fetchList = async () => {
  loading.value = true;
  try {
    const data = await projectStore.fetchConversationList(1, 20);
    conversations.value = data.items || [];
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '获取会话历史失败',
    });
  } finally {
    loading.value = false;
  }
};

const handleOpen = async (row: ConversationResponse) => {
  try {
    await projectStore.openConversation(row.number);
    visible.value = false;
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '打开会话失败',
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

.history-dropdown {
  width: 280px;
  max-height: 360px;
  overflow: auto;
}

.history-dropdown__empty {
  padding: 24px 16px;
  color: var(--faint, #88919e);
  font-size: 13px;
  text-align: center;
}

.history-dropdown__list {
  margin: 0;
  padding: 4px 0;
  list-style: none;
}

.history-dropdown__item {
  padding: 10px 12px;
  cursor: pointer;
}

.history-dropdown__item:hover,
.history-dropdown__item.is-current {
  background: #edf1ff;
}

.history-dropdown__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.history-dropdown__name {
  color: var(--ink, #12141a);
  font-size: 13px;
}

.history-dropdown__time {
  margin: 4px 0 0;
  color: var(--faint, #88919e);
  font-size: 12px;
}
</style>
