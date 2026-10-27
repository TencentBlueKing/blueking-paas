<template>
  <aside class="interaction-panel">
    <header class="interaction-panel__header">
      <div class="interaction-panel__title">
        <AppBreadcrumb />
      </div>
      <div class="interaction-panel__actions">
        <ConversationMenu :disabled="busy" :current-number="conversationNumber" />
      </div>
    </header>
    <div
      ref="scrollerRef"
      class="interaction-panel__body"
      @scroll="handleScroll"
    >
      <div v-if="hasEarlierHistory" class="interaction-panel__earlier">
        <bk-button
          text
          theme="primary"
          size="small"
          :loading="loadingEarlier"
          @click="handleLoadEarlier"
        >
          加载更多
        </bk-button>
      </div>
      <ChatMessageList :messages="messages" :status="status" />
    </div>
    <ChatComposer
      v-if="!viewingArchive"
      :disabled="composerDisabled"
      :enable-upload="false"
      :hint="composerHint"
      placeholder="描述你想做的改动"
      @send="sendMessage"
    />
    <div v-else class="interaction-panel__archived" role="status">
      <AppIcon name="archive" />
      <p>
        <strong>已归档会话仅支持查看</strong>
        <span>会话 #{{ conversationNumber }}，不能继续发送消息</span>
      </p>
      <button
        v-if="canReturnToLive"
        type="button"
        :disabled="busy"
        @click="handleReturn"
      >
        返回当前会话
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import Message from '@/common/message';
import AppIcon from '@/components/AppIcon.vue';
import AppBreadcrumb from '@/components/project/header/AppBreadcrumb.vue';
import ChatComposer from './ChatComposer.vue';
import ChatMessageList from './ChatMessageList.vue';
import ConversationMenu from './ConversationMenu.vue';
import { useProjectStore } from '@/store/project';

const projectStore = useProjectStore();
const {
  messages,
  status,
  busy,
  conversationNumber,
  isLive,
  loadingEarlier,
  hasEarlierHistory,
  viewingArchive,
  canReturnToLive,
} = storeToRefs(projectStore);
const { sendMessage } = projectStore;
const scrollerRef = ref<HTMLElement>();
const pinnedToBottom = ref(true);

const composerDisabled = computed(() => (
  busy.value || !isLive.value || !conversationNumber.value
));

const composerHint = computed(() => {
  if (!conversationNumber.value) return '正在准备会话…';
  if (!isLive.value) return '归档会话只能查看，不能发送消息';
  if (busy.value) return '正在回复，完成后可以继续';
  return 'Shift + Enter 换行';
});

const handleScroll = () => {
  const el = scrollerRef.value;
  if (!el) return;
  pinnedToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
};

watch(messages, async () => {
  await nextTick();
  if (pinnedToBottom.value && scrollerRef.value) {
    scrollerRef.value.scrollTop = scrollerRef.value.scrollHeight;
  }
}, { deep: true });

const handleReturn = async () => {
  if (busy.value) return;
  try {
    await projectStore.returnToLiveConversation();
  } catch (error) {
    Message({
      theme: 'error',
      message: error instanceof Error ? error.message : '返回当前会话失败',
    });
  }
};

/**
 * 往前接一页历史，并把视口钉在用户原本在看的那一段上。
 *
 * 新内容接在列表头部，`scrollTop` 不会跟着动，于是原来那一段会整体往下跑掉，看起来像是页面自己
 * 跳了。按「高度长了多少」把 `scrollTop` 补回去，手里这一段就还在原地。
 */
const handleLoadEarlier = async () => {
  const el = scrollerRef.value;
  const before = el?.scrollHeight ?? 0;
  try {
    await projectStore.loadEarlierHistory();
  } catch (error) {
    // 失败的提示由 http 层的全局拦截器给（见 `http/fetch/error-interceptor`），这里只要保证在什么
    // 都没接上的时候别去动滚动位置——那会把用户手里这一段莫名挪走。
    console.error('[project] 历史加载失败', error);
    return;
  }
  await nextTick();
  if (el) el.scrollTop += el.scrollHeight - before;
};
</script>

<style lang="postcss" scoped>
.interaction-panel {
  display: flex;
  flex-direction: column;
  width: 400px;
  min-width: 280px;
  overflow-x: clip;
  background: #fff;
  border-right: 1px solid var(--line, #e4e9f1);
}

.interaction-panel__header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: var(--rail-h, 56px);
  padding: 0 8px;
  background: #fff;
  border-bottom: 1px solid var(--line, #e4e9f1);
}

.interaction-panel__title {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.interaction-panel__actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 2px;
}

.interaction-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.interaction-panel__earlier {
  display: flex;
  justify-content: center;
  padding: 10px 16px 0;
}

.interaction-panel__archived {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  min-height: 88px;
  margin: 12px 16px 16px;
  padding: 14px 16px;
  background: var(--subtle-bg);
  border: 1px dashed #d5dae3;
  border-radius: 16px;
}

.interaction-panel__archived :deep(.app-icon) {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
  color: var(--faint);
  font-size: 18px;
}

.interaction-panel__archived p {
  flex: 1;
  min-width: 0;
  margin: 0;
  line-height: 1.45;
}

.interaction-panel__archived strong,
.interaction-panel__archived span {
  display: block;
}

.interaction-panel__archived strong {
  color: var(--ink);
  font-size: 13px;
}

.interaction-panel__archived span {
  color: var(--faint);
  font-size: 12px;
}

.interaction-panel__archived button {
  flex-shrink: 0;
  padding: 0;
  color: var(--accent);
  font-size: 13px;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.interaction-panel__archived button:disabled {
  color: var(--faint);
  cursor: not-allowed;
}
</style>
