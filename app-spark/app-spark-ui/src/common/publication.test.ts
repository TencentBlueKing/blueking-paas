import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { PublicationResponse } from '../http/types.ts';
import {
  createLatestDeploymentRequest,
  getPublicationLinks,
  hasNewPublicationVersion,
} from './publication.ts';

const state = (patch: Partial<PublicationResponse> = {}): PublicationResponse => ({
  online: null,
  task: null,
  last_failure: null,
  unseen_result: null,
  app_code: null,
  default_app_name: 'SparkDemo',
  dev_center_links: null,
  latest_version_id: 'app-spark/checkpoint/run-2',
  ...patch,
});

test('first deployment sends only the trimmed application name', () => {
  assert.deepEqual(
    createLatestDeploymentRequest(state(), '  SparkDemo  '),
    { app_name: 'SparkDemo' },
  );
});

test('an existing application ignores app_name and never sends version_id', () => {
  const request = createLatestDeploymentRequest(state({ app_code: 'spark-demo' }), 'AnotherName');
  assert.deepEqual(request, {});
  assert.equal('version_id' in request, false);
});

test('update is available only when workspace latest differs from online', () => {
  const online = {
    version_id: 'app-spark/checkpoint/run-1',
    url: 'https://spark-demo.example.com/',
    published_at: null,
  };
  assert.equal(hasNewPublicationVersion(state({ online })), true);
  assert.equal(hasNewPublicationVersion(state({
    online,
    latest_version_id: online.version_id,
  })), false);
  assert.equal(hasNewPublicationVersion(state({ online: null })), false);
});

test('publication links support both current and deployed response field names', () => {
  const links = {
    logs: 'https://example.com/logs',
    deployments: 'https://example.com/deployments',
    env_vars: 'https://example.com/env-vars',
    members: 'https://example.com/members',
  };
  assert.deepEqual(getPublicationLinks(state({ dev_center_links: links })), links);
  assert.deepEqual(getPublicationLinks(state({
    dev_center_links: undefined,
    bkpaas_links: links,
  })), links);
});
