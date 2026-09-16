<template>
  <aside class="interaction-panel">
    <header class="interaction-panel__header">
      <div class="interaction-panel__title">
        <h2>对话</h2>
        <span
          v-if="conversationNumber"
          class="session-tag"
          :class="{ 'is-live': isLive }"
        >
          会话 #{{ conversationNumber }} · {{ isLive ? '进行中' : '已结束' }}
        </span>
      </div>
      <div class="interaction-panel__actions">
        <span
          class="icon-btn"
          :class="{ 'is-disabled': busy }"
          v-bk-tooltips="{ content: '新建会话', placement: 'top', disabled: busy }"
          @click="handleCreate"
        >
          <Plus class="icon-btn__icon" />
        </span>
        <ConversationHistory :disabled="busy" :current-number="conversationNumber" />
      </div>
    </header>
    <div
      ref="scrollerRef"
      class="interaction-panel__body"
      @scroll="handleScroll"
    >
      <p
        v-if="!isLive && conversationNumber"
        class="interaction-panel__note"
      >
        这是已结束的会话，只能查看。新建会话后可以继续对话。
      </p>
      <ChatMessageList :messages="messages" :status="status" />
    </div>
    <ChatComposer
      :disabled="composerDisabled"
      :enable-upload="false"
      :hint="composerHint"
      placeholder="描述你想做的改动"
      @send="sendMessage"
    />
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { Message } from 'bkui-vue';
import { Plus } from 'bkui-vue/lib/icon';
import ChatComposer from './ChatComposer.vue';
import ChatMessageList from './ChatMessageList.vue';
import ConversationHistory from './ConversationHistory.vue';
import { useProjectStore } from '@/store/project';

const projectStore = useProjectStore();
const { messages, status, busy, conversationNumber, isLive } = storeToRefs(projectStore);
const { sendMessage } = projectStore;
const scrollerRef = ref<HTMLElement>();
const pinnedToBottom = ref(true);

const composerDisabled = computed(() => (
  busy.value || !isLive.value || !conversationNumber.value
));

const composerHint = computed(() => {
  if (!conversationNumber.value) return '正在准备会话…';
  if (!isLive.value) return '历史会话只能查看';
  if (busy.value) return '正在回复，完成后可以继续';
  return 'Enter 发送，Shift + Enter 换行';
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

const handleCreate = async () => {
  if (busy.value) return;
  try {
    await projectStore.createNewConversation();
    // Message({ theme: 'success', message: '已新建会话' });
  } catch {
    // Message({
    //   theme: 'error',
    //   message: '新建会话失败',
    // });
  }
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
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid var(--line, #e4e9f1);
}

.interaction-panel__title {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.interaction-panel__header h2 {
  margin: 0;
  color: var(--ink, #12141a);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.session-tag {
  overflow: hidden;
  color: var(--faint, #88919e);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-tag.is-live {
  color: #3d8f6a;
}

.interaction-panel__actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 2px;
}

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

.interaction-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.interaction-panel__note {
  margin: 12px 16px 0;
  padding: 10px 12px;
  color: var(--muted, #5c6573);
  font-size: 13px;
  line-height: 1.5;
  background: var(--accent-soft, #edf1ff);
  border-radius: 12px;
}
</style>
