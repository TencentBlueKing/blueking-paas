import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { resolveModelCode } from '@/common/model-catalog';
import { listModels } from '@/http/api';
import type { ModelCatalogResponse } from '@/http/types';

const STORAGE_KEY = 'app-spark:selected-model-code';

type CatalogStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

const readStoredCode = () => {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
};

const writeStoredCode = (code: string | null) => {
  try {
    if (code) localStorage.setItem(STORAGE_KEY, code);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 浏览器禁用本地存储时仍可使用当前会话内的选择。
  }
};

export const useModelCatalogStore = defineStore('model-catalog', () => {
  const status = ref<CatalogStatus>('idle');
  const catalog = ref<ModelCatalogResponse | null>(null);
  const selectedCode = ref<string | null>(null);
  let loadingPromise: Promise<void> | null = null;

  const models = computed(() => catalog.value?.models ?? []);
  const selectedModel = computed(() => (
    models.value.find(model => model.code === selectedCode.value) ?? null
  ));
  const switchable = computed(() => (
    status.value === 'ready'
    && Boolean(catalog.value?.switchable)
    && Boolean(selectedModel.value)
  ));
  const requestModelCode = computed(() => (
    switchable.value ? selectedCode.value ?? undefined : undefined
  ));
  const displayName = computed(() => {
    if (status.value === 'loading') return '加载模型…';
    return selectedModel.value?.name || '默认模型';
  });

  const loadCatalog = (
    { force = false, resetToDefault = false }: { force?: boolean; resetToDefault?: boolean } = {},
  ): Promise<void> => {
    if (loadingPromise) return loadingPromise;
    if (!force && status.value !== 'idle') return Promise.resolve();

    if (resetToDefault) {
      selectedCode.value = null;
      writeStoredCode(null);
    }
    status.value = 'loading';
    loadingPromise = (async () => {
      try {
        const response = await listModels();
        const nextCode = resolveModelCode(
          response.models,
          response.default_code,
          resetToDefault || !response.switchable ? null : readStoredCode(),
        );
        catalog.value = response;
        selectedCode.value = nextCode;
        writeStoredCode(nextCode);
        status.value = 'ready';
      } catch {
        catalog.value = null;
        selectedCode.value = null;
        status.value = 'unavailable';
      } finally {
        loadingPromise = null;
      }
    })();
    return loadingPromise;
  };

  const selectModel = (code: string) => {
    if (!switchable.value || !models.value.some(model => model.code === code)) return;
    selectedCode.value = code;
    writeStoredCode(code);
  };

  const recoverFromUnavailableModel = () => (
    loadCatalog({ force: true, resetToDefault: true })
  );

  return {
    status,
    catalog,
    models,
    selectedCode,
    selectedModel,
    switchable,
    requestModelCode,
    displayName,
    loadCatalog,
    selectModel,
    recoverFromUnavailableModel,
  };
});
