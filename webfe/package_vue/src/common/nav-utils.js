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

function excludeNavItemsByCategoryNames (navItems, categoryNames) {
  const invalidCategoryNames = categoryNames;
  navItems = _.filter(navItems, (item) => {
    return item && (!_.includes(invalidCategoryNames, item.categoryName));
  });
  return navItems;
}

function filterNavItemsByRole (appRole, navItems) {
  let result = [];
  if (appRole === 'administrator') {
    result = navItems;
  } else if (appRole === 'developer') {
    const validCategoryNames = [
      'appEngine',
      'appServices',
      'appMarketing',
      'appConfigs',
      'appPermissions'
    ];

    result = _.find(navItems, (item) => {
      return item.destRoute.name === 'appSummary';
    });
    result = [
      result,
      ..._.filter(navItems, (item) => {
        return _.includes(validCategoryNames, item.categoryName);
      })
    ];
  } else if (appRole === 'operator') {
    const validCategoryNames = [
      'appMarketing',
      'appConfigs',
      'appPermissions'
    ];
    result = _.find(navItems, (item) => {
      return item.destRoute.name === 'appSummary';
    });
    result = [
      result,
      ..._.filter(navItems, (item) => {
        return _.includes(validCategoryNames, item.categoryName);
      })
    ];
  }
  return result;
}

export default {
  excludeNavItemsByCategoryNames,
  filterNavItemsByRole
};
