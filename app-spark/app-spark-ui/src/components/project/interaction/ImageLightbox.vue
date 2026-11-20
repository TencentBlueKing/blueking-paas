<template>
  <Teleport to="body">
    <Transition name="image-lightbox">
      <div
        v-if="open"
        class="image-lightbox"
        role="dialog"
        aria-modal="true"
        :aria-label="alt || '图片预览'"
        tabindex="-1"
        @click.self="close"
        @keydown="handleKeydown"
      >
        <button
          ref="closeRef"
          type="button"
          class="image-lightbox__close"
          aria-label="关闭图片预览"
          @click="close"
        >
          <AppIcon name="x" />
        </button>
        <div class="image-lightbox__stage">
          <img
            v-if="!loadFailed"
            class="image-lightbox__image"
            :src="src"
            :alt="alt || '预览图片'"
            @error="loadFailed = true"
          >
          <div v-else class="image-lightbox__error" role="status">图片加载失败</div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import AppIcon from '@/components/AppIcon.vue';

const props = defineProps<{
  open: boolean;
  src: string;
  alt?: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const closeRef = ref<HTMLButtonElement>();
const loadFailed = ref(false);
let restoreFocusTo: HTMLElement | null = null;
let previousBodyOverflow = '';

const close = () => emit('close');

const restorePageState = () => {
  document.body.style.overflow = previousBodyOverflow;
  const target = restoreFocusTo;
  restoreFocusTo = null;
  if (target?.isConnected) target.focus();
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    event.preventDefault();
    close();
  } else if (event.key === 'Tab') {
    event.preventDefault();
    closeRef.value?.focus();
  }
};

watch(() => props.src, () => {
  loadFailed.value = false;
});

watch(() => props.open, async (open) => {
  if (open) {
    restoreFocusTo = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    loadFailed.value = false;
    await nextTick();
    closeRef.value?.focus();
  } else {
    restorePageState();
  }
}, { flush: 'post' });

onBeforeUnmount(() => {
  if (props.open) restorePageState();
});
</script>

<style lang="postcss" scoped>
.image-lightbox {
  position: fixed;
  z-index: 4000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 56px;
  background: rgba(18, 20, 26, 0.78);
}

.image-lightbox__stage {
  display: grid;
  place-items: center;
  max-width: 100%;
  max-height: 100%;
}

.image-lightbox__image {
  display: block;
  max-width: min(92vw, 1440px);
  max-height: calc(100vh - 112px);
  object-fit: contain;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 18px 56px rgba(0, 0, 0, 0.34);
}

.image-lightbox__close {
  position: fixed;
  top: 20px;
  right: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.image-lightbox__close:hover {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.38);
}

.image-lightbox__close:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 3px;
}

.image-lightbox__close :deep(.app-icon) {
  width: 18px;
  height: 18px;
  font-size: 18px;
}

.image-lightbox__error {
  padding: 18px 22px;
  color: #dcdee5;
  font-size: 14px;
  background: #182132;
  border-radius: 8px;
}

.image-lightbox-enter-active,
.image-lightbox-leave-active {
  transition: opacity 0.16s ease;
}

.image-lightbox-enter-active .image-lightbox__stage,
.image-lightbox-leave-active .image-lightbox__stage {
  transition: transform 0.18s ease;
}

.image-lightbox-enter-from,
.image-lightbox-leave-to {
  opacity: 0;
}

.image-lightbox-enter-from .image-lightbox__stage,
.image-lightbox-leave-to .image-lightbox__stage {
  transform: scale(0.98);
}

@media (max-width: 760px) {
  .image-lightbox {
    padding: 48px 16px 24px;
  }

  .image-lightbox__image {
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 72px);
  }

  .image-lightbox__close {
    top: 10px;
    right: 10px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .image-lightbox-enter-active,
  .image-lightbox-leave-active,
  .image-lightbox-enter-active .image-lightbox__stage,
  .image-lightbox-leave-active .image-lightbox__stage {
    transition: none;
  }
}
</style>
