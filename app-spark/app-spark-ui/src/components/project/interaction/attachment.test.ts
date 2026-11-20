import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  detectImageAttachmentMimeType,
  formatAttachmentSize,
  isAttachmentSizeAllowed,
  isImageAttachmentMimeType,
  MAX_ATTACHMENT_SIZE_BYTES,
  selectSendableAttachments,
} from './attachment.ts';

test('only the four backend image MIME types render as images', () => {
  for (const mimeType of ['image/gif', 'image/jpeg', 'image/png', 'image/webp']) {
    assert.equal(isImageAttachmentMimeType(mimeType), true);
  }
  assert.equal(isImageAttachmentMimeType('image/svg+xml'), false);
  assert.equal(isImageAttachmentMimeType('text/html'), false);
  assert.equal(isImageAttachmentMimeType('application/pdf'), false);
});

test('detects provisional image types from file headers without using names or browser MIME', async () => {
  const blob = (bytes: number[]) => new Blob([new Uint8Array(bytes)]);
  assert.equal(await detectImageAttachmentMimeType(blob([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
  ])), 'image/png');
  assert.equal(await detectImageAttachmentMimeType(blob([0xff, 0xd8, 0xff])), 'image/jpeg');
  assert.equal(await detectImageAttachmentMimeType(blob([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61,
  ])), 'image/gif');
  assert.equal(await detectImageAttachmentMimeType(blob([
    0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50,
  ])), 'image/webp');
  assert.equal(await detectImageAttachmentMimeType(blob([0x7b, 0x22, 0x61, 0x22, 0x3a])), null);
});

test('accepts attachments up to 5MB and rejects larger files', () => {
  assert.equal(isAttachmentSizeAllowed({ size: MAX_ATTACHMENT_SIZE_BYTES }), true);
  assert.equal(isAttachmentSizeAllowed({ size: MAX_ATTACHMENT_SIZE_BYTES + 1 }), false);
});

test('formats attachment sizes for draft and history file rows', () => {
  assert.equal(formatAttachmentSize(512), '512 B');
  assert.equal(formatAttachmentSize(1536), '1.5 KB');
  assert.equal(formatAttachmentSize(2 * 1024 * 1024), '2 MB');
});

test('a text model keeps file order and leaves images out of this run', () => {
  const attachments = [
    { id: 'file-1', kind: 'file' },
    { id: 'image', kind: 'image' },
    { id: 'file-2', kind: 'file' },
  ];
  assert.deepEqual(
    selectSendableAttachments(attachments, false).map(item => item.id),
    ['file-1', 'file-2'],
  );
  assert.deepEqual(
    selectSendableAttachments(attachments, true).map(item => item.id),
    ['file-1', 'image', 'file-2'],
  );
});
