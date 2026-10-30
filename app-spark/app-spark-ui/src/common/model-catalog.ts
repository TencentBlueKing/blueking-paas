import type { ModelCatalogItem, StartRunRequest } from '../http/types';

export const resolveModelId = (
  models: ModelCatalogItem[],
  defaultModelId: string,
  storedModelId?: string | null,
): string | null => {
  const stored = storedModelId?.trim();
  if (stored && models.some(model => model.id === stored)) return stored;
  if (models.some(model => model.id === defaultModelId)) return defaultModelId;
  return models[0]?.id ?? null;
};

export const filterModels = (models: ModelCatalogItem[], keyword: string): ModelCatalogItem[] => {
  const normalized = keyword.trim().toLocaleLowerCase();
  if (!normalized) return models;
  return models.filter(model => (
    model.name.toLocaleLowerCase().includes(normalized)
    || model.id.toLocaleLowerCase().includes(normalized)
  ));
};

export const createStartRunRequest = (
  content: string,
  modelId?: string,
): StartRunRequest => ({
  content,
  ...(modelId ? { model_id: modelId } : {}),
});
