<template>
  <AppModal
    v-model="visible"
    title="新项目"
    description="给它起个名字，创建后就可以用对话开始做。"
    :confirm-text="submitting ? '创建中…' : '创建并进入'"
    :confirm-disabled="submitting || !projectName.trim()"
    :cancel-disabled="submitting"
    :closeable="!submitting"
    :focus-confirm="false"
    @confirm="submit"
  >
    <label class="create-dialog__field">
      <span>项目名称</span>
      <input
        ref="inputRef"
        v-model="projectName"
        maxlength="20"
        placeholder="例如：预约活动页"
        :class="{ 'is-error': Boolean(error) }"
        :disabled="submitting"
        @input="error = ''"
        @keydown.enter="handleEnter"
      >
      <em>{{ projectName.trim().length }}/20</em>
    </label>
    <p v-if="error" class="create-dialog__error" role="alert">{{ error }}</p>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { Message } from 'bkui-vue';
import AppModal from '@/components/project/AppModal.vue';
import { createProject } from '@/http/api';
import type { ProjectResponse } from '@/http/types';

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'created', value: ProjectResponse): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const projectName = ref('');
const error = ref('');
const submitting = ref(false);
const inputRef = ref<HTMLInputElement>();

const generateProjectId = () => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let suffix = '';
  for (let i = 0; i < 10; i++) {
    suffix += chars[Math.floor(Math.random() * chars.length)];
  }
  return `p-${suffix}`;
};

const handleEnter = (event: KeyboardEvent) => {
  // 中文输入法用 Enter 上屏时，v-model 往往还是空的；229 是部分浏览器的 composition keyCode
  if (event.isComposing || event.keyCode === 229) return;
  const value = (inputRef.value?.value || projectName.value).trim();
  if (!value) return;
  event.preventDefault();
  submit();
};

const submit = async () => {
  const value = (inputRef.value?.value || projectName.value).trim();
  if (!value) {
    error.value = '请输入项目名称';
    return;
  }
  if (value.length > 20) {
    error.value = '项目名称长度为 1-20 个字符';
    return;
  }
  error.value = '';
  submitting.value = true;
  try {
    const created = await createProject({
      id: generateProjectId(),
      name: value,
    });
    Message({ theme: 'success', message: '创建成功' });
    visible.value = false;
    emit('created', created);
  } catch (err: any) {
    error.value = err?.message || '创建失败，请稍后重试';
  } finally {
    submitting.value = false;
  }
};

watch(() => props.modelValue, (open) => {
  if (!open) return;
  projectName.value = '';
  error.value = '';
  nextTick(() => inputRef.value?.focus());
});
</script>

<style lang="postcss" scoped>
.create-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 24px;
}

.create-dialog__field span {
  color: #12141a;
  font-size: 13px;
  font-weight: 600;
}

.create-dialog__field input {
  box-sizing: border-box;
  width: 100%;
  height: 44px;
  padding: 0 12px;
  color: #12141a;
  font-size: 15px;
  background: #f7f8fa;
  border: 1px solid #e4e9f1;
  border-radius: 12px;
}

.create-dialog__field input:focus {
  background: #fff;
  border-color: #8ea2ff;
  outline: none;
}

.create-dialog__field input.is-error {
  border-color: #e76761;
  background: #fff;
}

.create-dialog__field em {
  align-self: flex-end;
  color: #88919e;
  font-size: 12px;
  font-style: normal;
}

.create-dialog__error {
  margin: 8px 0 0;
  color: #b42318;
  font-size: 13px;
}
</style>
