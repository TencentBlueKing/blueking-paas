/*
* Tencent is pleased to support the open source community by making
* 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
* Copyright (C) 2017-2022THL A29 Limited, a Tencent company.  All rights reserved.
* Licensed under the MIT License (the "License").
* You may not use this file except in compliance with the License.
* You may obtain a copy of the License at http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*
* We undertake not to change the open source license (MIT license) applicable
*
* to the current version of the project delivered to anyone in the future.
*/

import _ from 'lodash';

class NavDataProcessor {
  constructor () {
    this.navItems = [];
    this.navCategories = [];
    this.id = 0;
  }

  _refineItem (item) {
    // Use desRoute as default
    const matchRouters = item.matchRouters || [item.destRoute.name];
    const matchRouterParams = item.matchRouterParams || item.destRoute.params;
    this.id++;
    return {
      ...item,
      matchRouters: matchRouters,
      matchRouterParams: matchRouterParams,
      id: this.id,
      type: 'item'
    };
  }

  addNavItem (item) {
    this.navItems.push(this._refineItem(item));
  }

  simpleAddNavItem (categoryName, destRouter, name) {
    this.addNavItem({
      'categoryName': categoryName,
      'name': name,
      'matchRouters': [destRouter],
      'destRoute': {
        'name': destRouter
      }
    });
  }

  addServiceNavItem (id, name) {
    this.addNavItem({
      'categoryName': 'appServices',
      'name': name,
      'matchRouters': ['appService', 'appServiceInner', 'appServiceConfig', 'appServiceInnerShared'],
      'destRoute': {
        'name': 'appService',
        'params': {
          'category_id': id.toString()
        }
      }
    });
  }

  addPermissionNavItem (type) {
    const nav = {
      user_access_control: {
        'categoryName': 'appPermissions',
        'name': '用户限制',
        'matchRouters': ['appPermissionUser', 'appPermissionPathExempt'],
        'destRoute': {
          'name': 'appPermissionUser'
        }
      },
      ip_access_control: {
        'categoryName': 'appPermissions',
        'name': 'IP限制',
        'matchRouters': ['appPermissionIP'],
        'destRoute': {
          'name': 'appPermissionIP'
        }
      },
      approval: {
        'categoryName': 'appPermissions',
        'name': '单据审批',
        'matchRouters': ['appOrderAudit'],
        'destRoute': {
          'name': 'appOrderAudit'
        }
      }
    };
    if (type && nav[type]) {
      this.addNavItem(nav[type]);
    }
  }

  feedOldStructures (data) {
    // Flat legacy sturecture
    _.forEach(data, (item) => {
      if (item.visible === false) {
        return;
      }

      if (item.sublist) {
        const categoryId = this.id;
        this.id++;
        const navCategory = {
          ...item,
          id: categoryId,
          type: 'category'
        };

        item.sublist.forEach((subitem) => {
          if (subitem.visible === false) {
            return;
          }

          this.navItems.push({
            ...this._refineItem(subitem),
            categoryName: navCategory.name
          });
        });

        delete navCategory.sublist;
        this.navCategories.push(navCategory);
      } else {
        this.navItems.push({
          ...this._refineItem(item),
          categoryName: null
        });
      }
    });
  }
}

export {
  NavDataProcessor
};

export function processNavData (data) {
  const processer = new NavDataProcessor();
  processer.feedOldStructures(data);
  return {
    'navItems': processer.navItems,
    'navCategories': processer.navCategories
  };
}

/**
 * 获取元素相对于页面的高度
 *
 * @param node {Object} 指定的 DOM 元素
 *
 * @return {number} 高度值
 */
export function getActualTop (node) {
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
export function getActualLeft (node) {
  let actualLeft = node.offsetLeft;
  let current = node.offsetParent;

  while (current !== null) {
    actualLeft += current.offsetLeft;
    current = current.offsetParent;
  }

  return actualLeft;
}
