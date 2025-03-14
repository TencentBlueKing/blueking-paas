<template lang="html">
  <ul class="overview-list">
    <template v-for="navItem in displayNavTree">
      <li class="group-title">{{ navItem.name }}</li>
      <!-- 显示分组 -->
      <template v-for="(category, categoryIndex) in navItem.children">
        <!-- 有子级导航 -->
        <li
          v-if="category.children && category.children.length"
          :key="categoryIndex"
          class="nav-item"
          :class="{
            'has-child-actived': category.isActived,
            'has-child-selected': !category.isExpanded && category.hasChildSelected,
          }"
        >
          <a
            class="overview-text"
            href="javascript:"
            @click="toggleNavCategory(category)"
          >
            {{ category.label }}
            <i :class="['paasng-icon paasng-angle-right', { down: category.isExpanded }]" />
            <!-- <i class="paasng-icon paasng-angle-right" v-else></i> -->
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
                @click="goPage(navItem)"
              >
                {{ navItem.name }}
              </a>
            </div>
          </transition>
        </li>

        <li
          v-else-if="category.destRoute"
          :key="category.name"
          class="nav-item"
          :class="{ 'no-child-actived': category.isActived }"
        >
          <a
            class="overview-text"
            href="javascript:"
            @click="goPage(category)"
          >
            {{ category.label }}
          </a>
          <span :class="getIconClass(category)" />
        </li>
      </template>
    </template>
  </ul>
</template>

<script>
import { cloneDeep } from 'lodash';
export default {
  props: {
    navCategories: {
      type: Array,
      default() {
        return [];
      },
    },
    navItems: {
      type: Array,
      default() {
        return [];
      },
    },
    groups: {
      type: Array,
      default() {
        return [];
      },
    },
  },
  data() {
    return {
      navTree: [],
      lastActivedCategory: null,
      lastActivedItem: null,
    };
  },
  computed: {
    // 创建分组结构
    displayNavTree() {
      // 转换 receivedGroups 格式为所需的格式
      const groups = this.groups.map((group) => {
        const key = Object.keys(group)[0];
        return {
          name: group[key],
          groupId: key,
          children: [],
        };
      });
      // 遍历 navTree 进行分组
      this.navTree.forEach((item) => {
        const group = groups.find((g) => g.groupId === item.groupId);
        if (group) {
          group.children.push(item);
        }
      });
      // 返回过滤后的分组
      return groups.filter((item) => item.children.length > 0);
    },
  },
  watch: {
    navItems() {
      const categories = cloneDeep(this.navCategories);
      const navItems = cloneDeep(this.navItems);

      categories.forEach((category) => {
        category.children = [];
        category.isActived = false;
        category.isExpanded = false;
        category.hasChildSelected = false;

        navItems.forEach((nav) => {
          nav.isSelected = false;
          if (nav.categoryName && nav.categoryName === category.name) {
            category.children.push(nav);
          }
        });
      });

      this.navTree = categories;
      this.matchNav();
    },
    $route() {
      this.matchNav();
    },
  },
  mounted() {
    this.matchNav();
  },
  methods: {
    /**
     * 访问相应路由
     *
     * @param {Object} nav 导航对象
     */
    goPage(nav) {
      const params = this.getNavRoute(nav);
      this.$router.push(params);
    },

    /**
     * 根据路由匹配相应的导航项
     */
    matchNav() {
      const routeName = this.$route.name;
      const routeParams = this.$route.params;

      for (const category of this.navTree) {
        category.isActived = false;
        category.isExpanded = false;
        category.hasChildSelected = false;

        if (!category.children?.length) {
          // 没有子导航，但匹配则激活
          if (category.matchRouters && category.matchRouters.includes(routeName)) {
            category.isActived = true;
          }
          continue;
        }
        // 如果有子导航
        for (const nav of category.children) {
          // 如果子导航有其中一个是选中，则父激活并展开
          if (nav.matchRouters.includes(routeName)) {
            category.isActived = true;
            category.isExpanded = true;
            category.hasChildSelected = true;

            // 如果有匹配参数
            if (nav.matchRouterParams && routeParams) {
              // 对参数和路由传入的参数对比，如果都相同则匹配上
              const keys = Object.keys(nav.matchRouterParams);
              nav.isSelected = true;
              for (const key of keys) {
                if (nav.matchRouterParams[key] !== String(routeParams[key])) {
                  nav.isSelected = false;
                }
              }
            } else {
              nav.isSelected = true;
            }
          } else {
            nav.isSelected = false;
          }
        }
      }
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
    getNavRoute(navItem) {
      const params = {
        ...(navItem.destRoute.params || {}),
        ...this.$router.params,
      };
      return {
        name: navItem.destRoute.name,
        params: params,
      };
    },
    getIconClass(navItem) {
      const classes = ['paasng-icon', 'overview-list-icon'];
      classes.push('paasng-' + (navItem.iconfontName || 'gear'));
      return classes;
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
  },
};
</script>

<style lang="scss" scoped>
.overview-list {
  padding-top: 8px;

  .group-title {
    margin-bottom: 4px;
    padding-left: 20px;
    font-size: 12px;
    color: #979ba5;
    z-index: 1;
    line-height: 40px;
    font-size: 14px;
  }

  .nav-item {
    margin-bottom: 4px;
    :last-child {
      margin-bottom: 0;
    }
  }

  > li {
    width: 100%;
    position: relative;

    &.has-child-actived {
      .overview-text {
        color: #313238 !important;
      }
      .overview-list-icon {
        color: #313238 !important;
      }
    }

    &.no-child-actived,
    &.has-child-selected {
      .overview-text {
        color: #3a84ff !important;
        background: #e1ecff;
      }
      .overview-list-icon {
        color: #3a84ff !important;
      }
    }

    &:hover {
      .overview-text {
        color: #3a84ff;
      }
      .overview-list-icon {
        color: #3a84ff;
      }
    }
  }
}

.overview-text {
  color: #4d4f56;
  padding-left: 50px;
  z-index: 1;
  line-height: 40px;
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
    line-height: 40px;
    height: 40px;
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
      background-color: #c4c6cc;
      border-radius: 50%;
    }
  }
}

.overview-list {
  .paasng-icon {
    font-size: 12px;
    font-weight: bold;
    position: absolute;
    top: 16px;
    right: 14px;
    color: #979ba5;
    display: inline-block;
    transition: all ease 0.3s;

    &.overview-list-icon {
      position: absolute;
      top: 12px;
      left: 20px;
      right: auto;
      z-index: 2;
      font-size: 18px;
      color: #4d4f56;
      font-weight: normal;
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
