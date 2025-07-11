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

/**
 * 应用基础信息
 */

import store from '@/store';

export default {
  data() {
    return {
      winHeight: 300,
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppCode() {
      return this.$store.state.curAppCode;
    },
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    curAppModuleList() {
      return this.$store.state.curAppModuleList;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    isSmartApp() {
      return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SMART_APP;
    },
    curModuleId() {
      return this.curAppModule.name;
    },
    confirmRequiredWhenPublish() {
      if (this.curAppInfo) {
        return this.curAppInfo.web_config.confirm_required_when_publish;
      }
      return false;
    },
    productInfoProvided() {
      if (this.curAppInfo) {
        // return !this.canPublishToMarket || Boolean(this.curAppInfo.product)
        return this.confirmRequiredWhenPublish || Boolean(this.curAppInfo.product);
      }
      return false;
    },
  },
  /**
     * 进入当前组件时请求应用信息
     */
  async beforeRouteEnter(to, from, next) {
    const appCode = to.params.id;
    const { moduleId } = to.params;

    if (!store.state.appInfo[appCode]) {
      await store.dispatch('getAppInfo', { appCode, moduleId });
    } else {
      store.commit('updateCurAppByCode', { appCode, moduleId });
    }
    next(true);
  },
  /**
     * 当前组件路由切换时请求应用信息
     */
  async beforeRouteUpdate(to, from, next) {
    const appCode = to.params.id;
    const { moduleId } = to.params;

    if (!store.state.appInfo[appCode]) {
      await store.dispatch('getAppInfo', { appCode, moduleId });
    } else {
      store.commit('updateCurAppByCode', { appCode, moduleId });
    }
    next(true);
  },

  mounted() {
    this.winHeight = window.innerHeight;
  },
};
