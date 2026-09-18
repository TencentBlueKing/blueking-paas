<template>
  <div class="tool-call" :class="{ 'is-running': isRunning }">
    <span
      v-if="isRunning"
      class="tool-call__dot"
      :class="{ 'is-live': live }"
    />
    <Done v-else class="tool-call__check" />
    <span class="tool-call__label">{{ tool.label }}</span>
    <code v-if="tool.detail" class="tool-call__detail" :title="tool.detail">{{ tool.detail }}</code>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Done } from 'bkui-vue/lib/icon';
import type { ChatToolCall } from './types';

const props = defineProps<{
  tool: ChatToolCall;
  /**
   * 这一轮对话还在进行中。
   *
   * 决定「正在执行」要不要转起来：回放一段被打断的历史时，工具调用会停在 running 上永远等不到
   * 结果，一个转个不停的点会让人以为页面卡住了，而打勾又是撒谎——所以静止的点是对的那一个。
   */
  live?: boolean;
}>();

const isRunning = computed(() => props.tool.state === 'running');
</script>

<style lang="postcss" scoped>
.tool-call {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 6px 0;
  padding: 5px 9px;
  overflow: hidden;
  color: #5a6270;
  font-size: 13px;
  line-height: 1.5;
  background: #f5f7fa;
  border-radius: 8px;
}

.tool-call__label {
  flex-shrink: 0;
  color: #424a57;
}

.tool-call__detail {
  overflow: hidden;
  color: #7a8494;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tool-call__check {
  flex-shrink: 0;
  align-self: center;
  color: #2f5bff;
  font-size: 14px;
}

.tool-call__dot {
  flex-shrink: 0;
  align-self: center;
  width: 7px;
  height: 7px;
  background: #b6bdc9;
  border-radius: 50%;
}

.tool-call__dot.is-live {
  background: #2f5bff;
  animation: tool-call-pulse 1.2s ease-in-out infinite;
}

@keyframes tool-call-pulse {
  0%,
  100% {
    opacity: 0.25;
  }

  50% {
    opacity: 1;
  }
}
</style>
