import type { ChatImage } from './types';

const MAX_EDGE = 2048;
const MAX_COUNT = 3;
const ALLOWED = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif']);

export const compressImage = (file: File): Promise<ChatImage> => new Promise((resolve, reject) => {
  if (!ALLOWED.has(file.type)) {
    reject(new Error('只支持 PNG / JPG / WEBP / GIF'));
    return;
  }

  const reader = new FileReader();
  reader.onerror = () => reject(new Error('读取图片失败'));
  reader.onload = () => {
    const image = new Image();
    image.onerror = () => reject(new Error('图片无法解析'));
    image.onload = () => {
      let { width, height } = image;
      if (Math.max(width, height) > MAX_EDGE) {
        const scale = MAX_EDGE / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');
      if (!context) {
        reject(new Error('图片处理失败'));
        return;
      }
      context.drawImage(image, 0, 0, width, height);

      const mimeType = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
      const preview = canvas.toDataURL(mimeType, 0.86);
      const data = preview.split(',')[1] || '';
      if (!data) {
        reject(new Error('图片压缩失败'));
        return;
      }
      resolve({
        data,
        mimeType,
        preview,
        name: file.name,
      });
    };
    image.src = String(reader.result || '');
  };
  reader.readAsDataURL(file);
});

export const appendImages = async (current: ChatImage[], files: File[]) => {
  const room = MAX_COUNT - current.length;
  if (room <= 0) {
    throw new Error(`最多上传 ${MAX_COUNT} 张图片`);
  }
  const next = await Promise.all(files.slice(0, room).map(compressImage));
  return [...current, ...next];
};
