<template lang="html">
  <ul class="overview-list">
    <template v-for="(category, categoryIndex) in navTree">
      <!-- 有子级导航 -->
      <li
        v-if="category.children && category.children.length"
        :key="categoryIndex"
        :class="{ 'has-child-actived': category.isActived, 'has-child-selected': !category.isExpanded && category.hasChildSelected }"
      >
        <a
          class="overview-text"
          href="javascript:"
          @click="toggleNavCategory(category)"
        >
          {{ category.label }}
          <i :class="['paasng-icon paasng-angle-right', { 'down': category.isExpanded }]" />
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
              :class="{ 'on': navItem.isSelected }"
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
        :key="categoryIndex"
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
  </ul>
</template>

<script>
    export default {
        props: {
            'navCategories': {
                type: Array,
                default () {
                    return [];
                }
            },
            'navItems': {
                type: Array,
                default () {
                    return [];
                }
            }
        },
        data () {
            return {
                navTree: [],
                lastActivedCategory: null,
                lastActivedItem: null
            };
        },
        watch: {
            navItems () {
                const categories = JSON.parse(JSON.stringify(this.navCategories));
                const navItems = JSON.parse(JSON.stringify(this.navItems));

                categories.forEach(category => {
                    category.children = [];
                    category.isActived = false;
                    category.isExpanded = false;
                    category.hasChildSelected = false;

                    navItems.forEach(nav => {
                        nav.isSelected = false;
                        if (nav.categoryName && nav.categoryName === category.name) {
                            if (nav.name !== '持续集成') {
                                category.children.push(nav);
                            }
                        }
                    });
                });

                this.navTree = categories;
                this.matchNav();
            },
            '$route' () {
                this.matchNav();
            }
        },
        mounted () {
            this.matchNav();
        },
        methods: {
            /**
             * 访问相应路由
             *
             * @param {Object} nav 导航对象
             */
            goPage (nav) {
                const params = this.getNavRoute(nav);
                this.$router.push(params);
            },

            /**
             * 根据路由匹配相应的导航项
             */
            matchNav () {
                const routeName = this.$route.name;
                const routeParams = this.$route.params;

                for (const category of this.navTree) {
                    category.isActived = false;
                    category.isExpanded = false;
                    category.hasChildSelected = false;

                    // 如果有子导航
                    if (category.children && category.children.length) {
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
                    } else {
                        // 没有子导航，但匹配则激活
                        if (category.matchRouters && category.matchRouters.includes(routeName)) {
                            category.isActived = true;
                        }
                    }
                }
            },

            /**
             * 切换展开状态
             *
             * @param {Object} category 父导航项
             */
            toggleNavCategory (category) {
                this.navTree.forEach(item => {
                    if (category.name === item.name) {
                        category.isExpanded = !category.isExpanded;
                    } else {
                        item.isExpanded = false;
                    }
                });
            },
            getNavRoute (navItem) {
                const params = {
                    ...navItem.destRoute.params || {},
                    ...this.$router.params
                };
                return {
                    name: navItem.destRoute.name,
                    params: params
                };
            },
            getIconClass (navItem) {
                const classes = ['paasng-icon', 'overview-list-icon'];
                classes.push('paasng-' + (navItem.iconfontName || 'gear'));
                return classes;
            },
            enter (el, done) {
                done();
            },
            afterEnter (el) {
                $(el).hide().slideDown(400);
            },
            leave (el, done) {
                $(el).slideUp(400, () => {
                    done();
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    .overview-list {
        padding-top: 9px;

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
                    color: #3A84FF !important;
                    background: #E1ECFF;
                }
                .overview-list-icon {
                    color: #3A84FF !important;
                }
            }

            &:hover {
                .overview-text {
                    color: #3A84FF;
                }
                .overview-list-icon {
                    color: #3A84FF;
                }
            }
        }
    }

    .overview-text {
        color: #63656E;
        padding-left: 50px;
        z-index: 1;
        line-height: 42px;
        font-size: 14px;
        display: block;

        &:hover {
            color: #63656E;
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
            color: #63656E;
            padding-left: 50px;
            cursor: pointer;
            position: relative;

            &:hover,
            &.on {
                color: #3A84FF;
                background: #E1ECFF;

                &:after {
                    background-color: #3A84FF;
                }
            }

            &:after {
                content: "";
                width: 4px;
                height: 4px;
                position: absolute;
                left: 28px;
                top: 50%;
                margin-top: -2px;
                background-color: #DCDEE5;
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
            color: #979BA5;
            display: inline-block;
            transition: all ease 0.3s;

            &.overview-list-icon {
                position: absolute;
                top: 12px;
                left: 20px;
                right: auto;
                z-index: 2;
                font-size: 18px;
                color: #666;
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
