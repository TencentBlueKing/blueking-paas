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

import cookie from 'cookie';

export default {
  bind (el, binding) {
    if ((typeof binding.value === 'string' && el && el.classList.contains(binding.value)) || cookie.parse(document.cookie).blueking_language !== 'en') {
      return;
    }
    if (typeof binding.value === 'string') {
      binding.value && el.classList.add(binding.value);
      return;
    }
    let options = { class: '', styles: {} };
    options = { ...options, ...binding.value };
    options.class && el.classList.add(options.class);
    let cssText = '';
    if (typeof options.styles === 'string') {
      cssText += options.styles;
    } else {
      Object.keys(options.styles).forEach((key) => {
        cssText += `${key}: ${options.styles[key]};`;
      });
    }
    el.style.cssText += cssText;
  }
};
