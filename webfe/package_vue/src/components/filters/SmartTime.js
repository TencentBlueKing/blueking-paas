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

import Vue from 'vue';
import moment from 'moment';
import cookie from 'cookie';

// 时间格式过滤器
Vue.filter('time-smart', function (value, type) {
  let language = cookie.parse(document.cookie).blueking_language || 'zh-cn';

  if (['zh-cn', 'zh-CN', 'None', 'none', ''].includes(language)) {
    language = 'zh-cn';
  }
  // moment日期中文显示
  moment.locale(language);

  let formatTime;
  const curYear = new Date().getFullYear();
  switch (type) {
    case 'fromNow':
      // 距离当前时间多久
      formatTime = moment(value).startOf('minute').fromNow();
      break;
    case 'smartShorten':
      // 当年日期显示：07-25 16:16
      if (moment(value).format('YYYY') === curYear) {
        formatTime = moment(value).format('MM-DD HH:mm');
      } else {
        formatTime = moment(value).format('YYYY-MM-DD HH:mm');
      }
      break;
    default:
      break;
  }
  return formatTime;
});

const SmartTime = Vue.filter('time-smart');

export default SmartTime;
