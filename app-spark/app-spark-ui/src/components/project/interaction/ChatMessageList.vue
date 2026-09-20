<template>
  <div class="chat-message-list">
    <div v-if="isFresh" class="chat-empty">
      <h3>描述你的需求</h3>
      <ul class="chat-empty__samples">
        <li>“开发一个番茄钟小工具，使用活泼的配色风格。”</li>
        <li>“开发一个抽奖小工具，可录入抽奖名单，奖品固定为一台 Switch 2。”</li>
        <li>……</li>
      </ul>
    </div>

    <article
      v-for="message in visibleMessages"
      :key="message.id"
      :class="[
        'chat-message',
        `chat-message--${message.role}`,
        { 'is-error': message.tone === 'error' },
      ]"
    >
      <template v-for="(block, index) in message.blocks" :key="index">
        <div
          v-if="block.type === 'text' && block.text && message.role === 'assistant'"
          class="chat-message__markdown"
          v-html="renderMarkdown(block.text)"
        />
        <p v-else-if="block.type === 'text' && block.text" class="chat-message__text">
          {{ block.text }}
        </p>
        <ToolCallBlock
          v-else-if="block.type === 'tool' && block.tool"
          :tool="block.tool"
          :live="status !== 'idle'"
        />
        <img
          v-else-if="block.type === 'image' && block.src"
          class="chat-message__thumb"
          :src="block.src"
          alt=""
        >
        <ul v-else-if="block.type === 'summary'" class="chat-message__summary">
          <li v-for="item in block.items" :key="item">
            <Done class="chat-message__icon" />
            {{ item }}
          </li>
        </ul>
      </template>
      <p
        v-if="pendingText(message)"
        class="chat-message__thinking"
      >
        {{ pendingText(message) }}
      </p>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Done } from 'bkui-vue/lib/icon';
import type { ProjectStatus } from '@/store/project';
import ToolCallBlock from './ToolCallBlock.vue';
import { renderMarkdown } from './render-markdown';
import type { ChatBlock, ChatMessage } from './types';

const props = defineProps<{
  messages: ChatMessage[];
  status?: ProjectStatus;
}>();

const hasContent = (block: ChatBlock) => Boolean(
  block.text || block.src || block.items?.length || block.tool,
);

const visibleMessages = computed(() => (
  props.messages.filter(message => message.id !== 'welcome')
));

const isFresh = computed(() => (
  !visibleMessages.value.some(message => (
    message.role === 'user' || message.blocks.some(hasContent)
  ))
));

/**
 * 助手消息末尾那行灰字，没有就返回空串。
 *
 * 一条空的助手消息是「已经发出去、还没等到第一个字」的样子，这时候必须说点什么，否则界面看着
 * 像没反应；已经有内容之后就只报 STEP_STARTED 之类带来的进度，没有进度就什么都不加。
 */
const pendingText = (message: ChatMessage) => {
  if (message.role !== 'assistant' || props.status === 'idle') return '';
  if (message.progress) return message.progress;
  return message.blocks.some(hasContent) ? '' : '正在生成…';
};
</script>

<style lang="postcss" scoped>
.chat-message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px 16px 24px;
}

.chat-empty {
  max-width: 22em;
  padding: 4px 4px 8px;
}

.chat-empty h3 {
  margin: 0 0 6px;
  color: #6f7886;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.chat-empty__samples {
  margin: 0;
  padding-left: 1.2em;
}

.chat-empty__samples li {
  color: #8b93a0;
  font-size: 13px;
  line-height: 1.6;
}

.chat-message {
  max-width: 92%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.65;
  border-radius: 14px;
}

.chat-message--user {
  align-self: flex-end;
  color: #1a2744;
  background: var(--accent-soft, #edf1ff);
  border-bottom-right-radius: 6px;
}

.chat-message--assistant {
  align-self: flex-start;
  color: var(--ink, #12141a);
  background: var(--surface, #fff);
  border-bottom-left-radius: 6px;
  box-shadow: 0 10px 24px rgba(18, 28, 48, 0.05);
}

.chat-message--assistant.is-error {
  color: #8a2b2b;
  background: #fff6f6;
  border-color: #f0d0d0;
}

.chat-message__text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-message__markdown {
  word-break: break-word;
}

.chat-message__markdown :deep(> *:first-child) {
  margin-top: 0;
}

.chat-message__markdown :deep(> *:last-child) {
  margin-bottom: 0;
}

.chat-message__markdown :deep(p),
.chat-message__markdown :deep(ul),
.chat-message__markdown :deep(ol),
.chat-message__markdown :deep(pre),
.chat-message__markdown :deep(blockquote) {
  margin: 0 0 8px;
}

.chat-message__markdown :deep(h1),
.chat-message__markdown :deep(h2),
.chat-message__markdown :deep(h3),
.chat-message__markdown :deep(h4) {
  margin: 0 0 8px;
  color: inherit;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.chat-message__markdown :deep(ul),
.chat-message__markdown :deep(ol) {
  padding-left: 18px;
}

.chat-message__markdown :deep(li + li) {
  margin-top: 4px;
}

.chat-message__markdown :deep(a) {
  color: var(--accent, #3d6dff);
  text-decoration: none;
}

.chat-message__markdown :deep(code) {
  padding: 1px 4px;
  color: #c41d7f;
  background: #f3f5f8;
  border-radius: 3px;
}

.chat-message__markdown :deep(pre) {
  padding: 8px 10px;
  overflow: auto;
  background: #f5f7fa;
  border-radius: 8px;
}

.chat-message__markdown :deep(pre code) {
  padding: 0;
  color: #1d2026;
  background: transparent;
}

.chat-message__markdown :deep(blockquote) {
  padding-left: 8px;
  color: #5a6270;
  border-left: 3px solid #e4e8ef;
}

.chat-message__thinking {
  margin: 8px 0 0;
  color: #7a8494;
  font-size: 13px;
}

.chat-message__thumb {
  display: block;
  max-width: 100%;
  max-height: 160px;
  margin-top: 8px;
  object-fit: cover;
  background: #f5f7fa;
  border: 1px solid #e4e8ef;
  border-radius: 8px;
}

.chat-message__summary {
  margin: 4px 0 0;
  padding: 0;
}

.chat-message__summary li {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 6px;
}

.chat-message__icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #2f5bff;
  font-size: 14px;
}
</style>
