<template>
  <div
    v-en-class="'en-header-cls'"
    :class="['ps-header', 'clearfix', 'top-bar-wrapper', { 'bk-header-static': is_static }]"
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
            :class="{ active: curpage === index }"
            @mouseover.stop.prevent="showSubNav(index, item)"
            @mouseout.stop.prevent="hideSubNav"
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
              <i
                v-show="item.showIcon"
                class="paasng-icon paasng-angle-down"
              />
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
                  <i :class="['bk-icon', 'lang-icon', item.icon]" />{{ item.text }}
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
            {{ user.chineseName || user.username }}
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
    <div
      :class="[
        'ps-header-invisible',
        'invisible1',
        'clearfix',
        { hoverStatus2: navText === $t('服务'), hoverStatus3: navText === $t('文档与支持') },
      ]"
      @mouseover.stop.prevent="showSubNav(navIndex)"
      @mouseout.stop.prevent="hideSubNav"
    >
      <dl v-for="colitem in curSubNav">
        <template v-if="colitem.hasOwnProperty('title')">
          <dt>{{ colitem.title }}</dt>
          <!-- 给有三级导航的dd添加sub-native类 -->
          <dd
            v-for="sitem in colitem.items"
            class="sub-native"
          >
            <a
              v-if="sitem.navs"
              href="javascript:;"
            >
              {{ sitem.text }}
              <i
                v-if="sitem.navs"
                class="paasng-icon paasng-angle-right"
              />
            </a>
            <template v-else>
              <a
                v-if="sitem.url.startsWith('http')"
                :href="sitem.url"
                target="_blank"
              >
                {{ sitem.text }}
              </a>
              <a
                v-else
                href="javascript:;"
                @click="goRouter(sitem)"
              >
                {{ sitem.text }}
              </a>
            </template>
            <dl v-if="sitem.navs">
              <dd v-for="minItem in sitem.navs">
                <a
                  :href="minItem.url"
                  target="_blank"
                >
                  {{ minItem.text }}
                  <span class="white">{{ minItem.eName }}</span>
                </a>
              </dd>
            </dl>
          </dd>
        </template>

        <template
          v-for="subColitem in colitem.items"
          v-else
        >
          <dt>{{ subColitem.title }}</dt>
          <!-- 给有三级导航的dd添加sub-native类 -->
          <dd
            v-for="sitem in subColitem.items"
            class="sub-native"
          >
            <a
              v-if="sitem.navs"
              href="javascript:;"
            >
              {{ sitem.text }}
              <i
                v-if="sitem.navs"
                class="paasng-icon paasng-angle-right"
              />
            </a>
            <template v-else>
              <a
                v-if="sitem.url.startsWith('http')"
                :href="sitem.url"
                target="_blank"
              >
                {{ sitem.text }}
              </a>
              <a
                v-else
                href="javascript:;"
                @click="goRouter(sitem)"
              >
                {{ sitem.text }}
              </a>
            </template>
            <dl v-if="sitem.navs">
              <dd v-for="minItem in sitem.navs">
                <a
                  :href="minItem.url"
                  target="_blank"
                >
                  {{ minItem.text }}
                  <span class="white">{{ minItem.eName }}</span>
                </a>
              </dd>
            </dl>
          </dd>
        </template>
        <dd class="last" />
      </dl>
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
      curpage: -1, // 当前页导航底部线标志控制
      is_static: false, // 头部导航背景色块控制
      navIndex: 0,
      curSubNav: [],
      loginFlag: false,
      user,
      backgroundHidden: false,
      navHideController: 0,
      navShowController: 0,
      filterKey: '',
      enableSearchApp: true, // 是否开启搜索APP功能
      currenSearchPanelIndex: -1,
      showLogVersion: false,
      searchComponentList: [
        {
          title: this.$t('蓝鲸应用'),
          component: 'searchAppList',
          max: 4,
          params: {
            include_inactive: true,
          },
        },
      ],
      // eslint-disable-next-line comma-dangle
      link: this.GLOBAL.LINK.APIGW_INDEX,
      navText: '',
      languageList: [
        { icon: 'icon-chinese', id: 'zh-cn', text: this.$t('中文') },
        { icon: 'icon-english', id: 'en', text: this.$t('英文') },
      ],
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    userFeature() {
      return this.$store.state.userFeature;
    },
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    displayNavList() {
      const nav = this.headerStaticInfo.list.nav || [];
      return this.transformNavData(nav);
    },
    platformConfig() {
      return this.$store.state.platformConfig;
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
  },
  watch: {
    $route: 'checkRouter',
    userFeature: {
      handler(val) {
        if (!val.ALLOW_PLUGIN_CENTER) {
          this.headerStaticInfo.list.nav = this.headerStaticInfo.list.nav.filter(e => e.text !== this.$t('插件开发'));
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
      this.hideSubNav();
    },
    // 监听滚动事件（滚动是头部样式切换）
    handleScroll() {
      if (window.scrollY > 0) {
        this.is_static = true;
      } else {
        this.is_static = false;
      }
    },
    hideSubNav() {
      clearTimeout(this.navShowController);
      this.navHideController = setTimeout(() => {
        this.navIndex = 0;
        this.navText = '';
      }, 300);
    },
    // 二级导航mouseover
    showSubNav(index, item) {
      clearTimeout(this.navHideController);
      if (item?.showIcon) {
        if (!item) return;
        this.navShowController = setTimeout(() => {
          this.navIndex = index;
          this.navText = item.text;
          this.curSubNav = this.headerStaticInfo.list.subnav_service;
        }, 500);
      } else {
        this.navIndex = index;
      }
    },
    // 路由页面重定向时导航标记
    checkRouter() {
      let noteIndex = -1;
      if (this.$route.name === 'index' || this.$route.name === 'home') {
        noteIndex = 0;
      }
      if (this.$route.path.indexOf('/developer-center/app') !== -1) {
        noteIndex = 1;
      }
      if (this.$route.path.indexOf('/plugin-center') !== -1) {
        noteIndex = 2;
      }
      if (this.$route.path.indexOf('/developer-center/service') !== -1) {
        noteIndex = this.displayNavList.findIndex(v => v.text === this.$t('服务')) || 3;
      }
      if (noteIndex !== -1) {
        this.backgroundHidden = false;
        this.curpage = noteIndex;
      } else {
        this.curpage = -1;
      }
    },
    logout() {
      window.location = `${window.GLOBAL_CONFIG.LOGIN_SERVICE_URL}/?is_from_logout=1&c_url=${encodeURIComponent(window.location.href)}`;
    },
    async switchLanguage(language) {
      const data = new URLSearchParams();
      data.append('language', language);
      this.$http.post(`${BACKEND_URL}/i18n/setlang/`, data, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }).then((res) => {
        this.$i18n.locale = language;
        this.$store.commit('updateLocalLanguage', language);
        // 设置cookies持续化
        if (window.BK_COMPONENT_API_URL) {
          ajaxRequest({
            url: `${window.BK_COMPONENT_API_URL}/api/c/compapi/v2/usermanage/fe_update_user_language/`,
            jsonp: `callback${uuid()}`,
            data: Object.assign({ language }),
            success: () => {
              this.$router.go(0);
            },
          });
        } else {
          this.$router.go(0);
        }
      }, (e) => {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      });
    },
    handlerLogVersion() {
      this.showLogVersion = true;
    },
    // 重组导航数据
    transformNavData(navData) {
      const navList = navData.map((item) => {
        let transformedItem = {
          text: item.text,
          type: 'external-link', // 默认为外部链接
          href: 'javascript:;',
          target: '_self',
          showIcon: true,
        };
        switch (item.name) {
          case 'homePage':
            transformedItem = {
              ...transformedItem,
              type: 'router-link',
              to: { name: 'index' },
              showIcon: false,
            };
            break;
          case 'appDevelopment':
            transformedItem = {
              ...transformedItem,
              type: 'router-link',
              to: { name: 'myApplications' },
              showIcon: false,
            };
            break;
          case 'pluginDevelopment':
            transformedItem = {
              ...transformedItem,
              type: 'router-link',
              to: { name: 'plugin' },
              showIcon: false,
            };
            break;
          case 'apiGateway':
            transformedItem = {
              ...transformedItem,
              showIcon: false,
              href: this.link,
            };
            break;
        }
        return transformedItem;
      });
      // 应用开关过滤插件开发
      if (!this.userFeature.ALLOW_PLUGIN_CENTER) {
        return navList.filter(e => e.name !== 'pluginDevelopment');
      }
      return navList;
    },
  },
};
</script>

<style lang="scss" scoped>
.ps-header {
  position: fixed;
  left: 0px;
  top: var(--app-notice-height);
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
    background: #191929;
    -webkit-transition-timing-function: cubic-bezier(0.2, 1, 0.3, 1);
    transition-timing-function: cubic-bezier(0.2, 1, 0.3, 1);
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
  background: #191929;
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

.ps-header-invisible {
  width: 100%;
  background: #262634;
  color: #fff;
  overflow: hidden;
  padding-left: 372px;
  position: relative;
  box-sizing: border-box;
}

.invisible1 {
  top: -1px;
  height: 0px !important;
  opacity: 0;
  visibility: hidden;
  transition: all 0s;
}

.invisible2 {
  top: -1px;
  height: 0px !important;
  opacity: 0;
  visibility: hidden;
  transition: all 0s;
}

.hoverStatus {
  top: -1px;
  height: 207px !important;
  opacity: 1;
  visibility: visible;
  transition: all 0.5s;
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

.ps-header-invisible.pl {
  padding-left: 512px;
}

.ps-header-invisible > dl {
  width: 139px;
  min-height: 400px;
  float: left;
  line-height: 32px;
  border-left: solid 1px #30303d;
  padding: 5px 0 62px 0;
}
.en-header-cls .ps-header-invisible > dl {
  width: 145px;
}

.ps-header-invisible > dl:last-child {
  border-right: solid 1px #30303d;
}

.ps-header-invisible dt {
  color: #ffffff;
  font-weight: bold;
  padding-bottom: 14px;

  margin-top: 20px;
}

.ps-header-invisible dt,
.ps-header-invisible dd {
  padding: 0 10px 0 20px;
}

.ps-header-invisible dd:hover {
  background: #191929;
}

.ps-header-invisible dd a {
  color: #9394a3;
  width: 100%;
  position: relative;
}

.ps-header-invisible dd i.paasng-angle-right {
  display: inline-block;
  width: 5px;
  height: 8px;
  position: absolute;
  top: 12px;
  right: 10px;
  font-size: 12px;
}

.sub-native dl {
  display: none;
  width: auto;
  min-width: 220px;
  background: #191929;
  position: absolute;
  left: -6px;
  margin-left: 1072px;
  top: 0;
  padding-top: 23px;
  padding-bottom: 999px;
}

.sub-native:hover dl {
  display: block;
}

.ps-header-invisible .sub-native dd a {
  font-weight: normal;
}

.ps-header-invisible .sub-native dd a:hover {
  color: #3a84ff;
  font-weight: normal;
}

.sub-native dd a span,
.sub-native dd:hover span {
  color: #767b87;
  font-size: 12px;
}

.ps-header-invisible dd.last {
  height: 62px;
  background: none;
}

.ps-header-invisible.pl dd.last {
  height: 28px;
  background: none;
}

.ps-header-invisible dd.last:hover,
.ps-header-invisible.pl dd.last:hover {
  background: none;
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
