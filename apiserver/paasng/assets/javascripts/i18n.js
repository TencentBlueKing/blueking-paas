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
 * @file i18n 封装
 */

import VueI18n from 'vue-i18n';
import cookie from 'cookie';


let localLanguage = cookie.parse(document.cookie).blueking_language || 'zh-cn';
if (['zh-cn', 'zh-CN', 'None', 'none', ''].includes(localLanguage)) {
  localLanguage = 'zh-cn';
}


const i18n = new VueI18n({
    // 语言标识
    locale: localLanguage,
    fallbackLocale: 'zh-cn',
    // this.$i18n.locale 通过切换locale的值来实现语言切换
    messages: {
      // 中文语言包
      'zh-cn': {
        '系统出现异常': '系统出现异常'
      },
      // 英文语言包
      en: {
        '系统出现异常': 'System exception'
      }
    },
    silentTranslationWarn: true
});


export default i18n;
