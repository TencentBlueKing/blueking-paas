<template>
  <div class="reasoning" :class="{ 'is-expanded': expanded }">
    <button
      type="button"
      class="reasoning__header"
      :aria-expanded="expanded"
      @click="toggle"
    >
      <LiveDot v-if="isRunning" :live="live" />
      <span class="reasoning__label">{{ label }}</span>
      <AngleDownLine class="reasoning__arrow" />
    </button>
    <div
      v-if="expanded && reasoning.text"
      ref="bodyRef"
      class="reasoning__body"
    >
      {{ reasoning.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { AngleDownLine } from 'bkui-vue/lib/icon';
import humanizeDuration from 'humanize-duration';
import LiveDot from './LiveDot.vue';
import type { ChatReasoning } from './types';

const props = defineProps<{
  reasoning: ChatReasoning;
  /** 这一轮对话还在进行中，含义同 `ToolCallBlock` 的 `live`。 */
  live?: boolean;
}>();

const isRunning = computed(() => props.reasoning.state === 'running');

/**
 * 默认收起，只在标题上报个状态：思考文字往往很长，摊开会把正文挤到下面去，想看的人自己点开。
 *
 * 回放一段在思考途中被打断的历史时，这段思考停在 running 上，但 `live` 是假的：它不会再动了，
 * 不该再说「思考中」。
 */
const isStreaming = computed(() => isRunning.value && Boolean(props.live));
const expanded = ref(false);

/**
 * 「8 秒」「2 分钟 5 秒」：只留最大的两级单位，给人看个大概。不到一秒按一秒报，否则取整后是「0 秒」。
 */
const formatElapsed = (ms: number) => humanizeDuration(Math.max(ms, 1000), {
  language: 'zh_CN',
  largest: 2,
  round: true,
  delimiter: ' ',
  spacer: ' ',
});

const label = computed(() => {
  if (isStreaming.value) return '思考中';
  const { startedAt, endedAt } = props.reasoning;
  if (startedAt === undefined || endedAt === undefined) return '已思考';
  return `已思考（耗时 ${formatElapsed(endedAt - startedAt)}）`;
});

const toggle = () => {
  expanded.value = !expanded.value;
};

// 正文区限了高度，流式追加时把它钉在底部，否则看到的永远是开头那几行。
const bodyRef = ref<HTMLElement | null>(null);
watch(() => props.reasoning.text, async () => {
  if (!isStreaming.value) return;
  await nextTick();
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight;
});
</script>

<style lang="postcss" scoped>
.reasoning {
  margin: 6px 0;
  color: #7a8494;
  font-size: 13px;
  line-height: 1.6;
}

.reasoning__header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  background: none;
  border: 0;
}

.reasoning__header:hover {
  color: #424a57;
}

.reasoning__arrow {
  font-size: 14px;
  transform: rotate(-90deg);
  transition: transform 0.15s ease;
}

.reasoning.is-expanded .reasoning__arrow {
  transform: none;
}

.reasoning__body {
  max-height: 240px;
  margin-top: 4px;
  padding: 2px 0 2px 10px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border-left: 2px solid #e4e8ef;
}

@media (prefers-reduced-motion: reduce) {
  .reasoning__arrow {
    transition: none;
  }
}
</style>
