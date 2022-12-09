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

import { bkMessage } from 'bk-magic-vue';
import i18n from '@/language/i18n.js';

const vPaasCopy = {
  bind (el, { value }) {
    el.$value = value;
    el.handler = ($event) => {
      $event.stopPropagation();
      if (!el.$value) {
        bkMessage({
          theme: 'warning',
          message: i18n.t('无复制内容'),
          delay: 2000,
          dismissable: false
        });
        return;
      }
      const textarea = document.createElement('textarea');
      textarea.readOnly = 'readonly';
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      textarea.value = el.$value;
      document.body.appendChild(textarea);
      textarea.select();
      const result = document.execCommand('Copy');
      if (result) {
        bkMessage({
          theme: 'success',
          message: i18n.t('复制成功'),
          delay: 2000,
          dismissable: false
        });
      }
      document.body.removeChild(textarea);
    };
    el.addEventListener('click', el.handler);
  },
  componentUpdated (el, { value }) {
    el.$value = value;
  },
  unbind (el) {
    el.removeEventListener('click', el.handler);
  }
};

export default vPaasCopy;
