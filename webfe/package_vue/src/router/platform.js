import i18n from '@/language/i18n.js';

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
    ],
  },
];
