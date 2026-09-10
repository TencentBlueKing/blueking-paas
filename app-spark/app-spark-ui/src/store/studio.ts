import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { ChatImage, ChatMessage } from '@/components/studio/interaction/types';
import { runCursorAgent } from '@/services/agent/cursor-agent';

const IMAGE_PROMPT = '请根据附图实现页面，尽量还原布局、颜色、文案和间距。';

export type StudioStatus = 'idle' | 'thinking' | 'streaming';

const createId = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

export const useStudioStore = defineStore('studio', () => {
  const messages = ref<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      blocks: [{
        type: 'text',
        text: '描述你想改的内容，也可以上传设计稿或截图。我会让 Cursor Agent 修改 template，中间预览会热更新。',
      }],
    },
  ]);
  const status = ref<StudioStatus>('idle');
  const busy = computed(() => status.value !== 'idle');

  const sendMessage = async (text: string, images: ChatImage[] = []) => {
    const content = text.trim() || (images.length ? IMAGE_PROMPT : '');
    if ((!content && !images.length) || busy.value) return;

    messages.value.push({
      id: createId(),
      role: 'user',
      blocks: [
        ...images.map(image => ({ type: 'image' as const, src: image.preview })),
        { type: 'text', text: content },
      ],
    });

    const assistantId = createId();
    messages.value.push({
      id: assistantId,
      role: 'assistant',
      blocks: [{ type: 'text', text: '' }],
    });
    status.value = 'thinking';

    try {
      for await (const event of runCursorAgent(content, images)) {
        const assistant = messages.value.find(item => item.id === assistantId);
        if (!assistant) continue;

        if (event.type === 'status') {
          assistant.progress = event.text;
        }

        if (event.type === 'delta') {
          status.value = 'streaming';
          assistant.progress = '';
          const textBlock = assistant.blocks.find(block => block.type === 'text');
          if (textBlock) {
            textBlock.text = `${textBlock.text || ''}${event.text}`;
          }
        }

        if (event.type === 'summary') {
          const existed = assistant.blocks.find(block => (
            block.type === 'summary' && block.items?.join() === event.items.join()
          ));
          if (!existed) {
            assistant.blocks.push({ type: 'summary', items: event.items });
          }
        }

        if (event.type === 'error') {
          assistant.progress = '';
          const textBlock = assistant.blocks.find(block => block.type === 'text');
          if (textBlock && !textBlock.text) {
            textBlock.text = event.text;
          } else {
            assistant.blocks.push({ type: 'text', text: event.text });
          }
        }
      }
    } catch (error) {
      const assistant = messages.value.find(item => item.id === assistantId);
      const textBlock = assistant?.blocks.find(block => block.type === 'text');
      if (textBlock && !textBlock.text) {
        textBlock.text = error instanceof Error ? error.message : '请求 Agent 失败';
      }
    } finally {
      const assistant = messages.value.find(item => item.id === assistantId);
      if (assistant) {
        assistant.progress = '';
        const textBlock = assistant.blocks.find(block => block.type === 'text');
        const hasSummary = assistant.blocks.some(block => block.type === 'summary' && block.items?.length);
        if (textBlock && !textBlock.text && !hasSummary) {
          textBlock.text = '已完成修改，预览已更新。';
        }
      }
      status.value = 'idle';
    }
  };

  return {
    messages,
    status,
    busy,
    sendMessage,
  };
});
