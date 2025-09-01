/* eslint-disable no-param-reassign, no-restricted-syntax */
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
import Vuex from 'vuex';
import region from './modules/region';
import application from './modules/application';
import deploy from './modules/deploy';
import packages from './modules/packages';
import search from './modules/search';
import sourcectl from './modules/sourcectl';
import log from './modules/log';
import baseInfo from './modules/base-info';
import entryConfig from './modules/entry-config';
import module from './modules/module';
import processes from './modules/processes';
import market from './modules/market';
import member from './modules/members';
import envVar from './modules/var';
import order from './modules/order';
import ip from './modules/ip';
import analysis from './modules/analysis';
import user from './modules/user';
import createApp from './modules/create-app';
import service from './modules/service';
import devopsAuth from './modules/devops-auth';
import alarm from './modules/alarm';
import docuManagement from './modules/docu-management';
import cloudApi from './modules/cloud-api';
import credential from './modules/credential';
import overview from './modules/overview';
import plugin from './modules/plugin';
import pluginMembers from './modules/plugin-members';
import imageManage from './modules/image-manage';
import observability from './modules/observability';
import persistentStorage from './modules/persistent-storage';
import authenticationInfo from './modules/authentication-info';
import migration from './modules/migration';
import sandbox from './modules/sandbox';
import tool from './modules/tool';
import tenant from './modules/tenant';
import tenantOperations from './modules/tenant-operations';
import tenantConfig from './modules/tenant-config';
import http from '@/api';
import cookie from 'cookie';
import { validateAppCode, createSafeObject, safeSet, safeHas } from '@/utils/safe-object';

Vue.use(Vuex);

let localLanguage = cookie.parse(document.cookie).blueking_language || 'zh-cn';
if (['zh-cn', 'zh-CN', 'None', 'none', ''].includes(localLanguage)) {
  localLanguage = 'zh-cn';
}

const state = {
  userFeature: {},
  platformFeature: {},
  curAppCode: '',
  curAppInfo: {
    feature: {},
  },
  curAppModule: {},
  curAppDefaultModule: {},
  curAppModuleList: [],
  appInfo: Object.create(null),
  pluginInfo: {},

  isAppLoading: true,
  canCreateModule: true,
  loadingConf: {
    speed: 2,
    primaryColor: '#f5f6fa',
    secondaryColor: '#ecebeb',
  },
  localLanguage,
  navType: {},
  applyUrl: '',
  envEventData: ['stag', 'prod'],
  errorDetail: {},
  // 是否显示通知中心
  isShowNotice: false,
  curUserInfo: {},
  platformConfig: {
    i18n: {},
  },
};

const getters = {
  tenantId: state => state.curUserInfo?.tenantId,
  isShowTenant: state => state.curUserInfo?.tenantId === window.GLOBAL_CONFIG.OP_TYPE_TENANT_ID,
  tenantApiBaseUrl: () => window.BK_API_URL_TMPL?.replace('{api_name}', 'bk-user-web/prod'),
  isMultiTenantDisplayMode: state => state.platformFeature?.MULTI_TENANT_MODE || window.BK_USER_API_IN_APIGW === 'true',
};

const mutations = {
  updateUserFeature(state, data) {
    state.userFeature = data;

    // 将平台功能合并到用户功能
    for (const key in state.platformFeature) {
      state.userFeature[key] = state.platformFeature[key];
    }

    const appCode = state.curAppCode;
    // 使用严格的 appCode 验证
    if (appCode && validateAppCode(appCode)) {
      // 确保 appInfo 是安全的无原型对象
      if (Object.getPrototypeOf(state.appInfo) !== null) {
        state.appInfo = createSafeObject(state.appInfo);
      }

      if (safeHas(state.appInfo, appCode)) {
        // 合并用户功能开关和应用功能开关
        const appFeature = state.appInfo[appCode].feature || {};
        state.appInfo[appCode].feature = {
          ...state.userFeature,
          ...state.platformFeature,
          ...appFeature,
        };
      }
    }
  },
  updatePlatformFeature(state, data) {
    state.platformFeature = data;
    // 将平台功能合并到用户功能
    for (const key in data) {
      state.userFeature[key] = data[key];
    }

    const appCode = state.curAppCode;
    // 使用严格的 appCode 验证
    if (appCode && validateAppCode(appCode)) {
      // 确保 appInfo 是安全的无原型对象
      if (Object.getPrototypeOf(state.appInfo) !== null) {
        state.appInfo = createSafeObject(state.appInfo);
      }

      if (safeHas(state.appInfo, appCode)) {
        // 合并用户功能开关和应用功能开关
        const appFeature = state.appInfo[appCode].feature || {};
        state.appInfo[appCode].feature = {
          ...state.userFeature,
          ...state.platformFeature,
          ...appFeature,
        };
      }
    }
  },
  updateAppLoading(state, data) {
    state.isAppLoading = data;
  },
  updateAppFeature(state, { appCode, data }) {
    // 使用严格的 appCode 验证
    if (!validateAppCode(appCode)) {
      console.warn(`[Security] Invalid appCode blocked in updateAppFeature: ${appCode}`);
      return;
    }

    // 确保 appInfo 是安全的无原型对象
    if (Object.getPrototypeOf(state.appInfo) !== null) {
      state.appInfo = createSafeObject(state.appInfo);
    }

    if (safeHas(state.appInfo, appCode)) {
      // 安全地设置 feature 属性
      state.appInfo[appCode].feature = {
        ...state.userFeature,
        ...state.platformFeature,
        ...data,
      };
    }
  },
  // curAppInfo && curAppModule 的信息都在这里获取
  updateAppInfo(state, { appCode, moduleId, data }) {
    // 使用严格的 appCode 验证
    if (!validateAppCode(appCode)) {
      console.warn(`[Security] Invalid appCode blocked: ${appCode}`);
      return;
    }

    if (!data.feature) {
      data.feature = {};
    }

    if (appCode === state.curAppCode) {
      data.feature = state.curAppInfo.feature;
    }

    state.curAppInfo = data;
    state.curAppCode = appCode;

    // 确保 appInfo 是安全的无原型对象
    if (Object.getPrototypeOf(state.appInfo) !== null) {
      state.appInfo = createSafeObject(state.appInfo);
    }

    // 使用安全的属性设置
    if (!safeSet(state.appInfo, appCode, data)) {
      console.error(`[Security] Failed to set app data for: ${appCode}`);
      return;
    }

    state.curAppModuleList = data.application.modules;
    state.curAppDefaultModule = data.application.modules.find(module => module.is_default);

    if (moduleId) {
      state.curAppModule = data.application.modules.find(module => module.name === moduleId);
    } else if (data.application.modules.length) {
      state.curAppModule = state.curAppDefaultModule;
    }
  },
  addAppModule(state, data) {
    // state.curAppModuleList.push(data)
    state.curAppModule = data;
    state.curAppInfo.application.modules.push(data);
  },
  updateCurAppName(state, name) {
    state.curAppInfo.application.name = name;
  },
  updateCurDescAppStatus(state, status) {
    state.curAppInfo.feature.APPLICATION_DESCRIPTION = status;
  },
  updateCurAppProduct(state, product) {
    state.curAppInfo.product = product;
    state.curAppInfo.name = product.name;
    state.curAppInfo.application.name = product.name;
  },
  updateCurAppBaseInfo(state, data) {
    state.curAppInfo.application.logo_url = data.logo_url;
    state.curAppInfo.application.name = data.name_zh_cn;
  },
  updateCurAppMarketPublished(state, flag) {
    if (state.curAppInfo.application && state.curAppInfo.application.config_info) {
      state.curAppInfo.application.config_info.market_published = flag;
    }
  },
  updateCurAppModule(state, data) {
    state.curAppModule = data;
  },
  updateCurAppModuleExposed(state, type) {
    state.curAppModule.exposed_url_type = type;
  },
  updateCurAppModuleIsDefault(state, moduleId) {
    state.curAppModuleList.forEach((modules) => {
      modules.is_default = modules.id === moduleId;
    });
  },
  updateCurAppByCode(state, { appCode, moduleId }) {
    // 使用严格的 appCode 验证
    if (!validateAppCode(appCode)) {
      console.warn(`[Security] Invalid appCode blocked in updateCurAppByCode: ${appCode}`);
      return;
    }

    // 确保 appInfo 是安全的无原型对象
    if (Object.getPrototypeOf(state.appInfo) !== null) {
      state.appInfo = createSafeObject(state.appInfo);
    }

    if (safeHas(state.appInfo, appCode)) {
      const data = state.appInfo[appCode];
      state.curAppInfo = data;
      state.curAppModuleList = data.application.modules;

      state.curAppDefaultModule = data.application.modules.find(module => module.is_default);

      if (moduleId) {
        state.curAppModule = data.application.modules.find(module => module.name === moduleId);
      } else if (data.application.modules.length) {
        state.curAppModule = state.curAppDefaultModule;
      }
    }
  },
  updateLocalLanguage(state, data) {
    state.localLanguage = data;
  },
  updateNavType(state, data) {
    state.navType = data;
  },
  updateApplyUrl(state, data) {
    state.applyUrl = data;
  },
  updateErrorDetail(state, data) {
    state.errorDetail = data;
  },
  updataEnvEventData(state, data) {
    if (data.length) {
      state.envEventData.push(...data);
    } else {
      state.envEventData = [];
    }
  },
  updataNoticeStatus(state, data) {
    state.isShowNotice = data;
  },
  updataUserInfo(state, data) {
    state.curUserInfo = data;
  },
  updataPlatformConfig(state, data) {
    state.platformConfig = data;
  },
};

// 公共 actions
const actions = {
  /**
   * 获取用户功能开关详情
   */
  getUserFeature({ commit }, config = {}) {
    const url = `${BACKEND_URL}/api/accounts/feature_flags/`;
    return http.get(url, config).then((data) => {
      commit('updateUserFeature', data);
    });
  },

  /**
   * 获取平台功能开关详情
   */
  getPlatformFeature({ commit }, config = {}) {
    const url = `${BACKEND_URL}/api/platform/frontend_features/`;
    return http.get(url, config).then((data) => {
      commit('updatePlatformFeature', data);
    });
  },

  /**
   * 获取应用功能开关详情
   */
  getAppFeature({ commit }, { appCode }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/feature_flags/${appCode}/`;
    return http.get(url, config).then((data) => {
      commit('updateAppFeature', { appCode, data });
    });
  },

  /**
   * 取消应用收藏
   */
  deleteAppMarked({}, { appCode }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/accounts/marked_applications/${appCode}`;
    return http.delete(url, config);
  },

  /**
   * 应用收藏
   */
  addAppMarked({}, { appCode }) {
    const url = `${BACKEND_URL}/api/bkapps/accounts/marked_applications/`;
    return http.post(url, {
      application: appCode,
    });
  },

  /**
   * 获取应用信息
   *
   * @param {Number} appCode 应用code
   */
  getAppInfo({ commit }, { appCode, moduleId }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/`;
    commit('updateAppLoading', true);
    return http.get(url).then((response) => {
      if (!moduleId) {
        moduleId = response.application.modules.find(module => module.is_default).name;
      }
      commit('updateAppInfo', { appCode, moduleId, data: response });
      return response;
    })
      .catch((err) => {
        if (err.apply_url_for_dev) {
          commit('updateApplyUrl', err.apply_url_for_dev);
        }
        return err;
      })
      .finally(() => {
        commit('updateAppLoading', false);
      });
  },

  /**
   * 获取应用列表
   *
   * @param {Object} params 参数配置
   */
  getAppList({}, { url }, config = {}) {
    return http.get(url, config);
  },

  /**
   * 对应用进行关注标记
   *
   * @param {Object} params 参数，包括appCode, isMarked
   */
  toggleAppMarked({ dispatch }, { appCode, isMarked }) {
    if (isMarked) {
      return dispatch('deleteAppMarked', { appCode });
    }
    return dispatch('addAppMarked', { appCode });
  },

  /**
   * 获取应用类型信息
   * @param {String} region 应用类型
   */
  getAppRegion({}, region) {
    const url = `${BACKEND_URL}/api/regions/${region}/`;
    return http.get(url, {}, { fromCache: true });
  },

  /**
   * 根据不同的代码库获取git repos列表
   * @param {String} sourceControlType 源码仓库类型
   */
  getRepoList({}, { sourceControlType }, config = {}) {
    const url = `${BACKEND_URL}/api/sourcectl/${sourceControlType}/repos/`;
    return http.get(url, config);
  },

  /**
   * 获取版本日志
   */
  getVersionLog({}, config = {}) {
    const url = `${BACKEND_URL}/api/changelogs/`;
    return http.get(url, config);
  },

  /**
   * 切换语言
   */
  switchLanguage({}, { data }, config = {}) {
    const url = `${BACKEND_URL}/i18n/setlang/`;
    return http.post(url, data, config);
  },
};

export default new Vuex.Store({
  // 模块
  modules: {
    region,
    application,
    deploy,
    packages,
    search,
    sourcectl,
    log,
    baseInfo,
    entryConfig,
    module,
    processes,
    market,
    member,
    envVar,
    order,
    ip,
    analysis,
    user,
    createApp,
    service,
    devopsAuth,
    alarm,
    docuManagement,
    cloudApi,
    credential,
    overview,
    // 插件开发者中心
    plugin,
    pluginMembers,
    imageManage,
    observability,
    persistentStorage,
    authenticationInfo,
    migration,
    sandbox,
    tool,
    tenant,
    tenantOperations,
    tenantConfig,
  },
  state,
  getters,
  mutations,
  actions,
});
