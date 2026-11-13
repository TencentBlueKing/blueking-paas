<template>
  <div
    class="chat-composer"
    :class="{ 'is-disabled': disabled }"
    @paste="handlePaste"
    @dragover.prevent
    @drop.prevent="handleDrop"
  >
    <div v-if="images.length" class="chat-composer__previews">
      <div
        v-for="image in images"
        :key="image.localId"
        class="chat-composer__preview"
        :class="`is-${image.status}`"
      >
        <img v-if="image.preview" :src="image.preview" :alt="image.name || '设计稿'">
        <div v-else class="chat-composer__preview-placeholder" aria-hidden="true" />
        <span
          v-if="image.status === 'processing' || image.status === 'uploading'"
          class="chat-composer__upload-state"
          role="status"
        >
          <i aria-hidden="true" />
          上传中
        </span>
        <button
          v-else-if="image.status === 'failed'"
          type="button"
          class="chat-composer__retry"
          :disabled="disabled"
          :title="image.errorMessage || '上传失败，点击重试'"
          aria-label="重试上传图片"
          @click="retryImage(image.localId)"
        >
          <AppIcon name="rotate-cw" />
          重试
        </button>
        <button
          type="button"
          class="chat-composer__remove"
          :disabled="disabled"
          aria-label="移除图片"
          @click="removeImage(image.localId)"
        >
          <Close />
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
          accept="image/png,image/jpeg,.jpg,.jpeg,image/webp"
          multiple
          @change="handleFileChange"
        >
        <button
          type="button"
          class="composer__tool"
          :class="{ 'is-inert': !enableUpload }"
          :disabled="disabled"
          :aria-disabled="!enableUpload"
          :title="enableUpload ? '上传设计稿或截图' : '暂不支持添加附件'"
          @click="enableUpload && openFile()"
        >
          <AppIcon name="plus-line" />
        </button>
        <ModelSelector placement="top-start" />
        <span
          class="composer__send-wrap"
          v-bk-tooltips="{
            content: sendTooltip,
            placement: 'top',
            disabled: !sendTooltip,
          }"
        >
          <button
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
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { Close } from 'bkui-vue/lib/icon';
import AppIcon from '@/components/AppIcon.vue';
import ModelSelector from '@/components/model/ModelSelector.vue';
import { useModelCatalogStore } from '@/store/model-catalog';
import { useProjectStore } from '@/store/project';
import type { ChatImage, ChatSendLifecycle } from './types';
import { useMessageAttachments } from './use-message-attachments';

const props = defineProps<{
  disabled?: boolean;
  enableUpload?: boolean;
  hint?: string;
  placeholder?: string;
}>();

const enableUpload = computed(() => props.enableUpload !== false);

const emit = defineEmits<{
  (
    e: 'send',
    value: string,
    images: ChatImage[],
    modelId?: string,
    lifecycle?: ChatSendLifecycle,
  ): void;
}>();

const modelCatalogStore = useModelCatalogStore();
const projectStore = useProjectStore();
const { projectId, conversationNumber } = storeToRefs(projectStore);
const {
  images,
  hasPendingImages,
  hasFailedImages,
  readyImages,
  addFiles: queueFiles,
  retryImage,
  removeImage,
  removeSubmittedImages,
} = useMessageAttachments({ projectId, conversationNumber });
const INPUT_LINE_HEIGHT = 22;
const INPUT_MIN_HEIGHT = INPUT_LINE_HEIGHT * 2;
const INPUT_MAX_HEIGHT = 300;

const draft = ref('');
const fileRef = ref<HTMLInputElement>();
const inputRef = ref<HTMLTextAreaElement>();
const rejectedVisionModelId = ref('');

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
const visionBlocked = computed(() => (
  images.value.length > 0
  && (
    !modelCatalogStore.supportsImageInput
    || rejectedVisionModelId.value === effectiveImageModelId.value
  )
));
const canSend = computed(() => (
  Boolean(draft.value.trim() || images.value.length)
  && !hasPendingImages.value
  && !hasFailedImages.value
  && !visionBlocked.value
));
const sendTooltip = computed(() => (
  visionBlocked.value ? '当前模型不支持图片输入' : ''
));
const placeholder = computed(() => (
  props.placeholder
  || (enableUpload.value ? '描述你想要的改动，或上传设计稿 / 截图后发送' : '描述你想做的改动')
));
const openFile = () => {
  if (props.disabled) return;
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
  const submittedImages = [...readyImages.value];
  const attachmentIds = submittedImages
    .map(image => image.attachmentId)
    .filter((id): id is string => Boolean(id));
  const submittedProjectId = projectId.value;
  const submittedNumber = conversationNumber.value;
  const submittedImageModelId = effectiveImageModelId.value;
  const stillSameConversation = () => (
    projectId.value === submittedProjectId
    && conversationNumber.value === submittedNumber
  );
  const lifecycle: ChatSendLifecycle = {
    onAccepted: () => {
      if (!stillSameConversation()) return;
      draft.value = '';
      removeSubmittedImages(attachmentIds);
      void nextTick(resizeInput);
    },
    onAttachmentsInvalid: (invalidIds) => {
      if (stillSameConversation()) removeSubmittedImages(invalidIds);
    },
    onImageInputUnsupported: () => {
      if (stillSameConversation()) {
        rejectedVisionModelId.value = submittedImageModelId;
      }
    },
  };
  emit(
    'send',
    draft.value.trim(),
    submittedImages,
    modelCatalogStore.requestModelId,
    lifecycle,
  );
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
  overflow: hidden;
  background: #f5f7fa;
  border: 1px solid var(--line, #e4e9f1);
  border-radius: 8px;
}

.chat-composer__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-composer__preview.is-failed {
  border-color: #ea6f6f;
}

.chat-composer__preview-placeholder {
  width: 100%;
  height: 100%;
  background: #eef1f6;
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
}

.chat-composer__upload-state i {
  width: 10px;
  height: 10px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: image-upload-spin 0.8s linear infinite;
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
  top: 0;
  right: 0;
  display: inline-flex;
  padding: 2px;
  color: #fff;
  background: rgba(18, 20, 26, 0.5);
  border: 0;
  border-radius: 0 0 0 8px;
  cursor: pointer;
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

.composer__send:focus-visible,
.composer__tool:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.chat-composer__file {
  display: none;
}

@keyframes image-upload-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-composer__upload-state i {
    animation: none;
  }
}
</style>
