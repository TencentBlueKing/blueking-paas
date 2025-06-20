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
import http from '@/api';
import { bus } from '@/common/bus';

const ANONYMOUS_USER = {
  id: null,
  isAuthenticated: false,
  username: 'anonymous',
  avatarUrl: null,
  chineseName: 'anonymous',
  phone: null,
  email: null
};

let currentUser = {
  avatar_url: '',
  bkpaas_user_id: '',
  chinese_name: '',
  username: ''
};

export default {
  HTTP_STATUS_UNAUTHORIZED: 401,
  getCurrentUser () {
    return currentUser;
  },
  getAnonymousUser () {
    return { ...ANONYMOUS_USER
    };
  },
  redirectToLogin () {
    if (window.location.href.indexOf(window.GLOBAL_CONFIG.V3_OA_DOMAIN) !== -1) {
      const url = window.location.href.replace(window.GLOBAL_CONFIG.V3_OA_DOMAIN, window.GLOBAL_CONFIG.V3_WOA_DOMAIN);
      window.location = window.GLOBAL_CONFIG.LOGIN_SERVICE_URL + '/?c_url=' + url;
    } else {
      window.location = window.GLOBAL_CONFIG.LOGIN_SERVICE_URL + '/?c_url=' + window.location.href;
    }
  },
  requestCurrentUser () {
    // Request user endpoint and set user info to currentUser
    const endpoint = BACKEND_URL + '/api/user/';
    const req = http.get(endpoint);

    const promise = new Promise((resolve, reject) => {
      req.then((resp) => {
        const user = {};
        _.forEach(resp, (value, key) => {
          key = _.camelCase(key);
          user[key] = value;
        });
        user.isAuthenticated = !!Object.keys(resp).length;
        // 存储当前用户信息(全局)
        currentUser = resp;
        resolve(user);
      }, (err) => {
        // When access to domain through smart proxy, it will redirect request to login page
        // and thus trigger a cross-domain error
        if (err.status === this.HTTP_STATUS_UNAUTHORIZED || err.crossDomain) {
          resolve({ ...ANONYMOUS_USER });
        } else {
          reject(err);
        }
      });
    });
    return promise;
  },
  requestHasApp () {
    const endpoint = BACKEND_URL + '/api/bkapps/applications/lists/minimal?is_active=true';
    const req = http.get(endpoint);

    const promise = new Promise((resolve, reject) => {
      req.then((resp) => {
        resolve(resp.count > 0);
      }, (err) => {
        if (err.status === this.HTTP_STATUS_UNAUTHORIZED) {
          bus.$emit('show-login-modal');
        }
      });
    });
    return promise;
  },
  requestOffApp () {
    const endpoint = BACKEND_URL + '/api/bkapps/applications/lists/minimal';
    const req = http.get(endpoint);

    const promise = new Promise((resolve, reject) => {
      req.then((resp) => {
        resolve(resp.count > 0);
      }, (err) => {
        if (err.status === this.HTTP_STATUS_UNAUTHORIZED) {
          bus.$emit('show-login-modal');
        }
      });
    });
    return promise;
  }
};
