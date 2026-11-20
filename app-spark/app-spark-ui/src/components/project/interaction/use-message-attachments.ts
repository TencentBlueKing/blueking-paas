import { computed, onScopeDispose, ref, watch } from 'vue';
import type { Ref } from 'vue';
import Message from '@/common/message';
import { uploadConversationAttachment } from '@/http/api';
import { ApiErrorCode, isApiError } from '@/http/error-codes';
import { resolveApiUrl } from '@/http/resolve-api-url';
import type { ChatAttachment } from './types';
import {
  ATTACHMENT_SIZE_ERROR,
  detectImageAttachmentMimeType,
  isAttachmentSizeAllowed,
  isImageAttachmentMimeType,
  MAX_ATTACHMENT_COUNT,
  readAttachmentPreview,
} from './attachment';

interface AttachmentTarget {
  projectId: Ref<string>;
  conversationNumber: Ref<number | null>;
}

const createLocalId = () => `attachment-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export const useMessageAttachments = ({
  projectId,
  conversationNumber,
}: AttachmentTarget) => {
  const attachments = ref<ChatAttachment[]>([]);
  let generation = 0;
  // 产品约定按用户添加顺序串行上传，保持输入框展示与后端落库顺序一致。
  let uploadQueue = Promise.resolve();
  const uploadControllers = new Map<string, AbortController>();

  const findAttachment = (localId: string, targetGeneration: number) => {
    if (targetGeneration !== generation) return null;
    return attachments.value.find(attachment => attachment.localId === localId) ?? null;
  };

  const removeAttachment = (localId: string) => {
    uploadControllers.get(localId)?.abort();
    uploadControllers.delete(localId);
    const index = attachments.value.findIndex(attachment => attachment.localId === localId);
    if (index !== -1) attachments.value.splice(index, 1);
  };

  const handleUploadError = (localId: string, targetGeneration: number, error: unknown) => {
    const attachment = findAttachment(localId, targetGeneration);
    if (!attachment) return;

    if (isApiError(error, ApiErrorCode.ATTACHMENT_TOO_LARGE)) {
      removeAttachment(localId);
      Message({ theme: 'warning', message: ATTACHMENT_SIZE_ERROR });
      return;
    }

    attachment.status = 'failed';
    if (isApiError(error, ApiErrorCode.ATTACHMENT_STORAGE_UNAVAILABLE)) {
      attachment.errorMessage = '暂时存不了，可重试';
    } else if (isApiError(error, ApiErrorCode.CONVERSATION_CLOSED)) {
      attachment.errorMessage = '会话已结束，不能再添加附件';
    } else {
      attachment.errorMessage = error instanceof Error && error.message
        ? error.message
        : '文件上传失败，请稍后重试';
    }
    Message({ theme: 'warning', message: attachment.errorMessage });
  };

  const prepareLocalImagePreview = async (
    localId: string,
    targetGeneration: number,
    file: File,
  ) => {
    try {
      const mimeType = await detectImageAttachmentMimeType(file);
      if (!mimeType) return;
      const preview = await readAttachmentPreview(file);
      const attachment = findAttachment(localId, targetGeneration);
      // 上传响应已经回来时以响应的 mime_type 为准，不能被稍晚完成的本地识别覆盖。
      if (!attachment || attachment.status === 'ready') return;
      attachment.kind = 'image';
      attachment.mimeType = mimeType;
      attachment.preview = preview;
    } catch {
      // 预渲染失败不影响原文件上传，最终类型与展示仍由接口响应决定。
    }
  };

  const enqueueUpload = (
    localId: string,
    targetGeneration: number,
    targetProjectId: string,
    targetNumber: number,
    file: File,
  ) => {
    uploadQueue = uploadQueue.then(async () => {
      const attachment = findAttachment(localId, targetGeneration);
      if (!attachment) return;
      attachment.status = 'uploading';
      attachment.errorMessage = undefined;

      const controller = new AbortController();
      uploadControllers.set(localId, controller);
      try {
        const uploaded = await uploadConversationAttachment(
          targetProjectId,
          targetNumber,
          file,
          controller.signal,
        );
        const current = findAttachment(localId, targetGeneration);
        if (!current) return;
        current.attachmentId = uploaded.id;
        current.mimeType = uploaded.mime_type;
        current.kind = isImageAttachmentMimeType(uploaded.mime_type) ? 'image' : 'file';
        current.name = uploaded.filename;
        current.size = uploaded.size;
        current.url = uploaded.url;
        if (current.kind === 'file') current.preview = '';
        if (current.kind === 'image') {
          if (uploaded.url) {
            // 上传期间用本地预览保证即时反馈；成功后切到服务端地址，避免大块 data URL
            // 跟着乐观消息在整个会话生命周期里常驻内存。
            current.preview = resolveApiUrl(uploaded.url);
          } else if (!current.preview) {
            void readAttachmentPreview(file).then((preview) => {
              const latest = findAttachment(localId, targetGeneration);
              if (latest?.attachmentId === uploaded.id) latest.preview = preview;
            }).catch(() => undefined);
          }
        }
        // 上传成功后重试只需复用 attachment ID，不再长期持有原始 File。
        current.file = null;
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
    const room = MAX_ATTACHMENT_COUNT - attachments.value.length;
    if (room <= 0) {
      Message({ theme: 'warning', message: `最多上传 ${MAX_ATTACHMENT_COUNT} 个附件` });
      return;
    }

    const selected = files.slice(0, room);
    if (files.length > room) {
      Message({ theme: 'warning', message: `最多上传 ${MAX_ATTACHMENT_COUNT} 个附件` });
    }

    const targetGeneration = generation;
    const targetProjectId = projectId.value;
    const targetNumber = conversationNumber.value;
    let hasTooLarge = false;
    for (const file of selected) {
      if (!isAttachmentSizeAllowed(file)) {
        hasTooLarge = true;
        continue;
      }
      const localId = createLocalId();
      attachments.value.push({
        localId,
        file,
        mimeType: '',
        kind: 'pending',
        preview: '',
        name: file.name,
        size: file.size,
        status: 'queued',
      });
      void prepareLocalImagePreview(localId, targetGeneration, file);
      enqueueUpload(
        localId,
        targetGeneration,
        targetProjectId,
        targetNumber,
        file,
      );
    }
    if (hasTooLarge) {
      Message({ theme: 'warning', message: ATTACHMENT_SIZE_ERROR });
    }
  };

  const retryAttachment = (localId: string) => {
    const attachment = attachments.value.find(item => item.localId === localId);
    if (
      !attachment
      || attachment.status !== 'failed'
      || !attachment.file
      || !projectId.value
      || conversationNumber.value == null
    ) return;
    attachment.status = 'queued';
    attachment.errorMessage = undefined;
    enqueueUpload(
      localId,
      generation,
      projectId.value,
      conversationNumber.value,
      attachment.file,
    );
  };

  const removeSubmittedAttachments = (attachmentIds: string[]) => {
    const submitted = new Set(attachmentIds);
    const retained: ChatAttachment[] = [];
    for (const attachment of attachments.value) {
      if (!attachment.attachmentId || !submitted.has(attachment.attachmentId)) {
        retained.push(attachment);
      }
    }
    attachments.value = retained;
  };

  const restoreSubmittedAttachments = (
    submittedAttachments: ChatAttachment[],
    originalOrder: string[],
  ) => {
    const byLocalId = new Map<string, ChatAttachment>();
    for (const attachment of submittedAttachments) {
      byLocalId.set(attachment.localId, attachment);
    }
    // 若拒绝响应到达前仍有附件留在草稿中，以当前对象为准。
    for (const attachment of attachments.value) {
      byLocalId.set(attachment.localId, attachment);
    }

    const restored: ChatAttachment[] = [];
    for (const localId of originalOrder) {
      const attachment = byLocalId.get(localId);
      if (!attachment) continue;
      restored.push(attachment);
      byLocalId.delete(localId);
    }
    // 保留极短时间窗口内可能新增的附件，不因恢复旧草稿而丢失。
    restored.push(...byLocalId.values());
    attachments.value = restored;
  };

  const clearAttachments = () => {
    uploadControllers.forEach(controller => controller.abort());
    uploadControllers.clear();
    attachments.value = [];
  };

  watch([projectId, conversationNumber], () => {
    generation += 1;
    uploadQueue = Promise.resolve();
    clearAttachments();
  });

  onScopeDispose(() => {
    generation += 1;
    clearAttachments();
  });

  return {
    attachments,
    attachmentLimitReached: computed(() => attachments.value.length >= MAX_ATTACHMENT_COUNT),
    hasPendingAttachments: computed(() => attachments.value.some(attachment => (
      attachment.status === 'queued' || attachment.status === 'uploading'
    ))),
    hasFailedAttachments: computed(() => (
      attachments.value.some(attachment => attachment.status === 'failed')
    )),
    readyAttachments: computed(() => attachments.value.filter(attachment => (
      attachment.status === 'ready' && Boolean(attachment.attachmentId)
    ))),
    addFiles,
    retryAttachment,
    removeAttachment,
    removeSubmittedAttachments,
    restoreSubmittedAttachments,
    clearAttachments,
  };
};
