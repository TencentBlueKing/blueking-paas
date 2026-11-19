import assert from 'node:assert/strict';
import { test } from 'node:test';

import { toAttachmentBlock } from './message-attachment.ts';

Object.defineProperty(globalThis, 'window', {
  value: { SITE_URL: '' },
  configurable: true,
});
Object.defineProperty(globalThis, 'location', {
  value: { origin: 'https://spark.example.com' },
  configurable: true,
});

test('本地图片预览优先于后端地址', () => {
  assert.deepEqual(toAttachmentBlock({
    kind: 'image',
    filename: 'shot.png',
    size: 128,
    url: '/api-svc/image',
    preview: 'data:image/png;base64,local',
  }), {
    type: 'image',
    src: 'data:image/png;base64,local',
    filename: 'shot.png',
  });
});

test('文件块统一解析下载地址并保留大小', () => {
  assert.deepEqual(toAttachmentBlock({
    kind: 'file',
    filename: 'notes.txt',
    size: 512,
    url: '/api-svc/file',
  }), {
    type: 'file',
    href: 'https://spark.example.com/api-svc/file',
    filename: 'notes.txt',
    size: 512,
  });
});

test('没有地址和本地预览的附件显示不可用占位', () => {
  assert.equal(toAttachmentBlock({
    kind: 'image',
    filename: 'missing.png',
    size: 0,
    url: null,
  }).src, undefined);
  assert.equal(toAttachmentBlock({
    kind: 'file',
    filename: 'missing.txt',
    size: 0,
    url: null,
  }).href, undefined);
});
