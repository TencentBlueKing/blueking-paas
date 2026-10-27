<template>
  <div
    class="chat-composer"
    :class="{ 'is-disabled': disabled }"
    @paste="handlePaste"
    @dragover.prevent
    @drop.prevent="handleDrop"
  >
    <div v-if="images.length" class="chat-composer__previews">
      <div v-for="(image, index) in images" :key="`${image.name}-${index}`" class="chat-composer__preview">
        <img :src="image.preview" :alt="image.name || '设计稿'">
        <button
          type="button"
          class="chat-composer__remove"
          :disabled="disabled"
          @click="images.splice(index, 1)"
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
          accept="image/png,image/jpeg,image/webp,image/gif"
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
        <button
          type="button"
          class="composer__model is-inert"
          aria-disabled="true"
          title="暂不支持切换模型"
        >
          DeepSeek v4.1 flash
          <AppIcon name="chevron-down" />
        </button>
        <button
          type="button"
          class="composer__send"
          :disabled="disabled || !canSend"
          aria-label="发送"
          @click="handleSend"
        >
          <AppIcon name="arrow-up" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import Message from '@/common/message';
import { Close } from 'bkui-vue/lib/icon';
import AppIcon from '@/components/AppIcon.vue';
import { appendImages } from './read-image';
import type { ChatImage } from './types';

const props = defineProps<{
  disabled?: boolean;
  enableUpload?: boolean;
  hint?: string;
  placeholder?: string;
}>();

const enableUpload = computed(() => props.enableUpload !== false);

const emit = defineEmits<{
  (e: 'send', value: string, images: ChatImage[]): void;
}>();

const INPUT_LINE_HEIGHT = 22;
const INPUT_MIN_HEIGHT = INPUT_LINE_HEIGHT * 2;
const INPUT_MAX_HEIGHT = 300;

const draft = ref('');
const images = ref<ChatImage[]>([]);
const fileRef = ref<HTMLInputElement>();
const inputRef = ref<HTMLTextAreaElement>();

const resizeInput = () => {
  const el = inputRef.value;
  if (!el) return;
  el.style.height = 'auto';
  const next = Math.min(Math.max(el.scrollHeight, INPUT_MIN_HEIGHT), INPUT_MAX_HEIGHT);
  el.style.height = `${next}px`;
  el.style.overflowY = el.scrollHeight > INPUT_MAX_HEIGHT ? 'auto' : 'hidden';
};

onMounted(resizeInput);
const canSend = computed(() => Boolean(draft.value.trim() || images.value.length));
const placeholder = computed(() => (
  props.placeholder
  || (enableUpload.value ? '描述你想要的改动，或上传设计稿 / 截图后发送' : '描述你想做的改动')
));
const openFile = () => {
  fileRef.value?.click();
};

const addFiles = async (files: File[]) => {
  if (!files.length) return;
  try {
    images.value = await appendImages(images.value, files);
  } catch (error) {
    Message({
      theme: 'warning',
      message: error instanceof Error ? error.message : '图片添加失败',
    });
  }
};

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  await addFiles(Array.from(input.files || []));
  input.value = '';
};

const handlePaste = async (event: ClipboardEvent) => {
  if (!enableUpload.value) return;
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.type.startsWith('image/'))
    .map(item => item.getAsFile())
    .filter((file): file is File => Boolean(file));
  if (!files.length) return;
  event.preventDefault();
  await addFiles(files);
};

const handleDrop = async (event: DragEvent) => {
  if (!enableUpload.value) return;
  const files = Array.from(event.dataTransfer?.files || []).filter(file => file.type.startsWith('image/'));
  await addFiles(files);
};

const handleSend = () => {
  if (props.disabled || !canSend.value) return;
  emit('send', draft.value.trim(), images.value);
  draft.value = '';
  images.value = [];
  nextTick(resizeInput);
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
.composer__model,
.composer__send {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
}

.composer__tool,
.composer__model {
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

.composer__model {
  gap: 4px;
  padding: 0 8px;
  font-size: 13px;
}

.composer__tool :deep(.app-icon) {
  font-size: 16px;
}

.composer__model :deep(.app-icon) {
  font-size: 13px;
}

.is-inert {
  cursor: not-allowed;
  opacity: 0.5;
}

.composer__send {
  width: 32px;
  height: 32px;
  margin-left: auto;
  padding: 0;
  color: #fff;
  background: var(--accent);
  border-radius: 10px;
  cursor: pointer;
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
.composer__tool:focus-visible,
.composer__model:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.chat-composer__file {
  display: none;
}
</style>
