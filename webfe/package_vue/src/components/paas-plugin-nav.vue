<template lang="html">
  <ul
    class="app-nav mt-8"
    @click.stop.prevent="handlerClick()"
  >
    <template v-for="(category, categoryIndex) in navTree">
      <li
        v-if="category.children && category.children.length"
        :key="categoryIndex"
        :class="{
          'on': category.isActived && !category.isExpanded
        }"
      >
        <a
          class="overview-text"
          href="javascript:"
          @click.stop.prevent="toggleNavCategory(category)"
        >
          {{ category.label }}
          <i :class="['paasng-icon paasng-angle-right', { 'down': category.isExpanded }]" />
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
              :class="{ 'on': navItem.isSelected }"
              href="javascript: void(0);"
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
          @click.stop.prevent="goPage(category)"
        >
          {{ category.label }}
        </a>
        <span :class="getIconClass(category)" />
      </li>
    </template>
  </ul>
</template>

<script>import { PAAS_STATIC_CONFIG as staticData } from '../../static/json/paas_static.js';

// 需要控制的菜单项
const PLUGIN_NAV_MAP = {
  API_GATEWAY: 'pluginCloudAPI',
  PROCESS_MANAGE: 'pluginProcess',
  STRUCTURE_LOG: 'pluginLog',
  CONFIGURATION_MANAGE: 'pluginDeployEnv',
  VISIBLE_RANGE_MANAGE: 'pluginVisibleRange',
};

export default {
  data() {
    return {
      navTree: [],
      allowedRouterName: [
        'pluginVersionRelease',
        'pluginVersionEditor',
        'pluginReleaseDetails',
        'pluginTestReport',
        'marketInfoEdit',
        'moreInfoEdit',
        'pluginFalsePositiveList',
      ],
      allNavItems: [],
      region: 'ieod',
      roleAllowRouters: {
        administrator: [
          'pluginSummary', // 概览
          'pluginVersionManager', // 版本管理
          'pluginLog', // 日志查询
          'pluginConfigs', // 基本设置
        ],
        developer: [
          'pluginSummary', // 概览
          'pluginVersionManager', // 版本管理
          'pluginLog', // 日志查询
          'pluginConfigs', // 基本设置
        ],
        operator: [],
      },
    };
  },
  computed: {
    curRouteName() {
      return this.$route.name;
    },
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    pluginFeatureFlags() {
      return this.$store.state.plugin.pluginFeatureFlags;
    },
  },
  watch: {
    '$route'(newVal, oldVal) {
      const isReload = (newVal.params.id !== oldVal.params.id) || (newVal.params.moduleId !== oldVal.params.moduleId);
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
      const appNav = JSON.parse(JSON.stringify(staticData.app_nav));

      if (isReload) {
        const hideNavMap = [];
        Object.keys(this.pluginFeatureFlags).forEach((item) => {
          if (!this.pluginFeatureFlags[item] && PLUGIN_NAV_MAP[item]) {
            // 不显示nav项
            hideNavMap.push(PLUGIN_NAV_MAP[item]);
          }
        });
        this.navTree = await this.initNavByRegion(appNav.pluginList);
        // 根据接口返回开关控制是否显示当前菜单项
        if (hideNavMap.length) {
          this.navTree = this.filterMenu(this.navTree, hideNavMap);
        }
        await this.initRouterPermission();
      }

      await this.selectRouterByName(this.curRouteName);
    },

    // 根据接口返回开关控制是否显示当前菜单项
    filterMenu(tree, hideNav) {
      return tree.filter((item) => {
        const nameToCheck = item.destRoute?.name || item.name;
        if (hideNav.includes(nameToCheck)) return false;
        // 如果有 children，递归过滤 children
        if (item.children?.length) {
          item.children = this.filterMenu(item.children, hideNav);
        }
        return true;
      });
    },

    /**
     * 根据接口来展示对应的导航项
     */
    async initNavByRegion(navTree) {
      try {
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
        return navTree;
      } catch (e) {
        console.error(e);
      }
    },

    /**
     * 根据角色，初始访问权限
     */
    initRouterPermission() {
      this.allowedRouterName = [
        'pluginVersionRelease',
        'pluginVersionEditor',
        'pluginReleaseDetails',
        'pluginTestReport',
        'marketInfoEdit',
        'moreInfoEdit',
        'pluginFalsePositiveList',
      ];

      this.navTree.forEach((nav) => {
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
        if (!e) {
          this.$router.push({
            name: 'pluginBaseInfo',
            params: {
              pluginTypeId: this.curPluginInfo.pd_id,
              id: this.curPluginInfo.id,
            },
          });
        } else {
          this.$router.push({
            name: 'pluginSummary',
            params: {
              pluginTypeId: this.curPluginInfo.pd_id,
              id: this.curPluginInfo.id,
            },
          });
          if (e.name) {
            this.$bkNotify({
              theme: 'error',
              message: `【${e.label || e.name}】${this.$t('没有访问权限！')}`,
              offsetY: 80,
            });
          }
        }
      }
    },

    checkPermission(routeName) {
      return new Promise((resolve, reject) => {
        if (this.allowedRouterName.includes(routeName)) {
          resolve(true);
        } else {
          const router = this.allNavItems.find(nav => (nav.matchRouters && nav.matchRouters.includes(routeName)) || nav.destRoute?.name === routeName);
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
      const category = navTree.find(item => item.name === categoryName);
      category.children.push({
        categoryName,
        name,
        matchRouters: [destRouter],
        destRoute: {
          name: destRouter,
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
        await this.checkPermission(navItem.destRoute.name);

        const routeName = navItem.destRoute.name;
        const params = {
          ...navItem.destRoute.params || {},
          ...this.$router.params,
          pluginTypeId: this.curPluginInfo.pd_id,
          id: this.curPluginInfo.id,
        };
        const routeConf = {
          name: routeName,
          params,
        };
        this.$router.push(routeConf);
      } catch (e) {
        this.$router.push({
          name: 'pluginSummary',
          params: {
            pluginTypeId: this.curPluginInfo.pd_id,
            id: this.curPluginInfo.id,
          },
        });
        if (e.name) {
          this.$bkNotify({
            theme: 'error',
            message: `【${e.label || e.name}】没有访问权限！`,
            offsetY: 80,
          });
        }
      }
    },

    enter(el, done) {
      done();
    },

    afterEnter(el) {
      $(el).hide()
        .slideDown(400);
    },

    leave(el, done) {
      $(el).slideUp(400, () => {
        done();
      });
    },

    handlerClick() {
      this.$emit('handlerClick');
    },
  },
};
</script>

<style lang="scss" scoped>
// 插件
.app-nav {
  width: 239px;

  > li {
    width: 100%;
    position: relative;

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
