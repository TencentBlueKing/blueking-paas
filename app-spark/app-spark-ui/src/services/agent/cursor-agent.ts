import type { ChatImage } from '@/components/studio/interaction/types';
import type { AgentEvent } from './types';

const parseSseChunk = (chunk: string): AgentEvent[] => {
  const events: AgentEvent[] = [];
  for (const block of chunk.split('\n\n')) {
    const line = block.split('\n').find(item => item.startsWith('data: '));
    if (!line) continue;
    events.push(JSON.parse(line.slice(6)));
  }
  return events;
};

const agentBase = (process.env.BK_AGENT_DEV_URL || '').replace(/\/$/, '');

export async function* runCursorAgent(
  message: string,
  images: ChatImage[] = [],
): AsyncGenerator<AgentEvent> {
  const response = await fetch(`${agentBase}/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      images: images.map(image => ({
        data: image.data,
        mimeType: image.mimeType,
      })),
    }),
  });

  if (!response.ok || !response.body) {
    const text = await response.text();
    let detail = text || `Agent 服务异常（${response.status}）`;
    try {
      detail = JSON.parse(text).message || detail;
    } catch {
      // keep raw text
    }
    yield { type: 'error', text: detail };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    for (const event of parseSseChunk(`${parts.join('\n\n')}${parts.length ? '\n\n' : ''}`)) {
      yield event;
    }
  }

  if (buffer.trim()) {
    for (const event of parseSseChunk(`${buffer}\n\n`)) {
      yield event;
    }
  }
}
