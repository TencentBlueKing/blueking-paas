<template lang="html">
  <ul class="app-nav">
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

<script>
    import { PAAS_STATIC_CONFIG as staticData } from '../../static/json/paas_static.js';
    import _ from 'lodash';

    export default {
        data () {
            return {
                navTree: [],
                allowedRouterName: [],
                allNavItems: [],
                region: 'ieod',
                roleAllowRouters: {
                    administrator: [
                        'appSummary', // ??????
                        'appEngine', // ????????????
                        'appServices', // ????????????
                        'appPermissions', // ????????????
                        'appMarketing', // ????????????
                        'appConfigs', // ????????????
                        'moduleManage', // ????????????
                        'appAnalysis', // ????????????
                        'monitorAlarm', // ????????????
                        'docuManagement', // ????????????
                        'appCloudAPI' // ??? API ????????????
                    ],

                    developer: [
                        'appSummary', // ??????
                        'appEngine', // ????????????
                        'appServices', // ????????????
                        'appMarketing', // ????????????
                        'appConfigs', // ????????????
                        'moduleManage', // ????????????
                        'appAnalysis', // ????????????
                        'monitorAlarm', // ????????????
                        'docuManagement', // ????????????
                        'appCloudAPI' // ??? API ????????????
                    ],

                    operator: [
                        'appPermissions', // ????????????
                        'appMarketing', // ????????????
                        'appConfigs', // ????????????
                        'appAnalysis', // ????????????
                        'monitorAlarm', // ????????????
                        'docuManagement' // ????????????
                    ]
                }
            };
        },
        computed: {
            curAppInfo () {
                return this.$store.state.curAppInfo;
            },
            curRouteName () {
                return this.$route.name;
            },
            curAppModule () {
                return this.$store.state.curAppModule;
            }
        },
        watch: {
            curAppInfo () {
                this.init();
            },
            'curAppInfo.feature': {
                handler (newValue, oldValue) {
                    if (!Object.keys(newValue).length) {
                        this.curAppInfo.feature = _.cloneDeep(oldValue);
                    }
                    this.init();
                },
                deep: true
            },
            '$route' (newVal, oldVal) {
                const isReload = (newVal.params.id !== oldVal.params.id) || (newVal.params.moduleId !== oldVal.params.moduleId);
                this.init(isReload);
            }
        },
        created () {
            this.init();
        },
        methods: {
            /**
             * ????????????????????????
             */
            async init (isReload = true) {
                if (!this.curAppInfo.application) return;
                const appNav = JSON.parse(JSON.stringify(staticData.app_nav));

                if (isReload) {
                    this.navTree = await this.initNavByRegion(appNav.list);
                    await this.initRouterPermission();
                }

                await this.selectRouterByName(this.curRouteName);
            },

            /**
             * ???????????????????????????????????????
             */
            async initNavByRegion (navTree) {
                try {
                    const region = this.curAppInfo.application.region;
                    const res = await this.$store.dispatch('fetchRegionInfo', region);
                    // this.$store.commit('updateCanCreateModule', res.mul_modules_config.creation_allowed)
                    this.curAppInfo.userType = res.access_control ? res.access_control.user_type : '';

                    // ??????????????????
                    res.services.categories.forEach(category => {
                        navTree = this.addServiceNavItem(navTree, category.id, category.name);
                    });

                    // ??????????????????
                    if (res.access_control && res.access_control.module) {
                        res.access_control.module.forEach(moduleType => {
                            navTree = this.addPermissionNavItem(navTree, moduleType);
                        });
                    }

                    // ??????????????????
                    this.simpleAddNavItem(navTree, 'appEngine', 'appEntryConfig', this.$t('????????????'));

                    // ??????????????????
                    this.simpleAddNavItem(navTree, 'appEngine', 'codeReview', this.$t('????????????'));

                    // ?????????????????????????????????????????????????????????????????????????????????
                    if (!this.curAppInfo.web_config.engine_enabled) {
                        navTree = navTree.filter(nav => {
                            if (nav.name === 'appMarketing') {
                                nav.children = [...nav.children.filter(sub => sub.destRoute.name !== 'appMobileMarket')];
                            }
                            return ['appMarketing', 'appConfigs', 'appAnalysis', 'appCloudAPI'].includes(nav.name);
                        });
                    }

                    // tencent && clouds???????????????????????????
                    if (this.curAppModule.region !== 'ieod') {
                        navTree.forEach(nav => {
                            if (nav.name === 'appMarketing') {
                                nav.children = [...nav.children.filter(sub => sub.destRoute.name !== 'appMobileMarket')];
                            }
                        });
                    }

                    // ???????????????????????????????????????????????????
                    if (this.curAppInfo.role.name === 'developer') {
                        navTree = navTree.filter(nav => this.roleAllowRouters['developer'].includes(nav.name));
                    }

                    // ????????????????????????????????????????????????
                    if (this.curAppInfo.role.name === 'operator') {
                        navTree = navTree.filter(nav => this.roleAllowRouters['operator'].includes(nav.name));
                    }

                    // smart?????????lesscode??????????????????
                    if (this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.LESSCODE_APP && this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.SMART_APP) {
                        navTree.forEach(nav => {
                            if (nav.name === 'appEngine') {
                                nav.children = [...nav.children.filter(sub => sub.destRoute.name !== 'appPackages')];
                            }
                        });
                    }

                    // ???????????????
                    this.allNavItems = [];
                    navTree = navTree.map(nav => {
                        nav.isExpanded = false; // ????????????????????????????????????
                        nav.isActived = false; // ???????????????????????????????????????????????????
                        nav.hasChildSelected = false; // ??????????????????????????????????????????

                        if (nav.children && nav.children.length) {
                            nav.children.forEach(child => {
                                child.isSelected = false;
                            });

                            this.allNavItems = this.allNavItems.concat(nav.children);
                        } else {
                            this.allNavItems.push(nav);
                        }

                        return nav;
                    });

                    // ??????feature flag?????????????????????
                    const featureMaps = {
                        'appAnalysis': 'ANALYTICS', // ????????????
                        'docuManagement': 'DOCUMENT_MANAGEMENT', // ????????????
                        'appCloudAPI': 'API_GATEWAY' // ???API????????????
                    };
                    const subFeatureMaps = {
                        'appWebAnalysis': 'PA_WEBSITE_ANALYTICS', // ??????????????????
                        'appLogAnalysis': 'PA_INGRESS_ANALYTICS', // ??????????????????
                        'appEventAnalysis': 'PA_CUSTOM_EVENT_ANALYTICS', // ?????????????????????
                        'codeReview': 'CI', // ????????????
                        'monitorAlarm': 'PHALANX' // ????????????
                    };
                    // ??????
                    navTree = navTree.filter(nav => {
                        const key = featureMaps[nav.name];
                        if (key && this.curAppInfo.feature.hasOwnProperty(key)) {
                            return this.curAppInfo.feature[key];
                        }
                        return true;
                    });
                    // ??????
                    for (let i = 0; i < navTree.length; i++) {
                        const nav = navTree[i];
                        if (!nav.children.length) {
                            continue;
                        }
                        const children = nav.children.filter(sub => {
                            const key = subFeatureMaps[sub.destRoute.name];
                            // ???????????????key?????????key?????????????????????
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
             * ?????????????????????????????????
             */
            initRouterPermission () {
                const appRole = this.curAppInfo.role;
                const allowRouters = this.roleAllowRouters[appRole.name] || [];

                this.allowedRouterName = [];

                this.navTree.forEach(nav => {
                    if (allowRouters.includes(nav.name)) {
                        if (nav.children && nav.children.length) {
                            nav.children.forEach(child => {
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
             * ????????????routeName????????????
             */
            async selectRouterByName (routeName) {
                try {
                    await this.checkPermission(routeName);
                    this.navTree.forEach(nav => {
                        // ?????????????????????????????????
                        if (nav.children && nav.children.length) {
                            nav.isActived = false;
                            nav.isExpanded = false;

                            nav.children.forEach(child => {
                                // ????????????matchRouters?????????????????????destRoute
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

                                // ??????????????????????????????????????????????????????????????????????????????????????????????????????????????????category_id??????
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
                            // ????????????matchRouters?????????????????????destRoute
                            nav.isExpanded = false;
                            nav.hasChildSelected = false;

                            if (nav.matchRouters && nav.matchRouters.includes(this.curRouteName)) {
                                nav.isActived = true;
                            // nav.destRoute might be `undefined`
                            } else if (nav.destRoute && nav.destRoute.name === this.curRouteName) {
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
                            name: 'appBaseInfo',
                            params: {
                                id: this.curAppInfo.application.code
                            }
                        });
                    } else {
                        this.$router.push({
                            name: 'appSummary',
                            params: {
                                id: this.curAppInfo.application.code,
                                moduleId: 'default'
                            }
                        });
                        if (e.name) {
                            this.$bkNotify({
                                theme: 'error',
                                message: `???${e.label || e.name}???${this.$t('?????????????????????')}`,
                                offsetY: 80
                            });
                        }
                    }
                }
            },

            checkPermission (routeName) {
                return new Promise((resolve, reject) => {
                    if (this.allowedRouterName.includes(routeName)) {
                        resolve(true);
                    } else {
                        const router = this.allNavItems.find(nav => {
                            return (nav.matchRouters && nav.matchRouters.includes(routeName)) || nav.destRoute.name === routeName;
                        });
                        reject(router);
                    }
                });
            },

            /**
             * ???????????????????????????Icon
             * @param {Object} navItem ??????
             * @return {Array} Classes
             */
            getIconClass (navItem) {
                const classes = ['paasng-icon', 'app-nav-icon'];
                classes.push('paasng-' + (navItem.iconfontName || 'gear'));
                return classes;
            },

            simpleAddNavItem (navTree, categoryName, destRouter, name) {
                const category = navTree.find(item => item.name === categoryName);
                category.children.push({
                    'categoryName': categoryName,
                    'name': name,
                    'matchRouters': [destRouter],
                    'destRoute': {
                        'name': destRouter
                    }
                });

                return navTree;
            },

            /**
             * ?????????????????????
             * @param {Number} id id
             * @param {String} name ??????
             */
            addServiceNavItem (navTree, id, name) {
                const category = navTree.find(item => item.name === 'appServices');
                category.children.push({
                    'categoryName': 'appServices',
                    'name': name,
                    'matchRouters': ['appService', 'appServiceInner', 'appServiceConfig', 'appServiceInnerShared'],
                    'destRoute': {
                        'name': 'appService',
                        'params': {
                            'category_id': id.toString()
                        }
                    }
                });

                return navTree;
            },

            /**
             * ????????????????????????
             * @param {String} type ??????
             */
            addPermissionNavItem (navTree, type) {
                const nav = {
                    user_access_control: {
                        'categoryName': 'appPermissions',
                        'name': this.$t('????????????'),
                        'matchRouters': ['appPermissionUser', 'appPermissionPathExempt'],
                        'destRoute': {
                            'name': 'appPermissionUser'
                        }
                    },
                    ip_access_control: {
                        'categoryName': 'appPermissions',
                        'name': this.$t('IP??????'),
                        'matchRouters': ['appPermissionIP'],
                        'destRoute': {
                            'name': 'appPermissionIP'
                        }
                    },
                    approval: {
                        'categoryName': 'appPermissions',
                        'name': this.$t('????????????'),
                        'matchRouters': ['appOrderAudit'],
                        'destRoute': {
                            'name': 'appOrderAudit'
                        }
                    }
                };

                const category = navTree.find(item => item.name === 'appPermissions');
                if (type && nav[type]) {
                    category.children.push(nav[type]);
                }

                return navTree;
            },

            /**
             * ??????????????????
             *
             * @param {Object} category ????????????
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

            /**
             * ??????????????????
             *
             * @param {Object} nav ????????????
             */
            async goPage (navItem) {
                try {
                    await this.checkPermission(navItem.destRoute.name);
                    // if (navItem.isSelected) return

                    const routeName = navItem.destRoute.name;
                    const params = {
                        ...navItem.destRoute.params || {},
                        ...this.$router.params,
                        moduleId: this.curAppModule.name
                    };
                    const routeConf = {
                        name: routeName,
                        params: params
                    };
                    this.$router.push(routeConf);
                } catch (e) {
                    this.$router.push({
                        name: 'appSummary',
                        params: {
                            id: this.curAppInfo.application.code,
                            moduleId: 'default'
                        }
                    });
                    if (e.name) {
                        this.$bkNotify({
                            theme: 'error',
                            message: `???${e.label || e.name}???${this.$t('?????????????????????')}`,
                            offsetY: 80
                        });
                    }
                }
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
    .app-nav {
        padding-top: 9px;
        width: 240px;
        margin-top: 1px;

        > li {
            width: 100%;
            position: relative;

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
                    color: #3A84FF !important;
                    background: #E1ECFF;
                }
                .app-nav-icon {
                    color: #3A84FF !important;
                }
            }

            &:hover {
                .overview-text {
                    color: #3A84FF;
                }
                .app-nav-icon {
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

    .app-nav {
        .paasng-icon {
            font-size: 12px;
            font-weight: bold;
            position: absolute;
            top: 16px;
            right: 14px;
            color: #979BA5;
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
