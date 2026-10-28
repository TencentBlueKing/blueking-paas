import type { ModelCatalogItem, StartRunRequest } from '../http/types';

export const resolveModelCode = (
  models: ModelCatalogItem[],
  defaultCode: string,
  storedCode?: string | null,
): string | null => {
  const stored = storedCode?.trim();
  if (stored && models.some(model => model.code === stored)) return stored;
  if (models.some(model => model.code === defaultCode)) return defaultCode;
  return models[0]?.code ?? null;
};

export const filterModels = (models: ModelCatalogItem[], keyword: string): ModelCatalogItem[] => {
  const normalized = keyword.trim().toLocaleLowerCase();
  if (!normalized) return models;
  return models.filter(model => (
    model.name.toLocaleLowerCase().includes(normalized)
    || model.code.toLocaleLowerCase().includes(normalized)
  ));
};

export const createStartRunRequest = (
  content: string,
  modelCode?: string,
): StartRunRequest => ({
  content,
  ...(modelCode ? { model_code: modelCode } : {}),
});
