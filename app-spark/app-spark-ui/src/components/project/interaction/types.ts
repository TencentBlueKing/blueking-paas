import type { AskUserQuestion } from '@/http/types';

export type ChatRole = 'user' | 'assistant';

export type ChatAttachmentStatus = 'queued' | 'uploading' | 'ready' | 'failed';
export type ChatAttachmentKind = 'pending' | 'image' | 'file';

export interface ChatAttachment {
  localId: string;
  file: File | null;
  mimeType: string;
  kind: ChatAttachmentKind;
  preview: string;
  name: string;
  size: number;
  url?: string | null;
  status: ChatAttachmentStatus;
  attachmentId?: string;
  errorMessage?: string;
}

export interface ChatSendLifecycle {
  /** `/runs/` 在 SSE 建立前直接拒绝时，恢复刚刚乐观清空的可重试草稿。 */
  onRejected?: () => void;
  onAttachmentsInvalid?: (attachmentIds: string[]) => void;
  onImageInputUnsupported?: () => void;
}

/**
 * 界面上的一次工具调用，一行装得下。
 *
 * 只有摘要，没有原始参数：写文件的参数里是整个文件，读文件的返回值也是整个文件，把它们摆进
 * 对话里既看不完也没人要看。参数怎么压成 `label` + `detail`，见 `services/agent/tool-call.ts`。
 */
export interface ChatToolCall {
  /** AG-UI 的 toolCallId，后续的参数与结果事件靠它认人 */
  id: string;
  /** 工具原名，如 `write_file` */
  name: string;
  /** 动作，如「写入文件」 */
  label: string;
  /** 动的是什么，如 `src/main.py`；抽不出来就是空串 */
  detail: string;
  /** `done` 意味着工具真的返回了（收到 TOOL_CALL_RESULT），不是模型把参数说完了 */
  state: 'running' | 'done';
}

/**
 * 模型的一段思考，来自 AG-UI 的 REASONING_* 事件。
 *
 * 只有模型回传了思考内容才会有这一块：Agent 不主动开启思考，有的模型思考了也不回传。
 */
export interface ChatReasoning {
  text: string;
  /** `done` 意味着这段思考说完了（收到它的结束事件），不代表这一轮结束了 */
  state: 'running' | 'done';
  /** 起止时刻（毫秒），取自事件自带的 timestamp，回放历史时也算得出耗时；缺了就不报耗时 */
  startedAt?: number;
  endedAt?: number;
}

export type ChatAskUserState = 'streaming' | 'pending' | 'answered' | 'declined' | 'bypassed';

/**
 * Agent 发起的结构化澄清提问卡片，对应 `ask_user_question` 工具调用。
 *
 * 与普通 `tool` 块分开建模：工具调用是一行摘要，而提问卡片需要保留完整问题和选项，并在
 * 收到 `TOOL_CALL_RESULT` 后原地收敛为已回答 / 已跳过 / 已旁路的摘要态。
 */
export interface ChatAskUser {
  /** AG-UI 的 toolCallId，提交回答或回放结果时靠它定位对应卡片 */
  id: string;
  questions: AskUserQuestion[];
  state: ChatAskUserState;
  /** 已回答时，每个问题 header 对应的选项或自定义输入列表 */
  answers?: Record<string, string[]>;
}

export interface ChatBlock {
  type: 'text' | 'image' | 'file' | 'summary' | 'tool' | 'reasoning' | 'ask-user';
  text?: string;
  items?: string[];
  src?: string;
  href?: string;
  filename?: string;
  size?: number;
  tool?: ChatToolCall;
  reasoning?: ChatReasoning;
  askUser?: ChatAskUser;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  blocks: ChatBlock[];
  progress?: string;
  tone?: 'error';
  /** 这一轮是被用户停下的，见 RUN_FINISHED 的 `outcome` */
  stopped?: boolean;
}
