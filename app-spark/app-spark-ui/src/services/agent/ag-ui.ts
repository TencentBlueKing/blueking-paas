import type { ChatBlock, ChatMessage, ChatToolCall } from '@/components/project/interaction/types';
import type { AgUiEvent, UserMessageRecord } from '@/http/types';
import { describeToolCall } from '@/services/agent/tool-call';

export type AgUiRunStatus = 'idle' | 'thinking' | 'streaming';

/** 一次还没收完的工具调用：界面上那一行，加上攒到一半的参数。 */
interface PendingToolCall {
  tool: ChatToolCall;
  /**
   * 累积的参数 JSON。只留开头一段：这里唯一的用途是抽出一行摘要，而写文件的参数带着整个文件，
   * 全存下来就是把一份文件副本挂在对话上。
   */
  args: string;
}

export interface AgUiApplyContext {
  messages: ChatMessage[];
  byId: Map<string, ChatMessage>;
  /** toolCallId -> 那次调用，后续的参数与结果事件靠它找回自己那一行 */
  toolCalls: Map<string, PendingToolCall>;
}

export interface AgUiApplyResult {
  status?: AgUiRunStatus;
  progress?: string;
  errorText?: string;
  done?: boolean;
}

export const createApplyContext = (messages: ChatMessage[]): AgUiApplyContext => ({
  messages,
  byId: new Map(),
  toolCalls: new Map(),
});

const createLocalId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const normalizeAgUiType = (type: unknown) => (
  String(type || '')
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/-/g, '_')
    .toUpperCase()
);

export const unwrapUiRecord = (record: AgUiEvent): AgUiEvent => {
  if (typeof record.type === 'string') return record;
  const nested = [record.event, record.payload, record.data]
    .find(item => item && typeof item === 'object' && typeof (item as AgUiEvent).type === 'string');
  return (nested as AgUiEvent) || record;
};

export const getRecordSeq = (record: AgUiEvent): number | null => {
  const raw = record.seq ?? record.ui_event_seq ?? unwrapUiRecord(record).seq;
  const seq = Number(raw);
  return Number.isFinite(seq) ? seq : null;
};

/**
 * 把块接到消息末尾，并把「接进去之后」的那一份还回来。
 *
 * 不能接着用传进来的那个对象：消息列表是 Vue 的响应式数组，push 进去的是原始对象，之后只有改
 * 从数组里读回来的那个代理才会触发重渲染。工具调用那一行的摘要和状态是后面几个事件慢慢补齐
 * 的，拿错了这一份，界面会一直停在「正在执行」。
 */
const appendBlock = (message: ChatMessage, block: ChatBlock): ChatBlock => {
  message.blocks.push(block);
  return message.blocks[message.blocks.length - 1];
};

/**
 * 取这条消息末尾那个文本块，用来接住下一段文本增量。
 *
 * 认「最后一个块」而不是「第一个文本块」：工具调用和文本在同一条消息里按发生顺序排着，一次调
 * 用之后模型接着说的话得落在那次调用下面，而不是回头续进它上面的段落。
 */
const getTextBlock = (message: ChatMessage) => {
  const last = message.blocks[message.blocks.length - 1];
  return last?.type === 'text' ? last : appendBlock(message, { type: 'text', text: '' });
};

const upsertMessage = (
  ctx: AgUiApplyContext,
  messageId: string,
  role: ChatMessage['role'],
) => {
  if (messageId && ctx.byId.has(messageId)) {
    return ctx.byId.get(messageId);
  }

  if (role === 'assistant') {
    const last = ctx.messages[ctx.messages.length - 1];
    const emptyAssistant = last?.role === 'assistant'
      && !last.blocks.some(block => block.type === 'text' && block.text);
    if (emptyAssistant && last) {
      if (messageId) ctx.byId.set(messageId, last);
      return last;
    }
  }

  const message: ChatMessage = {
    id: messageId || createLocalId(),
    role,
    blocks: [{ type: 'text', text: '' }],
  };
  ctx.messages.push(message);
  // 同 `appendBlock`：往下要改的是接进列表之后的那一份，不是手里这个原始对象。
  const stored = ctx.messages[ctx.messages.length - 1];
  if (messageId) ctx.byId.set(messageId, stored);
  return stored;
};

/**
 * 工具调用挂到哪条消息上：末尾那条助手消息，没有就新起一条。
 *
 * 事件里的 `parentMessageId` 是可选的，而且指向的本来就是刚说完话的那条助手消息，也就是末尾
 * 这条，所以不必绕一圈去查——真按 id 挂反而会把一次调用插回更早的位置，读起来是乱的。
 */
const currentAssistant = (ctx: AgUiApplyContext): ChatMessage => {
  const last = ctx.messages[ctx.messages.length - 1];
  if (last?.role === 'assistant') return last;
  ctx.messages.push({ id: createLocalId(), role: 'assistant', blocks: [] });
  return ctx.messages[ctx.messages.length - 1];
};

/** 参数只用来抽一行摘要，留个开头就够，其余的直接丢掉。 */
const MAX_TOOL_ARGS = 4096;

const refreshToolCall = (pending: PendingToolCall) => {
  const display = describeToolCall(pending.tool.name, pending.args);
  pending.tool.label = display.label;
  pending.tool.detail = display.detail;
};

const getToolCallId = (event: AgUiEvent) => String(event.toolCallId ?? event.tool_call_id ?? '');

const startToolCall = (ctx: AgUiApplyContext, event: AgUiEvent) => {
  const toolCallId = getToolCallId(event);
  const name = String(event.toolCallName ?? event.tool_call_name ?? event.name ?? '');
  const block = appendBlock(currentAssistant(ctx), {
    type: 'tool',
    tool: { id: toolCallId, name, label: '', detail: '', state: 'running' },
  });
  // `ChatBlock.tool` 是可选字段，靠 narrow 而不是断言拿它：断言等于替编译器打包票说上面那个
  // 字面量一定原样传了回来，而 `appendBlock` 还回来的是响应式代理，真有一天不是了也没人会提醒。
  if (block.type !== 'tool' || !block.tool) return;
  const pending: PendingToolCall = { tool: block.tool, args: '' };
  refreshToolCall(pending);
  if (toolCallId) ctx.toolCalls.set(toolCallId, pending);
};

const growToolCallArgs = (ctx: AgUiApplyContext, event: AgUiEvent, delta: string) => {
  const pending = ctx.toolCalls.get(getToolCallId(event));
  if (!pending || !delta) return;
  // 按剩下的额度裁掉再接，而不是「没超就整片接上」：一片本身就可能是整份文件——write_file 完全
  // 可以把 content 一次送完——那样第一片就把上限冲过去了，上限也就白设了。
  const room = MAX_TOOL_ARGS - pending.args.length;
  if (room > 0) {
    pending.args += delta.slice(0, room);
  }
  // 摘要一旦抽出来就不再逐片重算：参数可以有几万片，而要找的那个字段在开头就传完了。
  if (!pending.tool.detail) refreshToolCall(pending);
};

export const applyAgUiEvent = (
  ctx: AgUiApplyContext,
  rawEvent: AgUiEvent,
  options: { ignoreUser?: boolean } = {},
): AgUiApplyResult => {
  const event = unwrapUiRecord(rawEvent);
  const type = normalizeAgUiType(event.type);
  const messageId = String(event.messageId ?? event.message_id ?? '');
  const role = String(event.role || '').toLowerCase();
  const delta = String(event.delta ?? event.content ?? '');
  const chatRole: ChatMessage['role'] = role === 'user' ? 'user' : 'assistant';

  if (options.ignoreUser && (chatRole === 'user' || type.includes('USER_MESSAGE'))) {
    return {};
  }

  switch (type) {
    case 'TEXT_MESSAGE_START': {
      upsertMessage(ctx, messageId, chatRole);
      return chatRole === 'assistant' ? { status: 'thinking' } : {};
    }
    case 'TEXT_MESSAGE_CONTENT':
    case 'TEXT_MESSAGE_CHUNK': {
      if (!delta && type === 'TEXT_MESSAGE_CHUNK' && !messageId) return {};
      const message = upsertMessage(ctx, messageId, chatRole);
      if (delta) {
        const block = getTextBlock(message);
        block.text = `${block.text || ''}${delta}`;
      }
      return message.role === 'assistant' && delta ? { status: 'streaming' } : {};
    }
    case 'TEXT_MESSAGE_END':
      return {};
    case 'RUN_STARTED':
      return { status: 'thinking' };
    case 'RUN_FINISHED':
      return { status: 'idle', done: true };
    case 'RUN_ERROR':
      return {
        status: 'idle',
        done: true,
        errorText: String(event.message || event.error || event.detail || '对话失败'),
      };
    case 'STEP_STARTED':
      return {
        status: 'thinking',
        progress: String(event.stepName || event.step || event.name || '正在处理…'),
      };
    // 一次工具调用摊成四个事件：START 报名字，ARGS 一片片送参数，END 表示参数说完了，
    // RESULT 才是工具真的返回。界面上它们合成一行，状态跟着这条线走。
    case 'TOOL_CALL_START':
      startToolCall(ctx, event);
      // 调用本身已经在时间线上占了一行，进度条再重复一遍工具名就是噪音。
      return { status: 'thinking', progress: '' };
    case 'TOOL_CALL_ARGS':
      growToolCallArgs(ctx, event, delta);
      return {};
    case 'TOOL_CALL_END': {
      // 参数齐了，用完整的 JSON 再算一次，盖掉流式期间那份可能不准的摘要。
      const pending = ctx.toolCalls.get(getToolCallId(event));
      if (pending) refreshToolCall(pending);
      return {};
    }
    case 'TOOL_CALL_RESULT': {
      // 只记「跑完了」，不展示返回值：read_file 之类的返回值就是整个文件。
      const pending = ctx.toolCalls.get(getToolCallId(event));
      if (pending) pending.tool.state = 'done';
      return {};
    }
    default:
      return {};
  }
};

/**
 * 把历史里的一条用户输入接到消息列表末尾。
 *
 * 不走 `upsertMessage`：那条路是给 AG-UI 事件用的，靠事件自带的 messageId 认人，而用户输入是
 * 后端另一张表里的记录，没有那个 id。消息 id 用后端主键拼出来，回放同一段历史两次也不会出现两
 * 个不同 id 的同一条输入。
 */
export const appendUserMessage = (
  ctx: AgUiApplyContext,
  record: UserMessageRecord,
): ChatMessage | null => {
  const text = String(record.content ?? '');
  if (!text) return null;

  const message: ChatMessage = {
    id: `user-${record.id}`,
    role: 'user',
    blocks: [{ type: 'text', text }],
  };
  ctx.messages.push(message);
  return message;
};

export const createWelcomeMessage = (): ChatMessage => ({
  id: 'welcome',
  role: 'assistant',
  blocks: [{
    type: 'text',
    text: '用自然语言描述你想做的改动。发送后我会改应用，中间预览会跟着更新。',
  }],
});

export const hasConversationContent = (messages: ChatMessage[]) => (
  messages.some(message => (
    message.id !== 'welcome'
    && message.blocks.some(block => (
      (block.type === 'text' && Boolean(block.text))
      || (block.type === 'image' && Boolean(block.src))
      || block.type === 'tool'
    ))
  ))
);

export async function* readSseEvents(response: Response): AsyncGenerator<AgUiEvent> {
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const consume = (chunk: string): AgUiEvent[] => {
    const events: AgUiEvent[] = [];
    for (const block of chunk.split('\n\n')) {
      const raw = block
        .split('\n')
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n');
      if (!raw || raw === '[DONE]') continue;
      try {
        events.push(JSON.parse(raw));
      } catch {
        // 忽略非 JSON 心跳
      }
    }
    return events;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    for (const event of consume(`${parts.join('\n\n')}${parts.length ? '\n\n' : ''}`)) {
      yield event;
    }
  }

  if (buffer.trim()) {
    for (const event of consume(`${buffer}\n\n`)) {
      yield event;
    }
  }
}
