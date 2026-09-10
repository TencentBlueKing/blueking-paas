import type { ChatMessage } from '@/components/project/interaction/types';
import type { AgUiEvent } from '@/http/types';

export type AgUiRunStatus = 'idle' | 'thinking' | 'streaming';

export interface AgUiApplyContext {
  messages: ChatMessage[];
  byId: Map<string, ChatMessage>;
}

export interface AgUiApplyResult {
  status?: AgUiRunStatus;
  progress?: string;
  errorText?: string;
  done?: boolean;
}

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

const getTextBlock = (message: ChatMessage) => {
  let block = message.blocks.find(item => item.type === 'text');
  if (!block) {
    block = { type: 'text', text: '' };
    message.blocks.unshift(block);
  }
  return block;
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
  if (messageId) ctx.byId.set(messageId, message);
  return message;
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
    case 'TOOL_CALL_START':
      return {
        status: 'thinking',
        progress: String(event.toolCallName || event.name || '正在调用工具…'),
      };
    default:
      return {};
  }
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
