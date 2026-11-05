<template>
  <AppModal
    :model-value="modelValue"
    :title="`重命名 — ${project?.name || ''}`"
    :confirm-text="submitting ? '保存中…' : '确认'"
    :confirm-disabled="!canConfirm"
    :cancel-disabled="submitting"
    :closeable="!submitting"
    :close-on-mask="false"
    :focus-confirm="false"
    @confirm="confirm"
    @update:modelValue="$emit('update:modelValue', $event)"
  >
    <label class="rename-project">
      <span>新名字</span>
      <span class="rename-project__field">
        <input
          ref="inputRef"
          v-model="name"
          maxlength="20"
          placeholder="给项目起个好记的名字"
          :class="{ 'is-error': Boolean(error) }"
          :disabled="submitting"
          @input="error = ''"
          @keydown.enter="handleEnter"
        >
        <em>{{ name.trim().length }}/20</em>
      </span>
      <span v-if="error" class="rename-project__error" role="alert">{{ error }}</span>
    </label>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import Message from '@/common/message';
import { readableError } from '@/common/util';
import { renameProject } from '@/http/api';
import type { ProjectResponse } from '@/http/types';
import AppModal from './AppModal.vue';

const props = defineProps<{
  modelValue: boolean;
  project: ProjectResponse | null;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'renamed', project: ProjectResponse): void;
}>();

const inputRef = ref<HTMLInputElement>();
const name = ref('');
const error = ref('');
const submitting = ref(false);
const canConfirm = computed(() => {
  const value = name.value.trim();
  return Boolean(value && value !== props.project?.name && !submitting.value);
});

const confirm = async () => {
  const project = props.project;
  const value = name.value.trim();
  if (!project || !canConfirm.value || !value) return;
  error.value = '';
  submitting.value = true;
  try {
    const renamed = await renameProject(project.id, { name: value });
    emit('renamed', renamed);
    emit('update:modelValue', false);
    Message({ theme: 'success', message: '项目名称已更新' });
  } catch (err) {
    error.value = readableError(err, '重命名失败，请稍后重试');
    await nextTick();
    inputRef.value?.focus();
  } finally {
    submitting.value = false;
  }
};

const handleEnter = (event: KeyboardEvent) => {
  if (event.isComposing || event.keyCode === 229 || !canConfirm.value) return;
  event.preventDefault();
  void confirm();
};

watch(() => props.modelValue, async (visible) => {
  if (!visible) return;
  name.value = props.project?.name || '';
  error.value = '';
  submitting.value = false;
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

.rename-project > span:first-child {
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
}

.rename-project__field {
  position: relative;
  display: block;
  width: 100%;
  min-width: 0;
}

.rename-project input {
  box-sizing: border-box;
  display: block;
  width: 100%;
  min-width: 0;
  height: 44px;
  padding: 0 58px 0 12px;
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

.rename-project input.is-error {
  border-color: var(--danger);
}

.rename-project input:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.rename-project em {
  position: absolute;
  top: 50%;
  right: 12px;
  color: var(--faint);
  font-size: 12px;
  font-style: normal;
  line-height: 1;
  pointer-events: none;
  transform: translateY(-50%);
}

.rename-project__error {
  color: var(--danger);
  font-size: 12px;
  font-weight: 400;
}
</style>
