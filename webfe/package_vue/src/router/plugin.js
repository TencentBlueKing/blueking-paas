import i18n from '@/language/i18n.js';

const pluginCenterPage = () => import(/* webpackChunkName: 'plugin-center-index' */'@/views/plugin-center/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createPlugin = () => import(/* webpackChunkName: 'create-plugin' */'@/views/plugin-center/create-plugin/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const createPluginSuccess = () => import(/* webpackChunkName: 'create-plugin' */'@/views/plugin-center/create-plugin/success.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginIndex = () => import(/* webpackChunkName: 'plugin-index' */'@/views/plugin-center/plugin/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

// Plugin: summary
const pluginSummary = () => import(/* webpackChunkName: 'plugin-sumary' */'@/views/plugin-center/plugin/summary/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginFalsePositiveList = () => import(/* webpackChunkName: 'plugin-sumary' */'@/views/plugin-center/plugin/summary/false-positive-list.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginVersionManager = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/version-manager/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginVersionRelease = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/version-manager/version-release').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginVersionEditor = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/version-manager/create-version').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginReleaseDetails = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/version-manager/version-details').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginLog = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/log/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginBaseInfo = () => import(/* webpackChunkName: 'plugin-config' */'@/views/plugin-center/plugin/base-config/base-info.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginVisibleRange = () => import(/* webpackChunkName: 'plugin-config' */'@/views/plugin-center/plugin/base-config/visible-range.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginRoles = () => import(/* webpackChunkName: 'plugin-config' */'@/views/plugin-center/plugin/base-config/members.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginDeployEnv = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/deploy-env/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginTestReport = () => import(/* webpackChunkName: 'plugin-version' */'@/views/plugin-center/plugin/version-manager/test-report').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const marketInfoEdit = () => import(/* webpackChunkName: 'plugin-config' */'@/views/plugin-center/plugin/base-config/market-info-edit.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const moreInfoEdit = () => import(/* webpackChunkName: 'plugin-config' */'@/views/plugin-center/plugin/base-config/more-info-edit.vue').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginCloudAPI = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/dev-center/app/basic-config/cloud-api').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const pluginProcess = () => import(/* webpackChunkName: 'app-basic-config' */'@/views/plugin-center/plugin/process/index').then(module => module).catch((error) => {
  window.showDeployTip(error);
});

const plugin403 = () => import(/* webpackChunkName: 'permission403' */'@/views/error-pages/403').then(module => module).catch((error) => {
  window.showDeployTip(error);
});
export const pluginRouter = [
  {
    path: '/plugin-center/',
    name: 'plugin',
    component: pluginCenterPage,
  },
  {
    path: '/plugin-center/create',
    name: 'createPlugin',
    component: createPlugin,
    meta: {
      pathName: i18n.t('创建插件'),
      supportBack: true,
    },
  },
  {
    path: '/plugin-center/:pluginTypeId/:id/create-success',
    name: 'createPluginSuccess',
    component: createPluginSuccess,
    meta: {
      pathName: i18n.t('创建插件'),
      supportBack: true,
    },
  },
  {
    path: '/plugin-center/plugin/:pluginTypeId/:id/403',
    name: 'plugin403',
    component: plugin403,
    meta: {
      plugin: true,
    },
  },
  {
    path: '/plugin-center/plugin/',
    name: '插件概览',
    component: pluginIndex,
    meta: {
      capture403Error: false,
    },
    children: [
      {
        path: ':id',
        redirect: {
          name: 'pluginSummary',
        },
      },
      {
        path: ':pluginTypeId/:id/summary',
        component: pluginSummary,
        name: 'pluginSummary',
        meta: {
          pathName: i18n.t('概览'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/false-positive-list',
        component: pluginFalsePositiveList,
        name: 'pluginFalsePositiveList',
        meta: {
          pathName: i18n.t('误报列表'),
          capture403Error: false,
          supportBack: true,
        },
      },
      {
        path: ':pluginTypeId/:id/version-manage',
        component: pluginVersionManager,
        name: 'pluginVersionManager',
        meta: {
          pathName: i18n.t('版本管理'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/test-report',
        component: pluginTestReport,
        name: 'pluginTestReport',
        meta: {
          pathName: i18n.t('测试报告'),
          capture403Error: false,
          supportBack: true,
        },
      },
      {
        path: ':pluginTypeId/:id/deploy-env',
        component: pluginDeployEnv,
        name: 'pluginDeployEnv',
        meta: {
          pathName: i18n.t('配置管理'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/version-release',
        component: pluginVersionRelease,
        name: 'pluginVersionRelease',
        meta: {
          pathName: i18n.t('发布'),
          supportBack: true,
        },
      },
      {
        path: ':pluginTypeId/:id/version-edit',
        component: pluginVersionEditor,
        name: 'pluginVersionEditor',
        meta: {
          pathName: i18n.t('新建版本'),
          capture403Error: false,
          supportBack: true,
        },
      },
      {
        path: ':pluginTypeId/:id/version-details',
        component: pluginReleaseDetails,
        name: 'pluginReleaseDetails',
        meta: {
          pathName: i18n.t('版本发布'),
          capture403Error: false,
          supportBack: true,
        },
      },
      {
        path: ':pluginTypeId/:id/log',
        component: pluginLog,
        name: 'pluginLog',
        meta: {
          pathName: i18n.t('日志查询'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/process',
        component: pluginProcess,
        name: 'pluginProcess',
        meta: {
          pathName: i18n.t('进程管理'),
          capture403Error: false,
          isGetAppInfo: true,
        },
      },
      {
        path: ':pluginTypeId/:id/cloudapi',
        component: pluginCloudAPI,
        name: 'pluginCloudAPI',
        meta: {
          pathName: i18n.t('云 API 权限'),
          capture403Error: false,
          isGetAppInfo: true,
        },
      },
      {
        path: ':pluginTypeId/:id/base-info',
        component: pluginBaseInfo,
        name: 'pluginBaseInfo',
        meta: {
          pathName: i18n.t('基本信息'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/market-info-edit',
        component: marketInfoEdit,
        name: 'marketInfoEdit',
        meta: {
          pathName: i18n.t('编辑市场信息'),
          supportBack: true,
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/more-info-edit',
        component: moreInfoEdit,
        name: 'moreInfoEdit',
        meta: {
          pathName: i18n.t('编辑更多信息'),
          supportBack: true,
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/visible-range',
        component: pluginVisibleRange,
        name: 'pluginVisibleRange',
        meta: {
          pathName: i18n.t('可见范围'),
          capture403Error: false,
        },
      },
      {
        path: ':pluginTypeId/:id/roles',
        component: pluginRoles,
        name: 'pluginRoles',
        meta: {
          pathName: i18n.t('成员管理'),
          capture403Error: false,
          isPlugin: true,
        },
      },
    ],
  },
];
