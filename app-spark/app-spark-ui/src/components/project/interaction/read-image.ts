const MAX_EDGE = 2048;
export const MAX_IMAGE_COUNT = 3;
export const IMAGE_TYPE_ERROR = '只支持 PNG、JPG、JPEG、WebP';

const ALLOWED = new Set(['image/png', 'image/jpeg', 'image/webp']);
const EXTENSION_MIME_TYPES: Record<string, string> = {
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  webp: 'image/webp',
};

export interface CompressedImage {
  file: File;
  mimeType: string;
  preview: string;
  name: string;
}

export const getImageMimeType = (file: Pick<File, 'name' | 'type'>): string | null => {
  const declared = file.type.trim().toLowerCase();
  if (declared) return ALLOWED.has(declared) ? declared : null;
  const extension = file.name.split('.').pop()?.toLowerCase() || '';
  return EXTENSION_MIME_TYPES[extension] || null;
};

const readAsDataUrl = (file: Blob): Promise<string> => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onerror = () => reject(new Error('读取图片失败'));
  reader.onload = () => resolve(String(reader.result || ''));
  reader.readAsDataURL(file);
});

const encodeCanvas = (
  canvas: HTMLCanvasElement,
  mimeType: string,
  source: File,
): Promise<CompressedImage> => new Promise((resolve, reject) => {
  canvas.toBlob(async (blob) => {
    if (!blob) {
      reject(new Error('图片压缩失败'));
      return;
    }
    const file = new File([blob], source.name, {
      type: mimeType,
      lastModified: source.lastModified,
    });
    try {
      const preview = await readAsDataUrl(file);
      if (!preview) throw new Error('图片压缩失败');
      resolve({ file, mimeType, preview, name: source.name });
    } catch (error) {
      reject(error);
    }
  }, mimeType, mimeType === 'image/jpeg' ? 0.86 : undefined);
});

export const compressImage = (file: File): Promise<CompressedImage> => new Promise((resolve, reject) => {
  const sourceMimeType = getImageMimeType(file);
  if (!sourceMimeType) {
    reject(new Error(IMAGE_TYPE_ERROR));
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

      const mimeType = sourceMimeType === 'image/png' ? 'image/png' : 'image/jpeg';
      void encodeCanvas(canvas, mimeType, file).then(resolve, reject);
    };
    image.src = String(reader.result || '');
  };
  reader.readAsDataURL(file);
});
