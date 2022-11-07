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

/*
    这里管理当前 app 的 region 所拥有的属性
    一般用于控制侧边栏的展示
*/
import http from '@/api';

// store
const state = {
    region: '',
    module_custom_domain: {
        enabled: false
    },
    module_mobile_config: {
        enabled: false
    },
    entrance_config: {
        manually_upgrade_to_subdomain_allowed: false
    },
    access_control: {
        module: [],
        user_type: 'rtx'
    },
    services: {
        categories: []
    }
};

// getters
const getters = {
    region: state => state.region,
    moduleMobileConfigEnabled: state => state.module_mobile_config.enabled
};

// mutations
const mutations = {
    updateRegionInfo: function (state, regionObj) {
        state.region = regionObj.name;
        state.module_mobile_config = regionObj.module_mobile_config;
        state.module_custom_domain = regionObj.module_custom_domain;
        state.access_control = regionObj.access_control;
        state.services = regionObj.services;
        state.entrance_config = regionObj.entrance_config;
    }
};

// actions
const actions = {
    fetchRegionInfo ({ commit, state }, region, config = {}) {
        const url = `${BACKEND_URL}/api/regions/${region}/`;
        return http.get(url, {}, { fromCache: true }).then(data => {
            commit('updateRegionInfo', data);
            return data;
        });
    }
};

export default {
    state,
    getters,
    mutations,
    actions
};
