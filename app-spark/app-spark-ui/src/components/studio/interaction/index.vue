<template>
  <aside class="interaction-panel">
    <header class="interaction-panel__header">
      <h2>表达意图</h2>
      <bk-tag type="stroke">Chat + 截图</bk-tag>
    </header>
    <div ref="scrollerRef" class="interaction-panel__body">
      <ChatMessageList :messages="messages" :status="status" />
    </div>
    <ChatComposer :disabled="busy" @send="sendMessage" />
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import ChatComposer from './ChatComposer.vue';
import ChatMessageList from './ChatMessageList.vue';
import { useStudioStore } from '@/store/studio';

const studioStore = useStudioStore();
const { messages, status, busy } = storeToRefs(studioStore);
const { sendMessage } = studioStore;
const scrollerRef = ref<HTMLElement>();

watch(messages, async () => {
  await nextTick();
  if (scrollerRef.value) {
    scrollerRef.value.scrollTop = scrollerRef.value.scrollHeight;
  }
}, { deep: true });
</script>

<style lang="postcss" scoped>
.interaction-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  min-width: 320px;
  background: #fff;
  border-right: 1px solid #dcdee5;
}

.interaction-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #dcdee5;
}

.interaction-panel__header h2 {
  margin: 0;
  color: #313238;
  font-size: 14px;
  font-weight: 600;
}

.interaction-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #f5f7fa;
}
</style>
