import i18n from '@/language/i18n.js';

const platformOverview = () =>
  import(/* webpackChunkName: 'platform-management' */ '@/views/platform/overview')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformManagement = () =>
  import(/* webpackChunkName: 'platform-management' */ '@/views/platform')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformAppCluster = () =>
  import(/* webpackChunkName: 'platform-management' */ '@/views/platform/app-cluster')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const clusterCreateEdit = () =>
  import(/* webpackChunkName: 'platform-management' */ '@/views/platform/app-cluster/cluster-create-edit')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformAddOns = () =>
  import(/* webpackChunkName: 'platform-services' */ '@/views/platform/services')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformUserManagement = () =>
  import(/* webpackChunkName: 'platform-user' */ '@/views/platform/user-management')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformAppList = () =>
  import(/* webpackChunkName: 'platform-operations' */ '@/views/platform/operations')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformAppDetails = () =>
  import(/* webpackChunkName: 'platform-operations' */ '@/views/platform/operations/details')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformOperationAudit = () =>
  import(/* webpackChunkName: 'platform-user' */ '@/views/platform/operation-audit')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const builtInEnvVariable = () =>
  import(/* webpackChunkName: 'platform-config' */ '@/views/platform/env-var')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const repositoryConfig = () =>
  import(/* webpackChunkName: 'platform-config' */ '@/views/platform/repository-config')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

export const platformRouters = [
  {
    path: '/plat-mgt/',
    name: 'platformManagement',
    component: platformManagement,
    redirect: {
      name: 'platformAppCluster',
    },
    children: [
      {
        path: 'overview',
        component: platformOverview,
        name: 'platformOverview',
        meta: {
          title: i18n.t('概览'),
        },
      },
      {
        path: 'app-cluster',
        component: platformAppCluster,
        name: 'platformAppCluster',
        meta: {
          title: i18n.t('应用集群'),
          panels: [
            { name: 'config', label: i18n.t('集群配置') },
            { name: 'list', label: i18n.t('集群列表') },
          ],
        },
      },
      {
        path: 'app-cluster/:type(edit|add)',
        name: 'clusterCreateEdit',
        component: clusterCreateEdit,
        meta: {
          title: i18n.t('添加集群'),
          supportBack: true,
          subTitle: i18n.t('集群名称'),
          backRoute: {
            name: 'platformAppCluster',
            query: {
              active: 'list',
            }
          }
        },
      },
      {
        path: 'add-ons',
        component: platformAddOns,
        name: 'platformAddOns',
        meta: {
          title: i18n.t('增强服务'),
          panels: [
            { name: 'config', label: i18n.t('服务配置') },
            { name: 'plan', label: i18n.t('服务方案') },
          ],
        },
      },
      {
        path: 'user',
        component: platformUserManagement,
        name: 'platformUserManagement',
        meta: {
          title: i18n.t('用户管理'),
          panels: [
            { name: 'admin', label: i18n.t('平台管理员') },
            { name: 'feature', label: i18n.t('用户特性') },
            { name: 'authorized', label: i18n.t('已授权应用') },
          ],
        },
      },
      {
        path: 'repository',
        component: repositoryConfig,
        name: 'repositoryConfig',
        meta: {
          title: i18n.t('代码库配置'),
        },
      },
      {
        path: 'env-var',
        component: builtInEnvVariable,
        name: 'builtInEnvVariable',
        meta: {
          title: i18n.t('内置环境变量'),
        },
      },
      {
        path: 'apps',
        component: platformAppList,
        name: 'platformAppList',
        meta: {
          title: i18n.t('应用列表'),
        },
      },
      {
        path: 'app-detail/:code',
        component: platformAppDetails,
        name: 'platformAppDetails',
        meta: {
          title: i18n.t('应用详情'),
          supportBack: true,
          panels: [
            { name: 'overview', label: i18n.t('概览') },
            { name: 'feature', label: i18n.t('特性管理') },
            { name: 'services', label: i18n.t('增强服务') },
            { name: 'member', label: i18n.t('成员管理') },
          ],
          backRoute: {
            name: 'platformAppList',
          }
        },
      },
      {
        path: 'operation-audit',
        component: platformOperationAudit,
        name: 'platformOperationAudit',
        meta: {
          title: i18n.t('操作审计'),
          panels: [
            { name: 'platform', label: i18n.t('平台操作记录') },
            { name: 'app', label: i18n.t('应用操作记录') },
          ],
        },
      },
    ],
  },
];
