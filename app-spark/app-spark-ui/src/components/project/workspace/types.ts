export type WorkspaceView = 'preview' | 'code';
export type WorkspaceDevice = 'mobile' | 'desktop';

/**
 * 预览面板这一刻该画什么。只有 `ready` 会带上 iframe src。
 *
 * `starting` 是进程已起、端口还没应答，继续等，不当成失败。
 */
export type PreviewPhase =
  | 'no-conversation'
  | 'ended'
  | 'pending'
  | 'unavailable'
  | 'not_started'
  | 'starting'
  | 'stopped'
  | 'ready';
