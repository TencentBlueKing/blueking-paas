import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { resolveModelId } from '@/common/model-catalog';
import { listModels } from '@/http/api';
import type { ModelCatalogResponse } from '@/http/types';

const STORAGE_KEY = 'app-spark:selected-model-id';

type CatalogStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

const readStoredModelId = () => {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
};

const writeStoredModelId = (modelId: string | null) => {
  try {
    if (modelId) localStorage.setItem(STORAGE_KEY, modelId);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 浏览器禁用本地存储时仍可使用当前会话内的选择。
  }
};

export const useModelCatalogStore = defineStore('model-catalog', () => {
  const status = ref<CatalogStatus>('idle');
  const catalog = ref<ModelCatalogResponse | null>(null);
  const selectedModelId = ref<string | null>(null);
  let loadingPromise: Promise<void> | null = null;

  const models = computed(() => catalog.value?.models ?? []);
  const selectedModel = computed(() => (
    models.value.find(model => model.id === selectedModelId.value) ?? null
  ));
  // 接口允许切换之外，还要列表已加载、并且选中的模型在列表里，选择器才可用。
  const canSwitchModel = computed(() => (
    status.value === 'ready'
    && Boolean(catalog.value?.allow_user_switch)
    && Boolean(selectedModel.value)
  ));
  const requestModelId = computed(() => (
    canSwitchModel.value ? selectedModelId.value ?? undefined : undefined
  ));
  const displayName = computed(() => {
    if (status.value === 'loading') return '加载模型…';
    return selectedModel.value?.name || '默认模型';
  });

  const loadCatalog = (
    { force = false, resetToDefault = false }: { force?: boolean; resetToDefault?: boolean } = {},
  ): Promise<void> => {
    if (resetToDefault) {
      selectedModelId.value = null;
      writeStoredModelId(null);
    }
    if (loadingPromise) return loadingPromise;
    if (!force && status.value === 'ready') return Promise.resolve();

    status.value = 'loading';
    loadingPromise = (async () => {
      try {
        const response = await listModels();
        const nextModelId = resolveModelId(
          response.models,
          response.default_model_id,
          resetToDefault || !response.allow_user_switch ? null : readStoredModelId(),
        );
        catalog.value = response;
        selectedModelId.value = nextModelId;
        writeStoredModelId(nextModelId);
        status.value = 'ready';
      } catch {
        catalog.value = null;
        selectedModelId.value = null;
        status.value = 'unavailable';
      } finally {
        loadingPromise = null;
      }
    })();
    return loadingPromise;
  };

  const selectModel = (modelId: string) => {
    if (!canSwitchModel.value || !models.value.some(model => model.id === modelId)) return;
    selectedModelId.value = modelId;
    writeStoredModelId(modelId);
  };

  const recoverFromUnavailableModel = () => (
    loadCatalog({ force: true, resetToDefault: true })
  );

  return {
    status,
    catalog,
    models,
    selectedModelId,
    selectedModel,
    canSwitchModel,
    requestModelId,
    displayName,
    loadCatalog,
    selectModel,
    recoverFromUnavailableModel,
  };
});
