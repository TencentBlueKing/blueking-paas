<template>
  <div class="publication-app-name">
    <div class="publication-app-name__label">
      <span>蓝鲸应用名</span>
      <span
        v-bk-tooltips="{ content: APP_NAME_HELP, placement: 'top' }"
        class="publication-app-name__help"
        aria-label="蓝鲸应用名说明"
      >
        <AppIcon name="info" />
      </span>
    </div>

    <input
      v-if="editing"
      ref="inputRef"
      :value="modelValue"
      class="publication-app-name__input"
      :class="{ 'is-error': Boolean(problemText) }"
      maxlength="20"
      placeholder="请输入蓝鲸应用名"
      aria-label="蓝鲸应用名"
      @input="handleInput"
      @keydown.enter="handleEnter"
      @keydown.esc.stop="handleEsc"
      @blur="finishEdit"
    >
    <div v-else class="publication-app-name__view">
      <span class="publication-app-name__text">{{ modelValue }}</span>
      <button
        type="button"
        class="publication-app-name__edit"
        aria-label="修改蓝鲸应用名"
        @click="startEdit"
      >
        <AppIcon name="pencil" />
      </button>
    </div>

    <p v-if="pending" class="publication-app-name__hint">正在检查名称是否可用…</p>
    <p v-else-if="problemText" class="publication-app-name__hint is-error" role="alert">{{ problemText }}</p>
    <p v-else-if="normalizedHint" class="publication-app-name__hint">{{ normalizedHint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import AppIcon from '@/components/AppIcon.vue';
import type { PublicationAppNameValidateResponse } from '@/http/types';

const APP_NAME_HELP = '开发者中心内应用名不允许重名，冲突时需要以其他名字发布（默认取当前项目名）。';
const MSG_INVALID = '名称只能包含中文、英文字母、数字、连接符和下划线';

const props = defineProps<{
  modelValue: string;
  /** 当前名称还在等检查结果。 */
  pending: boolean;
  /** 当前名称的检查结果；还没检查或检查失败时为 null。 */
  result: PublicationAppNameValidateResponse | null;
}>();
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();

const editing = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);
// 进入编辑时的名称，Esc 或清空后离开时恢复成它。
let nameBeforeEdit = '';

const problemText = computed(() => {
  if (!props.modelValue.trim()) return editing.value ? '' : '请输入蓝鲸应用名';
  if (!props.result || props.result.is_available) return '';
  // 带上过滤后的名字：输入「Spa rk」时实际撞的是「Spark」。
  if (props.result.problem === 'taken') return `「${props.result.name}」已被开发者中心的其他应用使用，请换一个名称`;
  return props.result.message || MSG_INVALID;
});

// 开发者中心会静默去掉不支持的字符，提前告诉用户实际会用哪个名字。
const normalizedHint = computed(() => {
  const result = props.result;
  if (!result?.is_available || result.name === props.modelValue.trim()) return '';
  return `将以「${result.name}」发布`;
});

const startEdit = async () => {
  if (editing.value) return;
  nameBeforeEdit = props.modelValue;
  editing.value = true;
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
};

const handleInput = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement).value);
};

const finishEdit = () => {
  if (!editing.value) return;
  // 留空没有意义，回到进入编辑前的名称，免得发布按钮无故变灰。
  if (!props.modelValue.trim()) emit('update:modelValue', nameBeforeEdit);
  editing.value = false;
};

const cancelEdit = () => {
  if (!editing.value) return;
  emit('update:modelValue', nameBeforeEdit);
  editing.value = false;
};

// 输入法选词时的 Enter / Esc 属于输入法，不能当成确认或取消。
const isComposing = (event: KeyboardEvent) => event.isComposing || event.keyCode === 229;

const handleEnter = (event: KeyboardEvent) => {
  if (isComposing(event)) return;
  event.preventDefault();
  finishEdit();
};

const handleEsc = (event: KeyboardEvent) => {
  if (isComposing(event)) return;
  event.preventDefault();
  cancelEdit();
};

// 名称不能用时直接进入编辑，用户不用再去找笔形图标。
watch(() => props.result?.is_available === false, (unavailable) => {
  if (unavailable) void startEdit();
});
</script>

<style lang="postcss" scoped>
.publication-app-name {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.publication-app-name__label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
}

.publication-app-name__help {
  display: inline-flex;
  color: var(--faint);
  font-size: 13px;
  cursor: help;
}

.publication-app-name__help:hover {
  color: var(--muted);
}

.publication-app-name__view {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
}

.publication-app-name__text {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.publication-app-name__edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--muted);
  font-size: 14px;
  background: transparent;
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

.publication-app-name__edit:hover {
  color: var(--ink);
  background: var(--hover-bg);
}

.publication-app-name__edit:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.publication-app-name__input {
  box-sizing: border-box;
  width: 100%;
  height: 34px;
  padding: 0 12px;
  color: var(--ink);
  font-size: 13px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  outline: none;
}

.publication-app-name__input:hover {
  border-color: #cfd6e2;
}

.publication-app-name__input:focus {
  border-color: var(--accent-focus);
  box-shadow: 0 0 0 2px rgba(61, 109, 255, 0.12);
}

.publication-app-name__input.is-error {
  border-color: var(--danger);
}

.publication-app-name__hint {
  margin: 0;
  color: var(--faint);
  font-size: 12px;
  line-height: 1.5;
}

.publication-app-name__hint.is-error {
  color: var(--danger);
}
</style>
