export const MAX_ATTACHMENT_COUNT = 3;
export const MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024;
export const ATTACHMENT_SIZE_ERROR = '文件超过 5MB';

const IMAGE_MIME_TYPES = new Set([
  'image/gif',
  'image/jpeg',
  'image/png',
  'image/webp',
]);

/** 附件种类只认上传接口返回的 MIME；SVG、HTML 等即使浏览器能预览也按文件下载。 */
export const isImageAttachmentMimeType = (mimeType: string): boolean => (
  IMAGE_MIME_TYPES.has(mimeType.trim().toLowerCase())
);

const startsWith = (bytes: Uint8Array, signature: number[]) => (
  signature.every((value, index) => bytes[index] === value)
);

/**
 * 只用于上传期间的预渲染；上传响应的 mime_type 仍是最终分类依据。
 * 读取文件头而不是扩展名或浏览器 file.type，避免普通文件先以图片形式闪现。
 */
export const detectImageAttachmentMimeType = async (file: Blob): Promise<string | null> => {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  if (startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) {
    return 'image/png';
  }
  if (startsWith(bytes, [0xff, 0xd8, 0xff])) return 'image/jpeg';
  if (
    startsWith(bytes, [0x47, 0x49, 0x46, 0x38, 0x37, 0x61])
    || startsWith(bytes, [0x47, 0x49, 0x46, 0x38, 0x39, 0x61])
  ) {
    return 'image/gif';
  }
  if (
    startsWith(bytes, [0x52, 0x49, 0x46, 0x46])
    && startsWith(bytes.slice(8), [0x57, 0x45, 0x42, 0x50])
  ) {
    return 'image/webp';
  }
  return null;
};

export const isAttachmentSizeAllowed = (file: Pick<File, 'size'>): boolean => (
  file.size <= MAX_ATTACHMENT_SIZE_BYTES
);

export const readAttachmentPreview = (file: Blob): Promise<string> => new Promise(
  (resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('读取图片失败'));
    reader.onload = () => resolve(String(reader.result || ''));
    reader.readAsDataURL(file);
  },
);

/** 文本模型只跳过图片，文件仍按草稿中的顺序发送。 */
export const selectSendableAttachments = <T extends { kind: string }>(
  attachments: T[],
  supportsImageInput: boolean,
): T[] => attachments.filter(attachment => (
  attachment.kind !== 'image' || supportsImageInput
));

export const formatAttachmentSize = (size: number): string => {
  const bytes = Math.max(0, Number.isFinite(size) ? size : 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) {
    return `${Number((bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0))} KB`;
  }
  return `${Number((bytes / 1024 / 1024).toFixed(1))} MB`;
};
