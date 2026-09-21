export type ChatRole = 'user' | 'assistant';

export interface ChatImage {
  data: string;
  mimeType: string;
  preview: string;
  name?: string;
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

export interface ChatBlock {
  type: 'text' | 'image' | 'summary' | 'tool';
  text?: string;
  items?: string[];
  src?: string;
  tool?: ChatToolCall;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  blocks: ChatBlock[];
  progress?: string;
  tone?: 'error';
}
