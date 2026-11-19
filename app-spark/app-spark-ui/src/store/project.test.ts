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
