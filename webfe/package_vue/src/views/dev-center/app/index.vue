<template lang="html">
  <div class="overview-content">
    <template v-if="isAppFound">
      <div class="wrap">
        <div class="overview">
          <div
            class="overview-main"
            :style="{ 'min-height': `${minHeight}px` }"
          >
            <div class="overview-fleft">
              <app-quick-nav />
              <paas-cloud-app-nav v-if="type === 'cloud_native'" />
              <paas-app-nav v-else />
            </div>
            <div class="overview-fright">
              <router-view
                v-if="userVisitEnable && appVisitEnable"
                :app-info="appInfo"
                @current-app-info-updated="updateAppInfo"
              />

              <div
                v-else
                class="paas-loading-content"
              >
                <div class="no-permission">
                  <img src="/static/images/permissions.png">
                  <h2 v-if="errorMessage">
                    {{ errorMessage }}
                  </h2>
                  <h2
                    v-else-if="deniedMessageType === 'default'"
                    class="exception-text"
                  >
                    <template v-if="appPermissionMessage">
                      {{ appPermissionMessage }}，
                      {{ $t('如需开启请联系') }}
                      <a
                        v-if="GLOBAL.HELPER.href"
                        :href="GLOBAL.HELPER.href"
                      >{{ GLOBAL.HELPER.name }}</a>
                      <span v-else> {{ $t('管理员') }} </span>
                    </template>
                    <template v-else>
                      {{ $t('您没有访问当前应用该功能的权限，如需申请，请联系') }}
                      <router-link
                        class="toRolePage"
                        :to="{ name: 'appRoles', params: { id: appCode } }"
                      >
                        {{ $t('成员管理') }}
                      </router-link>
                      {{ $t('页面的应用管理员') }}
                    </template>
                  </h2>
                  <h2 v-else-if="deniedMessageType === 'noMarketingForBackendApp'">
                    {{ $t('当前应用为后台应用，无法上线到应用市场') }}
                  </h2>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <template v-else>
      <div
        class="nofound"
        style="width: 1180px; margin: 0px auto;"
      >
        <img src="/static/images/404.png">
        <p> {{ $t('应用找不到了！') }} </p>
      </div>
    </template>
  </div>
</template>

<script>
import paasAppNav from '@/components/paas-app-nav';
import paasCloudAppNav from '@/components/paas-cloud-app-nav';
import appQuickNav from '@/components/app-quick-nav';
import { bus } from '@/common/bus';
import appBaseMixin from '@/mixins/app-base-mixin.js';
import store from '@/store';

export default {
  components: {
    paasCloudAppNav,
    paasAppNav,
    appQuickNav,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      minHeight: 700,
      isAppFound: true,
      appInfo: {
        userType: '',
        repo: {
          linked_to_internal_svn: true,
        },
      },
      navCategories: [],
      allNavItems: [],
      navItems: [],
      allowNavItems: [],
      appVisitEnable: true,
      userVisitEnable: true,
      errorMessage: '',
      appPermissionMessage: '',
      deniedMessageType: 'default',
      showMarketMenus: true,

      // 非应用引擎 应用 时所要显示的父级导航
      parentNavIds: [8, 10],
      // 非应用引擎 应用 时所要显示的子级导航
      subNavIds: [10, 12, 13, 14],
      engineEnabled: false,
      type: 'default',
    };
  },
  computed: {
    appRole() {
      return this.appInfo.role;
    },
    routeName() {
      return this.$route.name;
    },
    // 是否显示通知中心
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
  },
  watch: {
    $route: {
      immediate: true,
      handler() {
        this.userVisitEnable = true;
        this.errorMessage = '';
        this.checkPermission();
      },
    },
    'curAppInfo.feature'(conf) {
      this.checkPermission();
    },
    appCode() {
      this.initNavInfo();
    },
    '$store.state.navType': {
      async handler(newValue) {
        const { code: appCode, moduleId } = newValue;
        const curAppInfo = await store.dispatch('getAppInfo', { appCode, moduleId });
        this.type = curAppInfo.application.type;
      },
    },
  },
  /**
         * 进入当前组件时请求应用信息
         */
  async beforeRouteEnter(to, from, next) {
    const appCode = to.params.id;
    const { moduleId } = to.params;
    let curAppInfo;
    try {
      if (!store.state.appInfo[appCode]) {
        curAppInfo = await store.dispatch('getAppInfo', { appCode, moduleId });
        await store.dispatch('getAppFeature', { appCode });
        console.log('beforeRouteEnter: getAppInfo');
      } else {
        curAppInfo = store.state.appInfo[appCode];
        store.commit('updateCurAppByCode', { appCode, moduleId });
      }
      next((vm) => {
        vm.type = curAppInfo.application.type;
      });
      // 如果不带moduleId, 以默认模块作一次重定向
      if (!moduleId) {
        to.params.moduleId = curAppInfo.application.modules.find(module => module.is_default).name;
        next({
          name: to.name,
          params: to.params,
          query: to.query,
        });
      } else {
        next(true);
      }
    } catch (e) {
      next({
        name: 'permission403',
        params: {
          id: appCode,
          url: store.state.applyUrl,
        },
      });
    }
  },
  /**
         * 当前组件路由切换时请求应用信息
         */
  async beforeRouteUpdate(to, from, next) {
    const appCode = to.params.id;
    const { moduleId } = to.params;
    let curAppInfo;

    try {
      if (!store.state.appInfo[appCode]) {
        curAppInfo = await store.dispatch('getAppInfo', { appCode, moduleId });
        await store.dispatch('getAppFeature', { appCode });
        console.log('beforeRouteEnter: getAppInfo');
        // 切换 navType
        this.type = curAppInfo.application.type;
      } else {
        curAppInfo = store.state.appInfo[appCode];
        store.commit('updateCurAppByCode', { appCode, moduleId });
      }

      // 如果不带moduleId, 以默认模块作一次重定向
      if (!moduleId) {
        to.params.moduleId = curAppInfo.application.modules.find(module => module.is_default).name;
        next({
          name: to.name,
          params: to.params,
          query: to.query,
        });
      } else {
        next(true);
      }
    } catch (e) {
      next({
        name: 'permission403',
        params: {
          id: appCode,
          url: store.state.applyUrl,
        },
      });
    }
  },
  async created() {
    bus.$on('api-error:user-permission-denied', () => {
      // 判定当前页面是应用内页
      // 当前应用无权限成员也可以访问应用首页 (屏蔽403时过滤应用首页)
      const RouterMatchedList = this.$route.matched;
      let capture = true;

      // undefined 为默认父级路由过滤设置
      if ((typeof RouterMatchedList[1].meta.capture403Error) !== 'undefined') {
        capture = RouterMatchedList[1].meta.capture403Error;
      }
      if (capture) {
        this.userVisitEnable = false;
      }
    });

    bus.$on('api-error:platform-fun-denied', (error) => {
      this.userVisitEnable = false;
      this.errorMessage = error.detail || this.$t('平台功能异常: 请联系平台负责人检查服务配置');
    });

    // 监听切换应用时，刷新左侧导航(applogo\appname\appcode)事件
    bus.$on('update-left-nav:base-info', (appCode) => {
      this.appCode = appCode;
      this.updateBaseInfo();
    });
    this.initNavInfo();
  },
  mounted() {
    // 通知中心高度
    const NOTICE_HEIGHT = this.isShowNotice ? this.GLOBAL.NOTICE_HEIGHT : 0;
    const HEADER_HEIGHT = 50;
    const FOOTER_HEIGHT = 0;
    const winHeight = window.innerHeight;
    const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT - NOTICE_HEIGHT;
    if (contentHeight > this.minHeight) {
      this.minHeight = contentHeight;
    }
    document.body.className = 'ps-app-detail';
  },
  beforeDestroy() {
    document.body.className = '';
  },
  methods: {
    initNavInfo() {
      this.retrieveAppInfo();
    },
    // Retrieve app informations
    retrieveAppInfo() {
      const { curAppInfo } = this;

      this.appInfo = {
        ...curAppInfo.application,
        logo: '',
        role: curAppInfo.role ? curAppInfo.role.name : 'nobody',
        userType: '',
        web_config: curAppInfo.web_config,
      };

      this.isAppFound = true;
      // this.showMarketMenus = curAppInfo.web_config.can_publish_to_market
      this.engineEnabled = curAppInfo.application.config_info.engine_enabled;

      // Use a default logo if error happens
      if (curAppInfo.application && curAppInfo.application.logo_url) {
        this.appInfo.logo = curAppInfo.application.logo_url;
      } else {
        this.appInfo.logo = '/static/images/default_logo.png';
      }
    },
    updateBaseInfo() {
      return this.initNavInfo();
    },
    updateAppInfo() {
      return this.initNavInfo();
    },
    // 检查当前路由权限
    checkPermission() {
      // 应用是否有访问权限
      this.appVisitEnable = true;
      this.appPermissionMessage = '';
      if (this.$route.name === 'appPermissionPathExempt') {
        if (!this.curAppInfo.feature.ACCESS_CONTROL_EXEMPT_MODE) {
          this.appVisitEnable = false;
          this.appPermissionMessage = this.$t('应用未开启“配置豁免路径”的功能');
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
    .no-permission {
        margin: 100px 30px 0 30px;
        font-size: 16px;
        text-align: center;

        h2 {
            margin-top: 15px;
            font-size: 14px;
            color: #666;
        }

        a {
            color: #3A84FF;
        }
    }

    .nofound {
        padding-top: 150px;
        width: 939px;
        text-align: center;
        font-size: 20px;
        color: #979797;
        line-height: 80px;
    }
</style>
