<template>
  <AppModal
    :model-value="modelValue"
    :title="`重命名 — ${project?.name || ''}`"
    confirm-text="确认"
    :confirm-disabled="!canConfirm"
    :focus-confirm="false"
    @confirm="confirm"
    @update:modelValue="$emit('update:modelValue', $event)"
  >
    <label class="rename-project">
      <span>新名字</span>
      <input
        ref="inputRef"
        v-model="name"
        maxlength="20"
        placeholder="给项目起个好记的名字"
        @keydown.enter.prevent="confirm"
      >
      <em>{{ name.trim().length }}/20</em>
    </label>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { ProjectResponse } from '@/http/types';
import AppModal from './AppModal.vue';

const props = defineProps<{
  modelValue: boolean;
  project: ProjectResponse | null;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'renamed', name: string): void;
}>();

const inputRef = ref<HTMLInputElement>();
const name = ref('');
const canConfirm = computed(() => {
  const value = name.value.trim();
  return Boolean(value && value !== props.project?.name);
});

const confirm = () => {
  const value = name.value.trim();
  if (!canConfirm.value || !value) return;
  emit('renamed', value);
  emit('update:modelValue', false);
};

watch(() => props.modelValue, async (visible) => {
  if (!visible) return;
  name.value = props.project?.name || '';
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
});
</script>

<style lang="postcss" scoped>
.rename-project {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
  margin-top: 24px;
}

.rename-project > span {
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
}

.rename-project input {
  box-sizing: border-box;
  display: block;
  width: 100%;
  max-width: 100%;
  height: 44px;
  padding: 0 12px;
  color: var(--ink);
  font-size: 15px;
  background: #f7f8fa;
  border: 1px solid var(--line);
  border-radius: 12px;
}

.rename-project input:focus {
  background: #fff;
  border-color: var(--accent-focus);
  outline: none;
}

.rename-project em {
  align-self: flex-end;
  color: var(--faint);
  font-size: 12px;
  font-style: normal;
}
</style>
