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


const vChildExist = {
  bind(el) {
    const childNodes = el.childNodes;

    // 判断子元素是否存在
    const allChildNodes = Array.from(childNodes).filter(node => node.nodeType !== 8); // 过滤掉注释节点

    if (allChildNodes.length === 0) {
      el.style.display = 'none'; // 隐藏当前元素
    }
  },
};

export default vChildExist;
