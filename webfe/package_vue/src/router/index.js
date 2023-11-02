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
import Router from 'vue-router';
import { pluginRouter } from './plugin';
import store from '@/store';

const frontPage = () => import(/* webpackChunkName: 'front-page' */'@/views/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const devCenterIndex = () => import(/* webpackChunkName: 'dev-center-index' */'@/views/dev-center/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const monitorIndex = () => import(/* webpackChunkName: 'monitor-index' */'@/views/dev-center/monitor').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const searchIndex = () => import(/* webpackChunkName: 'search' */'@/views/dev-center/search/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createApp = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/main').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createAppSucc = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/success').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createGitAppSucc = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/success-git').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createSmartAppSucc = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/success-smart').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createSimpleAppSucc = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/success-simple').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createAppFail = () => import(/* webpackChunkName: 'create-app' */'@/views/dev-center/create-app/failure').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appMigration = () => import(/* webpackChunkName: 'migration' */'@/views/dev-center/migration').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appIndex = () => import(/* webpackChunkName: 'app-index' */'@/views/dev-center/app/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// App: summary
const appSummary = () => import(/* webpackChunkName: 'app-sumary' */'@/views/dev-center/app/summary').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appSummaryNotDeployed = () => import(/* webpackChunkName: 'app-sumary' */'@/views/dev-center/app/summary/not-deployed').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appDeployments = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/deployment/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeployments = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForBuild = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-build').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForProcess = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-process').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForEnv = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-env').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForYaml = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-yaml').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeployForVolume = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-volume').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForResource = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-resource').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeploymentsForHook = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/cloud-deployment/deploy-hook').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appPackages = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/packages').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appDeploymentsForStag = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/deployment/deploy-stag').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appDeploymentsForProd = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/deployment/deploy-prod').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appDeploymentsForHistory = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/deployment/deploy-history').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appDeploymentsForConfig = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/deployment/deploy-config').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appProcesses = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/processes').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appStatus = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/app-status').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appEntryConfig = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/entry-config').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appEnvVars = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/env-vars').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppAnalysis = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/analysis/clound-index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appWebAnalysis = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/analysis/web').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appLogAnalysis = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/analysis/log').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appEventAnalysis = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/analysis/event').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appLog = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/log').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const monitorAlarm = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/monitor-alarm').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const codeReview = () => import(/* webpackChunkName: 'app-engine' */'@/views/dev-center/app/engine/code-review').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// App: market
const appMarket = () => import(/* webpackChunkName: 'app-market' */'@/views/dev-center/app/market').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
const appMobileMarket = () => import(/* webpackChunkName: 'app-market' */'@/views/dev-center/app/market/mobile-market').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appCreateModule = () => import(/* webpackChunkName: 'app-create-module' */'@/views/dev-center/app/create-module').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appCreateCloudModule = () => import(/* webpackChunkName: 'app-create-cloud-module' */'@/views/dev-center/app/create-cloud-module').then(module => module).catch((error) => {
  window.showDeployTip(error);
});


// App: basic config
const appConfigs = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// App: basic config
const appMembers = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/members').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appCloudAPI = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/cloud-api').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const imageCredential = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/engine/cloud-deployment/image-credential').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const moduleInfo = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/engine/cloud-deployment/module-info').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appBasicInfo = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/info').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
const moduleManage = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/module-manage').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// App: Services
const appServices = () => import(/* webpackChunkName: 'app-services' */'@/views/dev-center/app/engine/cloud-deployment/app-services').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// App: Services
const appServicesByCategory = () => import(/* webpackChunkName: 'app-services' */'@/views/dev-center/app/services/category').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appServicesInstance = () => import(/* webpackChunkName: 'app-services' */'@/views/dev-center/app/services/instance').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appServicesSharedInstance = () => import(/* webpackChunkName: 'app-services' */'@/views/dev-center/app/services/shared-instance').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const appServicesConfig = () => import(/* webpackChunkName: 'app-services' */'@/views/dev-center/app/services/config').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// Services:
const srvsBase = () => import(/* webpackChunkName: 'services' */'@/views/services/base').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// Services: dynamic
const srvIndex = () => import(/* webpackChunkName: 'services' */'@/views/services/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvOverview = () => import(/* webpackChunkName: 'services' */'@/views/services/overview').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvVCSMain = () => import(/* webpackChunkName: 'services' */'@/views/services/vcs').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvV3Services = () => import(/* webpackChunkName: 'services' */'@/views/services/v3-services').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// Services: static
const srvStaticMagicBox = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/magic-box').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticAppCI = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/ci').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticAPIGateway = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/api-gateway').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticLesscode = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/lesscode').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticSDKBlueapps = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/sdk-blueapps').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticAppEngine = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/app-engine').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticBamboo = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/bamboo').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticMarket = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/market').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const srvStaticFeaturedApps = () => import(/* webpackChunkName: 'services-info' */'@/views/services/static/featured-apps').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const docuManagement = () => import(/* webpackChunkName: 'docu-management' */'@/views/dev-center/app/docu-management').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// 云原生部署管理
const cloudAppDeployManage = () => import(/* webpackChunkName: 'cloud-deploy-manage' */'@/views/dev-center/app/engine/cloud-deploy-manage/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeployManageStag = () => import(/* webpackChunkName: 'cloud-deploy-manage' */'@/views/dev-center/app/engine/cloud-deploy-manage/comps/stag').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeployManageProd = () => import(/* webpackChunkName: 'cloud-deploy-manage' */'@/views/dev-center/app/engine/cloud-deploy-manage/comps/prod').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppDeployHistory = () => import(/* webpackChunkName: 'cloud-deploy-manage' */'@/views/dev-center/app/engine/cloud-deploy-manage/comps/deploy-history').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppEventQuery = () => import(/* webpackChunkName: 'cloud-event-query' */'@/views/dev-center/app/engine/cloud-event-query/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const cloudAppImageManage = () => import(/* webpackChunkName: 'cloud-image-manage' */'@/views/dev-center/app/engine/clound-image-manage/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
const cloudAppImageList = () => import(/* webpackChunkName: 'cloud-image-manage' */'@/views/dev-center/app/engine/clound-image-manage/comps/image-list').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
const cloudAppBuildHistory = () => import(/* webpackChunkName: 'cloud-image-manage' */'@/views/dev-center/app/engine/clound-image-manage/comps/build-history').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// error pages
const notFound = () => import(/* webpackChunkName: 'not-found' */'@/views/error-pages/not-found').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
const permission403 = () => import(/* webpackChunkName: 'permission403' */'@/views/error-pages/403').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

Vue.use(Router);

const router = new Router({
  mode: 'history',
  // 页面刷新时回到顶部
  scrollBehavior() {
    return { x: 0, y: 0 };
  },
  routes: [
    ...pluginRouter,
    {
      path: '/',
      name: 'home',
      component: frontPage,
    },
    {
      path: '/developer-center/',
      name: 'index',
      component: frontPage,
      meta: {
        // 只有首页需要footer版本信息
        showPaasFooter: true,
      },
    },
    {
      path: '/developer-center/apps/',
      name: 'myApplications',
      component: devCenterIndex,
    },
    {
      path: '/developer-center/apps/my-monitor',
      name: 'myMonitor',
      component: monitorIndex,
    },
    {
      path: '/developer-center/apps/search',
      name: 'search',
      component: searchIndex,
    },
    {
      path: '/developer-center/app/create',
      name: 'createApp',
      component: createApp,
    },
    {
      path: '/developer-center/apps/:id/module/create',
      component: appCreateModule,
      name: 'appCreateModule',
    },
    {
      path: '/developer-center/apps/:id/cloud-module/create',
      component: appCreateCloudModule,
      name: 'appCreateCloudModule',
    },
    {
      path: '/developer-center/apps/migration/',
      name: 'appLegacyMigration',
      component: appMigration,
    },
    {
      path: '/developer-center/apps/:id/403',
      name: 'permission403',
      component: permission403,
    },
    {
      path: '/developer-center/apps/',
      name: '应用概览',
      component: appIndex,
      meta: {
        capture403Error: true,
      },
      children: [
        {
          path: ':id',
          redirect: {
            name: 'appSummary',
          },
        },
        {
          path: ':id/:moduleId/summary',
          component: appSummary,
          name: 'appSummary',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/summary',
          component: appSummary,
          name: 'appSummaryWithModule',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/summary_none',
          component: appSummaryNotDeployed,
          name: 'appSummaryEmpty',
        },
        {
          path: ':id/base-info',
          component: appBasicInfo,
          name: 'appBaseInfo',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/:moduleId/module-manage',
          component: moduleManage,
          name: 'moduleManage',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/module-manage',
          component: moduleManage,
          name: 'moduleManageWithModule',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/app-configs',
          component: appConfigs,
          name: 'appConfigs',
          redirect: {
            name: 'cloudAppMarket',
          },
          children: [
            {
              path: 'market',
              component: appMarket,
              name: 'cloudAppMarket',
              meta: {
                module: 'market',
              },
            },
            {
              path: 'info',
              component: appBasicInfo,
              name: 'appBasicInfo',
              meta: {
                module: 'info',
              },
            },
            {
              path: 'member',
              component: appMembers,
              name: 'appMembers',
              meta: {
                module: 'member',
              },
            },
          ],
        },
        {
          path: ':id/:moduleId/event-query',
          component: cloudAppEventQuery,
          name: 'cloudAppEventQuery',
        },
        // 云原生访问统计
        {
          path: ':id/cloud-analysis',
          component: cloudAppAnalysis,
          name: 'cloudAppAnalysis',
          redirect: {
            name: 'cloudAppWebAnalysis',
          },
          children: [
            {
              path: ':moduleId/web-analysis',
              component: appWebAnalysis,
              name: 'cloudAppWebAnalysis',
              meta: {
                module: 'web',
              },
            },
            {
              path: ':moduleId/log-analysis',
              component: appLogAnalysis,
              name: 'cloudAppLogAnalysis',
              meta: {
                module: 'log',
              },
            },
            {
              path: ':moduleId/event-analysis',
              component: appEventAnalysis,
              name: 'cloudAppEventAnalysis',
              meta: {
                module: 'event',
              },
            },
          ],
        },
        {
          path: ':id/roles',
          component: appMembers,
          name: 'appRoles',
          meta: {
            capture403Error: false,
          },
        },
        {
          path: ':id/:moduleId/deploy',
          component: appDeployments,
          name: 'appDeploy',
          redirect: {
            name: 'appDeployForStag',
          },
          children: [
            {
              path: 'stag',
              component: appDeploymentsForStag,
              name: 'appDeployForStag',
              meta: {
                module: 'stag',
              },
            },
            {
              path: 'prod',
              component: appDeploymentsForProd,
              name: 'appDeployForProd',
              meta: {
                module: 'prod',
              },
            },
            {
              path: 'history',
              component: appDeploymentsForHistory,
              name: 'appDeployForHistory',
              meta: {
                module: 'history',
              },
            },
            {
              path: 'config',
              component: appDeploymentsForConfig,
              name: 'appDeployForConfig',
              meta: {
                module: 'config',
              },
            },
          ],
        },
        {
          path: ':id/:moduleId/cloud-deploy',
          component: cloudAppDeployments,
          name: 'cloudAppDeploy',
          redirect: {
            name: 'cloudAppDeployForProcess',
          },
          children: [
            {
              path: 'build',
              component: cloudAppDeploymentsForBuild,
              name: 'cloudAppDeployForBuild',
              meta: {
                module: 'build',
              },
            },
            {
              path: 'process',
              component: cloudAppDeploymentsForProcess,
              name: 'cloudAppDeployForProcess',
              meta: {
                module: 'process',
              },
            },
            {
              path: 'env',
              component: cloudAppDeploymentsForEnv,
              name: 'cloudAppDeployForEnv',
              meta: {
                module: 'env',
              },
            },
            {
              path: 'yaml',
              component: cloudAppDeploymentsForYaml,
              name: 'cloudAppDeployForYaml',
              meta: {
                module: 'yaml',
              },
            },
            {
              path: 'volume',
              component: cloudAppDeployForVolume,
              name: 'cloudAppDeployForVolume',
              meta: {
                module: 'volume',
              },
            },
            {
              path: 'hook',
              component: cloudAppDeploymentsForHook,
              name: 'cloudAppDeployForHook',
              meta: {
                module: 'hook',
              },
            },
            {
              path: 'resource',
              component: cloudAppDeploymentsForResource,
              name: 'cloudAppDeployForResource',
              meta: {
                module: 'resource',
              },
            },
            {
              path: 'ticket',
              component: imageCredential,
              name: 'imageCredential',
              meta: {
                module: 'ticket',
              },
            },
            {
              path: 'module-info',
              component: moduleInfo,
              name: 'moduleInfo',
              meta: {
                module: 'module-info',
              },
            },
            {
              path: 'services',
              component: appServices,
              name: 'appServices',
              meta: {
                module: 'services',
              },
            },
            {
              path: 'service/:category_id/service_inner/:service',
              component: appServicesInstance,
              name: 'cloudAppServiceInner',
            },
            {
              path: 'service/:category_id/service_inner_shared/:service',
              component: appServicesSharedInstance,
              name: 'cloudAppServiceInnerShared',
            },
            {
              path: 'service/:category_id/service_inner_shared/:service',
              component: appServicesSharedInstance,
              name: 'cloudAppServiceInnerShared',
            },
          ],
        },
        {
          path: ':id/deploy',
          component: appDeployments,
          name: 'appDeployWithModule',
        },
        {
          path: ':id/:moduleId/package',
          component: appPackages,
          name: 'appPackages',
        },
        {
          path: ':id/:moduleId/process',
          component: appProcesses,
          name: 'appProcess',
        },
        {
          path: ':id/clound-image-manage',
          component: cloudAppImageManage,
          name: 'cloudAppImageManage',
          redirect: {
            name: 'cloudAppImageList',
          },
          children: [
            {
              path: 'image-list',
              component: cloudAppImageList,
              name: 'cloudAppImageList',
            },
            {
              path: 'build-history',
              component: cloudAppBuildHistory,
              name: 'cloudAppBuildHistory',
              meta: {
                history: true,
              },
            },
          ],
        },
        // 云原生部署管理
        {
          path: ':id/cloud-deploy-manage',
          component: cloudAppDeployManage,
          name: 'cloudAppDeployManage',
          redirect: {
            name: 'cloudAppDeployForProcess',
          },
          children: [
            {
              path: 'stag',
              component: cloudAppDeployManageStag,
              name: 'cloudAppDeployManageStag',
              meta: {
                module: 'cloudDeployStag',
              },
            },
            {
              path: 'prod',
              component: cloudAppDeployManageProd,
              name: 'cloudAppDeployManageProd',
              meta: {
                module: 'cloudDeployProd',
              },
            },
            {
              path: 'deploy-history',
              component: cloudAppDeployHistory,
              name: 'cloudAppDeployHistory',
              meta: {
                module: 'cloudAppDeployHistory',
                history: true,
              },
            },
          ],
        },
        {
          path: ':id/:moduleId/status',
          component: appStatus,
          name: 'appStatus',
        },
        {
          path: ':id/process',
          component: appProcesses,
          name: 'appProcessWithModule',
        },
        {
          path: ':id/cloudapi',
          component: appCloudAPI,
          name: 'appCloudAPI',
        },
        {
          path: ':id/market',
          component: appMarket,
          name: 'appMarket',
        },
        {
          path: ':id/mobile-market',
          component: appMobileMarket,
          name: 'appMobileMarket',
        },
        {
          path: ':id/app_entry_config',
          component: appEntryConfig,
          name: 'appEntryConfig',
        },
        {
          path: ':id/:moduleId/log',
          component: appLog,
          name: 'appLog',
        },
        {
          path: ':id/log',
          component: appLog,
          name: 'appLogWithModule',
        },
        {
          path: ':id/:moduleId/monitor-alarm',
          component: monitorAlarm,
          name: 'monitorAlarm',
        },
        {
          path: ':id/monitor-alarm',
          component: monitorAlarm,
          name: 'monitorAlarmWithModule',
        },
        {
          path: ':id/:moduleId/web-analysis',
          component: appWebAnalysis,
          name: 'appWebAnalysis',
        },
        {
          path: ':id/web-analysis',
          component: appWebAnalysis,
          name: 'appWebAnalysisWithModule',
        },
        {
          path: ':id/:moduleId/log-analysis',
          component: appLogAnalysis,
          name: 'appLogAnalysis',
        },
        {
          path: ':id/log-analysis',
          component: appLogAnalysis,
          name: 'appLogAnalysisWithModule',
        },
        {
          path: ':id/:moduleId/event-analysis',
          component: appEventAnalysis,
          name: 'appEventAnalysis',
        },
        {
          path: ':id/event-analysis',
          component: appEventAnalysis,
          name: 'appEventAnalysisWithModule',
        },
        {
          path: ':id/:moduleId/code-review',
          component: codeReview,
          name: 'codeReview',
        },
        {
          path: ':id/code-review',
          component: codeReview,
          name: 'codeReviewWithModule',
        },
        {
          path: ':id/:moduleId/environment_variable',
          component: appEnvVars,
          name: 'appEnvVariables',
        },
        {
          path: ':id/environment_variable',
          component: appEnvVars,
          name: 'appEnvVariablesWithModule',
        },
        {
          path: ':id/none',
          name: 'none-app',
          component: notFound,
        },
        {
          path: ':id/:moduleId/service/:category_id',
          component: appServicesByCategory,
          name: 'appService',
        },
        {
          path: ':id/service/:category_id',
          component: appServicesByCategory,
          name: 'appServiceWithModule',
        },
        {
          path: ':id/:moduleId/service/:category_id/service_inner/:service',
          component: appServicesInstance,
          name: 'appServiceInner',
        },
        {
          path: ':id/service/:category_id/service_inner/:service',
          component: appServicesInstance,
          name: 'appServiceInnerWithModule',
        },
        {
          path: ':id/:moduleId/service/:category_id/service_inner_shared/:service',
          component: appServicesSharedInstance,
          name: 'appServiceInnerShared',
        },
        {
          path: ':id/service/:category_id/service_inner_shared/:service',
          component: appServicesSharedInstance,
          name: 'appServiceInnerShared',
        },
        {
          path: ':id/:moduleId/service/:category_id/service_config/:service',
          component: appServicesConfig,
          name: 'appServiceConfig',
        },
        {
          path: ':id/docu-management',
          component: docuManagement,
          name: 'docuManagement',
        },
      ],
    },
    {
      path: '/developer-center/service/',
      component: srvsBase,
      children: [
        {
          path: '',
          component: srvIndex,
          name: 'serviceIndex',
        },
        {
          path: 'code',
          component: srvVCSMain,
          name: 'serviceCode',
        },
        {
          path: 'magicbox',
          component: srvStaticMagicBox,
          name: 'serviceMagicBox',
        },
        {
          path: 'ci',
          component: srvStaticAppCI,
          name: 'serviceCi',
        },
        {
          path: 'apigateway',
          component: srvStaticAPIGateway,
          name: 'serviceAPIGateway',
        },
        {
          path: 'lesscode',
          component: srvStaticLesscode,
          name: 'serviceLesscode',
        },
        {
          path: 'framework',
          component: srvStaticSDKBlueapps,
          name: 'serviceFramework',
        },
        {
          path: 'vas/:category_id/service_inner/:name',
          component: srvOverview,
          name: 'serviceInnerPage',
        },
        {
          path: 'app-engine',
          component: srvStaticAppEngine,
          name: 'serviceAppEngine',
        },
        {
          path: 'vas/:category_id',
          component: srvV3Services,
          name: 'serviceVas',
        },
        {
          path: 'bamboo',
          component: srvStaticBamboo,
          name: 'serviceBamboo',
        },
        {
          path: 'market',
          component: srvStaticMarket,
          name: 'serviceMarket',
        },
        {
          path: 'recommend',
          component: srvStaticFeaturedApps,
          name: 'serviceRecommend',
        },
      ],
    },
    {
      path: '/developer-center/apps/:id/create/success',
      name: 'createSimpleAppSucc',
      component: createSimpleAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/smart/success',
      name: 'createSmartAppSucc',
      component: createSmartAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/bk_svn/success',
      name: 'createAppSucc',
      component: createAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/bare_svn/success',
      name: 'createCustomSvnAppSucc',
      component: createAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/bk_gitlab/success',
      name: 'createGitLabAppSucc',
      component: createGitAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/tc_git/success',
      name: 'createTCGitAppSucc',
      component: createGitAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/bare_git/success',
      name: 'createCustomGitAppSucc',
      component: createGitAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/github/success',
      name: 'createGithubAppSucc',
      component: createGitAppSucc,
    },
    {
      path: '/developer-center/apps/:id/create/gitee/success',
      name: 'createGithubAppSucc',
      component: createGitAppSucc,
    },
    {
      path: '/developer-center/app/create/fail',
      name: 'createAppFail',
      component: createAppFail,
    },
    {
      path: 'none',
      name: 'none',
      component: notFound,
    },
    {
      path: '*',
      name: '404',
      component: notFound,
    },
  ],
});

router.beforeEach(async (to, from, next) => {
  sessionStorage.setItem('NOTICE', true);
  if (window.location.href.indexOf(window.GLOBAL_CONFIG.V3_OA_DOMAIN) !== -1) {
    const url = window.location.href.replace(window.GLOBAL_CONFIG.V3_OA_DOMAIN, window.GLOBAL_CONFIG.V3_WOA_DOMAIN);
    window.location.replace(url);
  } else {
    if (to.path.startsWith('/plugin-center')) {
      // 可能为页面刷新重新调用获取功能开关
      if (!store.state.userFeature.ALLOW_PLUGIN_CENTER) {
        await store.dispatch('getUserFeature');
      }
      store.state.userFeature.ALLOW_PLUGIN_CENTER ? next() : next({ name: '404' });
    }
    next();
  }
});

export default router;
