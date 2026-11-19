<template>
  <div
    class="chat-composer"
    :class="{ 'is-disabled': disabled }"
    @paste="handlePaste"
    @dragover.prevent
    @drop.prevent="handleDrop"
  >
    <div v-if="attachments.length" class="chat-composer__previews">
      <div
        v-for="attachment in attachments"
        :key="attachment.localId"
        class="chat-composer__preview"
        :class="[`is-${attachment.status}`, `is-${attachment.kind}`]"
      >
        <button
          v-if="attachment.kind === 'image' && attachment.preview"
          type="button"
          class="chat-composer__image-trigger"
          :aria-label="`放大预览 ${attachment.name || '图片附件'}`"
          @click="previewImage = {
            src: attachment.preview,
            alt: attachment.name || '图片附件',
          }"
        >
          <img
            :src="attachment.preview"
            :alt="attachment.name || '图片附件'"
          >
        </button>
        <div
          v-else-if="attachment.kind === 'image'"
          class="chat-composer__image-placeholder"
          aria-hidden="true"
        />
        <div v-else class="chat-composer__file-preview">
          <AppIcon name="file" />
          <span :title="attachment.name">{{ attachment.name }}</span>
          <small>{{ formatAttachmentSize(attachment.size) }}</small>
        </div>
        <span
          v-if="attachment.status === 'queued' || attachment.status === 'uploading'"
          class="chat-composer__upload-state"
          role="status"
        >
          <i aria-hidden="true" />
          上传中
        </span>
        <button
          v-else-if="attachment.status === 'failed'"
          type="button"
          class="chat-composer__retry"
          :disabled="disabled"
          :title="attachment.errorMessage || '上传失败，点击重试'"
          aria-label="重试上传附件"
          @click="retryAttachment(attachment.localId)"
        >
          <AppIcon name="rotate-cw" />
          重试
        </button>
        <button
          type="button"
          class="chat-composer__remove"
          :disabled="disabled"
          aria-label="移除附件"
          @click="removeAttachment(attachment.localId)"
        >
          <AppIcon name="x" />
        </button>
      </div>
    </div>
    <div class="chat-composer__box">
      <textarea
        ref="inputRef"
        v-model="draft"
        class="chat-composer__input"
        rows="2"
        :disabled="disabled"
        :placeholder="placeholder"
        @input="resizeInput"
        @keydown="handleKeydown"
      />
      <div class="chat-composer__bar">
        <input
          v-if="enableUpload"
          ref="fileRef"
          class="chat-composer__file"
          type="file"
          multiple
          :disabled="disabled || attachmentLimitReached"
          @change="handleFileChange"
        >
        <span
          class="composer__tool-wrap"
          v-bk-tooltips="{
            content: attachmentToolHint,
            placement: 'top',
            disabled: !attachmentToolHint,
          }"
        >
          <button
            type="button"
            class="composer__tool"
            :class="{ 'is-inert': !enableUpload || attachmentLimitReached }"
            :disabled="disabled || attachmentLimitReached"
            :aria-disabled="!enableUpload || attachmentLimitReached"
            aria-label="添加附件"
            @click="openFile"
          >
            <AppIcon name="plus-line" />
          </button>
        </span>
        <ModelSelector placement="top-start" />
        <span
          class="composer__send-wrap"
          v-bk-tooltips="{
            content: sendTooltip,
            placement: 'top',
            disabled: !sendTooltip || running,
          }"
        >
          <button
            v-if="running"
            type="button"
            class="composer__send composer__send--stop"
            :disabled="!canStop"
            aria-label="停止"
            title="停止"
            @click="handleStop"
          >
            <AppIcon name="square" />
          </button>
          <button
            v-else
            type="button"
            class="composer__send"
            :disabled="disabled || !canSend"
            aria-label="发送"
            @click="handleSend"
          >
            <AppIcon name="arrow-up" />
          </button>
        </span>
      </div>
    </div>
    <ImageLightbox
      :open="Boolean(previewImage)"
      :src="previewImage?.src || ''"
      :alt="previewImage?.alt"
      @close="previewImage = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import AppIcon from '@/components/AppIcon.vue';
import ModelSelector from '@/components/model/ModelSelector.vue';
import { useModelCatalogStore } from '@/store/model-catalog';
import { useProjectStore } from '@/store/project';
import {
  formatAttachmentSize,
  MAX_ATTACHMENT_COUNT,
  selectSendableAttachments,
} from './attachment';
import ImageLightbox from './ImageLightbox.vue';
import type { ChatAttachment, ChatSendLifecycle } from './types';
import { useMessageAttachments } from './use-message-attachments';

const props = defineProps<{
  disabled?: boolean;
  enableUpload?: boolean;
  hint?: string;
  placeholder?: string;
  /** 有一轮正在跑：发送按钮换成停止按钮。与 `disabled` 无关，输入框锁着时也要能停。 */
  running?: boolean;
  canStop?: boolean;
}>();

const enableUpload = computed(() => props.enableUpload !== false);

const emit = defineEmits<{
  (
    e: 'send',
    value: string,
    attachments: ChatAttachment[],
    modelId?: string,
    lifecycle?: ChatSendLifecycle,
  ): void;
  (e: 'stop'): void;
}>();

const modelCatalogStore = useModelCatalogStore();
const projectStore = useProjectStore();
const { projectId, conversationNumber } = storeToRefs(projectStore);
const {
  attachments,
  attachmentLimitReached,
  hasPendingAttachments,
  hasFailedAttachments,
  readyAttachments,
  addFiles: queueFiles,
  retryAttachment,
  removeAttachment,
  removeSubmittedAttachments,
  restoreSubmittedAttachments,
} = useMessageAttachments({ projectId, conversationNumber });
const INPUT_LINE_HEIGHT = 22;
const INPUT_MIN_HEIGHT = INPUT_LINE_HEIGHT * 2;
const INPUT_MAX_HEIGHT = 300;

const draft = ref('');
const fileRef = ref<HTMLInputElement>();
const inputRef = ref<HTMLTextAreaElement>();
const rejectedVisionModelId = ref('');
const previewImage = ref<{ src: string; alt: string } | null>(null);

const resizeInput = () => {
  const el = inputRef.value;
  if (!el) return;
  el.style.height = 'auto';
  const next = Math.min(Math.max(el.scrollHeight, INPUT_MIN_HEIGHT), INPUT_MAX_HEIGHT);
  el.style.height = `${next}px`;
  el.style.overflowY = el.scrollHeight > INPUT_MAX_HEIGHT ? 'auto' : 'hidden';
};

onMounted(resizeInput);
const effectiveImageModelId = computed(() => (
  modelCatalogStore.imageInputModel?.id || '__default__'
));
const canSubmitImages = computed(() => (
  modelCatalogStore.supportsImageInput
  && rejectedVisionModelId.value !== effectiveImageModelId.value
));
const hasBlockedImages = computed(() => (
  attachments.value.some(attachment => attachment.kind === 'image')
  && !canSubmitImages.value
));
const sendableAttachments = computed(() => (
  selectSendableAttachments(readyAttachments.value, canSubmitImages.value)
));
const canSend = computed(() => (
  Boolean(draft.value.trim() || sendableAttachments.value.length)
  && !hasPendingAttachments.value
  && !hasFailedAttachments.value
));
const sendTooltip = computed(() => (
  hasBlockedImages.value && !draft.value.trim() && !sendableAttachments.value.length
    ? '当前模型不支持图片输入'
    : ''
));
const placeholder = computed(() => (
  props.placeholder
  || (enableUpload.value ? '描述你想要的改动，或添加附件后发送' : '描述你想做的改动')
));
const attachmentToolHint = computed(() => {
  if (!enableUpload.value) return '暂不支持添加附件';
  if (attachmentLimitReached.value) return `一次最多上传 ${MAX_ATTACHMENT_COUNT} 个附件`;
  return '';
});
const openFile = () => {
  if (props.disabled || !enableUpload.value || attachmentLimitReached.value) return;
  fileRef.value?.click();
};

const addFiles = (files: File[]) => {
  if (props.disabled) return;
  if (!files.length) return;
  queueFiles(files);
};

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  addFiles(Array.from(input.files || []));
  input.value = '';
};

const handlePaste = (event: ClipboardEvent) => {
  if (!enableUpload.value || props.disabled) return;
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.kind === 'file')
    .map(item => item.getAsFile())
    .filter((file): file is File => Boolean(file));
  if (!files.length) return;
  event.preventDefault();
  addFiles(files);
};

const handleDrop = (event: DragEvent) => {
  if (!enableUpload.value || props.disabled) return;
  addFiles(Array.from(event.dataTransfer?.files || []));
};

const handleSend = () => {
  if (props.disabled || !canSend.value) return;
  const submittedDraft = draft.value.trim();
  const submittedAttachments = [...sendableAttachments.value];
  const attachmentIds = submittedAttachments
    .map(attachment => attachment.attachmentId)
    .filter((id): id is string => Boolean(id));
  const originalAttachmentOrder = attachments.value.map(attachment => attachment.localId);
  const submittedProjectId = projectId.value;
  const submittedNumber = conversationNumber.value;
  const submittedImageModelId = effectiveImageModelId.value;
  const stillSameConversation = () => (
    projectId.value === submittedProjectId
    && conversationNumber.value === submittedNumber
  );
  const lifecycle: ChatSendLifecycle = {
    onRejected: () => {
      if (!stillSameConversation()) return;
      draft.value = submittedDraft;
      restoreSubmittedAttachments(submittedAttachments, originalAttachmentOrder);
      void nextTick(resizeInput);
    },
    onAttachmentsInvalid: (invalidIds) => {
      if (stillSameConversation()) removeSubmittedAttachments(invalidIds);
    },
    onImageInputUnsupported: () => {
      if (stillSameConversation()) {
        rejectedVisionModelId.value = submittedImageModelId;
      }
    },
  };

  // 已进入本轮发送范围的内容立即移出草稿；非多模态模型下被排除的图片继续保留。
  draft.value = '';
  removeSubmittedAttachments(attachmentIds);
  void nextTick(resizeInput);
  emit(
    'send',
    submittedDraft,
    submittedAttachments,
    modelCatalogStore.requestModelId,
    lifecycle,
  );
};

const handleStop = () => {
  if (props.canStop) emit('stop');
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  handleSend();
};
</script>

<style lang="postcss" scoped>
.chat-composer {
  box-sizing: border-box;
  flex-shrink: 0;
  width: 100%;
  min-width: 0;
  padding: 12px 16px 16px;
}

.chat-composer__box {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line, #e4e9f1);
  border-radius: 16px;
}

.chat-composer.is-disabled .chat-composer__box {
  background: #fafbfc;
}

.chat-composer__previews {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.chat-composer__preview {
  position: relative;
  width: 72px;
  height: 72px;
  overflow: visible;
  background: #f5f7fa;
  border: 1px solid var(--line, #e4e9f1);
  border-radius: 8px;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.chat-composer__preview.is-file,
.chat-composer__preview.is-pending {
  width: 150px;
}

.chat-composer__image-trigger {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow: hidden;
  background: transparent;
  border: 0;
  border-radius: inherit;
  cursor: zoom-in;
}

.chat-composer__image-trigger:focus-visible {
  outline: 2px solid var(--accent-focus, #8ea2ff);
  outline-offset: 2px;
}

.chat-composer__image-trigger img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: filter 0.15s ease;
}

.chat-composer__image-trigger:hover img {
  filter: brightness(0.94);
}

.chat-composer__preview.is-file:hover,
.chat-composer__preview.is-pending:hover {
  background: #eef1f6;
  border-color: #c9ced8;
}

.chat-composer__image-placeholder {
  width: 100%;
  height: 100%;
  background: #eef1f6;
  border-radius: inherit;
}

.chat-composer__preview.is-failed {
  border-color: #ea6f6f;
}

.chat-composer__file-preview {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  grid-template-rows: 20px 18px;
  align-content: center;
  width: 100%;
  height: 100%;
  padding: 8px 24px 8px 10px;
  color: var(--muted, #5c6573);
}

.chat-composer__file-preview :deep(.app-icon) {
  grid-row: 1 / 3;
  align-self: center;
  width: 20px;
  height: 20px;
  color: var(--accent, #3d6dff);
  font-size: 20px;
}

.chat-composer__file-preview span {
  overflow: hidden;
  color: var(--ink, #12141a);
  font-size: 12px;
  line-height: 20px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.chat-composer__file-preview small {
  color: var(--faint, #88919e);
  font-size: 11px;
  line-height: 18px;
}

.chat-composer__preview.is-uploading .chat-composer__file-preview,
.chat-composer__preview.is-queued .chat-composer__file-preview {
  padding-bottom: 24px;
}

.chat-composer__preview.is-pending {
  width: 100%;
  max-width: 150px;
}

.chat-composer__upload-state,
.chat-composer__retry {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 24px;
  color: #fff;
  font-size: 11px;
  background: rgba(18, 20, 26, 0.62);
  border-radius: 0 0 7px 7px;
}

.chat-composer__upload-state i {
  width: 10px;
  height: 10px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: attachment-upload-spin 0.8s linear infinite;
}

.chat-composer__retry {
  padding: 0;
  border: 0;
  cursor: pointer;
}

.chat-composer__retry :deep(.app-icon) {
  width: 12px;
  height: 12px;
  font-size: 12px;
}

.chat-composer__remove {
  position: absolute;
  z-index: 1;
  top: -8px;
  right: -8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  color: #fff;
  background: #c4c6cc;
  border: 0;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(18, 20, 26, 0.16);
  cursor: pointer;
}

.chat-composer__remove:hover:not(:disabled) {
  background: #979ba5;
}

.chat-composer__remove :deep(.app-icon) {
  width: 12px;
  height: 12px;
  font-size: 12px;
}

.chat-composer__remove:disabled,
.chat-composer__retry:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.chat-composer__input {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  max-height: 300px;
  padding: 12px 14px 4px;
  overflow-y: hidden;
  color: var(--ink, #12141a);
  font-size: 14px;
  line-height: 22px;
  resize: none;
  background: transparent;
  border: 0;
  caret-color: var(--accent, #3d6dff);
}

.chat-composer__input::placeholder {
  color: var(--faint, #88919e);
}

.chat-composer__input:focus,
.chat-composer__input:focus-visible {
  outline: none;
  box-shadow: none;
}

.chat-composer__box:focus-within {
  border-color: #8ea2ff;
}

.chat-composer__bar {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px 10px 10px;
}

.composer__tool,
.composer__send {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
}

.composer__tool-wrap {
  display: inline-flex;
}

.composer__tool {
  height: 32px;
  color: var(--muted, #5c6573);
  background: transparent;
  border-radius: 10px;
}

.composer__tool {
  width: 32px;
  padding: 0;
  border: 1px solid var(--line);
}

.composer__tool :deep(.app-icon) {
  font-size: 16px;
}

.is-inert {
  cursor: not-allowed;
  opacity: 0.5;
}

.composer__send {
  width: 32px;
  height: 32px;
  margin-left: 0;
  padding: 0;
  color: #fff;
  background: var(--accent);
  border-radius: 10px;
  cursor: pointer;
}

.composer__send-wrap {
  display: inline-flex;
  margin-left: auto;
}

.composer__send :deep(.app-icon) {
  font-size: 16px;
}

.composer__send:hover:not(:disabled) {
  background: #1f46d6;
}

.composer__send:disabled {
  background: #c9d3e6;
  cursor: not-allowed;
}

.composer__send--stop :deep(.app-icon) {
  font-size: 12px;
}

.composer__send--stop :deep(svg) {
  fill: currentColor;
}

.composer__send:focus-visible,
.composer__tool:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.chat-composer__file {
  display: none;
}

@keyframes attachment-upload-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-composer__preview,
  .chat-composer__image-trigger img {
    transition: none;
  }

  .chat-composer__upload-state i {
    animation: none;
  }
}
</style>
