<template>
  <bk-popover
    ref="popoverRef"
    trigger="click"
    placement="bottom-end"
    theme="light"
    :arrow="false"
    :disabled="disabled"
    :padding="0"
    @after-show="handleShow"
    @after-hidden="onAfterHidden"
  >
    <span
      class="icon-btn"
      :class="{ 'is-disabled': disabled }"
      v-bk-tooltips="{ content: '查看对话归档', placement: 'top', disabled: visible || disabled }"
    >
      <TextFile class="icon-btn__icon" />
    </span>
    <template #content>
      <div class="archive-dropdown">
        <bk-loading :loading="loading">
          <!-- 活跃会话放在最上面：翻看归档时，这是回到当前对话的入口 -->
          <section v-if="live" class="archive-dropdown__section">
            <p class="archive-dropdown__label">当前活跃会话</p>
            <div
              :class="[
                'archive-dropdown__item',
                { 'is-current': live.number === currentNumber },
              ]"
              @click="handleOpen(live)"
            >
              <div class="archive-dropdown__row">
                <span class="archive-dropdown__name">会话 #{{ live.number }}</span>
                <bk-tag theme="success" size="small">进行中</bk-tag>
              </div>
              <p class="archive-dropdown__time">开始于 {{ fromNowFormatter(live.created_at) }}</p>
            </div>
          </section>
          <section class="archive-dropdown__section">
            <p class="archive-dropdown__label">归档会话（仅供查看）</p>
            <div v-if="!loading && !conversations.length" class="archive-dropdown__empty">
              暂无归档会话
            </div>
            <ul v-else class="archive-dropdown__list">
              <li
                v-for="row in conversations"
                :key="row.number"
                :class="[
                  'archive-dropdown__item',
                  { 'is-current': row.number === currentNumber },
                ]"
                @click="handleOpen(row)"
              >
                <div class="archive-dropdown__row">
                  <span class="archive-dropdown__name">会话 #{{ row.number }}</span>
                  <bk-tag size="small">已归档</bk-tag>
                </div>
                  <p class="archive-dropdown__time">归档于 {{ timeFormatter(row.closed_at || row.created_at) }}</p>
              </li>
            </ul>
          </section>
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
import { usePopoverVisible } from '@/composables/use-popover-visible';
import { useProjectStore } from '@/store/project';
import { fromNowFormatter, timeFormatter } from '@/common/util';

const props = defineProps<{
  disabled?: boolean;
  currentNumber: number | null;
}>();

const projectStore = useProjectStore();
const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();
const loading = ref(false);
const live = ref<ConversationResponse | null>(null);
const conversations = ref<ConversationResponse[]>([]);

const fetchList = async () => {
  loading.value = true;
  try {
    // 两个列表一起要：活跃会话不在归档列表里，得单独问一次
    const [liveRow, archived] = await Promise.all([
      projectStore.fetchLiveConversation(),
      projectStore.fetchArchivedConversations(1, 20),
    ]);
    live.value = liveRow;
    conversations.value = archived.items || [];
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '获取对话归档失败',
    });
  } finally {
    loading.value = false;
  }
};

const handleShow = () => {
  onAfterShow();
  fetchList();
};

const handleOpen = async (row: ConversationResponse) => {
  // 点的就是眼下这段对话，没什么可切的，重新加载一遍只是白闪一下
  if (row.number === props.currentNumber) {
    close();
    return;
  }
  try {
    await projectStore.openConversation(row.number);
    close();
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

.archive-dropdown {
  width: 280px;
  max-height: 360px;
  overflow: auto;
}

.archive-dropdown__section + .archive-dropdown__section {
  border-top: 1px solid var(--line, #e4e9f1);
}

.archive-dropdown__label {
  margin: 0;
  padding: 10px 12px 4px;
  color: var(--faint, #88919e);
  font-size: 12px;
}

.archive-dropdown__empty {
  padding: 12px 12px 20px;
  color: var(--faint, #88919e);
  font-size: 13px;
  text-align: center;
}

.archive-dropdown__list {
  margin: 0;
  padding: 0 0 4px;
  list-style: none;
}

.archive-dropdown__item {
  padding: 8px 12px;
  cursor: pointer;
}

.archive-dropdown__item:hover,
.archive-dropdown__item.is-current {
  background: #edf1ff;
}

.archive-dropdown__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.archive-dropdown__name {
  color: var(--ink, #12141a);
  font-size: 13px;
}

.archive-dropdown__time {
  margin: 4px 0 0;
  color: var(--faint, #88919e);
  font-size: 12px;
}
</style>
