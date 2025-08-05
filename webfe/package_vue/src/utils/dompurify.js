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

import Vue from 'vue';
import VueDOMPurifyHTML from 'vue-dompurify-html';

const ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr', 'span', 'div',
  'em', 'i', 'strong', 'b', 'u', 's', 'del', 'ins',
  'ul', 'ol', 'li',
  'code', 'pre',
  'a', 'img',
  'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
  'marked', 'pasmark', 'filtermark',
  'sub', 'sup', 'small', 'abbr', 'cite', 'q', 'time'
];
const ALLOWED_ATTR = ['class', 'style', 'id', 'src'];
const ADDITIONAL_ATTR = ['target', 'href'];

// DOMPurify 配置对象
const dompurifyConfig = {
  default: {
    ALLOWED_TAGS,
    ALLOWED_ATTR: [...ALLOWED_ATTR, ...ADDITIONAL_ATTR],
    KEEP_CONTENT: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    ADD_ATTR: ADDITIONAL_ATTR,
    hooks: {
      afterSanitizeAttributes: (node) => {
        if (node.tagName === 'SPAN') {
          node.removeAttribute('style');
        }
        // 确保链接安全
        if (node.tagName === 'A' && node.getAttribute('href')) {
          node.setAttribute('rel', 'noopener noreferrer');
          node.setAttribute('target', '_blank');
        }
        // 严格限制图片只允许 base64
        if (node.tagName === 'IMG') {
          const src = node.getAttribute('src') || '';
          if (!src.startsWith('data:image/')) {
            node.removeAttribute('src');
          } else {
            // 强制添加 alt 属性
            if (!node.getAttribute('alt')) {
              node.setAttribute('alt', 'user image');
            }
          }
        }
      },
    },
  },
};

// 注册 VueDOMPurifyHTML 插件
Vue.use(VueDOMPurifyHTML, dompurifyConfig);
