import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { PublicationAppNameValidationRet } from '../http/types.ts';
import type { SuggestionCheck } from './app-name-suggestion.ts';
import {
  buildSuggestedAppName,
  classifySuggestionCheck,
  drawSuggestionNumbers,
  findAvailableSuggestion,
} from './app-name-suggestion.ts';

const taken = (name: string): PublicationAppNameValidationRet => ({
  name,
  is_available: false,
  problem: 'unique',
  message: '名称已存在',
});

const available = (name: string): PublicationAppNameValidationRet => ({
  name,
  is_available: true,
  problem: null,
  message: null,
});

const AVAILABLE_AS_ASKED = (candidate: string): SuggestionCheck => ({ status: 'available', name: candidate });
const UNAVAILABLE: SuggestionCheck = { status: 'unavailable' };
const FAILED: SuggestionCheck = { status: 'failed' };

const makeSequence = (...numbers: number[]) => {
  let index = 0;
  return () => (numbers[index++] - 100) / 900;
};

test('a short name keeps every character and gains one three-digit suffix', () => {
  assert.equal(buildSuggestedAppName('Spark', 123), 'Spark-123');
  assert.equal(buildSuggestedAppName('蓝'.repeat(16), 123), `${'蓝'.repeat(16)}-123`);
});

test('a name longer than 16 characters is cut from the end and the suffix stays intact', () => {
  const original = '蓝鲸应用名称示例一二三四五六七八九零甲乙';
  assert.equal(original.length, 20);
  assert.equal(
    buildSuggestedAppName(original, 123),
    `${'蓝鲸应用名称示例一二三四五六七八'}-123`,
  );
  assert.equal(buildSuggestedAppName('蓝'.repeat(17), 666).length, 20);
});

test('truncation counts code points and never splits a surrogate pair', () => {
  const name = `${'a'.repeat(15)}𠀀𠀀`;
  assert.equal(buildSuggestedAppName(name, 123), `${'a'.repeat(15)}𠀀-123`);
});

test('an empty stem or a number outside 100 to 999 is not a candidate', () => {
  assert.equal(buildSuggestedAppName('', 123), null);
  assert.equal(buildSuggestedAppName('Spark', 99), null);
  assert.equal(buildSuggestedAppName('Spark', 1000), null);
});

test('one round draws five different numbers from 100 to 999', () => {
  const rolls = [0, 0, 0.5, 0.5, 0.999, 0.2, 0.3];
  let index = 0;
  const numbers = drawSuggestionNumbers(() => rolls[index++]);
  assert.deepEqual(numbers, [100, 550, 999, 280, 370]);
});

test('the first available candidate is the recommendation and later ones are not asked', async () => {
  const asked: string[] = [];
  const found = await findAvailableSuggestion('Spark', async (candidate) => {
    asked.push(candidate);
    return AVAILABLE_AS_ASKED(candidate);
  }, { random: () => 0 });

  assert.equal(found, 'Spark-100');
  assert.deepEqual(asked, ['Spark-100']);
});

test('unavailable candidates are skipped until one is available', async () => {
  const asked: string[] = [];
  const found = await findAvailableSuggestion('番茄钟', async (candidate) => {
    asked.push(candidate);
    return asked.length < 3 ? UNAVAILABLE : AVAILABLE_AS_ASKED(candidate);
  }, { random: makeSequence(123, 666, 124, 125, 126) });

  assert.equal(found, '番茄钟-124');
  assert.deepEqual(asked, ['番茄钟-123', '番茄钟-666', '番茄钟-124']);
});

test('a failed check stops the round and does not ask for another suffix', async () => {
  const asked: string[] = [];
  const found = await findAvailableSuggestion('Spark', async (candidate) => {
    asked.push(candidate);
    return asked.length < 3 ? UNAVAILABLE : FAILED;
  }, { random: makeSequence(201, 202, 203, 204, 205) });

  assert.equal(found, null);
  assert.deepEqual(asked, ['Spark-201', 'Spark-202', 'Spark-203']);
});

test('five unavailable candidates produce no recommendation', async () => {
  const asked: string[] = [];
  const found = await findAvailableSuggestion('Spark', async (candidate) => {
    asked.push(candidate);
    return UNAVAILABLE;
  }, { random: makeSequence(301, 302, 303, 304, 305) });

  assert.equal(found, null);
  assert.deepEqual(asked, ['Spark-301', 'Spark-302', 'Spark-303', 'Spark-304', 'Spark-305']);
});

test('a suggestion finished after the input changed is dropped', async () => {
  let current = true;
  const found = await findAvailableSuggestion('Spark', async (candidate) => {
    current = false;
    return AVAILABLE_AS_ASKED(candidate);
  }, { random: () => 0, isCurrent: () => current });

  assert.equal(found, null);
});

test('a raw name from a publish-time conflict recommends the filtered name the check returns', async () => {
  const found = await findAvailableSuggestion(
    'Spa rk',
    async (candidate) => classifySuggestionCheck(candidate, available(candidate.replace(' ', ''))),
    { random: makeSequence(123, 124, 125, 126, 127) },
  );

  assert.equal(found, 'Spark-123');
});

test('only an available answer that keeps this suffix counts', () => {
  assert.deepEqual(
    classifySuggestionCheck('Spark-123', available('Spark-123')),
    { status: 'available', name: 'Spark-123' },
  );
  assert.deepEqual(
    classifySuggestionCheck('Spa rk-123', available('Spark-123')),
    { status: 'available', name: 'Spark-123' },
  );
  assert.deepEqual(classifySuggestionCheck('Spark-123', taken('Spark-123')), UNAVAILABLE);
  assert.deepEqual(classifySuggestionCheck('Spark-123', available('Spark-124')), UNAVAILABLE);
});
