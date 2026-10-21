<template>
  <AppModal
    v-model="visible"
    title="确定删除项目？"
    :closeable="!submitting"
    :close-on-mask="false"
    :focus-confirm="false"
    panel-width="600px"
  >
    <div v-if="project" class="delete-dialog">
      <div class="delete-dialog__notice">
        <p>项目 <span class="delete-dialog__highlight">{{ project.name }}</span> 被删除后不能恢复，所有相关会话、上下文、Git 仓库与凭证等都会被清理。</p>
        <p>出于安全原因，项目 ID <span class="delete-dialog__highlight">{{ project.id }}</span> 不能用于创建新项目。</p>
      </div>
      <p class="delete-dialog__confirm">
        该操作不可撤销，请输入项目 ID:
        <button
          type="button"
          class="delete-dialog__id"
          v-bk-tooltips="{ content: '点击复制', placement: 'top' }"
          @click="copyId"
        >
          {{ project.id }}
        </button>
        进行确认
      </p>
      <label class="delete-dialog__field">
        <input
          v-model="typedId"
          placeholder="请输入项目 ID"
          :class="{ 'is-error': Boolean(error) }"
          :disabled="submitting"
          autocomplete="off"
          spellcheck="false"
          @input="error = ''"
          @keydown.enter="handleEnter"
        >
      </label>
      <p v-if="error" class="delete-dialog__error" role="alert">{{ error }}</p>
    </div>
    <template #footer>
      <button
        type="button"
        class="delete-dialog__cancel"
        :disabled="submitting"
        @click="visible = false"
      >
        取消
      </button>
      <button
        type="button"
        class="delete-dialog__submit"
        :disabled="submitting || !idMatches"
        @click="submit"
      >
        {{ submitting ? '删除中…' : '删除' }}
      </button>
    </template>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Message from '@/common/message';
import AppModal from '@/components/project/AppModal.vue';
import { deleteProject } from '@/http/api';
import type { ProjectResponse } from '@/http/types';

const props = defineProps<{
  modelValue: boolean;
  project: ProjectResponse | null;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'deleted'): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const typedId = ref('');
const error = ref('');
const submitting = ref(false);

const idMatches = computed(() => (
  Boolean(props.project) && typedId.value.trim() === props.project.id
));

const copyText = async (text: string) => {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement('textarea');
  area.value = text;
  area.setAttribute('readonly', 'true');
  area.style.position = 'fixed';
  area.style.top = '0';
  area.style.left = '-9999px';
  document.body.appendChild(area);
  area.select();
  const copied = document.execCommand('copy');
  area.remove();
  if (!copied) throw new Error('copy failed');
};

const copyId = async () => {
  const id = props.project?.id;
  if (!id) return;
  try {
    await copyText(id);
    error.value = '';
    Message({ theme: 'success', message: '项目 ID 已复制', delay: 1000 });
  } catch {
    error.value = '复制失败，请手动输入项目 ID';
  }
};

const handleEnter = (event: KeyboardEvent) => {
  if (event.isComposing || event.keyCode === 229) return;
  if (!idMatches.value || submitting.value) return;
  event.preventDefault();
  submit();
};

const submit = async () => {
  const project = props.project;
  if (!project || !idMatches.value || submitting.value) return;
  error.value = '';
  submitting.value = true;
  try {
    await deleteProject(project.id);
    Message({ theme: 'success', message: '项目已删除', delay: 2000 });
    visible.value = false;
    emit('deleted');
  } catch (err: any) {
    error.value = err?.message || '删除失败，请稍后重试';
  } finally {
    submitting.value = false;
  }
};

watch(() => props.modelValue, (open) => {
  if (!open) return;
  typedId.value = '';
  error.value = '';
});
</script>

<style lang="postcss" scoped>
:deep(.app-modal__head h2) {
  text-align: center;
}

.delete-dialog__notice {
  margin-top: 20px;
  padding: 14px 16px;
  background: #f4f6f8;
  border-radius: 10px;
}

.delete-dialog__notice p {
  margin: 0;
  color: #4e5969;
  font-size: 13px;
  line-height: 1.7;
}

.delete-dialog__notice p + p {
  margin-top: 8px;
}

.delete-dialog__highlight {
  color: #3a84ff;
  font-weight: 600;
}

.delete-dialog__confirm {
  margin: 18px 0 0;
  color: #63656e;
  font-size: 14px;
  line-height: 1.6;
}

.delete-dialog__id {
  padding: 0;
  color: #ea3636;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  font-weight: 600;
  background: none;
  border: 0;
  cursor: pointer;
}

.delete-dialog__id:hover {
  color: #c82020;
}

.delete-dialog__id:focus-visible {
  outline: 2px solid #f5a3a3;
  outline-offset: 2px;
  border-radius: 4px;
}

.delete-dialog__field {
  display: block;
  margin-top: 6px;
}

.delete-dialog__field input {
  box-sizing: border-box;
  width: 100%;
  height: 40px;
  padding: 0 12px;
  color: #12141a;
  font-size: 14px;
  background: #fff;
  border: 1px solid #dcdee5;
  border-radius: 2px;
}

.delete-dialog__field input::placeholder {
  color: #c4c6cc;
}

.delete-dialog__field input:focus {
  border-color: #3a84ff;
  outline: none;
}

.delete-dialog__field input.is-error {
  border-color: #ea3636;
}

.delete-dialog__error {
  margin: 8px 0 0;
  color: #ea3636;
  font-size: 13px;
}

.delete-dialog__cancel,
.delete-dialog__submit {
  height: 32px;
  padding: 0 16px;
  font-size: 14px;
  border-radius: 2px;
  cursor: pointer;
}

.delete-dialog__cancel {
  color: #63656e;
  background: #fff;
  border: 1px solid #c4c6cc;
}

.delete-dialog__cancel:hover:not(:disabled) {
  color: #3a84ff;
  border-color: #3a84ff;
}

.delete-dialog__submit {
  color: #fff;
  font-weight: 600;
  background: #ea3636;
  border: 1px solid #ea3636;
}

.delete-dialog__submit:hover:not(:disabled) {
  background: #d12b2b;
  border-color: #d12b2b;
}

.delete-dialog__cancel:disabled,
.delete-dialog__submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.delete-dialog__cancel:focus-visible,
.delete-dialog__submit:focus-visible {
  outline: 2px solid #f5a3a3;
  outline-offset: 2px;
}
</style>
