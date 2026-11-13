import assert from 'node:assert/strict';
import { test } from 'node:test';

import { getImageMimeType } from './read-image.ts';

const file = (name: string, type = '') => ({ name, type }) as File;

test('accepts PNG, JPEG and WebP MIME types', () => {
  assert.equal(getImageMimeType(file('shot.any', 'image/png')), 'image/png');
  assert.equal(getImageMimeType(file('shot.any', 'image/jpeg')), 'image/jpeg');
  assert.equal(getImageMimeType(file('shot.any', 'image/webp')), 'image/webp');
});

test('falls back to case-insensitive file extensions when MIME is missing', () => {
  assert.equal(getImageMimeType(file('shot.JPG')), 'image/jpeg');
  assert.equal(getImageMimeType(file('shot.JpEg')), 'image/jpeg');
  assert.equal(getImageMimeType(file('shot.PNG')), 'image/png');
  assert.equal(getImageMimeType(file('shot.WEBP')), 'image/webp');
});

test('rejects GIF and unrelated image formats', () => {
  assert.equal(getImageMimeType(file('motion.gif', 'image/gif')), null);
  assert.equal(getImageMimeType(file('motion.GIF')), null);
  assert.equal(getImageMimeType(file('photo.heic', 'image/heic')), null);
  assert.equal(getImageMimeType(file('vector.svg', 'image/svg+xml')), null);
});
