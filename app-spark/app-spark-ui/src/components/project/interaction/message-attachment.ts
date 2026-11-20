import { resolveApiUrl } from '@/http/resolve-api-url';
import type { ChatBlock } from './types';

export interface MessageAttachmentInput {
  kind: 'image' | 'file';
  filename: string;
  size: number;
  url?: string | null;
  /** 刚发送时优先使用本地图片，重新进入会话后则只传后端 url。 */
  preview?: string;
}

/** 将草稿附件和历史附件统一转换为消息列表使用的图片或文件块。 */
export const toAttachmentBlock = ({
  kind,
  filename,
  size,
  url,
  preview,
}: MessageAttachmentInput): ChatBlock => {
  const resolvedUrl = url ? resolveApiUrl(url) : undefined;
  if (kind === 'image') {
    return {
      type: 'image',
      src: preview || resolvedUrl,
      filename,
    };
  }
  return {
    type: 'file',
    href: resolvedUrl,
    filename,
    size,
  };
};
