import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { AskUserQuestion } from '../../http/types.ts';
import {
  ASK_USER_BYPASSED_RESULT,
  ASK_USER_DECLINED_RESULT,
  buildAskUserResponse,
  createEmptyAskUserDraft,
  isAskUserDraftComplete,
  parseAskUserQuestions,
  parseAskUserResult,
} from './ask-user.ts';

const sampleQuestions: AskUserQuestion[] = [
  {
    header: 'Style',
    question: 'Choose a visual style',
    options: [
      { label: 'Minimal', description: 'Clean layout' },
      { label: 'Bold' },
    ],
    multi_select: false,
  },
  {
    header: 'Features',
    question: 'Pick features to include',
    options: [
      { label: 'Dark mode' },
      { label: 'Export CSV' },
    ],
    multi_select: true,
  },
];

test('parseAskUserQuestions 解析完整 JSON 并忽略半截内容', () => {
  assert.equal(parseAskUserQuestions('{"questions":['), null);
  assert.equal(parseAskUserQuestions('{}'), null);

  const parsed = parseAskUserQuestions(JSON.stringify({
    questions: [
      {
        header: 'Style',
        question: 'Choose style',
        options: [{ label: 'Minimal', description: 'Clean' }, { label: 'Bold' }],
        multi_select: false,
      },
      {
        header: 'Features',
        question: 'Pick features',
        options: [{ label: 'Export' }],
        multiSelect: true,
      },
    ],
  }));

  assert.deepEqual(parsed, [
    {
      header: 'Style',
      question: 'Choose style',
      options: [{ label: 'Minimal', description: 'Clean' }, { label: 'Bold' }],
      multi_select: false,
    },
    {
      header: 'Features',
      question: 'Pick features',
      options: [{ label: 'Export' }],
      multi_select: true,
    },
  ]);
});

test('parseAskUserResult 区分回答、跳过与直接发新消息旁路', () => {
  assert.deepEqual(parseAskUserResult(ASK_USER_DECLINED_RESULT), { state: 'declined' });
  assert.deepEqual(parseAskUserResult(ASK_USER_BYPASSED_RESULT), { state: 'bypassed' });
  assert.deepEqual(
    parseAskUserResult(JSON.stringify({ Style: ['Bold'], Features: ['Dark mode', 'Export CSV'] })),
    {
      state: 'answered',
      answers: { Style: ['Bold'], Features: ['Dark mode', 'Export CSV'] },
    },
  );
  assert.deepEqual(parseAskUserResult('unexpected plain text'), {
    state: 'answered',
    answers: {},
  });
});

test('草稿校验与构建请求体遵守预设选项和自定义输入互斥约束', () => {
  const draft = createEmptyAskUserDraft(sampleQuestions);
  assert.equal(isAskUserDraftComplete(sampleQuestions, draft), false);

  draft.Style.selected = ['Minimal'];
  assert.equal(isAskUserDraftComplete(sampleQuestions, draft), false);

  draft.Features.useCustom = true;
  draft.Features.customAnswer = '   ';
  assert.equal(isAskUserDraftComplete(sampleQuestions, draft), false);

  draft.Features.customAnswer = '  Keyboard shortcuts  ';
  assert.equal(isAskUserDraftComplete(sampleQuestions, draft), true);

  assert.deepEqual(buildAskUserResponse('call-ask-1', sampleQuestions, draft), {
    tool_call_id: 'call-ask-1',
    answers: [
      { header: 'Style', selected: ['Minimal'] },
      { header: 'Features', selected: [], custom_answer: 'Keyboard shortcuts' },
    ],
    cancelled: false,
  });
});
