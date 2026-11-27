import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';

import { createPinia, setActivePinia } from 'pinia';
import RequestError from '../http/fetch/request-error.ts';
import type { RuntimeStateResponse } from '../http/types.ts';
import { callsOf, handlers, resetApi } from '../test-support/http-api.ts';
import { shownMessages } from '../test-support/message.ts';
import { useProjectStore } from './project.ts';

const PROJECT = 'p1';
const NUMBER = 1;
const RUN = 'run-1';

const conversationState = (overrides: Partial<RuntimeStateResponse> = {}): RuntimeStateResponse => ({
  number: NUMBER,
  conversation_id: 'c1',
  is_live: true,
  closed_at: null,
  model: null,
  context_version: 0,
  log_seq: 0,
  ui_event_seq: 0,
  running: false,
  dev_server_status: null,
  replication_pending: false,
  runtime_ready: true,
  run_id: null,
  ...overrides,
});

/** 一条由测试逐条喂事件的 SSE 响应。 */
const controlledSse = () => {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(value) {
      controller = value;
    },
  });
  const encoder = new TextEncoder();
  return {
    response: new Response(body),
    send: (event: Record<string, unknown>) => {
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
    },
    close: () => controller.close(),
    /** 连接在半路断了：本服务重启、网络中断都是这样。 */
    drop: () => controller.error(new TypeError('network error')),
  };
};

/** 等排着的 Promise 回调和 SSE 读取都跑完。 */
const settle = () => new Promise(resolve => setTimeout(resolve, 0));

let store: ReturnType<typeof useProjectStore>;
let serverState: RuntimeStateResponse;

beforeEach(async () => {
  resetApi();
  shownMessages.length = 0;
  setActivePinia(createPinia());
  serverState = conversationState();
  handlers.getConversation = async () => serverState;
  handlers.listHistory = async () => ({ records: [], next_cursor: null, last_seq: 0 });
  handlers.stopConversationRun = async (_project, _number, runId) => ({ run_id: runId, stopping: true });
  store = useProjectStore();
  await store.enterProject(PROJECT, NUMBER);
});

afterEach(() => {
  // 停掉还在等的补历史轮询。
  store.reset();
});

test('RUN_STARTED 之前按下的停止，等 RUN_STARTED 到了补发一次', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const sending = store.sendMessage('做个番茄钟');
  await settle();

  assert.equal(store.canStop, true);
  await store.stopRun();
  assert.equal(store.stopping, true);
  assert.deepEqual(callsOf('stopConversationRun'), []);

  sse.send({ type: 'RUN_STARTED', runId: RUN });
  await settle();
  assert.deepEqual(callsOf('stopConversationRun'), [[PROJECT, NUMBER, RUN]]);

  sse.send({ type: 'RUN_FINISHED', outcome: { type: 'cancelled' } });
  sse.close();
  await sending;

  assert.equal(store.status, 'idle');
  assert.equal(store.stopping, false);
  assert.deepEqual(callsOf('stopConversationRun'), [[PROJECT, NUMBER, RUN]]);
  const reply = store.messages[store.messages.length - 1];
  assert.equal(reply.stopped, true);
  // 被停下的一轮标「已停止」，不再补「本轮对话已结束。」。
  assert.equal(reply.blocks.some(block => block.text), false);
});

test('RUN_STARTED 之前按下停止、SSE 又在 RUN_STARTED 之前断开，恢复时补发停止', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const sending = store.sendMessage('做个番茄钟');
  await settle();
  await store.stopRun();

  // 断开时 Runtime 已经接下这一轮，会话状态里有它的 run ID。
  serverState = conversationState({ running: true, run_id: RUN, ui_event_seq: 3 });
  sse.drop();
  await sending;

  assert.deepEqual(callsOf('stopConversationRun'), [[PROJECT, NUMBER, RUN]]);
  assert.equal(store.stopping, true);
  assert.equal(store.status, 'thinking');
});

test('SSE 断开时这一轮已经结束，不再补发停止', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const sending = store.sendMessage('做个番茄钟');
  await settle();
  await store.stopRun();

  serverState = conversationState({ ui_event_seq: 3 });
  sse.drop();
  await sending;

  assert.deepEqual(callsOf('stopConversationRun'), []);
  assert.equal(store.status, 'idle');
  assert.equal(store.stopping, false);
});

test('/runs/ 直接拒绝时通知输入框恢复草稿', async () => {
  handlers.startConversationRun = async () => {
    throw new RequestError('VALIDATION_ERROR', '请求未通过校验');
  };
  let rejected = 0;

  await store.sendMessage('做个番茄钟', [], undefined, {
    onRejected: () => {
      rejected += 1;
    },
  });

  assert.equal(rejected, 1);
});

test('SSE 已建立后的 RUN_ERROR 不恢复已发送草稿', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  let replicationReads = 0;
  handlers.getConversation = async () => {
    if (!serverState.replication_pending) return serverState;
    replicationReads += 1;
    return replicationReads === 1
      ? serverState
      : conversationState({ ui_event_seq: 4 });
  };
  const historyCallsBeforeRun = callsOf('listHistory').length;
  let rejected = 0;
  const sending = store.sendMessage('做个番茄钟', [], undefined, {
    onRejected: () => {
      rejected += 1;
    },
  });
  await settle();

  sse.send({ type: 'RUN_STARTED', runId: RUN });
  sse.send({
    type: 'RUN_ERROR',
    message: 'status_code: 400, model_name: deepseek-v4-flash, body: model request failed',
  });
  serverState = conversationState({ ui_event_seq: 3, replication_pending: true });
  sse.close();
  await sending;

  assert.equal(rejected, 0);
  assert.equal(store.runEndedWithError, true);
  assert.equal(store.failedRunMayHaveChangedWorkspace, false);
  assert.equal(store.failedRunPreviewSyncSeq, 1);
  assert.equal(store.uiEventSeq, 4);
  assert.equal(store.busy, false);
  assert.equal(callsOf('listHistory').length, historyCallsBeforeRun);
});

test('修改工作区后才 RUN_ERROR 会要求最终预览重载', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const sending = store.sendMessage('改一下首页');
  await settle();

  sse.send({ type: 'RUN_STARTED', runId: RUN });
  sse.send({ type: 'TOOL_CALL_START', toolCallId: 'tool-1', toolCallName: 'write_file' });
  sse.send({ type: 'TOOL_CALL_RESULT', toolCallId: 'tool-1', content: 'ok' });
  sse.send({
    type: 'RUN_ERROR',
    message: 'status_code: 400, model_name: deepseek-v4-flash, body: later model request failed',
  });
  serverState = conversationState({ ui_event_seq: 4 });
  sse.close();
  await sending;

  assert.equal(store.runEndedWithError, true);
  assert.equal(store.failedRunMayHaveChangedWorkspace, true);
  assert.equal(store.failedRunPreviewSyncSeq, 1);
});

test('API 补出的 Runtime 断流错误仍按历史恢复', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const historyCallsBeforeRun = callsOf('listHistory').length;
  const sending = store.sendMessage('做个番茄钟');
  await settle();

  sse.send({ type: 'RUN_STARTED', runId: RUN });
  sse.send({
    type: 'RUN_ERROR',
    message: 'The Agent Runtime stopped responding: connection reset',
  });
  serverState = conversationState({ ui_event_seq: 3 });
  sse.close();
  await sending;

  assert.equal(store.runEndedWithError, false);
  assert.equal(store.failedRunPreviewSyncSeq, 0);
  assert.equal(callsOf('listHistory').length, historyCallsBeforeRun + 1);
});

test('无法识别的 RUN_ERROR 保守地按历史恢复', async () => {
  const sse = controlledSse();
  handlers.startConversationRun = async () => sse.response;
  const historyCallsBeforeRun = callsOf('listHistory').length;
  const sending = store.sendMessage('做个番茄钟');
  await settle();

  sse.send({ type: 'RUN_STARTED', runId: RUN });
  sse.send({ type: 'RUN_ERROR', message: 'unknown runtime error' });
  serverState = conversationState({ ui_event_seq: 3 });
  sse.close();
  await sending;

  assert.equal(store.runEndedWithError, false);
  assert.equal(store.failedRunPreviewSyncSeq, 0);
  assert.equal(callsOf('listHistory').length, historyCallsBeforeRun + 1);
});

/** 进入一个正在跑的会话：run ID 来自会话状态。 */
const enterRunningConversation = async () => {
  serverState = conversationState({ running: true, run_id: RUN });
  await store.enterProject(PROJECT, NUMBER);
  assert.equal(store.canStop, true);
};

test('要停的那一轮已经结束，不算失败', async () => {
  await enterRunningConversation();
  handlers.stopConversationRun = async () => {
    throw new RequestError('RUN_NOT_RUNNING', 'run is not running');
  };
  await store.stopRun();

  assert.equal(store.stopping, true);
  assert.deepEqual(shownMessages, []);
});

test('停止请求失败时提示，并放开按钮好再试', async () => {
  await enterRunningConversation();
  handlers.stopConversationRun = async () => {
    throw new RequestError('INTERNAL_ERROR', '停不下来');
  };
  await store.stopRun();

  assert.equal(store.stopping, false);
  assert.equal(store.canStop, true);
  assert.equal(shownMessages.length, 1);
});

const samplePendingQuestion = {
  tool_call_id: 'call-ask-1',
  questions: [
    {
      header: 'Style',
      question: 'Choose a visual style',
      options: [{ label: 'Minimal' }, { label: 'Bold' }],
      multi_select: false,
    },
  ],
};

test('ask_user_question 暂停后暴露 pendingQuestions 且不补「本轮对话已结束。」，回答后原地更新卡片并续跑', async () => {
  const pauseSse = controlledSse();
  handlers.startConversationRun = async () => pauseSse.response;
  const firstTurn = store.sendMessage('帮我做个记账应用');
  await settle();

  pauseSse.send({ type: 'RUN_STARTED', runId: 'run-pause' });
  pauseSse.send({
    type: 'TOOL_CALL_START',
    toolCallId: 'call-ask-1',
    toolCallName: 'ask_user_question',
  });
  pauseSse.send({
    type: 'TOOL_CALL_ARGS',
    toolCallId: 'call-ask-1',
    delta: JSON.stringify({ questions: samplePendingQuestion.questions }),
  });
  pauseSse.send({ type: 'TOOL_CALL_END', toolCallId: 'call-ask-1' });
  serverState = conversationState({
    ui_event_seq: 4,
    pending_questions: [samplePendingQuestion],
  });
  pauseSse.send({ type: 'RUN_FINISHED' });
  pauseSse.close();
  await firstTurn;

  assert.equal(store.status, 'idle');
  assert.equal(store.hasPendingQuestions, true);
  assert.deepEqual(store.pendingQuestions, [samplePendingQuestion]);
  const pausedReply = store.messages[store.messages.length - 1];
  // 卡片本身是可见内容，不应在上方多补一句「本轮对话已结束。」。
  assert.equal(pausedReply.blocks.some(block => block.type === 'text' && Boolean(block.text)), false);
  const askBlock = pausedReply.blocks.find(block => block.type === 'ask-user');
  assert.equal(askBlock?.askUser?.state, 'pending');

  const resumeSse = controlledSse();
  handlers.startConversationRun = async () => resumeSse.response;
  const userMessageCountBefore = store.messages.filter(item => item.role === 'user').length;
  const answering = store.answerQuestions([
    {
      tool_call_id: 'call-ask-1',
      answers: [{ header: 'Style', selected: ['Bold'] }],
      cancelled: false,
    },
  ], 'model-x');
  await settle();

  // 回答不新增用户气泡，只发 ask_user_responses。
  assert.equal(store.messages.filter(item => item.role === 'user').length, userMessageCountBefore);
  const lastRunCall = callsOf('startConversationRun')[callsOf('startConversationRun').length - 1];
  assert.deepEqual(lastRunCall[2], {
    ask_user_responses: [
      {
        tool_call_id: 'call-ask-1',
        answers: [{ header: 'Style', selected: ['Bold'] }],
        cancelled: false,
      },
    ],
    model_id: 'model-x',
  });

  resumeSse.send({ type: 'RUN_STARTED', runId: 'run-resume' });
  resumeSse.send({
    type: 'TOOL_CALL_RESULT',
    toolCallId: 'call-ask-1',
    content: JSON.stringify({ Style: ['Bold'] }),
  });
  resumeSse.send({ type: 'TEXT_MESSAGE_START', messageId: 'm2', role: 'assistant' });
  resumeSse.send({ type: 'TEXT_MESSAGE_CONTENT', messageId: 'm2', delta: '好的，使用 Bold 风格。' });
  resumeSse.send({ type: 'TEXT_MESSAGE_END', messageId: 'm2' });
  serverState = conversationState({ ui_event_seq: 8, pending_questions: [] });
  resumeSse.send({ type: 'RUN_FINISHED' });
  resumeSse.close();
  const ok = await answering;

  assert.equal(ok, true);
  assert.equal(store.hasPendingQuestions, false);
  assert.equal(askBlock?.askUser?.state, 'answered');
  assert.deepEqual(askBlock?.askUser?.answers, { Style: ['Bold'] });
  const resumedReply = store.messages[store.messages.length - 1];
  assert.equal(resumedReply.blocks.some(block => block.text === '好的，使用 Bold 风格。'), true);
});

test('提交回答被 422 拒绝时保留挂起卡片并撤回空占位消息；409 冲突时同步服务端状态', async () => {
  serverState = conversationState({ pending_questions: [samplePendingQuestion] });
  await store.enterProject(PROJECT, NUMBER);
  assert.equal(store.hasPendingQuestions, true);
  const messageCountBefore = store.messages.length;

  handlers.startConversationRun = async () => {
    throw new RequestError('ASK_USER_RESPONSE_INVALID', 'Invalid option selected');
  };
  const invalidResult = await store.answerQuestions([
    {
      tool_call_id: 'call-ask-1',
      answers: [{ header: 'Style', selected: ['Unknown'] }],
      cancelled: false,
    },
  ]);

  assert.equal(invalidResult, false);
  assert.equal(store.messages.length, messageCountBefore);
  assert.deepEqual(store.pendingQuestions, [samplePendingQuestion]);
  assert.equal(shownMessages[shownMessages.length - 1].theme, 'warning');

  serverState = conversationState({ pending_questions: [] });
  handlers.startConversationRun = async () => {
    throw new RequestError('ASK_USER_CONFLICT', 'No pending questions');
  };
  const conflictResult = await store.answerQuestions([
    { tool_call_id: 'call-ask-1', answers: [], cancelled: true },
  ]);

  assert.equal(conflictResult, false);
  assert.equal(store.messages.length, messageCountBefore);
  assert.deepEqual(store.pendingQuestions, []);
  assert.equal(shownMessages[shownMessages.length - 1].theme, 'warning');
});
