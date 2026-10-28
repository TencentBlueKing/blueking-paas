<template>
  <div class="model-selector">
    <bk-popover
      v-if="switchable"
      ref="popoverRef"
      trigger="click"
      :placement="placement"
      theme="light"
      :arrow="false"
      :padding="0"
      :offset="6"
      boundary="body"
      ext-cls="model-selector-popover"
      @after-show="handleAfterShow"
      @after-hidden="onAfterHidden"
    >
      <button
        type="button"
        class="model-selector__trigger"
        :class="{ 'is-open': visible }"
        aria-haspopup="listbox"
        :aria-expanded="visible"
        :title="selectedModel?.name"
      >
        <span>{{ displayName }}</span>
        <AppIcon name="chevron-down" />
      </button>
      <template #content>
        <div class="model-selector__panel">
          <label class="model-selector__search">
            <AppIcon name="search" />
            <input
              ref="searchRef"
              v-model="keyword"
              type="search"
              autocomplete="off"
              placeholder="搜索模型关键字"
              aria-label="搜索模型关键字"
              @keydown.esc.stop.prevent="close"
            >
          </label>
          <div class="model-selector__list" role="listbox" aria-label="可用模型">
            <button
              v-for="model in filteredModels"
              :key="model.code"
              type="button"
              class="model-selector__option"
              :class="{ 'is-selected': model.code === selectedCode }"
              role="option"
              :aria-selected="model.code === selectedCode"
              @click="handleSelect(model.code)"
            >
              <strong class="model-selector__name">{{ model.name }}</strong>
              <em v-if="model.supports_vision" class="model-selector__multimodal">多模态</em>
            </button>
            <div v-if="!filteredModels.length" class="model-selector__empty" role="status">
              没有匹配的模型
            </div>
          </div>
        </div>
      </template>
    </bk-popover>

    <div v-else class="model-selector__static">
      <button
        type="button"
        class="model-selector__trigger is-readonly"
        disabled
        aria-disabled="true"
        :title="displayName"
      >
        <span>{{ displayName }}</span>
        <em v-if="catalog?.source === 'direct'" class="model-selector__source">内置</em>
      </button>
      <button
        v-if="status === 'unavailable' || retrying"
        type="button"
        class="model-selector__retry"
        :class="{ 'is-loading': retrying }"
        :disabled="retrying"
        :aria-label="retrying ? '正在刷新模型列表' : '刷新模型列表'"
        :title="retrying ? '正在刷新模型列表' : '刷新模型列表'"
        @click="handleRetry"
      >
        <AppIcon name="rotate-cw" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { filterModels } from '@/common/model-catalog';
import AppIcon from '@/components/AppIcon.vue';
import { usePopoverVisible } from '@/composables/use-popover-visible';
import { useModelCatalogStore } from '@/store/model-catalog';

withDefaults(defineProps<{
  placement?: 'top-start' | 'top-end' | 'bottom-start' | 'bottom-end';
}>(), {
  placement: 'bottom-start',
});

const modelStore = useModelCatalogStore();
const {
  status,
  models,
  catalog,
  selectedCode,
  selectedModel,
  switchable,
  displayName,
} = storeToRefs(modelStore);
const {
  popoverRef,
  visible,
  onAfterShow,
  onAfterHidden,
  close,
} = usePopoverVisible();
const keyword = ref('');
const searchRef = ref<HTMLInputElement>();
const retrying = ref(false);

const filteredModels = computed(() => filterModels(models.value, keyword.value));

const handleAfterShow = async () => {
  keyword.value = '';
  onAfterShow();
  await nextTick();
  searchRef.value?.focus();
};

const handleSelect = (code: string) => {
  modelStore.selectModel(code);
  close();
};

const handleRetry = async () => {
  if (retrying.value) return;
  retrying.value = true;
  try {
    await modelStore.loadCatalog({ force: true });
  } finally {
    retrying.value = false;
  }
};
</script>

<style lang="postcss" scoped>
.model-selector {
  display: inline-flex;
  max-width: 240px;
  min-width: 0;
}

.model-selector__trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  max-width: 240px;
  height: 32px;
  min-width: 0;
  padding: 0 10px;
  color: var(--muted);
  font-size: 13px;
  background: transparent;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}

.model-selector__trigger > span {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.model-selector__source {
  flex-shrink: 0;
  padding: 1px 5px;
  color: var(--faint);
  font-size: 10px;
  font-style: normal;
  line-height: 16px;
  background: var(--subtle-bg);
  border-radius: 5px;
}

.model-selector__trigger:hover,
.model-selector__trigger.is-open {
  color: var(--ink);
  background: var(--subtle-bg);
}

.model-selector__trigger.is-readonly {
  color: var(--muted);
  cursor: default;
  opacity: 1;
}

.model-selector__static {
  display: inline-flex;
  align-items: center;
  max-width: 240px;
  min-width: 0;
}

.model-selector__static .model-selector__trigger {
  flex: 1 1 auto;
  width: auto;
}

.model-selector__retry {
  display: inline-flex;
  flex: 0 0 24px;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 32px;
  margin-left: 6px;
  padding: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.model-selector__retry:hover:not(:disabled) {
  color: var(--ink);
  background: var(--subtle-bg);
}

.model-selector__retry:disabled {
  cursor: default;
}

.model-selector__retry.is-loading :deep(.app-icon) {
  animation: model-selector-retry-spin 0.8s linear infinite;
}

.model-selector__retry:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.model-selector__trigger :deep(.app-icon) {
  flex: 0 0 13px;
  font-size: 13px;
  transition: transform 120ms ease;
}

.model-selector__trigger.is-open :deep(.app-icon) {
  transform: rotate(180deg);
}

.model-selector__trigger:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.model-selector__panel {
  box-sizing: border-box;
  width: min(360px, calc(100vw - 32px));
  overflow: hidden;
  background: #fff;
  border-radius: 12px;
}

.model-selector__search {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 48px;
  padding: 0 14px;
  color: var(--faint);
  border-bottom: 1px solid var(--line);
}

.model-selector__search:focus-within {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.model-selector__search :deep(.app-icon) {
  flex: 0 0 18px;
  font-size: 18px;
}

.model-selector__search input {
  box-sizing: border-box;
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  color: var(--ink);
  font-size: 14px;
  background: transparent;
  border: 0;
  outline: none;
}

.model-selector__search input::placeholder {
  color: #aeb7c6;
}

.model-selector__search input::-webkit-search-cancel-button {
  cursor: pointer;
}

.model-selector__list {
  max-height: 336px;
  padding: 6px;
  overflow-y: auto;
}

.model-selector__option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  padding: 7px 10px;
  color: var(--ink);
  text-align: left;
  background: #fff;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.model-selector__option:hover,
.model-selector__option:focus-visible {
  background: var(--subtle-bg);
  outline: none;
}

.model-selector__option.is-selected {
  color: var(--accent);
  background: var(--accent-soft);
}

.model-selector__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.model-selector__multimodal {
  flex-shrink: 0;
  padding: 2px 6px;
  color: #d98216;
  font-size: 11px;
  font-style: normal;
  line-height: 18px;
  white-space: nowrap;
  background: #fff3df;
  border-radius: 6px;
}

.model-selector__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 96px;
  color: var(--faint);
  font-size: 13px;
}

@keyframes model-selector-retry-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .model-selector__retry.is-loading :deep(.app-icon) {
    animation: none;
  }
}

:global(.model-selector-popover),
:global(.model-selector-popover.bk-popover),
:global(.model-selector-popover .bk-pop2-content) {
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}

:global(.model-selector-popover) {
  border-radius: 12px;
  box-shadow: 0 14px 36px rgba(16, 22, 34, 0.16), 0 0 0 1px rgba(16, 22, 34, 0.05);
}

@media (max-width: 520px) {
  .model-selector {
    max-width: 170px;
  }

  .model-selector__panel {
    width: min(360px, calc(100vw - 24px));
  }
}
</style>
