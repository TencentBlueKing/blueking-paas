<template lang="html">
  <ul :class="['app-nav', { 'mt-8': !isMigrationEntryShown }]">
    <div
      v-if="isMigrationEntryShown"
      class="migration-app-btn"
      @click="handleShowAppMigrationDialog"
    >
      {{ $t('迁移为云原生应用') }}
    </div>
    <template v-for="(category, categoryIndex) in navTree">
      <li
        v-if="category.children && category.children.length"
        :key="categoryIndex"
        :class="{
          on: category.isActived && !category.isExpanded,
          expanded: category.isExpanded,
        }"
      >
        <a
          class="overview-text"
          href="javascript:"
          @click.stop.prevent="toggleNavCategory(category)"
        >
          {{ category.label }}
          <i :class="['paasng-icon paasng-angle-right', { down: category.isExpanded }]" />
        </a>
        <span :class="getIconClass(category)" />
        <transition
          @enter="enter"
          @after-enter="afterEnter"
          @leave="leave"
        >
          <div
            v-if="category.isExpanded"
            class="overview-text-slide"
          >
            <a
              v-for="(navItem, navIndex) in category.children"
              :key="navIndex"
              :class="{ on: navItem.isSelected }"
              href="javascript: void(0);"
              :bk-trace="`{id: '${traceIds[navItem.name]}', action: 'nav', category: '普通应用'}`"
              @click.stop.prevent="goPage(navItem)"
            >
              {{ $t(navItem.name) }}
            </a>
          </div>
        </transition>
      </li>

      <li
        v-else-if="category.destRoute"
        :key="categoryIndex"
        :class="{ 'no-child-actived': category.isActived }"
      >
        <a
          class="overview-text"
          href="javascript:"
          :bk-trace="`{id: '${traceIds[category.label]}', action: 'nav', category: '普通应用'}`"
          @click.stop.prevent="goPage(category)"
        >
          {{ category.label }}
        </a>
        <span :class="getIconClass(category)" />
      </li>
    </template>
  </ul>
</template>

<script>
import { PAAS_STATIC_CONFIG as staticData } from '../../static/json/paas_static.js';
import { traceIds } from '@/common/trace-ids';
import { cloneDeep } from 'lodash';

export default {
  props: {
    isMigrationEntryShown: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      navTree: [],
      allowedRouterName: [],
      allNavItems: [],
      region: 'ieod',
      traceIds,
      roleAllowRouters: {
        administrator: [
          'appSummary', // 概览
          'appEngine', // 应用引擎
          'appServices', // 增强服务
          'appPermissions', // 权限管理
          'appMarketing', // 市场推广
          'appConfigs', // 基本设置
          'moduleManage', // 模块管理
          'appAnalysis', // 数据统计
          'monitorAlarm', // 监控告警
          'appCloudAPI', // 云 API 权限管理
          'operationRecord', // 操作记录
        ],

        developer: [
          'appSummary', // 概览
          'appEngine', // 应用引擎
          'appServices', // 增强服务
          'appMarketing', // 市场推广
          'appConfigs', // 基本设置
          'moduleManage', // 模块管理
          'appAnalysis', // 数据统计
          'monitorAlarm', // 监控告警
          'appCloudAPI', // 云 API 权限管理
          'operationRecord', // 操作记录
        ],

        operator: [
          'appSummary', // 概览
          'appEngineOperator', // 运营者应用引擎
          'appPermissions', // 权限管理
          'appMarketing', // 市场推广
          'appConfigs', // 基本设置
          'appAnalysis', // 数据统计
          'monitorAlarm', // 监控告警
          'operationRecord', // 操作记录
        ],
      },
    };
  },
  computed: {
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    curRouteName() {
      return this.$route.name;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
  },
  watch: {
    'curAppInfo.feature': {
      handler(newValue, oldValue) {
        if (!Object.keys(newValue).length) {
          this.curAppInfo.feature = cloneDeep(oldValue);
        }
      },
      deep: true,
    },
    $route(newVal, oldVal) {
      const isReload = newVal.params.id !== oldVal.params.id || newVal.params.moduleId !== oldVal.params.moduleId;
      this.init(isReload);
    },
  },
  created() {
    this.init();
  },
  methods: {
    /**
     * 侧导航初始化入口
     */
    async init(isReload = true) {
      if (!this.curAppInfo.application) return;
      const appNav = JSON.parse(JSON.stringify(staticData.app_nav));

      if (isReload) {
        this.navTree = await this.initNavByRegion(appNav.list);
        await this.initRouterPermission();
      }

      await this.selectRouterByName(this.curRouteName);
    },

    /**
     * 根据接口来展示对应的导航项
     */
    async initNavByRegion(navTree) {
      try {
        const { region } = this.curAppInfo.application;
        const res = await this.$store.dispatch('fetchRegionInfo', region);
        this.curAppInfo.userType = res.access_control ? res.access_control.user_type : '';

        // 添加增强服务
        res.services.categories.forEach((category) => {
          navTree = this.addServiceNavItem(navTree, category.id, category.name);
        });

        // 添加访问管理
        this.simpleAddNavItem(navTree, 'appEngine', 'appEntryConfig', this.$t('访问管理'));

        // 添加代码检查
        this.simpleAddNavItem(navTree, 'appEngine', 'codeReview', this.$t('代码检查'));

        // 如果不开启引擎，仅仅显示部分功能
        if (!this.curAppInfo.web_config.engine_enabled) {
          navTree = navTree.filter((nav) => {
            if (nav.name === 'appMarketing') {
              nav.children = [...nav.children.filter((sub) => sub.destRoute.name !== 'appMobileMarket')];
            }
            return ['appSummary', 'appConfigs', 'appAnalysis', 'appCloudAPI', 'operationRecord'].includes(nav.name);
          });
        }

        // tencent && clouds去掉应用市场移动端
        if (this.curAppModule?.region !== 'ieod') {
          navTree.forEach((nav) => {
            if (nav.name === 'appMarketing') {
              nav.children = [...nav.children.filter((sub) => sub.destRoute.name !== 'appMobileMarket')];
            }
          });
        }

        // 当角色为开发者时，过滤部分功能入口
        if (this.curAppInfo.role.name === 'developer') {
          navTree = navTree.filter((nav) => this.roleAllowRouters.developer.includes(nav.name));
        }

        // 当角色运营者时，过滤部分功能入口
        if (this.curAppInfo.role.name === 'operator') {
          navTree = navTree.filter((nav) => this.roleAllowRouters.operator.includes(nav.name));
          this.simpleAddNavItem(navTree, 'appEngineOperator', 'appEntryConfig', this.$t('访问管理'));
        }

        // smart应用或lesscode应用，包管理
        if (
          this.curAppModule?.source_origin !== this.GLOBAL.APP_TYPES.LESSCODE_APP &&
          this.curAppModule?.source_origin !== this.GLOBAL.APP_TYPES.SMART_APP
        ) {
          navTree.forEach((nav) => {
            if (nav.name === 'appEngine') {
              nav.children = [...nav.children.filter((sub) => sub.destRoute.name !== 'appPackages')];
            }
          });
        }

        // 初始化属性
        this.allNavItems = [];
        navTree = navTree.map((nav) => {
          nav.isExpanded = false; // 是否展开，有子项时可应用
          nav.isActived = false; // 是否激活，本身匹配或子项匹配时应用
          nav.hasChildSelected = false; // 是否展开，只有子项匹配时应用

          if (nav.children && nav.children.length) {
            nav.children.forEach((child) => {
              child.isSelected = false;
            });

            this.allNavItems = this.allNavItems.concat(nav.children);
          } else {
            this.allNavItems.push(nav);
          }

          return nav;
        });

        // 接入feature flag来控制应用导航
        const featureMaps = {
          appAnalysis: 'ANALYTICS', // 访问统计
        };
        const subFeatureMaps = {
          codeReview: 'CODE_CHECK', // 代码检查
          monitorAlarm: 'MONITORING', // 告警记录
        };
        // 一级
        navTree = navTree.filter((nav) => {
          const key = featureMaps[nav.name];
          if (nav.name === 'appAnalysis') {
            const result = ['PA_WEBSITE_ANALYTICS', 'PA_INGRESS_ANALYTICS', 'PA_CUSTOM_EVENT_ANALYTICS'].some(
              (key) => this.curAppInfo.feature[key]
            );
            // 访问统计三项都为false，不展示一级导航
            if (!result) {
              return false;
            }
          }
          if (key && this.curAppInfo.feature.hasOwnProperty(key)) {
            return this.curAppInfo.feature[key];
          }
          return true;
        });
        // 二级
        for (let i = 0; i < navTree.length; i++) {
          const nav = navTree[i];
          if (!nav.children.length) {
            continue;
          }
          const children = nav.children.filter((sub) => {
            const key = subFeatureMaps[sub.destRoute.name];
            // 如果有相应key，根据key来处理是否启用
            if (key && this.curAppInfo.feature.hasOwnProperty(key)) {
              return this.curAppInfo.feature[key];
            }
            return true;
          });
          if (children.length) {
            nav.children = [...children];
          } else {
            navTree.splice(i, 1);
          }
        }
        return navTree;
      } catch (e) {
        console.error(e);
      }
    },

    /**
     * 根据角色，初始访问权限
     */
    initRouterPermission() {
      const appRole = this.curAppInfo.role;
      const allowRouters = this.roleAllowRouters[appRole.name] || [];

      // 访问统计合并为一级导航，feature flag在页面进行控制
      this.allowedRouterName = [
        'appWebAnalysis', // 网站访问统计
        'appLogAnalysis', // 访问日志统计
        'appEventAnalysis', // 自定义事件统计
        'appMarket', // 应用市场
        'appMobileMarket', // 应用市场(移动端)
        'appBasicInfo', // 基本信息
        'appMembers', // 成员管理
        'appPersistentStorage', // 持久存储
        'docuManagement', // 文档管理
      ];

      this.navTree.forEach((nav) => {
        if (allowRouters.includes(nav.name)) {
          if (nav.children && nav.children.length) {
            nav.children.forEach((child) => {
              if (child.matchRouters) {
                this.allowedRouterName = this.allowedRouterName.concat(child.matchRouters);
              } else {
                this.allowedRouterName.push(child.destRoute.name);
              }
            });
          } else {
            this.allowedRouterName.push(nav.name);
          }
        }
      });
    },

    /**
     * 根据当前routeName选中导航
     */
    async selectRouterByName(routeName) {
      try {
        await this.checkPermission(routeName);
        this.navTree.forEach((nav) => {
          // 如果有子项，先遍历匹配
          if (nav.children && nav.children.length) {
            nav.isActived = false;
            nav.isExpanded = false;

            nav.children.forEach((child) => {
              // 优先使用matchRouters来匹配，其次是destRoute
              if (child.matchRouters && child.matchRouters.includes(routeName)) {
                child.isSelected = true;
                nav.isActived = true;
                nav.isExpanded = true;
              } else if (child.destRoute.name === routeName) {
                child.isSelected = true;
                nav.isActived = true;
                nav.isExpanded = true;
              } else {
                child.isSelected = false;
              }

              // 若命中，有配置参数，也需要再匹配一次，像增强服务里的数据存储和健康检查是通过category_id区分
              if (child.isSelected && child.destRoute.params) {
                const childParams = child.destRoute.params;
                const routeParams = this.$route.params;
                for (const key in childParams) {
                  if (childParams[key] !== String(routeParams[key])) {
                    child.isSelected = false;
                  }
                }
              }
            });
          } else {
            // 优先使用matchRouters来匹配，其次是destRoute
            nav.isExpanded = false;
            nav.hasChildSelected = false;

            if (nav.matchRouters && nav.matchRouters.includes(this.curRouteName)) {
              nav.isActived = true;
              // nav.destRoute might be `undefined`
            } else if (nav.destRoute && nav.destRoute?.name === this.curRouteName) {
              nav.isActived = true;
            } else {
              nav.isActived = false;
            }
          }
        });
      } catch (e) {
        console.warn('error', e);
        if (e && e.name === 'appSummary') {
          this.$router.push({
            name: 'appSummary',
            params: {
              id: this.curAppInfo.application.code,
              moduleId: 'default',
            },
          });
        } else {
          this.$router.push({
            name: 'appSummary',
            params: {
              id: this.curAppInfo.application.code,
            },
          });
        }
        if (e && (e.label || e.name)) {
          this.$bkNotify({
            theme: 'error',
            message: `【${e.label || e.name}】${this.$t('没有访问权限！')}`,
            offsetY: 80,
          });
        }
      }
    },

    checkPermission(routeName) {
      return new Promise((resolve, reject) => {
        if (this.allowedRouterName.includes(routeName)) {
          resolve(true);
        } else {
          const router = this.allNavItems.find(
            (nav) => (nav.matchRouters && nav.matchRouters.includes(routeName)) || nav.destRoute?.name === routeName
          );
          reject(router);
        }
      });
    },

    /**
     * 返回导航目录对应的Icon
     * @param {Object} navItem 导航
     * @return {Array} Classes
     */
    getIconClass(navItem) {
      const classes = ['paasng-icon', 'app-nav-icon'];
      classes.push(`paasng-${navItem.iconfontName || 'gear'}`);
      return classes;
    },

    simpleAddNavItem(navTree, categoryName, destRouter, name) {
      const category = navTree.find((item) => item.name === categoryName);
      if (category) {
        category.children.push({
          categoryName,
          name,
          matchRouters: [destRouter],
          destRoute: {
            name: destRouter,
          },
        });
      }

      return navTree;
    },

    /**
     * 强服务添加子项
     * @param {Number} id id
     * @param {String} name 名称
     */
    addServiceNavItem(navTree, id, name) {
      const category = navTree.find((item) => item.name === 'appServices');
      category.children.push({
        categoryName: 'appServices',
        name: this.$t(name),
        matchRouters: ['appService', 'appServiceInner', 'appServiceConfig', 'appServiceInnerShared'],
        destRoute: {
          name: 'appService',
          params: {
            category_id: id.toString(),
          },
        },
      });

      return navTree;
    },

    /**
     * 切换展开状态
     *
     * @param {Object} category 父导航项
     */
    toggleNavCategory(category) {
      this.navTree.forEach((item) => {
        if (category.name === item.name) {
          category.isExpanded = !category.isExpanded;
        } else {
          item.isExpanded = false;
        }
      });
    },

    /**
     * 访问相应路由
     *
     * @param {Object} nav 导航对象
     */
    async goPage(navItem) {
      try {
        await this.checkPermission(navItem.destRoute?.name);
        // if (navItem.isSelected) return

        const routeName = navItem.destRoute.name;
        const params = {
          ...(navItem.destRoute.params || {}),
          ...this.$router.params,
          moduleId: this.curAppModule?.name,
        };
        const routeConf = {
          name: routeName,
          params,
        };
        this.$router.push(routeConf);
      } catch (e) {
        if (e && e.name === 'appSummary') {
          this.$router.push({
            name: 'appSummary',
            params: {
              id: this.curAppInfo.application.code,
              moduleId: 'default',
            },
          });
        } else {
          this.$router.push({
            name: 'appBaseInfo',
            params: {
              id: this.curAppInfo.application.code,
            },
          });
        }
        if (e && (e.label || e.name)) {
          this.$bkNotify({
            theme: 'error',
            message: `【${e.label || e.name}】${this.$t('没有访问权限！')}`,
            offsetY: 80,
          });
        }
      }
    },

    enter(el, done) {
      done();
    },

    afterEnter(el) {
      $(el).hide().slideDown(400);
    },

    leave(el, done) {
      $(el).slideUp(400, () => {
        done();
      });
    },

    // 迁移应用弹窗
    handleShowAppMigrationDialog() {
      this.$emit('show-migration-dialog', {
        visible: true,
        data: this.curAppInfo.application,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.app-nav {
  width: 240px;

  .migration-app-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 8px 16px;
    height: 32px;
    background: #f0f5ff;
    border-radius: 2px;
    font-size: 12px;
    color: #3a84ff;
    cursor: pointer;
    &:hover {
      background: #e1ecff;
    }
  }

  > li {
    width: 239px;
    position: relative;
    &.expanded {
      background: #f5f7fa;
    }

    &.on {
      .overview-text {
        color: #313238 !important;
      }
      .app-nav-icon {
        color: #313238 !important;
      }
    }

    &.no-child-actived,
    &.has-child-selected {
      .overview-text {
        color: #3a84ff !important;
        background: #e1ecff;
      }
      .app-nav-icon {
        color: #3a84ff !important;
      }
    }

    &:hover {
      .overview-text {
        color: #63656e;
      }
      .app-nav-icon {
        color: #63656e;
      }
      background: #f5f7fa;
    }
  }
}

.overview-text {
  color: #63656e;
  padding-left: 50px;
  z-index: 1;
  line-height: 42px;
  font-size: 14px;
  display: block;

  &:hover {
    color: #63656e;
  }
}

.overview-text-slide {
  width: 100%;
  position: relative;
  overflow: hidden;
  background: rgb(245, 247, 250);
  > a {
    width: 240px;
    display: block;
    line-height: 42px;
    height: 42px;
    display: block;
    color: #63656e;
    padding-left: 50px;
    cursor: pointer;
    position: relative;

    &:hover,
    &.on {
      color: #3a84ff;
      background: #e1ecff;

      &:after {
        background-color: #3a84ff;
      }
    }

    &:after {
      content: '';
      width: 4px;
      height: 4px;
      position: absolute;
      left: 28px;
      top: 50%;
      margin-top: -2px;
      background-color: #dcdee5;
      border-radius: 50%;
    }
  }
}

.app-nav {
  .paasng-icon {
    font-size: 12px;
    font-weight: bold;
    position: absolute;
    top: 16px;
    right: 14px;
    color: #979ba5;
    display: inline-block;
    transition: all ease 0.3s;

    &.app-nav-icon {
      position: absolute;
      font-weight: normal;
      top: 12px;
      left: 20px;
      right: auto;
      z-index: 2;
      color: #666;
      font-size: 18px;
    }

    &.down {
      transform: rotate(90deg);
    }
  }

  li.active i.paasng-icon {
    color: #313238;
  }
}
</style>
