<template>
  <div class="chat-message-list">
    <div
      v-for="message in messages"
      :key="message.id"
      :class="['chat-message', `chat-message--${message.role}`]"
    >
      <template v-for="(block, index) in message.blocks" :key="index">
        <div
          v-if="block.type === 'text' && block.text && message.role === 'assistant'"
          class="chat-message__markdown"
          v-html="renderMarkdown(block.text)"
        />
        <p v-else-if="block.type === 'text'" class="chat-message__text">
          <template v-if="block.text">{{ block.text }}</template>
          <span v-else-if="status !== 'idle'" class="chat-message__thinking">
            {{ message.progress || '正在生成…' }}
          </span>
        </p>
        <img
          v-else-if="block.type === 'image' && block.src"
          class="chat-message__thumb"
          :src="block.src"
          alt="上传的设计稿"
        >
        <ul v-else-if="block.type === 'summary'" class="chat-message__summary">
          <li v-for="item in block.items" :key="item">
            <Done class="chat-message__icon" />
            {{ item }}
          </li>
        </ul>
        <p
          v-if="block.type === 'text' && block.text && message.progress && status !== 'idle'"
          class="chat-message__thinking"
        >
          {{ message.progress }}
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Done } from 'bkui-vue/lib/icon';
import type { StudioStatus } from '@/store/studio';
import { renderMarkdown } from './render-markdown';
import type { ChatMessage } from './types';

defineProps<{
  messages: ChatMessage[];
  status?: StudioStatus;
}>();
</script>

<style lang="postcss" scoped>
.chat-message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.chat-message {
  max-width: 92%;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.6;
  border-radius: 8px;
}

.chat-message--user {
  align-self: flex-start;
  color: #313238;
  background: #f0f1f5;
}

.chat-message--assistant {
  align-self: stretch;
  color: #313238;
  background: #fff;
  border: 1px solid #dcdee5;
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
  color: #313238;
  font-size: 13px;
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
  color: #3a84ff;
  text-decoration: none;
}

.chat-message__markdown :deep(code) {
  padding: 1px 4px;
  color: #c41d7f;
  background: #f0f1f5;
  border-radius: 3px;
}

.chat-message__markdown :deep(pre) {
  padding: 8px 10px;
  overflow: auto;
  background: #f5f7fa;
  border-radius: 6px;
}

.chat-message__markdown :deep(pre code) {
  padding: 0;
  color: #313238;
  background: transparent;
}

.chat-message__markdown :deep(blockquote) {
  padding-left: 8px;
  color: #63656e;
  border-left: 3px solid #dcdee5;
}

.chat-message__thinking {
  color: #979ba5;
}

.chat-message__thumb {
  display: block;
  max-width: 100%;
  max-height: 160px;
  margin-top: 8px;
  object-fit: cover;
  background: #f5f7fa;
  border: 1px solid #dcdee5;
  border-radius: 6px;
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
  color: #3a84ff;
  font-size: 14px;
}
</style>
