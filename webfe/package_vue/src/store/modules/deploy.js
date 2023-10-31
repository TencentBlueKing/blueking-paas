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
 * 管理当前 app 部署相关的属性
 */
import http from '@/api';
import { json2Query } from '@/common/tools';

const state = {
  // 是否允许推广到应用市场, 一般只有接入登录的应用才允许
  // canPublishToMarket: false,
  availableBranch: '',
  productInfoProvided: false,

  confirmRequiredWhenPublish: false,
  availableType: 'branch',
};

const getters = {
  // canPublishToMarket: state => state.canPublishToMarket,
  productInfoProvided: state => state.productInfoProvided,
  availableBranch: state => state.availableBranch,
  confirmRequiredWhenPublish: state => state.confirmRequiredWhenPublish,
};

const mutations = {
  updateDeploymentInfo(state, { key, value }) {
    state[key] = value;
  },
};

// actions
const actions = {
  checkProductInfoProvided({ commit, state }, appCode) {
    return http.get(`${BACKEND_URL}/api/bkapps/applications/${appCode}/`).then((response) => {
      commit('updateDeploymentInfo', {
        key: 'confirmRequiredWhenPublish',
        value: response.web_config.confirm_required_when_publish,
      });
      commit('updateDeploymentInfo', {
        key: 'productInfoProvided',
        value: !state.confirmRequiredWhenPublish || Boolean(response.product),
      });
    });
  },

  refreshAvailableBranch({ commit }, { appCode, moduleId }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/stag/released_state/`;
    return http.get(url).then((res) => {
      const branchData = res.deployment;
      if (branchData) {
        commit('updateDeploymentInfo', {
          key: 'availableBranch',
          value: branchData.repo.name,
        });
        commit('updateDeploymentInfo', {
          key: 'availableType',
          value: branchData.repo.type,
        });
        return `${branchData.repo.type}:${branchData.repo.name}`;
      }
      commit('updateDeploymentInfo', {
        key: 'availableBranch',
        value: '',
      });
      commit('updateDeploymentInfo', {
        key: 'availableType',
        value: 'branch',
      });
      return '';
    }, () => {
      commit('updateDeploymentInfo', {
        key: 'availableBranch',
        value: '',
      });
      commit('updateDeploymentInfo', {
        key: 'availableType',
        value: 'branch',
      });
    });
  },

  updateAvailableBranch({ commit }, availableBranch) {
    commit('updateDeploymentInfo', {
      key: 'availableBranch',
      value: availableBranch,
    });
  },

  updateAvailableType({ commit }, availableType) {
    commit('updateDeploymentInfo', {
      key: 'availableType',
      value: availableType,
    });
  },

  /**
     * 获取部署的基本信息
     * @param {Object} params 请求参数：appCode, apiType, apiPackageSelected
     */
  getModuleRuntimeOverview({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/runtime/overview`;
    return http.get(url, config);
  },

  /**
     * 获取模块部署信息
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getModuleReleaseInfo({ commit }, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/released_state/`;
    return http.get(url, config).then((res) => {
      if (!res.is_offlined && env === 'stag') {
        commit('updateDeploymentInfo', {
          key: 'availableBranch',
          value: res.deployment.repo.name,
        });
        commit('updateDeploymentInfo', {
          key: 'availableType',
          value: res.deployment.repo.type,
        });
      }
      return res;
    })
      .catch((res) => {
        commit('updateDeploymentInfo', {
          key: 'availableBranch',
          value: '',
        });
        commit('updateDeploymentInfo', {
          key: 'availableType',
          value: 'branch',
        });
        return res;
      });
  },

  /**
   * 获取部署管理列表信息
   * @param {Object} params 请求参数：appCode, env
   */
  getModuleReleaseList({ }, { appCode, env },  config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/envs/${env}/processes/list/`;
    return http.get(url, config);
  },

  /**
     * 获取模块部署分支
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getModuleBranches({}, { appCode, moduleId }, config = { requestId: 'getModuleBranches' }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/repo/branches/`;
    return http.get(url, config);
  },

  /**
     * 部署模块
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  createDeployForModule({}, { appCode, moduleId, env, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deployments/`;
    return http.post(url, params, config);
  },

  /**
     * 获取模块部署结果
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getDeployResult({}, { appCode, moduleId, deployId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deployments/${deployId}/result/`;
    return http.get(url, config);
  },

  /**
     * 获取git代码对比链接
     * @param {Object} params 请求参数：appCode, fromVersion, toVersion
     */
  getGitCompareUrl({}, { appCode, moduleId, fromVersion, toVersion }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/repo/commit-diff-external/${fromVersion}/${toVersion}/`;
    return http.get(url, config);
  },

  /**
     * 获取svn代码提交记录
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getSvnCommits({}, { appCode, moduleId, fromVersion, toVersion }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/repo/commit-diff/${fromVersion}/${toVersion}/logs/`;
    return http.get(url, config);
  },

  /**
     * 获取部署前条件准备情况
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getDeployPreparations({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deploy/preparations`;
    return http.get(url, config);
  },

  /**
     * 模块下架
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  offlineApp({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/offlines/`;
    return http.post(url, {}, config);
  },

  /**
     * 获取模块下架进度
     * @param {Object} params 请求参数：appCode, moduleId, offlineOperationId
     */
  getOfflineResult({}, { appCode, moduleId, offlineOperationId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/offlines/${offlineOperationId}/result/`;
    return http.get(url, config);
  },

  /**
     * 检测模块下架进度状况，如果进行中需要拉起“获取模块下架进度”
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getOfflineStatus({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/offlines/resumable/`;
    return http.get(url, config);
  },

  /**
     * 检测模块部署进度状况
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getDeployStatus({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deployments/resumable/`;
    return http.get(url, config);
  },

  /**
     * 获取部署记录
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getDeployHistory({}, { appCode, moduleId, pageParams }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deploy_operations/lists/?${json2Query(pageParams)}`;
    return http.get(url, config);
  },

  /**
     * 获取部署前各阶段详情
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getPreDeployDetail({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deploy_phases/`;
    return http.get(url, config);
  },

  /**
     * 获取部署中阶段详情
     * @param {Object} params 请求参数：appCode, moduleId, env, uuid
     */
  getBeingDeployDetail({}, { appCode, moduleId, env, uuid }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deploy_phases/${uuid}/`;
    return http.get(url, config);
  },

  /**
     * 创建svn分支
     * @param {Object} params 请求参数：appCode, moduleId
     */
  createSvnBranch({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/repo/tags/`;
    return http.post(url, {}, config);
  },

  /**
     * 获取部署后各阶段详情
     * @param {Object} params 请求参数：appCode, moduleId, env, deployId
     */
  getDeployTimeline({}, { appCode, moduleId, env, deployId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deploy_phases/${deployId}/`;
    return http.get(url, config);
  },

  /**
     * 获取部署后日志
     * @param {Object} params 请求参数：appCode, moduleId, env, deployId
     */
  getDeployLog({}, { appCode, moduleId, deployId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deployments/${deployId}/result/`;
    return http.get(url, config);
  },

  /**
     * 获取应用文档列表
     * @param {Object} params 请求参数：appCode, moduleId, env, deployId
     */
  getAppDocLinks({}, { appCode, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/accessories/advised_documentary_links/?${json2Query(params)}`;
    return http.get(url, config);
  },

  /**
     * 获取架构信息
     * @param {Object} params 请求参数：appCode, moduleName, smart_revision
     */
  getSchemaInfo({}, { appCode, moduleName, versionType, versionName }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleName}/repo/revisions/${versionType}:${versionName}`;
    return http.get(url, config);
  },

  /**
     * 停止部署
     *
     * @param {Object} params 请求参数：appCode, moduleId, deployId
     */
  stopDeploy({}, { appCode, moduleId, deployId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deployments/${deployId}/interruptions/`;
    return http.post(url, {}, config);
  },

  /**
     * 获取当前模块的部署配置信息
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  getDeployConfig({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deploy_config/`;
    return http.get(url, {}, config);
  },

  /**
     * 更新当前模块的部署配置信息
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  updateDeployConfig({}, { appCode, moduleId, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deploy_config/hooks/`;
    return http.post(url, params, config);
  },

  /**
     * 禁用当前模块的部署配置信息
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  closeDeployConfig({}, { appCode, moduleId, type }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/deploy_config/hooks/${type}/disable/`;
    return http.put(url, {}, config);
  },

  /**
     * 获取指定模块所有环境的增强服务使用信息
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  getCloudAppResource({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/services/info/`;
    return http.get(url, config);
  },

  /**
     * 获取查看云原生YAML内容
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  getAppYamlManiFests({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bkapp_model/manifests/current/?output_format=json`;
    return http.get(url, config);
  },


  /**
   * 获取云原生hooks
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  getAppReleaseHook({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bkapp_model/deploy_hooks/pre-release-hook/`;
    return http.get(url, config);
  },

  /**
   * 保存云原生hooks
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  saveAppReleaseHook({}, { appCode, moduleId, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bkapp_model/deploy_hooks/`;
    return http.post(url, params, config);
  },

  /**
   * 获取云原生基本信息
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  getAppBuildConfigInfo({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/build_config/`;
    return http.get(url, config);
  },

  /**
   * 保存云原生基本信息
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  SaveAppBuildConfigInfo({}, { appCode, moduleId, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/build_config/`;
    return http.post(url, params, config);
  },


  /**
   * 获取云原生process进程配置
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  getAppProcessInfo({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bkapp_model/process_specs/`;
    return http.get(url, config);
  },

  /**
   * 保存云原生process进程配置
   *
   * @param {Object} params 请求参数：appCode, moduleId
  */
  saveAppProcessInfo({}, { appCode, moduleId, params }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bkapp_model/process_specs/`;
    return http.post(url, params, config);
  },

  /**
     * 提交发送云原生模块信息
     *
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  sumbitCloudApp({}, { appCode, moduleId, env, params }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/envs/${env}/mres/deployments/`;
    return http.post(url, params, config);
  },

  /**
     * 获取二次确认信息
     *
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getCloudAppInfo({}, { appCode, moduleId, env, params }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/envs/${env}/mres/deploy_preps/`;
    return http.post(url, params, config);
  },

  /**
     * 查看应用模型资源当前状态
     *
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getCloudAppStatus({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/envs/${env}/mres/status/`;
    return http.get(url, config);
  },

  /**
     * 查看应用模型状态YAML
     *
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getCloudAppDeployYaml({}, { appCode, moduleId, env, deployId }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/envs/${env}/mres/deployments/${deployId}/`;
    return http.get(url, config);
  },
  /**
     * 获取应用模型部署记录
     * @param {Object} params 请求参数：appCode, moduleId, env
     */
  getCloudAppDeployHistory({}, { appCode, moduleId, env, pageParams }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/envs/${env}/mres/deployments/?${json2Query(pageParams)}`;
    return http.get(url, config);
  },
  /**
     * 获取云原生应用ext
     *
     * @param {Object} params 请求参数：appCode, moduleId
     */
  getManifestExt({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/manifest_ext/`;
    return http.get(url, config);
  },

  /**
   * 获取进程是否开启自动扩缩容
   * @param {Object} params 请求参数：appCode, moduleId, env
   */
  getAutoScalFlagWithEnv({}, { appCode, moduleId, env }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/feature_flags/${appCode}/modules/${moduleId}/env/${env}/`;
    return http.get(url, config);
  },

  /**
   * 保存信息
   *
   * @param {Object} params 请求参数：appCode, moduleId, env
   */
  saveCloudAppInfo({}, { appCode, moduleId, params }, config = {}) {
    const url = `${BACKEND_URL}/svc_workloads/api/cnative/specs/applications/${appCode}/modules/${moduleId}/mres/`;
    return http.put(url, params, config);
  },

  /**
   * 获取进程资源配额方案
   * @param {Object} params 请求参数：appCode, moduleId, env
   */
  fetchQuotaPlans({}, {}, config = {}) {
    const url = `${BACKEND_URL}/api/mres/quota_plans/`;
    return http.get(url, config);
  },

  /**
   * 获取镜像信息
   * @param {Object} params 请求参数：appCode, moduleId
   */
  getMirrorInfo({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/build_config/`;
    return http.get(url, {}, config);
  },

  /**
   * 获取基础镜像列表
   * @param {Object} params 请求参数：appCode, moduleId
   */
  getBaseImageList({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/bp_runtimes/`;
    return http.get(url, {}, config);
  },

  /**
   * 获取代码检查详情
   * @param {Object} params 请求参数：appCode, moduleId
   */
  getCodeInspection({}, { appCode, moduleId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/ci/detail/`;
    return http.get(url, {}, config);
  },

  /**
   * 保存镜像信息
   * @param {Object} params 请求参数：appCode, moduleId, data
   */
  saveMirrorInfo({}, { appCode, moduleId, data }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/build_config/`;
    return http.post(url, data, config);
  },

  cloudDeployments({}, { appCode, moduleId, env, data }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${env}/deployments/`;
    return http.post(url, data, config);
  },

  /**
   * 获取镜像tag列表
   * @param {Object} params 请求参数：appCode, moduleId
   */
  getImageTagData({}, { appCode, moduleId, data }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/build/artifact/image/?${json2Query(data)}`;
    return http.get(url, {}, config);
  },

  /**
   * 仅镜像下获取镜像tag列表
   * @param {Object} params 请求参数：appCode, moduleId
   */
  getCustomImageTagData({}, { appCode, moduleId }, config = { globalError: false }) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/mres/image_tags/`;
    return http.get(url, {}, config);
  },

  /**
   * 获取某个部署版本的详细信息
   * @param {Object} params 请求参数：appCode, moduleId, environment, revisionId
   */
  getDeployVersionDetails({}, { appCode, moduleId, environment, revisionId }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/envs/${environment}/mres/revisions/${revisionId}/`;
    return http.get(url, {}, config);
  },

  /**
   * 新建挂载卷
   * @param {Object} params 请求参数：appCode, moduleId
   */
  createVolumeData({}, { appCode, moduleId, data }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/mres/volume_mounts/`;
    return http.post(url, data, config);
  },

  /**
   * 更新挂载卷
   * @param {Object} params 请求参数：appCode, moduleId
   */
  updateVolumeData({}, { appCode, moduleId, id, data }, config = {}) {
    const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/modules/${moduleId}/mres/volume_mounts/${id}`;
    return http.put(url, data, config);
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
