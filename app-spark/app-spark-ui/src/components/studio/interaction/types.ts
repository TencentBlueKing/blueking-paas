export type ChatRole = 'user' | 'assistant';

export interface ChatImage {
  data: string;
  mimeType: string;
  preview: string;
  name?: string;
}

export interface ChatBlock {
  type: 'text' | 'image' | 'summary';
  text?: string;
  items?: string[];
  src?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  blocks: ChatBlock[];
  progress?: string;
}
