<template>
  <div class="chat-composer" @paste="handlePaste" @dragover.prevent @drop.prevent="handleDrop">
    <div v-if="images.length" class="chat-composer__previews">
      <div v-for="(image, index) in images" :key="`${image.name}-${index}`" class="chat-composer__preview">
        <img :src="image.preview" :alt="image.name || '设计稿'">
        <bk-button
          class="chat-composer__remove"
          text
          :disabled="disabled"
          @click="images.splice(index, 1)"
        >
          <Close />
        </bk-button>
      </div>
    </div>
    <bk-input
      v-model="draft"
      type="textarea"
      :rows="4"
      :disabled="disabled"
      placeholder="描述你想要的改动，或上传设计稿 / 截图后发送"
    />
    <div class="chat-composer__toolbar">
      <div class="chat-composer__tools">
        <input
          ref="fileRef"
          class="chat-composer__file"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          @change="handleFileChange"
        >
        <bk-button text :disabled="disabled" title="上传设计稿或截图" @click="openFile">
          <ImageFill />
        </bk-button>
      </div>
      <bk-button theme="primary" :disabled="disabled || !canSend" @click="handleSend">
        发送
      </bk-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Message } from 'bkui-vue';
import { Close, ImageFill } from 'bkui-vue/lib/icon';
import { appendImages } from './read-image';
import type { ChatImage } from './types';

defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'send', value: string, images: ChatImage[]): void;
}>();

const draft = ref('');
const images = ref<ChatImage[]>([]);
const fileRef = ref<HTMLInputElement>();
const canSend = computed(() => Boolean(draft.value.trim() || images.value.length));

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
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.type.startsWith('image/'))
    .map(item => item.getAsFile())
    .filter((file): file is File => Boolean(file));
  if (!files.length) return;
  event.preventDefault();
  await addFiles(files);
};

const handleDrop = async (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files || []).filter(file => file.type.startsWith('image/'));
  await addFiles(files);
};

const handleSend = () => {
  if (!canSend.value) return;
  emit('send', draft.value.trim(), images.value);
  draft.value = '';
  images.value = [];
};
</script>

<style lang="postcss" scoped>
.chat-composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px 16px;
  border-top: 1px solid #dcdee5;
}

.chat-composer__previews {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat-composer__preview {
  position: relative;
  width: 72px;
  height: 72px;
  overflow: hidden;
  background: #f5f7fa;
  border: 1px solid #dcdee5;
  border-radius: 6px;
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
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 0 0 0 6px;
}

.chat-composer__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-composer__tools {
  display: flex;
  gap: 4px;
}

.chat-composer__file {
  display: none;
}
</style>
