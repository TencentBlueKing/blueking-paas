import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';

import {
  effectScope,
  nextTick,
  ref,
} from 'vue';
import type { EffectScope } from 'vue';
import RequestError from '../../../http/fetch/request-error.ts';
import { ApiErrorCode } from '../../../http/error-codes.ts';
import { handlers, resetApi } from '../../../test-support/http-api.ts';
import { shownMessages } from '../../../test-support/message.ts';
import type { ChatAttachment } from './types.ts';
import { useMessageAttachments } from './use-message-attachments.ts';

class TestFileReader {
  result: string | ArrayBuffer | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onload: ((event: unknown) => void) | null = null;

  readAsDataURL(blob: Blob) {
    void blob.arrayBuffer()
      .then((buffer) => {
        this.result = `data:${blob.type || 'application/octet-stream'};base64,${
          Buffer.from(buffer).toString('base64')
        }`;
        this.onload?.({ target: this });
      })
      .catch(error => this.onerror?.(error));
  }
}

Object.defineProperty(globalThis, 'FileReader', {
  value: TestFileReader,
  configurable: true,
});
Object.defineProperty(globalThis, 'window', {
  value: { SITE_URL: '' },
  configurable: true,
});
Object.defineProperty(globalThis, 'location', {
  value: { origin: 'https://spark.example.com' },
  configurable: true,
});

const uploaded = (file: File, id = file.name) => ({
  id,
  filename: file.name,
  mime_type: file.type || 'application/octet-stream',
  size: file.size,
  url: `/api-svc/attachments/${id}`,
  created_at: '2026-11-19T10:00:00+08:00',
});

const settle = async () => {
  await new Promise(resolve => setTimeout(resolve, 0));
  await nextTick();
};

let scope: EffectScope;
let projectId: ReturnType<typeof ref<string>>;
let conversationNumber: ReturnType<typeof ref<number | null>>;
let attachmentsState: ReturnType<typeof useMessageAttachments>;

beforeEach(() => {
  resetApi();
  shownMessages.length = 0;
  projectId = ref('p1');
  conversationNumber = ref<number | null>(1);
  scope = effectScope();
  scope.run(() => {
    attachmentsState = useMessageAttachments({ projectId, conversationNumber });
  });
});

afterEach(() => {
  scope.stop();
});

test('切换会话会取消在途上传并丢弃迟到的回包', async () => {
  let uploadSignal!: AbortSignal;
  let finishUpload!: (value: ReturnType<typeof uploaded>) => void;
  handlers.uploadConversationAttachment = async (
    _projectId,
    _number,
    file: File,
    signal: AbortSignal,
  ) => new Promise((resolve) => {
    uploadSignal = signal;
    finishUpload = resolve;
  });

  const file = new File(['hello'], 'note.txt', { type: 'text/plain' });
  attachmentsState.addFiles([file]);
  await settle();

  conversationNumber.value = 2;
  await nextTick();
  assert.equal(uploadSignal.aborted, true);
  finishUpload(uploaded(file));
  await settle();
  assert.deepEqual(attachmentsState.attachments.value, []);
});

test('上传失败后可以使用原文件重试', async () => {
  let attempts = 0;
  handlers.uploadConversationAttachment = async (_projectId, _number, file: File) => {
    attempts += 1;
    if (attempts === 1) {
      throw new RequestError(
        ApiErrorCode.ATTACHMENT_STORAGE_UNAVAILABLE,
        'storage unavailable',
      );
    }
    return uploaded(file);
  };

  attachmentsState.addFiles([new File(['hello'], 'note.txt', { type: 'text/plain' })]);
  await settle();
  const [failed] = attachmentsState.attachments.value;
  assert.equal(failed.status, 'failed');

  attachmentsState.retryAttachment(failed.localId);
  await settle();
  assert.equal(attachmentsState.attachments.value[0].status, 'ready');
  assert.equal(attachmentsState.attachments.value[0].attachmentId, 'note.txt');
  assert.equal(attempts, 2);
});

test('图片上传成功后改用服务端地址并释放原始文件', async () => {
  handlers.uploadConversationAttachment = async (_projectId, _number, value: File) => uploaded(value);
  const file = new File([
    new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  ], 'shot.png', { type: 'image/png' });

  attachmentsState.addFiles([file]);
  await settle();

  const [attachment] = attachmentsState.attachments.value;
  assert.equal(attachment.errorMessage, undefined);
  assert.equal(attachment.status, 'ready');
  assert.equal(attachment.kind, 'image');
  assert.equal(attachment.preview, 'https://spark.example.com/api-svc/attachments/shot.png');
  assert.equal(attachment.file, null);
});

test('移除上传中的附件会中止请求且不接收回包', async () => {
  let uploadSignal!: AbortSignal;
  let finishUpload!: (value: ReturnType<typeof uploaded>) => void;
  handlers.uploadConversationAttachment = async (
    _projectId,
    _number,
    file: File,
    signal: AbortSignal,
  ) => new Promise((resolve) => {
    uploadSignal = signal;
    finishUpload = resolve;
  });

  const file = new File(['hello'], 'note.txt', { type: 'text/plain' });
  attachmentsState.addFiles([file]);
  await settle();
  const localId = attachmentsState.attachments.value[0].localId;
  attachmentsState.removeAttachment(localId);

  assert.equal(uploadSignal.aborted, true);
  finishUpload(uploaded(file));
  await settle();
  assert.deepEqual(attachmentsState.attachments.value, []);
});

test('较晚完成的本地图片识别不会覆盖上传响应类型', async () => {
  handlers.uploadConversationAttachment = async (_projectId, _number, file: File) => ({
    ...uploaded(file),
    mime_type: 'text/plain',
  });

  const file = new File([
    new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  ], 'header.bin', { type: 'application/octet-stream' });
  const originalSlice = file.slice.bind(file);
  let releaseHeader!: () => void;
  Object.defineProperty(file, 'slice', {
    value: (...args: Parameters<File['slice']>) => {
      const blob = originalSlice(...args);
      const read = blob.arrayBuffer.bind(blob);
      Object.defineProperty(blob, 'arrayBuffer', {
        value: () => new Promise<ArrayBuffer>((resolve) => {
          releaseHeader = () => {
            void read().then(resolve);
          };
        }),
      });
      return blob;
    },
  });

  attachmentsState.addFiles([file]);
  await settle();
  assert.equal(attachmentsState.attachments.value[0].status, 'ready');
  assert.equal(attachmentsState.attachments.value[0].kind, 'file');

  releaseHeader();
  await settle();
  assert.equal(attachmentsState.attachments.value[0].kind, 'file');
  assert.equal(attachmentsState.attachments.value[0].mimeType, 'text/plain');
  assert.equal(attachmentsState.attachments.value[0].preview, '');
});

test('被拒后按原顺序恢复附件并保留期间新增项', () => {
  const ready = (localId: string, kind: ChatAttachment['kind']): ChatAttachment => ({
    localId,
    file: null,
    mimeType: kind === 'image' ? 'image/png' : 'text/plain',
    kind,
    preview: '',
    name: localId,
    size: 1,
    status: 'ready',
    attachmentId: localId,
  });
  const file1 = ready('file-1', 'file');
  const image = ready('image', 'image');
  const file2 = ready('file-2', 'file');
  const addedLater = ready('later', 'file');
  attachmentsState.attachments.value = [file1, image, file2];
  const originalOrder = ['file-1', 'image', 'file-2'];

  attachmentsState.removeSubmittedAttachments(['file-1', 'file-2']);
  attachmentsState.attachments.value.push(addedLater);
  attachmentsState.restoreSubmittedAttachments([file1, file2], originalOrder);

  assert.deepEqual(
    attachmentsState.attachments.value.map(attachment => attachment.localId),
    ['file-1', 'image', 'file-2', 'later'],
  );
});

test('多文件按用户选择顺序串行上传', async () => {
  const started: string[] = [];
  let finishFirst!: () => void;
  handlers.uploadConversationAttachment = async (_projectId, _number, file: File) => {
    started.push(file.name);
    if (file.name === 'first.txt') {
      await new Promise<void>((resolve) => {
        finishFirst = resolve;
      });
    }
    return uploaded(file);
  };

  attachmentsState.addFiles([
    new File(['1'], 'first.txt', { type: 'text/plain' }),
    new File(['2'], 'second.txt', { type: 'text/plain' }),
  ]);
  await settle();
  assert.deepEqual(started, ['first.txt']);

  finishFirst();
  await settle();
  assert.deepEqual(started, ['first.txt', 'second.txt']);
  assert.deepEqual(
    attachmentsState.attachments.value.map(attachment => attachment.attachmentId),
    ['first.txt', 'second.txt'],
  );
});
