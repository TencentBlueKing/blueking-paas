<template>
  <div class="conversation-menu">
    <bk-popover
      ref="popoverRef"
      trigger="click"
      placement="bottom-end"
      theme="light"
      :arrow="false"
      :padding="0"
      :disabled="disabled"
      ext-cls="conversation-menu-popover"
      @after-show="handleShow"
      @after-hidden="handleHidden"
    >
      <button
        type="button"
        class="conversation-menu__trigger"
        :class="{ 'is-open': visible }"
        :disabled="disabled"
        aria-label="对话"
        v-bk-tooltips="{ content: '对话', placement: 'bottom-end', disabled: visible || disabled }"
      >
        <AppIcon name="messages-square" />
      </button>
      <template #content>
        <div class="conversation-menu__panel" role="menu">
          <button
            type="button"
            class="conversation-menu__item"
            role="menuitem"
            @click="openNewConversation"
          >
            <AppIcon name="square-pen" />
            <span>新建对话</span>
          </button>
          <div
            class="conversation-menu__archive-owner"
            @mouseenter="showArchive()"
            @mouseleave="scheduleArchiveHide"
            @focusin="showArchive()"
            @focusout="scheduleArchiveHide"
          >
            <bk-popover
              trigger="manual"
              placement="right-start"
              theme="light"
              :is-show="archiveVisible"
              :arrow="false"
              :padding="0"
              :offset="4"
              boundary="body"
              ext-cls="conversation-archive-popover"
            >
              <button
                ref="archiveTriggerRef"
                type="button"
                class="conversation-menu__item"
                role="menuitem"
                aria-haspopup="menu"
                :aria-expanded="archiveVisible"
                @click="toggleArchive"
                @keydown.right.prevent="showArchive(true)"
              >
                <AppIcon name="archive" />
                <span>查看归档</span>
                <AppIcon class="conversation-menu__chevron" name="chevron-right" />
              </button>
              <template #content>
                <div
                  ref="archivePanelRef"
                  class="conversation-menu__submenu"
                  role="menu"
                  aria-label="已归档会话"
                  @mouseenter="cancelArchiveHide"
                  @mouseleave="scheduleArchiveHide"
                  @focusin="cancelArchiveHide"
                  @focusout="scheduleArchiveHide"
                  @keydown.left.prevent="closeArchive(true)"
                  @keydown.esc.stop.prevent="closeArchive(true)"
                >
                  <div
                    v-if="loading"
                    class="conversation-menu__status is-loading"
                    role="status"
                  >
                    <span class="conversation-menu__spinner" aria-hidden="true" />
                    加载中…
                  </div>
                  <div v-else-if="archiveError" class="conversation-menu__status is-error">
                    <span>{{ archiveError }}</span>
                    <button type="button" class="conversation-menu__retry" @click="fetchConversations">
                      重试
                    </button>
                  </div>
                  <div
                    v-else-if="!archived.length"
                    class="conversation-menu__status"
                  >
                    暂无已归档会话，当前对话将在新建会话后归档
                  </div>
                  <div v-else class="conversation-menu__archive">
                    <button
                      v-for="row in archived"
                      :key="row.number"
                      type="button"
                      role="menuitem"
                      :class="{ 'is-current': row.number === currentNumber }"
                      :aria-current="row.number === currentNumber ? 'true' : undefined"
                      @click="openConversation(row)"
                    >
                      <span>会话 #{{ row.number }}</span>
                      <time>{{ fromNowFormatter(row.closed_at || row.created_at) }}</time>
                    </button>
                  </div>
                </div>
              </template>
            </bk-popover>
          </div>
        </div>
      </template>
    </bk-popover>

    <AppModal
      v-model="confirmVisible"
      title="确认新建会话？"
      description="新会话会使用全新上下文，当前会话将归档并保留为只读。"
      confirm-text="确认新建"
      @confirm="confirmNewConversation"
    />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue';
import Message from '@/common/message';
import { fromNowFormatter } from '@/common/util';
import AppIcon from '@/components/AppIcon.vue';
import AppModal from '@/components/project/AppModal.vue';
import { usePopoverVisible } from '@/composables/use-popover-visible';
import type { ConversationResponse } from '@/http/types';
import { useProjectStore } from '@/store/project';

const props = defineProps<{
  disabled?: boolean;
  currentNumber: number | null;
}>();

const projectStore = useProjectStore();
const { popoverRef, visible, onAfterShow, onAfterHidden, close } = usePopoverVisible();
const archiveTriggerRef = ref<HTMLButtonElement>();
const archivePanelRef = ref<HTMLElement>();
const archiveVisible = ref(false);
const loading = ref(false);
const confirmVisible = ref(false);
const archived = ref<ConversationResponse[]>([]);
const archiveError = ref('');
let archiveHideTimer = 0;

const fetchConversations = async () => {
  loading.value = true;
  archiveError.value = '';
  try {
    const history = await projectStore.fetchArchivedConversations(1, 20);
    archived.value = history.items || [];
  } catch (error) {
    archiveError.value = error instanceof Error ? error.message : '获取对话归档失败';
  } finally {
    loading.value = false;
  }
};

const handleShow = () => {
  onAfterShow();
  closeArchive();
};

const handleHidden = () => {
  onAfterHidden();
  closeArchive();
};

const cancelArchiveHide = () => {
  window.clearTimeout(archiveHideTimer);
};

const closeArchive = (restoreFocus = false) => {
  cancelArchiveHide();
  archiveVisible.value = false;
  if (restoreFocus) nextTick(() => archiveTriggerRef.value?.focus());
};

const scheduleArchiveHide = () => {
  cancelArchiveHide();
  archiveHideTimer = window.setTimeout(() => closeArchive(), 120);
};

const showArchive = (focusFirst = false) => {
  cancelArchiveHide();
  if (!archiveVisible.value) {
    archiveVisible.value = true;
    fetchConversations();
  }
  if (focusFirst) {
    nextTick(() => archivePanelRef.value?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus());
  }
};

const toggleArchive = () => {
  if (archiveVisible.value) closeArchive();
  else showArchive();
};

const openNewConversation = () => {
  closeArchive();
  close();
  confirmVisible.value = true;
};

const confirmNewConversation = async () => {
  confirmVisible.value = false;
  try {
    await projectStore.startFreshConversation();
  } catch (error) {
    const reason = error instanceof Error ? error.message : '新建会话失败';
    Message({
      theme: 'error',
      message: projectStore.liveNumber == null
        ? `${reason}。原会话已归档，可再次点击新建。`
        : reason,
    });
  }
};

const openConversation = async (row: ConversationResponse) => {
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

onBeforeUnmount(cancelArchiveHide);
</script>

<style lang="postcss" scoped>
.conversation-menu__trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--muted);
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.conversation-menu__trigger:hover:not(:disabled),
.conversation-menu__trigger.is-open {
  color: var(--ink);
  background: #eef1f6;
}

.conversation-menu__trigger:disabled {
  color: #c4c6cc;
  cursor: not-allowed;
}

.conversation-menu :deep(.app-icon) {
  width: 18px;
  height: 18px;
  font-size: 18px;
}

.conversation-menu__panel {
  box-sizing: border-box;
  width: 168px;
  padding: 6px;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 12px 32px rgba(16, 22, 34, 0.14),
    0 0 0 1px rgba(16, 22, 34, 0.05);
}

.conversation-menu__item {
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

.conversation-menu__item:hover,
.conversation-menu__item:focus-visible,
.conversation-menu__item[aria-expanded="true"] {
  background: var(--subtle-bg);
  outline: none;
}

.conversation-menu__item > :deep(.app-icon) {
  flex-shrink: 0;
  width: 15px;
  height: 15px;
  margin-top: 2px;
  color: var(--faint);
  font-size: 15px;
}

.conversation-menu__archive-owner {
  width: 100%;
}

.conversation-menu__archive-owner :deep(.bk-popover) {
  display: block;
  width: 100%;
}

.conversation-menu__chevron {
  flex-shrink: 0;
  margin: 2px -2px 0 auto;
  font-size: 14px;
}

.conversation-menu__submenu {
  box-sizing: border-box;
  width: 264px;
  min-height: 56px;
  max-height: min(420px, calc(100vh - 16px));
  padding: 6px;
  overflow-y: auto;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 12px 32px rgba(16, 22, 34, 0.14),
    0 0 0 1px rgba(16, 22, 34, 0.05);
}

.conversation-menu__archive {
  display: flex;
  flex-direction: column;
}

.conversation-menu__archive button {
  display: flex;
  align-items: baseline;
  gap: 12px;
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

.conversation-menu__archive button:hover,
.conversation-menu__archive button:focus-visible,
.conversation-menu__archive button.is-current {
  background: var(--accent-soft);
  outline: none;
}

.conversation-menu__archive span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-menu__archive time {
  flex-shrink: 0;
  color: var(--faint);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.conversation-menu__status {
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 12px 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.conversation-menu__status.is-loading {
  min-height: 44px;
}

.conversation-menu__status.is-error {
  color: var(--danger);
}

.conversation-menu__spinner {
  display: inline-block;
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: var(--muted);
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: conversation-menu-spin 0.8s linear infinite;
}

.conversation-menu__retry {
  padding: 0;
  color: var(--accent);
  font-size: 13px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

@keyframes conversation-menu-spin {
  to {
    transform: rotate(360deg);
  }
}

.conversation-menu__trigger:focus-visible,
.conversation-menu__panel button:focus-visible,
.conversation-menu__submenu button:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: -2px;
}
</style>

<style lang="postcss">
.conversation-menu-popover,
.conversation-menu-popover.bk-popover,
.conversation-menu-popover .bk-pop2-content,
.conversation-archive-popover,
.conversation-archive-popover.bk-popover,
.conversation-archive-popover .bk-pop2-content {
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
</style>
