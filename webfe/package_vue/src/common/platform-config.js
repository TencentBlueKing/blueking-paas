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
import i18n from '@/language/i18n.js';
import { getPlatformConfig, setShortcutIcon } from '@blueking/platform-config';

// 应用平台配置
function applyPlatformConfig(config) {
  store.commit('updataPlatformConfig', config);
  // 更新标题和图标
  document.title = config.title;
  setShortcutIcon(config.favicon);
}

export default async function (vm) {
  const url = `${window.BK_SHARED_RES_URL}/bk_paas3/base.js`;

  // 默认配置
  const defaults = {
    title: window.GLOBAL_CONFIG.APP_VERSION === 'te' ? i18n.t('开发者中心 | 蓝鲸') : i18n.t('开发者中心 | 腾讯蓝鲸智云'),
    name: i18n.t('蓝鲸开发者中心'),
    favicon: '/static/images/logo.svg',
    version: window.BK_PAAS_VERSION,
  };

  if (vm.GLOBAL.LINK.BK_HELP) {
    defaults.footerInfoHTML = `<a target="_blank" class="link-item" href="${vm.GLOBAL.LINK.BK_HELP}">${i18n.t('联系BK助手')}</a>
    | <a target="_blank" class="link-item" href="${vm.GLOBAL.LINK.BK_DESKTOP}">${i18n.t('蓝鲸桌面')}</a>`;
  } else {
    defaults.footerInfoHTML = `<a target="_blank" class="link-item" href="${vm.GLOBAL.LINK.BK_TECHNICAL_SUPPORT}">${i18n.t('技术支持')}</a>
    | <a target="_blank" class="link-item" href="${vm.GLOBAL.LINK.BK_COMMUNITY}">${i18n.t('社区论坛')}</a>
    | <a target="_blank" class="link-item" href="${vm.GLOBAL.LINK.BK_OFFICIAL_WEBSITE}">${i18n.t('产品官网')}</a>`;
  }
  defaults.footerInfoHTMLEn = defaults.footerInfoHTML;

  try {
    const config = await getPlatformConfig(url, defaults);
    applyPlatformConfig(config);
  } catch (error) {
    applyPlatformConfig(defaults);
  }
}
