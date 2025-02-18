const platformManagement = () =>
  import(/* webpackChunkName: 'app-migration-info' */ '@/views/platform')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

const platformAppCluster = () =>
  import(/* webpackChunkName: 'app-migration-info' */ '@/views/platform/app-cluster')
    .then((module) => module)
    .catch((error) => {
      window.showDeployTip(error);
    });

export const platformRouters = [
  {
    path: '/developer-center/platform/',
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
          title: '应用集群',
          panels: [
            { name: 'config', label: '集群配置' },
            { name: 'list', label: '集群列表' },
          ],
        },
      },
    ],
  },
];
