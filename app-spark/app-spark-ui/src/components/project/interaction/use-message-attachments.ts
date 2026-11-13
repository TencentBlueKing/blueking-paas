import { computed, onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import Message from '@/common/message';
import { uploadConversationAttachment } from '@/http/api';
import { ApiErrorCode, isApiError } from '@/http/error-codes';
import type { ChatImage } from './types';
import {
  compressImage,
  getImageMimeType,
  IMAGE_TYPE_ERROR,
  MAX_IMAGE_COUNT,
} from './read-image';

interface AttachmentTarget {
  projectId: Ref<string>;
  conversationNumber: Ref<number | null>;
}

const createLocalId = () => `image-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export const useMessageAttachments = ({
  projectId,
  conversationNumber,
}: AttachmentTarget) => {
  const images = ref<ChatImage[]>([]);
  let generation = 0;
  let uploadQueue = Promise.resolve();
  const uploadControllers = new Map<string, AbortController>();

  const findImage = (localId: string, targetGeneration: number) => {
    if (targetGeneration !== generation) return null;
    return images.value.find(image => image.localId === localId) ?? null;
  };

  const removeImage = (localId: string) => {
    uploadControllers.get(localId)?.abort();
    uploadControllers.delete(localId);
    const index = images.value.findIndex(image => image.localId === localId);
    if (index !== -1) images.value.splice(index, 1);
  };

  const handleUploadError = (localId: string, targetGeneration: number, error: unknown) => {
    const image = findImage(localId, targetGeneration);
    if (!image) return;

    if (isApiError(error, ApiErrorCode.ATTACHMENT_TOO_LARGE)) {
      removeImage(localId);
      Message({ theme: 'warning', message: '图片超过 5MB，请换一张小一些的' });
      return;
    }
    if (isApiError(error, ApiErrorCode.ATTACHMENT_TYPE_UNSUPPORTED)) {
      removeImage(localId);
      Message({ theme: 'warning', message: IMAGE_TYPE_ERROR });
      return;
    }

    image.status = 'failed';
    if (isApiError(error, ApiErrorCode.ATTACHMENT_STORAGE_UNAVAILABLE)) {
      image.errorMessage = '图片暂时存不了，请稍后重试';
    } else if (isApiError(error, ApiErrorCode.CONVERSATION_CLOSED)) {
      image.errorMessage = '会话已结束，不能再添加图片';
    } else {
      image.errorMessage = error instanceof Error && error.message
        ? error.message
        : '图片上传失败，请稍后重试';
    }
    Message({ theme: 'warning', message: image.errorMessage });
  };

  const enqueueUpload = (
    localId: string,
    targetGeneration: number,
    targetProjectId: string,
    targetNumber: number,
    compressed: ReturnType<typeof compressImage>,
  ) => {
    // 压缩可以并行开始，但立即接住失败，避免后面的图片在等待上传队列时产生未处理拒绝。
    const settled = compressed.then(
      (result) => {
        const image = findImage(localId, targetGeneration);
        if (image) {
          image.file = result.file;
          image.mimeType = result.mimeType;
          image.preview = result.preview;
          image.name = result.name;
        }
        return { result, error: null as unknown };
      },
      (error) => {
        if (findImage(localId, targetGeneration)) {
          removeImage(localId);
          Message({
            theme: 'warning',
            message: error instanceof Error ? error.message : '图片处理失败',
          });
        }
        return { result: null, error };
      },
    );
    uploadQueue = uploadQueue.then(async () => {
      const outcome = await settled;
      if (!outcome.result) return;
      const { result } = outcome;

      const image = findImage(localId, targetGeneration);
      if (!image) return;
      image.status = 'uploading';
      image.errorMessage = undefined;

      const controller = new AbortController();
      uploadControllers.set(localId, controller);
      try {
        const attachment = await uploadConversationAttachment(
          targetProjectId,
          targetNumber,
          result.file,
          controller.signal,
        );
        const current = findImage(localId, targetGeneration);
        if (!current) return;
        current.attachmentId = attachment.id;
        current.status = 'ready';
        current.errorMessage = undefined;
      } catch (error) {
        handleUploadError(localId, targetGeneration, error);
      } finally {
        if (uploadControllers.get(localId) === controller) {
          uploadControllers.delete(localId);
        }
      }
    });
  };

  const addFiles = (files: File[]) => {
    if (!files.length || !projectId.value || conversationNumber.value == null) return;
    const room = MAX_IMAGE_COUNT - images.value.length;
    if (room <= 0) {
      Message({ theme: 'warning', message: `最多上传 ${MAX_IMAGE_COUNT} 张图片` });
      return;
    }

    const selected = files.slice(0, room);
    if (files.length > room) {
      Message({ theme: 'warning', message: `最多上传 ${MAX_IMAGE_COUNT} 张图片` });
    }

    const targetGeneration = generation;
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    let hasUnsupported = false;
    for (const file of selected) {
      const mimeType = getImageMimeType(file);
      if (!mimeType) {
        hasUnsupported = true;
        continue;
      }
      const localId = createLocalId();
      images.value.push({
        localId,
        file,
        mimeType,
        preview: '',
        name: file.name,
        status: 'processing',
      });
      enqueueUpload(
        localId,
        targetGeneration,
        targetProjectId,
        targetNumber,
        compressImage(file),
      );
    }
    if (hasUnsupported) {
      Message({ theme: 'warning', message: IMAGE_TYPE_ERROR });
    }
  };

  const retryImage = (localId: string) => {
    const image = images.value.find(item => item.localId === localId);
    if (
      !image
      || image.status !== 'failed'
      || !image.file
      || !projectId.value
      || conversationNumber.value == null
    ) return;
    image.status = 'uploading';
    image.errorMessage = undefined;
    const result = Promise.resolve({
      file: image.file,
      mimeType: image.mimeType,
      preview: image.preview,
      name: image.name,
    });
    enqueueUpload(
      localId,
      generation,
      projectId.value,
      conversationNumber.value,
      result,
    );
  };

  const removeSubmittedImages = (attachmentIds: string[]) => {
    const submitted = new Set(attachmentIds);
    images.value = images.value.filter(image => (
      !image.attachmentId || !submitted.has(image.attachmentId)
    ));
  };

  const clearImages = () => {
    uploadControllers.forEach(controller => controller.abort());
    uploadControllers.clear();
    images.value = [];
  };

  watch([projectId, conversationNumber], () => {
    generation += 1;
    uploadQueue = Promise.resolve();
    clearImages();
  });

  onScopeDispose(() => {
    generation += 1;
    clearImages();
  });

  return {
    images,
    hasPendingImages: computed(() => images.value.some(image => (
      image.status === 'processing' || image.status === 'uploading'
    ))),
    hasFailedImages: computed(() => images.value.some(image => image.status === 'failed')),
    readyImages: computed(() => images.value.filter(image => (
      image.status === 'ready' && Boolean(image.attachmentId)
    ))),
    addFiles,
    retryImage,
    removeImage,
    removeSubmittedImages,
    clearImages,
  };
};
