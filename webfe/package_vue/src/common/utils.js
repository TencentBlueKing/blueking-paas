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

import _ from 'lodash';

class NavDataProcessor {
  constructor() {
    this.navItems = [];
    this.navCategories = [];
    this.id = 0;
  }

  _refineItem(item) {
    // Use desRoute as default
    const matchRouters = item.matchRouters || [item.destRoute.name];
    const matchRouterParams = item.matchRouterParams || item.destRoute.params;
    // eslint-disable-next-line no-plusplus
    this.id++;
    return {
      ...item,
      matchRouters,
      matchRouterParams,
      id: this.id,
      type: 'item',
    };
  }

  addNavItem(item) {
    // eslint-disable-next-line no-underscore-dangle
    this.navItems.push(this._refineItem(item));
  }

  simpleAddNavItem(categoryName, destRouter, name) {
    this.addNavItem({
      categoryName,
      name,
      matchRouters: [destRouter],
      destRoute: {
        name: destRouter,
      },
    });
  }

  addServiceNavItem(id, name) {
    this.addNavItem({
      categoryName: 'appServices',
      name,
      matchRouters: ['appService', 'appServiceInner', 'appServiceConfig', 'appServiceInnerShared'],
      destRoute: {
        name: 'appService',
        params: {
          category_id: id.toString(),
        },
      },
    });
  }

  addPermissionNavItem(type) {
    const nav = {
      user_access_control: {
        categoryName: 'appPermissions',
        name: '用户限制',
        matchRouters: ['appPermissionUser', 'appPermissionPathExempt'],
        destRoute: {
          name: 'appPermissionUser',
        },
      },
      ip_access_control: {
        categoryName: 'appPermissions',
        name: 'IP限制',
        matchRouters: ['appPermissionIP'],
        destRoute: {
          name: 'appPermissionIP',
        },
      },
      approval: {
        categoryName: 'appPermissions',
        name: '单据审批',
        matchRouters: ['appOrderAudit'],
        destRoute: {
          name: 'appOrderAudit',
        },
      },
    };
    if (type && nav[type]) {
      this.addNavItem(nav[type]);
    }
  }

  feedOldStructures(data) {
    // Flat legacy sturecture
    _.forEach(data, (item) => {
      if (item.visible === false) {
        return;
      }

      if (item.sublist) {
        const categoryId = this.id;
        // eslint-disable-next-line no-plusplus
        this.id++;
        const navCategory = {
          ...item,
          id: categoryId,
          type: 'category',
        };

        item.sublist.forEach((subitem) => {
          if (subitem.visible === false) {
            return;
          }

          this.navItems.push({
            // eslint-disable-next-line no-underscore-dangle
            ...this._refineItem(subitem),
            categoryName: navCategory.name,
          });
        });

        delete navCategory.sublist;
        this.navCategories.push(navCategory);
      } else {
        this.navItems.push({
          // eslint-disable-next-line no-underscore-dangle
          ...this._refineItem(item),
          categoryName: null,
        });
      }
    });
  }
}

export {
  NavDataProcessor,
};

export function processNavData(data) {
  const processer = new NavDataProcessor();
  processer.feedOldStructures(data);
  return {
    navItems: processer.navItems,
    navCategories: processer.navCategories,
  };
}

/**
 * 获取元素相对于页面的高度
 *
 * @param node {Object} 指定的 DOM 元素
 *
 * @return {number} 高度值
 */
export function getActualTop(node) {
  let actualTop = node.offsetTop;
  let current = node.offsetParent;

  while (current !== null) {
    actualTop += current.offsetTop;
    current = current.offsetParent;
  }

  return actualTop;
}

/**
 * 获取元素相对于页面左侧的宽度
 *
 * @param node {Object} 指定的 DOM 元素
 *
 * @return {number} 宽度值
 */
export function getActualLeft(node) {
  let actualLeft = node.offsetLeft;
  let current = node.offsetParent;

  while (current !== null) {
    actualLeft += current.offsetLeft;
    current = current.offsetParent;
  }

  return actualLeft;
}

/**
 * 手动清空table过滤条件
 *
 * @param refInstance {Object} 指定的 table
 *
 */
export function clearFilter(refInstance) {
  if (refInstance.filterPanels) {
    const { filterPanels } = refInstance;
    // eslint-disable-next-line no-restricted-syntax
    for (const key in filterPanels) {
      filterPanels[key].handleReset();
    };
  }
}

/**
 *  设置bk-talbe表头tips
 *
 * @param refInstance {h, { column }} 渲染函数
 *
 */
export function renderHeader(h, { column }) {
  return h('p', { class: 'table-header-tips-cls', directives: [{ name: 'bk-overflow-tips' }] }, [column.label]);
}

// 获取唯一随机数
export function uuid() {
  let id = '';
  const randomNum = Math.floor((1 + Math.random()) * 0x10000).toString(16)
    .substring(1);

  for (let i = 0; i < 7; i++) {
    id += randomNum;
  }
  return id;
}

// 格式化参数
export function formatParams(data) {
  const arr = [];
  // eslint-disable-next-line no-restricted-syntax
  for (const name in data) {
    arr.push(`${encodeURIComponent(name)}=${encodeURIComponent(data[name])}`);
  }
  return arr.join('&');
}

export function ajaxRequest(params = {}) {
  const fetchParams = params || {};
  fetchParams.data = params.data || {};

  const callbackName = fetchParams.jsonp;
  const head = document.getElementsByTagName('head')[0];
  fetchParams.data.callback = callbackName;

  // 设置传递给后台的回调参数名
  const data = formatParams(fetchParams.data);
  const script = document.createElement('script');

  script.addEventListener('error', () => {
    head.removeChild(script);
    fetchParams.error && fetchParams.error();
  });
  head.appendChild(script);

  // 创建 jsonp 回调函数
  window[callbackName] = function (res) {
    head.removeChild(script);
    clearTimeout(script.timer);
    window[callbackName] = null;
    fetchParams.success && fetchParams.success(res);
  };

  // 发送请求
  script.src = `${fetchParams.url}?${data}`;
}

/**
 * 合并深层次对象
 *
 * @param {obj1, obj2} 需要合并的两个对象
 *
 * @return {obj1} 合并后的对象
 */
export function mergeObjects(obj1, obj2) {
  // eslint-disable-next-line no-restricted-syntax
  for (const prop in obj2) {
    // eslint-disable-next-line no-prototype-builtins
    if (obj2.hasOwnProperty(prop)) {
      // eslint-disable-next-line no-prototype-builtins
      if (obj1.hasOwnProperty(prop) && typeof obj1[prop] === 'object' && typeof obj2[prop] === 'object') {
        mergeObjects(obj1[prop], obj2[prop]);
      } else {
        // eslint-disable-next-line no-param-reassign
        obj1[prop] = obj2[prop];
      }
    }
  }
  return obj1;
}

/**
 * 判断字符串是否为json字符串
 *
 * @param {str} 字符串
 *
 * @return {boolean} true or false
 */
export function isJsonString(str) {
  try {
    if (typeof JSON.parse(str) === 'object') {
      return true;
    }
  } catch (e) {
  }
  return false;
}
