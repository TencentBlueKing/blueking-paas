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

/*
    sourcectl
*/
import http from '@/api';
import { DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';

// store
const state = {
  source_control_type: DEFAULT_APP_SOURCE_CONTROL_TYPES,
  updated: false
};

// getters
const getters = {
  isMultiSourcectlType: state => state.source_control_type.length > 1
};

// mutations
const mutations = {
  updateAccountAllowSourceControlType: function (state, data) {
    state.source_control_type = data;
    state.updated = true;
  }
};

// actions
const actions = {
  async fetchAccountAllowSourceControlType ({ commit, state }, { force = false }) {
    return new Promise(resolve => {
      if (!force && state.updated) {
        resolve(state.source_control_type);
        return;
      }
      const url = `${BACKEND_URL}/api/sourcectl/providers/`;
      http.get(url).then(resp => {
        commit('updateAccountAllowSourceControlType', resp.results);
        resolve(state.source_control_type);
      }, resp => {
        resolve(state.source_control_type);
      });
    });
  }
};

export default {
  state,
  getters,
  mutations,
  actions
};
