<template>
  <div
    v-en-class="'en-header-cls'"
    :class="['ps-header', 'clearfix', 'top-bar-wrapper', { 'bk-header-static': isStatic }]"
  >
    <div class="ps-header-visible">
      <section class="nav-left-wrapper">
        <router-link
          :to="{ name: 'index' }"
          class="ps-logo"
        >
          <span class="logo-warp">
            <img
              :src="appLogo"
              alt=""
            />
            <span class="logo-text">{{ appName }}</span>
          </span>
        </router-link>
        <ul
          class="ps-nav"
          ref="navListRef"
        >
          <li
            v-for="(item, index) in displayNavList"
            :key="index"
            :class="{ active: curActiveName === item.name }"
          >
            <router-link
              v-if="item.type === 'router-link'"
              :to="item.to"
            >
              {{ item.text }}
            </router-link>
            <a
              v-else
              :href="item.href"
              :target="item.target"
            >
              {{ item.text }}
            </a>
          </li>
        </ul>
      </section>
      <ul
        v-if="userInitialized && user.isAuthenticated"
        class="ps-head-right"
      >
        <template>
          <!-- 全局搜索 -->
          <global-input v-if="userFeature.AGGREGATE_SEARCH && isShowInput" />
          <!-- 语言切换 -->
          <bk-popover
            theme="light navigation-message"
            ext-cls="top-bar-popover"
            placement="bottom"
            :arrow="false"
            offset="0, 5"
            trigger="mouseenter"
            :tippy-options="{ hideOnClick: false }"
          >
            <div class="header-mind is-left header-mind-cls">
              <span :class="`bk-icon icon-${localLanguage === 'en' ? 'english' : 'chinese'} lang-icon nav-lang-icon`" />
            </div>
            <template #content>
              <ul class="monitor-navigation-admin">
                <li
                  v-for="item in languageList"
                  :class="['nav-item', { active: item.id === localLanguage }]"
                  @click="switchLanguage(item.id)"
                  :key="item.id"
                >
                  <i :class="['bk-icon', 'lang-icon', item.icon]" />
                  {{ item.text }}
                </li>
              </ul>
            </template>
          </bk-popover>
          <bk-popover
            theme="light navigation-message"
            ext-cls="top-bar-popover"
            :arrow="false"
            offset="-20, 5"
            placement="bottom-start"
            :tippy-options="{ hideOnClick: false }"
          >
            <div class="header-help is-left">
              <i class="paasng-icon paasng-help" />
            </div>
            <template #content>
              <ul class="monitor-navigation-admin">
                <li class="nav-item">
                  <a
                    :href="GLOBAL.DOC.PRODUCT_DOC"
                    target="_blank"
                  >
                    {{ $t('产品文档') }}
                  </a>
                </li>
                <li
                  v-if="GLOBAL.CONFIG.RELEASE_LOG"
                  class="nav-item"
                >
                  <a
                    href="javascript:"
                    @click="handlerLogVersion"
                  >
                    {{ $t('版本日志') }}
                  </a>
                </li>
                <li class="nav-item">
                  <a
                    :href="GLOBAL.LINK.PA_ISSUE"
                    target="_blank"
                  >
                    {{ $t('问题反馈') }}
                  </a>
                </li>
                <li class="nav-item">
                  <a
                    :href="GLOBAL.LINK.BK_OPEN_COMMUNITY"
                    target="_blank"
                  >
                    {{ $t('开源社区') }}
                  </a>
                </li>
              </ul>
            </template>
          </bk-popover>
        </template>
        <!-- 退出登录 -->
        <bk-popover
          theme="light navigation-message"
          ext-cls="top-bar-popover"
          :arrow="false"
          offset="30, 13"
          placement="bottom-start"
          :tippy-options="{ hideOnClick: false }"
        >
          <div class="header-user is-left ps-head-last">
            <!-- 多租户展示 -->
            <span v-if="isMultiTenantDisplayMode">
              <bk-user-display-name :user-id="user.username"></bk-user-display-name>
            </span>
            <template v-else>{{ user.chineseName || user.username }}</template>
            <i class="bk-icon icon-down-shape" />
          </div>
          <template #content>
            <ul class="monitor-navigation-admin">
              <li class="nav-item">
                <a
                  id="logOut"
                  href="javascript:"
                  target="_blank"
                  @click="logout"
                >
                  {{ $t('退出登录') }}
                </a>
              </li>
            </ul>
          </template>
        </bk-popover>
      </ul>
    </div>
    <log-version :dialog-show.sync="showLogVersion" />
  </div>
</template>

<script>
import auth from '@/auth';
import { bus } from '@/common/bus';
import selectEventMixin from '@/components/searching/selectEventMixin';
import { psHeaderInfo } from '@/mixins/ps-static-mixin';
import defaultUserLogo from '../../static/images/default-user.png';
import logVersion from './log-version.vue';
import { ajaxRequest, uuid } from '@/common/utils';
import logoSvg from '/static/images/logo.svg';
import globalInput from './global-search/search-input.vue';
import { mapState, mapGetters } from 'vuex';

export default {
  components: {
    logVersion,
    globalInput,
  },
  mixins: [psHeaderInfo, selectEventMixin],
  props: [],
  data() {
    const user = auth.getAnonymousUser();
    return {
      userInitialized: false,
      avatars: defaultUserLogo,
      curActiveName: '',
      isStatic: false, // 头部导航背景色块控制
      user,
      backgroundHidden: false,
      navHideController: 0,
      navShowController: 0,
      filterKey: '',
      enableSearchApp: true, // 是否开启搜索APP功能
      currenSearchPanelIndex: -1,
      showLogVersion: false,
      languageList: [
        { icon: 'icon-chinese', id: 'zh-cn', text: this.$t('中文') },
        { icon: 'icon-english', id: 'en', text: this.$t('英文') },
      ],
    };
  },
  computed: {
    ...mapState(['localLanguage', 'userFeature', 'platformConfig']),
    ...mapGetters(['tenantId', 'isMultiTenantDisplayMode']),
    displayNavList() {
      const nav = this.headerStaticInfo.list.nav || [];
      return this.transformNavData(nav);
    },
    appName() {
      return this.platformConfig.i18n?.productName || this.$t('蓝鲸开发者中心');
    },
    appLogo() {
      return this.platformConfig.appLogo ?? logoSvg;
    },
    isShowInput() {
      return !this.$route.meta.hideGlobalSearch;
    },
    defaultSwitchLanguageUrl() {
      return `${window.BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fe_update_user_language/`;
    },
  },
  watch: {
    $route: 'checkRouter',
    userFeature: {
      handler(val) {
        if (!val.ALLOW_PLUGIN_CENTER) {
          this.headerStaticInfo.list.nav = this.headerStaticInfo.list.nav.filter((e) => e.text !== this.$t('插件开发'));
        }
      },
      deep: true,
    },
  },
  created() {
    this.checkRouter();
    window.addEventListener('scroll', this.handleScroll);

    bus.$on('page-header-be-transparent', () => {
      this.backgroundHidden = true;
    });

    // 入口请求成功，说明用户已认证
    bus.$on('on-user-data', (user) => {
      this.userInitialized = true;
      this.user = user;
      if (user.avatarUrl) {
        this.avatars = user.avatarUrl;
      }
      this.$store.commit('updataUserInfo', user);
    });
  },
  methods: {
    goRouter(sitem) {
      if (!sitem.url.startsWith('javascript')) {
        const to = `/developer-center/service/${sitem.url}`;
        this.$router.push({
          path: to,
        });
      }
    },
    // 监听滚动事件（滚动是头部样式切换）
    handleScroll() {
      this.isStatic = window.scrollY > 0;
    },
    // 路由页面重定向时导航标记
    checkRouter() {
      const routeConfig = [
        { names: ['index', 'home'], active: 'homePage' },
        { paths: ['/developer-center/app', '/sandbox'], active: 'appDevelopment' },
        { paths: ['/plugin-center'], active: 'pluginDevelopment' },
        { paths: ['/developer-center/service'], active: 'tools' },
        { paths: ['/plat-mgt'], active: 'platformManagement' },
      ];
      // 默认高亮
      let active = 'homePage';
      // 遍历配置对象，检查当前路由是否匹配
      for (const config of routeConfig) {
        if (
          (config.names && config.names.includes(this.$route.name)) ||
          (config.paths && config.paths.some((path) => this.$route.path.includes(path)))
        ) {
          active = config.active;
          break;
        }
      }
      this.curActiveName = active;
    },
    logout() {
      window.location = `${window.GLOBAL_CONFIG.LOGIN_SERVICE_URL}/?is_from_logout=1&c_url=${encodeURIComponent(
        window.location.href
      )}`;
    },
    makeAjaxRequest(url, language) {
      return new Promise((resolve, reject) => {
        ajaxRequest({
          url,
          jsonp: `callback${uuid()}`,
          data: { language },
          success: resolve,
          error: reject,
        });
      });
    },
    /**
     * 切换系统语言
     * @param {string} language - 目标语言
     */
    async switchLanguage(language) {
      try {
        const data = new URLSearchParams();
        data.append('language', language);
        await this.$http.post(`${BACKEND_URL}/i18n/setlang/`, data, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });

        // 更新本地语言状态
        this.$i18n.locale = language;
        this.$store.commit('updateLocalLanguage', language);

        // 根据环境变量判断是否需要额外请求
        const needAjaxRequest = this.isMultiTenantDisplayMode ? window.BK_API_URL_TMPL : window.BK_COMPONENT_API_URL;

        if (!needAjaxRequest) {
          return window.location.reload();
        }

        // 处理多租户和非多租户环境请求
        if (this.isMultiTenantDisplayMode) {
          await this.$store.dispatch('tenant/tenantLocaleSwitch', {
            tenantId: this.tenantId,
            data: {
              language,
            },
          });
        } else {
          await this.makeAjaxRequest(this.defaultSwitchLanguageUrl, language);
        }
        window.location.reload();
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },
    handlerLogVersion() {
      this.showLogVersion = true;
    },
    // 重组导航数据
    transformNavData(navData) {
      const navConfig = {
        homePage: { type: 'router-link', to: { name: 'index' } },
        appDevelopment: { type: 'router-link', to: { name: 'myApplications' } },
        pluginDevelopment: { type: 'router-link', to: { name: 'plugin' } },
        apiGateway: { type: 'external-link', href: this.GLOBAL.LINK.APIGW_INDEX, target: '_blank' },
        tools: { type: 'router-link', to: { name: 'serviceCode' } },
        platformManagement: { type: 'router-link', to: { name: 'platformManagement' } },
      };
      return navData
        .map((item) => {
          const { text, name } = item;
          const config = navConfig[name];
          return {
            text,
            name,
            ...config,
          };
        })
        .filter((item) => {
          // 特性开关控制插件开发、平台管理
          const excludePlugin = !this.userFeature.ALLOW_PLUGIN_CENTER && item.name === 'pluginDevelopment';
          const excludePlatform = !this.userFeature.PLATFORM_MANAGEMENT && item.name === 'platformManagement';
          return !excludePlugin && !excludePlatform;
        });
    },
  },
};
</script>

<style lang="scss" scoped>
.ps-header {
  margin-top: var(--app-notice-height);
  width: 100%;
  z-index: 1001;
  transition: all 0.5s;
  background: #182132;
  box-sizing: border-box;

  > * {
    box-sizing: border-box;
  }

  &::before {
    content: '';
    position: fixed;
    top: var(--app-notice-height);
    left: 0;
    width: 100%;
    height: 0;
    background-color: transparent;
    -webkit-transition: height 0.2s, background-color 0.2s;
    transition: height 0.2s, background-color 0.2s;
  }

  &:hover::before {
    content: '';
    position: fixed;
    top: var(--app-notice-height);
    left: 0;
    width: 100%;
    height: 50px;
  }

  .ps-logo {
    width: 242px;
    position: relative;
    margin-left: 16px;
    display: flex;
    align-items: center;
    .logo-warp {
      display: flex;
      align-items: center;
      img {
        display: inline-block;
        vertical-align: middle;
        height: 28px;
      }
      .logo-text {
        color: #eaebf0;
        font-size: 16px;
        padding-left: 16px;
      }
    }
  }
}

.bg-hidden {
  background: transparent;
}

.bk-header-static {
  background: #191929;
  transition: all 0.5s;
}

.ps-header-visible {
  overflow: inherit;
  position: relative;
  z-index: 99;
  // min-width: 1200px;
  min-width: 1000px;
  height: 52px;
  display: flex;
  justify-content: space-between;
  flex-wrap: nowrap;

  .nav-left-wrapper {
    display: flex;
    flex: 1;
  }
}

.ps-header {
  a {
    color: #96a2b9;
    &:hover {
      color: #c2cee5;
    }
  }
  .active a {
    color: #ffffff;
  }
}

.ps-nav {
  flex: 1;
  display: flex;
  overflow: hidden;

  li {
    flex-shrink: 0;
    margin-right: 32px;

    &:last-child {
      margin-right: 0;
    }
  }
}

.ps-nav li > a {
  line-height: 36px;
  position: relative;
  padding: 8px 0;

  &.has-angle {
    padding: 7px 16px 7px 0;
  }
}

.ps-nav li > span {
  width: 0;
  height: 3px;
  background: #3976e4;
  position: absolute;
  left: 0;
  bottom: 0;
  transform-origin: 50% 50%;
  transition: all 0.3s;
}

.ps-nav li:hover > span,
.ps-nav li.active > span {
  width: 100%;
}

.ps-nav li .paasng-icon.paasng-angle-down {
  font-size: 10px;
  font-weight: bold;
  transform: scale(0.8);
}

.ps-head-right {
  position: relative;
  margin: 0;
  padding: 8px 10px 8px 0px;
  display: flex;
  align-items: center;
  color: #96a2b9;

  /deep/ .bk-tooltip:not(:last-child) {
    margin-right: 8px;
  }

  li {
    float: left;
  }
}

.ps-head-right .notice-button {
  width: 18px;
  height: 24px;
  display: inline-block;
  margin: 6px 0 0 8px;
  position: relative;
  background: url(/static/images/news-icon.png) no-repeat;
  transition: all 0.5s;
}

.ps-head-right .notice-button:hover {
  background: url(/static/images/news-icon2.png) no-repeat;
}

.ps-head-right .notice-button-icon {
  display: inline-block;
  position: absolute;
  width: 19px;
  height: 14px;
  color: #fff;
  text-align: center;
  line-height: 14px;
  top: -3px;
  right: -12px;
  font-size: 10px;
  border-radius: 7px;
  background: #ff2d2d;
}

.ps-head-right .login-button {
  display: inline-block;
  width: 78px;
  height: 34px;
  text-align: center;
  line-height: 34px;
  border-radius: 18px;
  border: solid 1px #3976e4;
  color: #3976e4;
  transition: all 0.5s;
}

.ps-head-right .login-button:hover {
  color: #fff;
  background: #3976e4;
  border-color: #3976e4;
}

.hoverStatus2 {
  top: -1px;
  height: 406px !important;
  opacity: 1;
  visibility: visible;
  transition: all 0.5s;
}

.hoverStatus3 {
  top: -1px;
  height: 207px !important;
  opacity: 1;
  visibility: visible;
  transition: all 0.5s;
}

.ps-head-right li a.link-text {
  color: #96a2b9;
  font-size: 14px;
  line-height: 34px;
  position: relative;
  transition: all 0.5s;

  .paasng-down-shape {
    position: absolute;
    top: 12px;
    right: 0;
    transform: scale(0.8);
  }

  .monitor-icon {
    font-size: 16px;
  }

  &:hover {
    color: #ffffff;
  }
}

.user,
.contact {
  opacity: 0;
  visibility: hidden;
  background: #fff;
  border: solid 1px #eeeeee;
  border-radius: 2px;
  position: absolute;
  right: 0;
  top: 50px;
  transition: all 0.3s;
  box-shadow: 0 2px 5px #e5e5e5;
}

.user {
  max-width: 200px;
}

.contact {
  width: 110px;
  right: 50%;
  transform: translate(50%, 0);
}

.contact ul {
  padding: 10px 15px;
}

.contact li {
  line-height: 30px;
  clear: both;
  float: none;
  padding: 0;
  margin: 0;
  text-align: center;

  a {
    color: #666;

    &:hover {
      color: #3a84ff;
    }
  }
}

.user:after,
.contact:after {
  content: '';
  position: absolute;
  top: -10px;
  right: 36px;
  width: 16px;
  height: 10px;
  background: url(/static/images/user-icon2.png) no-repeat;
}

.contact:after {
  right: 45px;
}

.user-yourname {
  padding: 20px 24px 15px 24px;
  border-bottom: solid 1px #eeeeee;
  display: flex;
}

.user-yourname img {
  width: 36px;
  border-radius: 2px;
}

.user-yourname span.fright {
  min-width: 80px;
  max-width: 115px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #666666;
  padding-left: 15px;
  line-height: 36px;
}

.user-opation {
  width: 80px;
  height: 40px;
  text-align: center;
  line-height: 40px;
}

.user-opation a {
  font-size: 12px;
  line-height: 36px;
  color: #666666;
}

.user-opation a:hover {
  color: #3a84ff;
}

.ps-head-last {
  position: relative;
}
.ps-head-last:hover .user,
.ps-head-last:hover .contact {
  opacity: 1;
  visibility: visible;
}
.ps-head-last .language {
  li {
    cursor: pointer;
    text-align: left;
    display: flex;
    align-items: center;
    &:hover i {
      color: #3a84ff;
    }
  }
  li i {
    font-size: 16px;
    margin-right: 5px;
  }
}
.switch-language {
  line-height: 34px;
  font-size: 14px !important;
  color: #9b9ca8;
  user-select: none;
  &:hover {
    cursor: pointer;
    color: #fff;
  }
}
.translate-icon {
  width: 20px;
  height: 20px;
  transform: translateY(6px);
}
.translate-icon-font {
  padding-left: 3px;
}
.my-alarm {
  width: 32px;
  height: 32px;
  display: flex;
  justify-content: center;
  align-content: center;
  margin-right: 8px;
  color: #96a2b9 !important;
  transition: all 0s !important;
  &:hover {
    color: #fff;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 100%;
    i {
      color: #fff !important;
    }
  }
  i {
    color: #96a2b9 !important;
  }
}
</style>
<style lang="scss">
.top-bar-popover {
  .tippy-tooltip.light-theme {
    box-shadow: 0 0 6px 0 #dcdee5 !important;
    padding: 0 !important;
  }
  .tippy-content {
    box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.1) !important;
    border-radius: 2px;
  }
}
.top-bar-wrapper {
  .header-mind,
  .header-help {
    width: 32px;
    height: 32px;
    font-size: 18px;
    &.is-left {
      color: #96a2b9;
      cursor: pointer;
      &:hover {
        color: #fff;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
      }
    }
  }
}
.top-bar-wrapper .header-mind {
  position: relative;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  -webkit-box-pack: center;
  -ms-flex-pack: center;
  justify-content: center;
  font-size: 18px;
}
.top-bar-wrapper .header-mind-mark {
  position: absolute;
  right: 8px;
  top: 8px;
  height: 7px;
  width: 7px;
  border: 1px solid #27334c;
  background-color: #ea3636;
  border-radius: 100%;
}
.top-bar-wrapper .header-mind-mark.is-left {
  border-color: #f0f1f5;
}
.top-bar-wrapper .header-help {
  position: relative;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  -webkit-box-pack: center;
  -ms-flex-pack: center;
  justify-content: center;
  font-size: 16px;
  transform: translateY(0px);
}
.top-bar-wrapper .header-user {
  height: 100%;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  -webkit-box-pack: center;
  -ms-flex-pack: center;
  justify-content: center;
  color: #96a2b9;
  margin-left: 8px;
}
.top-bar-wrapper .header-user .bk-icon {
  margin-left: 5px;
  font-size: 12px;
}
.top-bar-wrapper .header-user.is-left:hover {
  color: #fff;
}
.top-bar-wrapper .header-user:hover {
  cursor: pointer;
  color: #d3d9e4;
}
.monitor-navigation-admin {
  width: 170px #96a2b9;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-orient: vertical;
  -webkit-box-direction: normal;
  -ms-flex-direction: column;
  flex-direction: column;
  background: #ffffff;
  padding: 6px 0;
  margin: 0;
  color: #63656e;
}
.monitor-navigation-admin .nav-item {
  flex: 0 0 32px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  list-style: none;
  color: #63656e;
  a {
    color: #63656e;
  }
  .lang-icon {
    font-size: 18px;
    margin-right: 6px;
  }
  &.active {
    background-color: #eaf3ff;
    color: #3a84ff;
    a {
      color: #3a84ff;
    }
  }
}
.monitor-navigation-admin .nav-item:hover {
  cursor: pointer;
  background-color: #eaf3ff;
  color: #3a84ff;
  a {
    color: #3a84ff;
  }
}
</style>
