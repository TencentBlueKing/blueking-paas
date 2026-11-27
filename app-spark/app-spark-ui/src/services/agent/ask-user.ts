import type {
  AskUserAnswerInput,
  AskUserOption,
  AskUserQuestion,
  AskUserResponseInput,
} from '@/http/types';

/** Agent 发起澄清提问时使用的工具名，与 pydantic-ai-harness 的 AskUser 保持一致。 */
export const ASK_USER_TOOL_NAME = 'ask_user_question';

/** 用户点击跳过后 Agent 写进 TOOL_CALL_RESULT 的固定文案。 */
export const ASK_USER_DECLINED_RESULT = (
  'The user declined to answer. Continue without the answer, or ask differently if it is essential.'
);

/** 用户未操作卡片而是直接发了新消息时，Agent 关闭旧提问写进 TOOL_CALL_RESULT 的固定文案。 */
export const ASK_USER_BYPASSED_RESULT = (
  "The user did not answer the question directly and sent a new message instead. Follow the user's new message."
);

export interface AskUserDraftEntry {
  selected: string[];
  useCustom: boolean;
  customAnswer: string;
}

export interface ParsedAskUserResult {
  state: 'answered' | 'declined' | 'bypassed';
  answers?: Record<string, string[]>;
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
  Boolean(value) && typeof value === 'object' && !Array.isArray(value)
);

const parseOption = (raw: unknown): AskUserOption | null => {
  if (!isRecord(raw) || typeof raw.label !== 'string' || !raw.label.trim()) return null;
  const description = typeof raw.description === 'string' && raw.description.trim()
    ? raw.description
    : undefined;
  return description ? { label: raw.label, description } : { label: raw.label };
};

const parseQuestion = (raw: unknown): AskUserQuestion | null => {
  if (!isRecord(raw)) return null;
  if (typeof raw.question !== 'string' || !raw.question.trim()) return null;
  if (typeof raw.header !== 'string' || !raw.header.trim()) return null;
  if (!Array.isArray(raw.options)) return null;
  const options = raw.options
    .map(parseOption)
    .filter((option): option is AskUserOption => option !== null);
  if (!options.length) return null;
  return {
    question: raw.question,
    header: raw.header,
    options,
    multi_select: Boolean(raw.multi_select ?? raw.multiSelect),
  };
};

/**
 * 解析 `ask_user_question` 工具参数 JSON 中的问题列表。
 *
 * 参数在流式阶段可能不完整，解析失败返回 null，等 `TOOL_CALL_END` 再解析完整文本。
 */
export const parseAskUserQuestions = (argsText: string): AskUserQuestion[] | null => {
  const trimmed = argsText.trim();
  if (!trimmed.startsWith('{')) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return null;
  }
  if (!isRecord(parsed) || !Array.isArray(parsed.questions)) return null;
  const questions = parsed.questions
    .map(parseQuestion)
    .filter((item): item is AskUserQuestion => item !== null);
  return questions.length ? questions : null;
};

const normalizeAnswersMap = (raw: Record<string, unknown>): Record<string, string[]> => {
  const result: Record<string, string[]> = {};
  for (const [header, value] of Object.entries(raw)) {
    if (Array.isArray(value)) {
      const items = value
        .map(item => (typeof item === 'string' ? item.trim() : ''))
        .filter(Boolean);
      if (items.length) result[header] = items;
    } else if (typeof value === 'string' && value.trim()) {
      result[header] = [value.trim()];
    }
  }
  return result;
};

/**
 * 解析 `ask_user_question` 的 `TOOL_CALL_RESULT.content`。
 *
 * Agent 会写入三种载荷之一：跳过固定文案、旁路固定文案，或 `Record<header, string[]>` JSON。
 */
export const parseAskUserResult = (content: unknown): ParsedAskUserResult => {
  if (typeof content === 'string') {
    const trimmed = content.trim();
    if (trimmed === ASK_USER_DECLINED_RESULT) return { state: 'declined' };
    if (trimmed === ASK_USER_BYPASSED_RESULT) return { state: 'bypassed' };
    if (trimmed.startsWith('{')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (isRecord(parsed)) {
          return { state: 'answered', answers: normalizeAnswersMap(parsed) };
        }
      } catch {
        // 非 JSON 结果兜底为已回答，避免卡片永久停留在可交互态。
      }
    }
    return { state: 'answered', answers: {} };
  }
  if (isRecord(content)) {
    return { state: 'answered', answers: normalizeAnswersMap(content) };
  }
  return { state: 'answered', answers: {} };
};

export const createEmptyAskUserDraft = (
  questions: AskUserQuestion[],
): Record<string, AskUserDraftEntry> => {
  const draft: Record<string, AskUserDraftEntry> = {};
  for (const question of questions) {
    draft[question.header] = {
      selected: [],
      useCustom: false,
      customAnswer: '',
    };
  }
  return draft;
};

/**
 * 判断每道题是否都已填写合法回答。
 *
 * 与后端 `check_response` 约束对齐：预设选项和自定义输入互斥；未走自定义时至少选一项，
 * 单选题最多选一项；走自定义时输入去空后非空。
 */
export const isAskUserDraftComplete = (
  questions: AskUserQuestion[],
  draft: Record<string, AskUserDraftEntry>,
): boolean => {
  if (!questions.length) return false;
  return questions.every((question) => {
    const entry = draft[question.header];
    if (!entry) return false;
    if (entry.useCustom) {
      return Boolean(entry.customAnswer.trim());
    }
    if (!entry.selected.length) return false;
    return question.multi_select || entry.selected.length === 1;
  });
};

export const buildAskUserResponse = (
  toolCallId: string,
  questions: AskUserQuestion[],
  draft: Record<string, AskUserDraftEntry>,
): AskUserResponseInput => {
  const answers: AskUserAnswerInput[] = questions.map((question) => {
    const entry = draft[question.header];
    if (entry?.useCustom) {
      return {
        header: question.header,
        selected: [],
        custom_answer: entry.customAnswer.trim(),
      };
    }
    return {
      header: question.header,
      selected: [...(entry?.selected || [])],
    };
  });
  return {
    tool_call_id: toolCallId,
    answers,
    cancelled: false,
  };
};
