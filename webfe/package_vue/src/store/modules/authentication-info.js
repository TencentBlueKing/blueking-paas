/*
*  鉴权信息/默认变量默认密钥
*/
import http from '@/api';

export default {
  namespaced: true,
  state: {},
  getters: {},
  mutations: {},
  actions: {
    /**
     * 获取密钥列表
     */
    getSecrets({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secrets/`;
      return http.get(url, config);
    },
    /**
     * 新建密钥
     */
    createSecrets({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secrets/`;
      return http.post(url, {}, config);
    },
    /**
     * 启用/禁用密钥
     */
    toggleKeyEnabledDisabled({}, { appCode, id, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secrets/${id}/`;
      return http.post(url, data, config);
    },
    /**
     * 删除密钥
     */
    deleteSecret({}, { appCode, id }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secrets/${id}/`;
      return http.delete(url, {}, config);
    },
    /**
      * 密钥查看-验证码校验带id
      */
    secretVerification({}, { appCode, id, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secret_verification/${id}/`;
      return http.post(url, data, config);
    },
    /**
     * 获取环境变量默认密钥
     */
    getDefaultSecret({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/default_secret/`;
      return http.get(url, config);
    },
    /**
      * 更换默认密钥
      */
    changeDefaultSecret({}, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/default_secret/`;
      return http.post(url, data, config);
    },
    /**
      * 默认密钥校验验证码无id
      */
    defaultSecretVerifications({}, { appCode, data }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/secret_verifications/`;
      return http.post(url, data, config);
    },
    /**
      * 获取已部署密钥
      */
    getDeployedSecret({}, { appCode }, config = {}) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${appCode}/deployed_secret/`;
      return http.get(url, {}, config);
    },
  },
};
