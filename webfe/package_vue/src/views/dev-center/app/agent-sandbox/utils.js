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

// 空值占位符
export const EMPTY_TEXT = '--';

// 列表默认分页条数
export const DEFAULT_PAGE_LIMIT = 20;

export function isNil(value) {
  return value === null || value === undefined;
}

/**
 * 提取接口错误信息，缺失时回退到默认文案
 */
export function getErrorMessage(error, fallback) {
  return error?.detail || error?.message || fallback;
}

/**
 * 删除类接口约定返回空响应体，用于校验操作是否真正成功
 */
export function isEmptyResponse(result) {
  return result === '' || isNil(result);
}

/**
 * 数据量变化后将当前页码收敛到有效范围内
 */
export function clampPage(page, total, limit) {
  return Math.min(page, Math.max(1, Math.ceil(total / limit)));
}
