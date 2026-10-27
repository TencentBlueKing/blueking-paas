import {
  createRouter,
  createWebHistory,
} from 'vue-router';

import {
  rootPath,
  connectToMain
} from '@blueking/sub-saas'

const Home = () => import(/* webpackChunkName: "Home" */ '../views/home/index.vue');
const Projects = () => import(/* webpackChunkName: "Projects" */ '../views/projects/index.vue');
const Project = () => import(/* webpackChunkName: "Project" */ '../views/project/index.vue');

// 由于接入了子路由，path 需要使用相对路径
const appRouter = createRouter({
  history: createWebHistory(window.SITE_URL),
  routes: [
    {
      path: rootPath,
      children: [
        {
          path: '',
          name: 'home',
          component: Home,
        },
        {
          path: 'projects/:projectId',
          name: 'project',
          component: Project,
        },
        {
          path: 'projects',
          name: 'projects',
          component: Projects,
        },
      ]
    },
  ],
});

connectToMain(appRouter)

export default appRouter
