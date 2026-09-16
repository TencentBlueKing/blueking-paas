<template>
  <teleport to="body">
    <div
      v-if="modelValue"
      class="app-modal"
      @keydown.esc="close"
    >
      <div
        class="app-modal__mask"
        @click="close"
      />
      <div
        class="app-modal__panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
      >
        <header class="app-modal__head">
          <h2 :id="titleId">{{ title }}</h2>
          <p v-if="description">{{ description }}</p>
        </header>
        <slot />
        <footer class="app-modal__foot">
          <slot name="footer">
            <button
              type="button"
              class="app-modal__ghost"
              :disabled="cancelDisabled"
              @click="close"
            >
              {{ cancelText }}
            </button>
            <button
              ref="confirmRef"
              type="button"
              class="app-modal__primary"
              :disabled="confirmDisabled"
              @click="$emit('confirm')"
            >
              {{ confirmText }}
            </button>
          </slot>
        </footer>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

const props = withDefaults(defineProps<{
  modelValue: boolean;
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  confirmDisabled?: boolean;
  cancelDisabled?: boolean;
  closeable?: boolean;
  focusConfirm?: boolean;
}>(), {
  description: '',
  confirmText: '确定',
  cancelText: '取消',
  confirmDisabled: false,
  cancelDisabled: false,
  closeable: true,
  focusConfirm: true,
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'confirm'): void;
}>();

const titleId = `app-modal-title-${Math.random().toString(36).slice(2, 8)}`;
const confirmRef = ref<HTMLButtonElement>();

const close = () => {
  if (!props.closeable) return;
  emit('update:modelValue', false);
};

watch(() => props.modelValue, (visible) => {
  if (!visible || !props.focusConfirm) return;
  nextTick(() => confirmRef.value?.focus());
});
</script>

<style lang="postcss" scoped>
.app-modal {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.app-modal__mask {
  position: absolute;
  inset: 0;
  background: rgba(16, 22, 34, 0.42);
  cursor: pointer;
}

.app-modal__panel {
  position: relative;
  width: min(440px, 100%);
  padding: 28px 28px 24px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(16, 22, 34, 0.18);
}

.app-modal__head h2 {
  margin: 0 0 8px;
  color: #12141a;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.app-modal__head p {
  margin: 0;
  color: #5c6573;
  font-size: 14px;
  line-height: 1.55;
}

.app-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.app-modal__ghost,
.app-modal__primary {
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}

.app-modal__ghost {
  color: #5c6573;
  background: #f3f4f7;
}

.app-modal__ghost:hover:not(:disabled) {
  background: #e8eaef;
}

.app-modal__primary {
  color: #fff;
  font-weight: 600;
  background: #3a84ff;
}

.app-modal__primary:hover:not(:disabled) {
  background: #1768ef;
}

.app-modal__primary:disabled,
.app-modal__ghost:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.app-modal__primary:focus-visible,
.app-modal__ghost:focus-visible {
  outline: 2px solid #8ea2ff;
  outline-offset: 2px;
}
</style>
