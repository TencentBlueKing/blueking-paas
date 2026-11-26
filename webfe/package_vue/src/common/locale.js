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

import cookie from 'cookie';

function toSupportedLanguage(language) {
  const value = String(language || '').trim().toLowerCase()
    .replace(/_/g, '-');
  if (value === 'en' || value.startsWith('en-')) {
    return 'en';
  }
  // 简体：zh、zh-CN、zh-Hans、zh-Hans-CN。繁体 zh-TW / zh-HK / zh-Hant 不支持。
  if (
    value === 'zh'
    || value === 'zh-cn'
    || value.startsWith('zh-cn-')
    || value === 'zh-hans'
    || value.startsWith('zh-hans-')
  ) {
    return 'zh-cn';
  }
  return '';
}

function getBrowserLanguage() {
  const language = (typeof navigator !== 'undefined' && (navigator.language || navigator.userLanguage)) || '';
  return toSupportedLanguage(language) || 'en';
}

// 有 cookie 时用 cookie；没有时用浏览器语言。只支持 zh-cn / en，其余为 en。
export function resolveLocalLanguage() {
  const raw = cookie.parse(document.cookie).blueking_language;
  const normalized = String(raw || '').trim().toLowerCase();
  if (!raw || normalized === 'none') {
    return getBrowserLanguage();
  }
  return toSupportedLanguage(raw) || 'en';
}
