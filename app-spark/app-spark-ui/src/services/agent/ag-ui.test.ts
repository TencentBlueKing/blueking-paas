import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { ChatMessage } from '../../components/project/interaction/types.ts';
import {
  appendRunError,
  applyAgUiEvent,
  createApplyContext,
  currentTurnAssistant,
  markRunStopped,
  messageHasContent,
} from './ag-ui.ts';

const user = (id: string): ChatMessage => ({ id, role: 'user', blocks: [{ type: 'text', text: id }] });
const assistant = (id: string, text = id): ChatMessage => ({
  id,
  role: 'assistant',
  blocks: [{ type: 'text', text }],
});

test('一段思考从开始到结束落成一块，耗时取自事件的 timestamp', () => {
  const ctx = createApplyContext([user('u1')]);
  for (const event of [
    { type: 'REASONING_START', messageId: 'r1' },
    { type: 'REASONING_MESSAGE_START', messageId: 'r1', timestamp: 1000 },
    { type: 'REASONING_MESSAGE_CONTENT', messageId: 'r1', delta: '先看' },
    { type: 'REASONING_MESSAGE_CONTENT', messageId: 'r1', delta: '目录' },
    { type: 'REASONING_MESSAGE_END', messageId: 'r1', timestamp: 4000 },
    // 正常结束时外层的 END 紧跟着到，不能把已经收好的那段再改一遍。
    { type: 'REASONING_END', messageId: 'r1', timestamp: 9000 },
  ]) applyAgUiEvent(ctx, event);

  const reply = ctx.messages[1];
  assert.equal(reply.role, 'assistant');
  assert.deepEqual(reply.blocks, [{
    type: 'reasoning',
    reasoning: { text: '先看目录', state: 'done', startedAt: 1000, endedAt: 4000 },
  }]);
});

test('等不到结束事件的思考停在 running 上', () => {
  const ctx = createApplyContext([user('u1')]);
  applyAgUiEvent(ctx, { type: 'REASONING_MESSAGE_START', messageId: 'r1' });
  applyAgUiEvent(ctx, { type: 'REASONING_MESSAGE_CONTENT', messageId: 'r1', delta: '想' });
  assert.equal(ctx.messages[1].blocks[0].reasoning?.state, 'running');
});

test('RUN_FINISHED 的 outcome 为 cancelled 时说明这一轮是被停下的', () => {
  const ctx = createApplyContext([]);
  assert.equal(applyAgUiEvent(ctx, { type: 'RUN_FINISHED', outcome: { type: 'cancelled' } }).stopped, true);
  assert.equal(applyAgUiEvent(ctx, { type: 'RUN_FINISHED', outcome: { type: 'success' } }).stopped, false);
  assert.equal(applyAgUiEvent(ctx, { type: 'RUN_FINISHED' }).stopped, false);
});

test('这一轮的助手消息不越过用户消息往前找', () => {
  assert.equal(currentTurnAssistant([assistant('a1'), user('u2')]), undefined);
  assert.equal(currentTurnAssistant([user('u1'), assistant('a1')])?.id, 'a1');
});

test('模型开口之前失败的一轮，报错另起一条，不接到上一轮的回复上', () => {
  const ctx = createApplyContext([user('u1'), assistant('a1'), user('u2')]);
  appendRunError(ctx, '对话失败');

  assert.deepEqual(ctx.messages[1], assistant('a1'));
  const reply = ctx.messages[3];
  assert.equal(reply.tone, 'error');
  assert.deepEqual(reply.blocks, [{ type: 'text', text: '对话失败' }]);
});

test('已经说过话的一轮出错，报错接在末尾，整条不标红', () => {
  const ctx = createApplyContext([user('u1'), assistant('a1')]);
  appendRunError(ctx, '对话失败');
  // 同一句报错不重复接：本服务补的 RUN_ERROR 和 Runtime 自己的可能同时到。
  appendRunError(ctx, '对话失败');

  const reply = ctx.messages[1];
  assert.equal(reply.tone, undefined);
  assert.deepEqual(reply.blocks.map(block => block.text), ['a1', '对话失败']);
});

test('被停下的一轮记在它自己的助手消息上，模型还没开口就新起一条', () => {
  const spoken = createApplyContext([user('u1'), assistant('a1')]);
  markRunStopped(spoken);
  assert.equal(spoken.messages.length, 2);
  assert.equal(spoken.messages[1].stopped, true);

  const silent = createApplyContext([user('u1'), assistant('a1'), user('u2')]);
  markRunStopped(silent);
  assert.equal(silent.messages[1].stopped, undefined);
  assert.equal(silent.messages[3].stopped, true);
});

test('消息有没有看得见的东西', () => {
  const message = (blocks: ChatMessage['blocks'], extra: Partial<ChatMessage> = {}): ChatMessage => ({
    id: 'm',
    role: 'assistant',
    blocks,
    ...extra,
  });
  assert.equal(messageHasContent(message([{ type: 'text', text: '' }])), false);
  assert.equal(messageHasContent(message([{ type: 'text', text: 'hi' }])), true);
  // 思考还没有正文，标题也已经在界面上了。
  assert.equal(messageHasContent(message([{ type: 'reasoning', reasoning: { text: '', state: 'running' } }])), true);
  assert.equal(messageHasContent(message([], { stopped: true })), true);
});
