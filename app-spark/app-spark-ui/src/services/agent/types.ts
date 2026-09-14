export interface AppFile {
  path: string;
  content: string;
}

export type AgentEvent =
  | { type: 'delta'; text: string }
  | { type: 'status'; text: string }
  | { type: 'summary'; items: string[] }
  | { type: 'files'; files: AppFile[] }
  | { type: 'error'; text: string }
  | { type: 'done' };
