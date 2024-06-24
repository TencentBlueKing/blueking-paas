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

import store from '@/store';
import { getPlatformConfig, setShortcutIcon, setDocumentTitle } from '@blueking/platform-config';

// 应用平台配置
function applyPlatformConfig(config) {
  store.commit('updataPlatformConfig', config);
  // 更新标题和图标
  setDocumentTitle(config.i18n);
  setShortcutIcon(config.favicon);
}

export default async function (vm) {
  const url = `${window.BK_SHARED_RES_URL}/bk_paas3/base.js`;

  // 默认配置
  const defaults = {
    name: '蓝鲸开发者中心',
    nameEn: 'BK Developer Center',
    brandName: window.GLOBAL_CONFIG.APP_VERSION === 'te' ? '蓝鲸' : '腾讯蓝鲸智云',
    brandNameEn: 'Tencent BlueKing',
    appLogo: '/static/images/logo.svg',
    favicon: '/static/images/logo.svg',
    version: window.BK_PAAS_VERSION,
    footerInfo: vm.GLOBAL.LINK.BK_HELP
      ? `[联系BK助手](${vm.GLOBAL.LINK.BK_HELP}) | [蓝鲸桌面](${vm.GLOBAL.LINK.BK_DESKTOP})`
      : `[技术支持](${vm.GLOBAL.LINK.BK_TECHNICAL_SUPPORT}) | [社区论坛](${vm.GLOBAL.LINK.BK_COMMUNITY}) | [产品官网](${vm.GLOBAL.LINK.BK_OFFICIAL_WEBSITE})`,
    footerInfoEn: vm.GLOBAL.LINK.BK_HELP
      ? `[Contact BK Customer Service](${vm.GLOBAL.LINK.BK_HELP}) | [BlueKing Desktop](${vm.GLOBAL.LINK.BK_DESKTOP})`
      : `[Support](${vm.GLOBAL.LINK.BK_TECHNICAL_SUPPORT}) | [Forum](${vm.GLOBAL.LINK.BK_COMMUNITY}) | [Official](${vm.GLOBAL.LINK.BK_OFFICIAL_WEBSITE})`,
  };

  try {
    const config = await getPlatformConfig(url, defaults);
    applyPlatformConfig(config);
  } catch (error) {
    applyPlatformConfig(defaults);
  }
}
