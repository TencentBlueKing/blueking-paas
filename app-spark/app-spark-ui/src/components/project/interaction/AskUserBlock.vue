<template>
  <div v-if="askUser.state === 'streaming'" class="ask-user ask-user--streaming">
    <LiveDot :live="live" />
    <span>正在整理确认问题…</span>
  </div>

  <div v-else-if="askUser.state === 'answered'" class="ask-user ask-user--summary">
    <div class="ask-user__summary-head">
      <Done class="ask-user__check" />
      <span>已确认需求细节</span>
    </div>
    <dl v-if="answeredEntries.length" class="ask-user__summary-list">
      <div
        v-for="entry in answeredEntries"
        :key="entry.header"
        class="ask-user__summary-row"
      >
        <dt>{{ entry.header }}</dt>
        <dd>{{ entry.values.join('、') }}</dd>
      </div>
    </dl>
  </div>

  <div v-else-if="askUser.state === 'declined'" class="ask-user ask-user--muted">
    <Done class="ask-user__check is-muted" />
    <span>已跳过确认，按默认方案继续</span>
  </div>

  <div v-else-if="askUser.state === 'bypassed'" class="ask-user ask-user--muted">
    <Done class="ask-user__check is-muted" />
    <span>已直接回复新消息继续</span>
  </div>

  <section
    v-else
    class="ask-user ask-user--card"
    :class="{ 'is-readonly': !interactive }"
  >
    <header class="ask-user__header">
      <strong>需要确认以下细节</strong>
      <span v-if="!interactive" class="ask-user__badge">
        {{ busy ? '处理中' : '已结束' }}
      </span>
      <span v-else-if="askUser.questions.length > 1" class="ask-user__badge">
        共 {{ askUser.questions.length }} 项
      </span>
    </header>

    <div class="ask-user__questions">
      <div
        v-for="(item, qIndex) in askUser.questions"
        :key="item.header || qIndex"
        class="ask-user__question"
      >
        <div class="ask-user__q-head">
          <span class="ask-user__q-chip">{{ item.header }}</span>
          <span v-if="item.multi_select" class="ask-user__q-mode">可多选</span>
        </div>
        <p class="ask-user__q-text">{{ item.question }}</p>

        <div
          class="ask-user__options"
          :role="item.multi_select ? 'group' : 'radiogroup'"
          :aria-label="item.header"
        >
          <button
            v-for="option in item.options"
            :key="option.label"
            type="button"
            class="ask-user__option"
            :class="{ 'is-selected': isOptionSelected(item.header, option.label) }"
            :disabled="!interactive"
            @click="toggleOption(item, option.label)"
          >
            <span
              class="ask-user__indicator"
              :class="{ 'is-multi': item.multi_select }"
              aria-hidden="true"
            />
            <span class="ask-user__option-body">
              <span class="ask-user__option-label">{{ option.label }}</span>
              <span v-if="option.description" class="ask-user__option-desc">
                {{ option.description }}
              </span>
            </span>
          </button>

          <div
            v-if="interactive"
            class="ask-user__custom"
            :class="{ 'is-selected': isCustomSelected(item.header) }"
          >
            <button
              type="button"
              class="ask-user__option ask-user__option--custom"
              :class="{ 'is-selected': isCustomSelected(item.header) }"
              :disabled="!interactive"
              @click="selectCustom(item.header)"
            >
              <span
                class="ask-user__indicator"
                :class="{ 'is-multi': item.multi_select }"
                aria-hidden="true"
              />
              <span class="ask-user__option-body">
                <span class="ask-user__option-label">其他（自定义说明）</span>
              </span>
            </button>
            <input
              v-if="isCustomSelected(item.header)"
              v-model="ensureEntry(item.header).customAnswer"
              type="text"
              class="ask-user__custom-input"
              placeholder="输入你的想法…"
              @keydown.enter.prevent="handleSubmit"
            >
          </div>
        </div>
      </div>
    </div>

    <footer v-if="interactive" class="ask-user__footer">
      <button
        type="button"
        class="ask-user__btn ask-user__btn--ghost"
        :disabled="busy"
        @click="handleSkip"
      >
        跳过，按推荐继续
      </button>
      <button
        type="button"
        class="ask-user__btn ask-user__btn--primary"
        :disabled="busy || !canSubmit"
        @click="handleSubmit"
      >
        提交回答
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue';
import { Done } from 'bkui-vue/lib/icon';
import type { AskUserQuestion, AskUserResponseInput } from '@/http/types';
import {
  buildAskUserResponse,
  createEmptyAskUserDraft,
  isAskUserDraftComplete,
} from '@/services/agent/ask-user';
import type { AskUserDraftEntry } from '@/services/agent/ask-user';
import LiveDot from './LiveDot.vue';
import type { ChatAskUser } from './types';

const props = defineProps<{
  askUser: ChatAskUser;
  live?: boolean;
  /** 仅当卡片属于后端当前挂起的 `pending_questions` 且会话活跃空闲时允许作答。 */
  interactive?: boolean;
  busy?: boolean;
}>();

const emit = defineEmits<{
  (e: 'submit', response: AskUserResponseInput): void;
}>();

const draft = reactive<Record<string, AskUserDraftEntry>>({});

const syncDraftWithQuestions = (questions: AskUserQuestion[]) => {
  const fresh = createEmptyAskUserDraft(questions);
  for (const [header, entry] of Object.entries(fresh)) {
    if (!draft[header]) draft[header] = entry;
  }
};

watch(() => props.askUser.questions, syncDraftWithQuestions, { immediate: true, deep: true });

const ensureEntry = (header: string): AskUserDraftEntry => {
  if (!draft[header]) {
    draft[header] = { selected: [], useCustom: false, customAnswer: '' };
  }
  return draft[header];
};

const isOptionSelected = (header: string, label: string) => {
  const entry = draft[header];
  return Boolean(entry && !entry.useCustom && entry.selected.includes(label));
};

const isCustomSelected = (header: string) => Boolean(draft[header]?.useCustom);

const toggleOption = (question: AskUserQuestion, label: string) => {
  if (!props.interactive) return;
  const entry = ensureEntry(question.header);
  entry.useCustom = false;
  if (question.multi_select) {
    const idx = entry.selected.indexOf(label);
    if (idx >= 0) entry.selected.splice(idx, 1);
    else entry.selected.push(label);
  } else {
    entry.selected = [label];
  }
};

const selectCustom = (header: string) => {
  if (!props.interactive) return;
  const entry = ensureEntry(header);
  entry.useCustom = true;
  entry.selected = [];
};

const canSubmit = computed(() => (
  Boolean(props.interactive) && isAskUserDraftComplete(props.askUser.questions, draft)
));

const answeredEntries = computed(() => {
  const answers = props.askUser.answers || {};
  return Object.entries(answers)
    .filter(([, values]) => values.length > 0)
    .map(([header, values]) => ({ header, values }));
});

const handleSubmit = () => {
  if (!canSubmit.value || props.busy) return;
  emit('submit', buildAskUserResponse(props.askUser.id, props.askUser.questions, draft));
};

const handleSkip = () => {
  if (!props.interactive || props.busy) return;
  emit('submit', {
    tool_call_id: props.askUser.id,
    answers: [],
    cancelled: true,
  });
};
</script>

<style lang="postcss" scoped>
.ask-user {
  margin: 8px 0;
  font-size: 13px;
  line-height: 1.5;
}

.ask-user--streaming,
.ask-user--muted {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  color: #5a6270;
  background: #f5f7fa;
  border-radius: 8px;
}

.ask-user--summary {
  padding: 8px 10px;
  background: #f5f7fa;
  border: 1px solid #e7ecf3;
  border-radius: 10px;
}

.ask-user__summary-head {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #424a57;
  font-weight: 500;
}

.ask-user__summary-list {
  margin: 6px 0 0;
  padding: 0;
}

.ask-user__summary-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
}

.ask-user__summary-row dt {
  flex-shrink: 0;
  color: #7a8494;
}

.ask-user__summary-row dd {
  margin: 0;
  color: #1d2026;
  word-break: break-word;
}

.ask-user__check {
  flex-shrink: 0;
  color: #2f5bff;
  font-size: 14px;
}

.ask-user__check.is-muted {
  color: #8b93a0;
}

.ask-user--card {
  padding: 12px;
  background: #f9fbff;
  border: 1px solid #dce5f7;
  border-radius: 12px;
}

.ask-user--card.is-readonly {
  background: #f7f9fc;
  border-color: #e4e8ef;
}

.ask-user__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.ask-user__header strong {
  color: var(--ink, #12141a);
  font-size: 13px;
  font-weight: 600;
}

.ask-user__badge {
  padding: 1px 7px;
  color: #5a6270;
  font-size: 11px;
  background: #edf1f8;
  border-radius: 999px;
}

.ask-user__questions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ask-user__q-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.ask-user__q-chip {
  padding: 1px 7px;
  color: #2f5bff;
  font-size: 11px;
  font-weight: 500;
  background: #eaf0ff;
  border-radius: 6px;
}

.ask-user__q-mode {
  color: #7a8494;
  font-size: 11px;
}

.ask-user__q-text {
  margin: 0 0 8px;
  color: var(--ink, #12141a);
  font-size: 13px;
  font-weight: 500;
}

.ask-user__options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ask-user__option {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  color: inherit;
  text-align: left;
  background: #fff;
  border: 1px solid #e1e6f0;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.ask-user__option:hover:not(:disabled) {
  border-color: #9fb5ff;
}

.ask-user__option.is-selected {
  background: #f0f4ff;
  border-color: var(--accent, #3d6dff);
}

.ask-user__option:disabled {
  cursor: default;
  opacity: 0.78;
}

.ask-user__indicator {
  box-sizing: border-box;
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  margin-top: 3px;
  background: #fff;
  border: 1.5px solid #c0c8d6;
  border-radius: 50%;
}

.ask-user__indicator.is-multi {
  border-radius: 4px;
}

.ask-user__option.is-selected .ask-user__indicator {
  border-width: 4px;
  border-color: var(--accent, #3d6dff);
}

.ask-user__option.is-selected .ask-user__indicator.is-multi {
  background: var(--accent, #3d6dff);
  border-width: 1.5px;
}

.ask-user__option-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ask-user__option-label {
  color: var(--ink, #12141a);
  font-size: 13px;
  font-weight: 500;
  word-break: break-word;
}

.ask-user__option-desc {
  color: #6f7886;
  font-size: 12px;
  line-height: 1.45;
  word-break: break-word;
}

.ask-user__custom {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ask-user__custom-input {
  box-sizing: border-box;
  width: 100%;
  padding: 7px 10px;
  color: var(--ink, #12141a);
  font-size: 13px;
  background: #fff;
  border: 1px solid #9fb5ff;
  border-radius: 8px;
}

.ask-user__custom-input:focus {
  border-color: var(--accent, #3d6dff);
  outline: none;
}

.ask-user__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e7ecf5;
}

.ask-user__btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
}

.ask-user__btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.ask-user__btn--ghost {
  color: #5a6270;
  background: transparent;
  border: 1px solid #d8dee9;
}

.ask-user__btn--ghost:hover:not(:disabled) {
  color: var(--ink, #12141a);
  background: #eef2f8;
}

.ask-user__btn--primary {
  color: #fff;
  background: var(--accent, #3d6dff);
  border: 1px solid transparent;
}

.ask-user__btn--primary:hover:not(:disabled) {
  background: #1f46d6;
}

@media (prefers-reduced-motion: reduce) {
  .ask-user__option {
    transition: none;
  }
}
</style>
