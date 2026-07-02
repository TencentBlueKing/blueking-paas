/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

const loaderTable = () => import(/* webpackChunkName: 'paas-loader-table' */ './base/table.vue');
const tableLoading = () => ({
  component: loaderTable,
});

const loadingMap = {
  'analysis-loading': () => import(/* webpackChunkName: 'paas-loader-analysis' */ './loading/analysis.vue'),
  'apps-loading': () => import(/* webpackChunkName: 'paas-loader-apps' */ './loading/apps.vue'),
  'base-info-loading': () => import(/* webpackChunkName: 'paas-loader-base-info' */ './loading/base-info.vue'),
  'cloud-api-index-loading': () => import(/* webpackChunkName: 'paas-loader-cloud-api-index' */ './loading/cloud-api-index.vue'),
  'cloud-api-inner-index-loading': () => import(/* webpackChunkName: 'paas-loader-cloud-api-index-inner' */ './loading/cloud-api-index-inner.vue'),
  'build-config-loading': () => import(/* webpackChunkName: 'paas-loader-clound-build-config' */ './loading/clound-build-config.vue'),
  'code-loading': () => import(/* webpackChunkName: 'paas-loader-code' */ './loading/code.vue'),
  'code-review-loading': () => import(/* webpackChunkName: 'paas-loader-code-review' */ './loading/code-review.vue'),
  'create-plugin-loading': () => import(/* webpackChunkName: 'paas-loader-create-plugin' */ './loading/create-plugin.vue'),
  'dashboard-loading': () => import(/* webpackChunkName: 'paas-loader-dashboard' */ './loading/dashboard.vue'),
  'data-inner-shared-loading': () => import(/* webpackChunkName: 'paas-loader-data-inner-shared' */ './loading/data-inner-shared.vue'),
  'data-store-loading': () => import(/* webpackChunkName: 'paas-loader-data-store' */ './loading/data-store.vue'),
  'deploy-loading': () => import(/* webpackChunkName: 'paas-loader-deploy' */ './loading/deploy.vue'),
  'deploy-config-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-config' */ './loading/deploy-config.vue'),
  'table-loading': tableLoading(),
  'deploy-hook-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-hook' */ './loading/deploy-hook.vue'),
  'deploy-inner-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-inner' */ './loading/deploy-inner.vue'),
  'deploy-module-info-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-module-info' */ './loading/deploy-module-info.vue'),
  'deploy-process-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-process' */ './loading/deploy-process.vue'),
  'deploy-resource-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-resource' */ './loading/deploy-resource.vue'),
  'deploy-top-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-top' */ './loading/deploy-top.vue'),
  'deploy-yaml-loading': () => import(/* webpackChunkName: 'paas-loader-deploy-yaml' */ './loading/deploy-yaml.vue'),
  'devops-loading': () => import(/* webpackChunkName: 'paas-loader-devops' */ './loading/devops.vue'),
  'docu-manager-loading': () => import(/* webpackChunkName: 'paas-loader-docu-manager' */ './loading/docu-manager.vue'),
  'entry-loading': () => import(/* webpackChunkName: 'paas-loader-entry' */ './loading/entry.vue'),
  'env-loading': () => import(/* webpackChunkName: 'paas-loader-env' */ './loading/env.vue'),
  'exempt-loading': () => import(/* webpackChunkName: 'paas-loader-exempt' */ './loading/exempt.vue'),
  'image-manage-loading': () => import(/* webpackChunkName: 'paas-loader-image-manage' */ './loading/image-manage.vue'),
  'index-loading': () => import(/* webpackChunkName: 'paas-loader-index' */ './loading/index.vue'),
  'log-loading': () => import(/* webpackChunkName: 'paas-loader-log' */ './loading/log.vue'),
  'market-loading': () => import(/* webpackChunkName: 'paas-loader-market' */ './loading/market.vue'),
  'market-info-loading': () => import(/* webpackChunkName: 'paas-loader-market-info' */ './loading/market-info.vue'),
  'market-mobile-loading': () => import(/* webpackChunkName: 'paas-loader-market-mobile' */ './loading/market-mobile.vue'),
  'market-visit-loading': () => import(/* webpackChunkName: 'paas-loader-market-visit' */ './loading/market-visit.vue'),
  'migration-loading': () => import(/* webpackChunkName: 'paas-loader-migration' */ './loading/migration.vue'),
  'module-manage-loading': () => import(/* webpackChunkName: 'paas-loader-module-manage' */ './loading/module-manage.vue'),
  'persistent-storage-loading': () => import(/* webpackChunkName: 'paas-loader-persistent-storage' */ './loading/persistent-storage.vue'),
  'platform-config-loading': () => import(/* webpackChunkName: 'paas-loader-platform-config' */ './loading/platform-config.vue'),
  'plugin-base-info-loading': () => import(/* webpackChunkName: 'paas-loader-plugin-base-info' */ './loading/plugin-base-info.vue'),
  'plugin-market-info-loading': () => import(/* webpackChunkName: 'paas-loader-plugin-market-info' */ './loading/plugin-market-info.vue'),
  'plugin-new-version-loading': () => import(/* webpackChunkName: 'paas-loader-plugin-new-version' */ './loading/plugin-new-version.vue'),
  'plugin-process-loading': () => import(/* webpackChunkName: 'paas-loader-plugin-process' */ './loading/plugin-process.vue'),
  'pluin-list-loading': () => import(/* webpackChunkName: 'paas-loader-pluin-list' */ './loading/pluin-list.vue'),
  'pluin-version-list-Loading': () => import(/* webpackChunkName: 'paas-loader-pluin-version-list' */ './loading/pluin-version-list.vue'),
  'process-loading': () => import(/* webpackChunkName: 'paas-loader-process' */ './loading/process.vue'),
  'process-service-loading': () => import(/* webpackChunkName: 'paas-loader-process-service' */ './loading/process-service.vue'),
  'sandbox-loading': () => import(/* webpackChunkName: 'paas-loader-sandbox' */ './loading/sandbox.vue'),
  'search-loading': () => import(/* webpackChunkName: 'paas-loader-search' */ './loading/search.vue'),
  'service-loading': () => import(/* webpackChunkName: 'paas-loader-service' */ './loading/service.vue'),
  'service-inner-loading': () => import(/* webpackChunkName: 'paas-loader-service-inner' */ './loading/service-inner.vue'),
  'summary-loading': () => import(/* webpackChunkName: 'paas-loader-summary' */ './loading/summary.vue'),
  'summary-plugin-loading': () => import(/* webpackChunkName: 'paas-loader-summary-plugin' */ './loading/summary-plugin.vue'),
  'visible-range-loading': () => import(/* webpackChunkName: 'paas-loader-visible-range' */ './loading/visible-range.vue'),
};

export default loadingMap;
