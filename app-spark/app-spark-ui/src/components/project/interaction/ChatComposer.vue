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
        <p class="chat-composer__hint">{{ hint }}</p>
        <div class="chat-composer__tools">
          <template v-if="enableUpload">
            <input
              ref="fileRef"
              class="chat-composer__file"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              @change="handleFileChange"
            >
            <button
              type="button"
              class="chat-composer__icon"
              :disabled="disabled"
              title="上传设计稿或截图"
              @click="openFile"
            >
              <ImageFill />
            </button>
          </template>
          <button
            type="button"
            class="chat-composer__send"
            :disabled="disabled || !canSend"
            @click="handleSend"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { Message } from 'bkui-vue';
import { Close, ImageFill } from 'bkui-vue/lib/icon';
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
const hint = computed(() => {
  if (props.hint) return props.hint;
  return 'Shift + Enter 换行';
});

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
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 8px 10px 10px;
}

.chat-composer__hint {
  margin: 0;
  overflow: hidden;
  color: var(--faint, #88919e);
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-composer__tools {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
}

.chat-composer__icon {
  display: inline-flex;
  color: var(--muted, #5c6573);
  background: none;
  border: 0;
  cursor: pointer;
}

.chat-composer__send {
  height: 32px;
  padding: 0 14px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  background: var(--ink, #12141a);
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.chat-composer__send:hover:not(:disabled) {
  background: #2a2e38;
}

.chat-composer__send:disabled {
  color: #a8b0bc;
  background: #eef0f4;
  cursor: not-allowed;
}

.chat-composer__send:focus-visible,
.chat-composer__icon:focus-visible {
  outline: 2px solid var(--accent, #3d6dff);
  outline-offset: 2px;
}

.chat-composer__file {
  display: none;
}
</style>
