import assert from 'node:assert/strict';
import { test } from 'node:test';

import { previewFrameUrl } from './preview-frame-url.ts';

const page = 'http://studio.example.com';

test('an API preview path folds back onto the page', () => {
  const origin = 'https://api.example.com/api/projects/p/conversations/3/preview/app/?x=1#top';
  assert.equal(
    previewFrameUrl(origin, page),
    'http://studio.example.com/api/projects/p/conversations/3/preview/app/?x=1#top',
  );
});

test('an API preview path on the same host stays put', () => {
  const origin = `${page}/api/projects/p/conversations/3/preview/app/`;
  assert.equal(previewFrameUrl(origin, page), origin);
});

test('an exposed preview host is the iframe src', () => {
  const origin = 'https://9000-sbx.sandbox.example/';
  assert.equal(previewFrameUrl(origin, page), origin);
});
