/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

/**
 *  云api权限续期按钮状态&tips
 * @param {*} status
 * @param {*} row
 * @returns { disabled, tips }
 */
export function formatRenewFun(status, row) {
  switch (status) {
    case 'unlimited':
      return {
        disabled: true,
        tips: '权限无限制，无需续期',
      };
    case 'owned':
      if (row.expires_in === null) {
        return {
          disabled: true,
          tips: '有效期为永久，无需续期',
        };
      }
      return {
        disabled: false,
        tips: '',
      };
    case 'expired':
      return {
        disabled: false,
        tips: '',
      };
    default:
      return {
        disabled: true,
        tips: '尚未获得资源权限，不支持续期',
      };
  }
}

/**
 *  云api权限申请按钮状态&tips
 * @param {*} status
 * @returns { disabled, tips }
 */
export function formatApplyFun(status) {
  const data = {
    disabled: false,
    tips: '',
  };
  switch (status) {
    case 'unlimited':
      data.disabled = true;
      data.tips = '权限无限制，无需申请';
      break;
    case 'pending':
      data.disabled = true;
      data.tips = '权限申请中';
      break;
    case 'owned':
      data.disabled = true;
      data.tips = '已有权限，无需申请';
      break;
    default:
      // 可申请
      data.disabled = false;
      break;
  }
  return data;
}
