/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

import dayjs from '@/common/dayjs';
import { EMPTY_TEXT, isNil } from './utils';

export function displayValue(value) {
  return isNil(value) || value === '' ? EMPTY_TEXT : value;
}

export function formatMemory(value) {
  if (isNil(value)) return EMPTY_TEXT;
  return value < 1024 ? `${value} MB` : `${Number((value / 1024).toFixed(2))} GiB`;
}

export function formatResources(resource) {
  const cpu = isNil(resource.cpu_count) ? EMPTY_TEXT : `${resource.cpu_count}C`;
  return `${cpu} / ${formatMemory(resource.memory_mb)} / ${formatMemory(resource.disk_size_mb)}`;
}

export function formatRelativeTime(value) {
  if (!value) return EMPTY_TEXT;
  const iso = value.replace(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) ([+-]\d{2})(\d{2})$/, '$1T$2$3:$4');
  const date = dayjs(iso);
  return date.isValid() ? date.fromNow() : EMPTY_TEXT;
}

export function formatTimeout(value) {
  return isNil(value) ? EMPTY_TEXT : `${value} s`;
}
