import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { ModelCatalogItem } from '../http/types.ts';
import {
  createStartRunRequest,
  filterModels,
  resolveModelCode,
} from './model-catalog.ts';

const model = (
  code: string,
  name = code,
  supportsVision = false,
): ModelCatalogItem => ({
  code,
  name,
  context_window: null,
  supports_vision: supportsVision,
});

const models = [
  model('hy3', 'HY 3'),
  model('glm-online', 'GLM-5_3-Online-32k'),
  model('vision-auto', 'aidev-vision-auto', true),
];

test('a valid stored model wins over the API default', () => {
  assert.equal(resolveModelCode(models, 'glm-online', 'hy3'), 'hy3');
});

test('an unavailable stored model falls back to the API default', () => {
  assert.equal(resolveModelCode(models, 'glm-online', 'removed'), 'glm-online');
});

test('the first model is used when the API default is unavailable', () => {
  assert.equal(resolveModelCode(models, 'removed', null), 'hy3');
});

test('model search matches name and code without changing API order', () => {
  assert.deepEqual(
    filterModels(models, 'GLM').map(item => item.code),
    ['glm-online'],
  );
  assert.deepEqual(
    filterModels(models, 'VISION').map(item => item.code),
    ['vision-auto'],
  );
  assert.deepEqual(filterModels(models, 'zzz'), []);
});

test('run payload includes a selected model and omits an unavailable selection', () => {
  assert.deepEqual(
    createStartRunRequest('build a page', 'hy3'),
    { content: 'build a page', model_code: 'hy3' },
  );
  assert.deepEqual(
    createStartRunRequest('build a page'),
    { content: 'build a page' },
  );
});
