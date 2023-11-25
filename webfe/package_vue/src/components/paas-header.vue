<template>
  <div
    v-en-class="'en-header-cls'"
    :class="['ps-header','clearfix', 'top-bar-wrapper', { 'bk-header-static': is_static }]"
  >
    <div class="ps-header-visible clearfix">
      <router-link
        :to="{ name: 'index' }"
        class="ps-logo"
      >
        <span class="logo-warp">
          <img
            src="/static/images/logo.svg"
            alt=""
          >
          <span class="logo-text">{{ $t('蓝鲸开发者中心') }}</span>
        </span>
      </router-link>
      <ul class="ps-nav">
        <li
          v-for="(item,index) in headerStaticInfo.list.nav"
          :key="index"
          :class="{ 'active': curpage === index }"
          @mouseover.stop.prevent="showSubNav(index, item)"
          @mouseout.stop.prevent="hideSubNav"
        >
          <router-link
            v-if="index === 0"
            :to="{ name: 'index' }"
          >
            {{ item.text }}
          </router-link>
          <router-link
            v-else-if="index === 1"
            :class="{ 'has-angle': index !== 1 }"
            :to="{ name: 'myApplications' }"
          >
            {{ item.text }}
          </router-link>
          <router-link
            v-else-if="(index === 2 && userFeature.ALLOW_PLUGIN_CENTER)"
            :to="{ name: 'plugin' }"
          >
            {{ item.text }}
          </router-link>
          <a
            v-else-if="(item.text === $t('API 网关'))"
            :href="link"
            target="_blank"
          >
            {{ item.text }}
          </a>
          <a
            v-else
            :class="{ 'has-angle': index !== 0 }"
            href="javascript:;"
          >
            {{ item.text }}<i
              v-show="index !== 0"
              class="paasng-icon paasng-angle-down"
            />
          </a>
          <!-- <span
            v-if="isShowInput"
            class="line"
          /> -->
        </li>
      </ul>
      <!-- 右侧 -->
      <ul
        v-if="userInitialized && !user.isAuthenticated"
        class="ps-head-right"
      >
        <li>
          <div class="ps-search clearfix">
            <input
              type="text"
              placeholder=""
            >
            <input type="button">
          </div>
        </li>
        <li>
          <a
            class="notice-button"
            href="javascript:"
          />
        </li>
        <li>
          <a
            class="login-button"
            href="javascript:"
            @click="open_login_dialog()"
          > {{ $t('登录') }} </a>
        </li>
      </ul>
      <ul
        v-if="userInitialized && user.isAuthenticated"
        class="ps-head-right"
      >
        <template>
          <li class="mr20" v-if="userFeature.AGGREGATE_SEARCH">
            <dropdown
              ref="dropdown"
              :options="{
                position: 'bottom right',
                classes: 'ps-header-dropdown exclude-drop',
                tetherOptions: {
                  targetOffset: '0px 30px'
                }, beforeClose
              }"
            >
              <div
                slot="trigger"
                class="ps-search clearfix"
              >
                <input
                  v-if="isShowInput"
                  v-model="filterKey"
                  type="text"
                  :placeholder="`${$t('输入')} &quot;FAQ&quot; ${$t('看看')}`"
                  @keydown.down.prevent="emitChildKeyDown"
                  @keydown.up.prevent="emitChildKeyUp"
                  @keypress.enter="enterCallBack($event)"
                  @compositionstart="handleCompositionstart"
                  @compositionend="handleCompositionend"
                  @focus="handleFocus"
                  @blur="handleBlur"
                >
                <div class="ps-search-icon">
                  <span
                    v-if="filterKey === ''"
                    class="paasng-icon paasng-search"
                  />
                  <span
                    v-else
                    class="paasng-icon paasng-close close-cursor"
                    @click="clearInputValue"
                  />
                </div>
              </div>
              <!-- 先不显示搜索蓝鲸应用的功能，需要前端：1）添加dropdwon插件，即鼠标点击其它位置时关闭下来框内容；2）下来框样式调整 -->
              <div
                slot="content"
                class="header-search-result"
              >
                <div v-if="isShowInput && isFocus">
                  <div
                    v-if="filterKey !== ''"
                    class="paas-search-trigger"
                    @click.stop="handleToSearchPage"
                  >
                    <span> {{ $t('查看更多结果') }} </span>
                  </div>
                  <div
                    v-for="(searchComponent, index) of searchComponentList"
                    v-show="filterKey"
                    :key="index"
                  >
                    <h3>{{ searchComponent.title }}</h3>
                    <component
                      :is="searchComponent.component"
                      ref="searchPanelList"
                      :theme="'ps-header-search'"
                      :max="searchComponent.max"
                      :filter-key="filterKey"
                      :params="searchComponent.params"
                      @selectAppCallback="selectAppCallback"
                      @key-up-overflow="onKeyUp(), emitChildKeyUp()"
                      @key-down-overflow="onKeyDown(), emitChildKeyDown()"
                    />
                  </div>
                </div>
              </div>
            </dropdown>
          </li>
          <li
            v-if="userFeature.PHALANX"
            v-bk-tooltips.bottom="{ content: $t('我的告警'), distance: 20 }"
            class="ps-head-last my-alarm"
          >
            <a
              class="link-text"
              href="javascript:"
              @click="handleToMonitor"
            >
              <i class="paasng-icon paasng-monitor-fill monitor-icon" />
            </a>
          </li>
          <!-- 语言切换 -->
          <bk-popover
            theme="light navigation-message"
            ext-cls="top-bar-popover"
            placement="bottom"
            :arrow="false"
            offset="0, 10"
            trigger="mouseenter"
            :tippy-options="{ 'hideOnClick': false }"
          >
            <div class="header-mind is-left header-mind-cls">
              <span :class="`bk-icon icon-${localLanguage === 'en' ? 'english' : 'chinese'} lang-icon nav-lang-icon`" />
            </div>
            <template #content>
              <ul class="monitor-navigation-admin">
                <li
                  class="nav-item"
                  @click="switchLanguage('zh-cn')"
                >
                  <i class="bk-icon icon-chinese lang-icon" />{{ $t('中文') }}
                </li>
                <li
                  class="nav-item"
                  @click="switchLanguage('en')"
                >
                  <i class="bk-icon icon-english lang-icon" />{{ $t('英文') }}
                </li>
              </ul>
            </template>
          </bk-popover>
          <bk-popover
            theme="light navigation-message"
            ext-cls="top-bar-popover"
            :arrow="false"
            offset="-20, 10"
            placement="bottom-start"
            :tippy-options="{ 'hideOnClick': false }"
          >
            <div class="header-help is-left">
              <svg
                class="bk-icon"
                style="width: 1em; height: 1em;vertical-align: middle;fill: currentColor;overflow: hidden;"
                viewBox="0 0 64 64"
                version="1.1"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M32,4C16.5,4,4,16.5,4,32c0,3.6,0.7,7.1,2,10.4V56c0,1.1,0.9,2,2,2h13.6C36,63.7,52.3,56.8,58,42.4S56.8,11.7,42.4,6C39.1,4.7,35.6,4,32,4z M31.3,45.1c-1.7,0-3-1.3-3-3s1.3-3,3-3c1.7,0,3,1.3,3,3S33,45.1,31.3,45.1z M36.7,31.7c-2.3,1.3-3,2.2-3,3.9v0.9H29v-1c-0.2-2.8,0.7-4.4,3.2-5.8c2.3-1.4,3-2.2,3-3.8s-1.3-2.8-3.3-2.8c-1.8-0.1-3.3,1.2-3.5,3c0,0.1,0,0.1,0,0.2h-4.8c0.1-4.4,3.1-7.4,8.5-7.4c5,0,8.3,2.8,8.3,6.9C40.5,28.4,39.2,30.3,36.7,31.7z" />
              </svg>
            </div>
            <template #content>
              <ul class="monitor-navigation-admin">
                <li class="nav-item">
                  <a
                    :href="GLOBAL.DOC.PRODUCT_DOC"
                    target="_blank"
                  > {{ $t('产品文档') }} </a>
                </li>
                <li
                  v-if="GLOBAL.CONFIG.RELEASE_LOG"
                  class="nav-item"
                >
                  <a
                    href="javascript:"
                    @click="handlerLogVersion"
                  > {{ $t('版本日志') }} </a>
                </li>
                <li class="nav-item">
                  <a
                    :href="GLOBAL.LINK.PA_ISSUE"
                    target="_blank"
                  > {{ $t('问题反馈') }} </a>
                </li>
                <li class="nav-item">
                  <a
                    :href="GLOBAL.LINK.BK_OPEN_COMMUNITY"
                    target="_blank"
                  > {{ $t('开源社区') }} </a>
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
          offset="30, 18"
          placement="bottom-start"
          :tippy-options="{ 'hideOnClick': false }"
        >
          <div class="header-user is-left ps-head-last">
            <!-- 头像 -->
            <!-- <img
                :src="avatars"
                width="36px"
              > -->
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
                > {{ $t('退出登录') }} </a>
              </li>
            </ul>
          </template>
        </bk-popover>
      </ul>
    </div>
    <div
      :class="['ps-header-invisible','invisible1','clearfix',{ 'hoverStatus2': navText === $t('服务'), 'hoverStatus3': navText === $t('文档与支持') }]"
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
              >{{ sitem.text }}
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
              >{{ sitem.text }}
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

<script>import auth from '@/auth';
import { bus } from '@/common/bus';
import { bk_logout as bkLogout } from '../../static/js/bklogout';
import selectEventMixin from '@/components/searching/selectEventMixin';
import searchAppList from '@/components/searching/searchAppList';
import Dropdown from '@/components/ui/Dropdown';
import { psHeaderInfo } from '@/mixins/ps-static-mixin';
import defaultUserLogo from '../../static/images/default-user.png';
import logVersion from './log-version.vue';
import { ajaxRequest, uuid } from '@/common/utils';

export default {
  components: {
    dropdown: Dropdown,
    searchAppList,
    logVersion,
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
      userInfoShow: false,
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
      isShowInput: true,
      isFocus: false,
      // eslint-disable-next-line comma-dangle
      link: this.GLOBAL.LINK.APIGW_INDEX,
      navText: '',
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
  },
  watch: {
    $route: 'checkRouter',
    filterKey() {
      this.curActiveIndex = -1;
    },
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

    bus.$on('on-leave-search', () => {
      this.isShowInput = true;
      this.clearInputValue();
    });

    bus.$on('on-being-search', () => {
      this.isShowInput = false;
    });

    this.getCurrentUser();
  },
  methods: {
    goRouter(sitem) {
      if (!sitem.url.startsWith('javascript')) {
        const to = `/developer-center/service/${sitem.url}`;
        this.$router.push({
          path: to,
        });
      }
      this.hideSubNav(0);
    },
    handleToMonitor() {
      this.$router.push({
        name: 'myMonitor',
      });
    },
    clearInputValue() {
      this.filterKey = '';
    },
    beforeClose(event, instance) {
      // return !instance.target.contains(event.target)
    },
    // enter键 选择事件回调
    enterCallBack(event) {
      if (this.isInputing) {
        return;
      }
      event.currentTarget.blur();
      if (this.$refs.searchPanelList[this.curActiveIndex]) {
        this.$refs.searchPanelList[this.curActiveIndex].enterSelect();
      }
      this.$refs.dropdown.close();

      if (this.filterKey !== '') {
        this.isShowInput = false;
        this.$router.push({
          name: 'search',
          query: {
            keyword: this.filterKey,
          },
        });
      }
    },

    handleCompositionstart() {
      this.isInputing = true;
    },

    handleCompositionend() {
      this.isInputing = false;
    },

    handleFocus() {
      this.isFocus = true;
    },

    handleBlur() {
      setTimeout(() => {
        this.isFocus = false;
      }, 500);
    },

    handleToSearchPage() {
      this.$refs.dropdown.close();
      this.isShowInput = false;
      this.$router.push({
        name: 'search',
        query: {
          keyword: this.filterKey,
        },
      });
    },
    // 键盘上下键 选择事件回调
    emitChildKeyUp() {
      if (this.$refs.searchPanelList.filter(panel => panel.getSelectListLength()).length === 0) {
        return;
      }
      if (this.curActiveIndex === -1) {
        this.onKeyUp();
      }
      this.$refs.searchPanelList[this.curActiveIndex].onKeyUp();
    },
    emitChildKeyDown() {
      if (this.$refs.searchPanelList.filter(panel => panel.getSelectListLength()).length === 0) {
        return;
      }
      if (this.curActiveIndex === -1) {
        this.onKeyDown();
      }
      this.$refs.searchPanelList[this.curActiveIndex].onKeyDown();
    },
    getSelectListLength() {
      return this.$refs.searchPanelList.length;
    },
    // 鼠标选择事件回调
    selectAppCallback(item) {
      // 清空搜索条件，不再显示APP下拉框
      this.filterKey = '';
      this.$refs.dropdown.close();
    },
    getCurrentUser() {
      auth.requestCurrentUser().then((user) => {
        this.userInitialized = true;
        this.user = user;
        if (user.avatarUrl) {
          this.avatars = user.avatarUrl;
        }
      });
    },
    // 监听滚动事件（滚动是头部样式切换）
    handleScroll() {
      if (window.scrollY > 0) {
        this.is_static = true;
      } else {
        this.is_static = false;
      }
    },
    hideSubNav(timeout = 300) {
      clearTimeout(this.navShowController);
      this.navHideController = setTimeout(() => {
        this.navIndex = 0;
        this.navText = '';
      }, 300);
    },
    // 二级导航mouseover
    showSubNav(index, item) {
      clearTimeout(this.navHideController);
      if (index === 0 || index === 1 || index === 2 || (index === 3 && this.userFeature.ALLOW_PLUGIN_CENTER)) {
        this.navIndex = index;
      } else {
        this.navShowController = setTimeout(() => {
          this.navIndex = index;
          this.navText = item.text;
          switch (index) {
            case 3:
              if (!this.userFeature.ALLOW_PLUGIN_CENTER) {
                this.curSubNav = this.headerStaticInfo.list.subnav_service;
              }
              break;
            case 4:
              if (!this.userFeature.ALLOW_PLUGIN_CENTER) {
                this.curSubNav = this.headerStaticInfo.list.subnav_doc;
              } else {
                this.curSubNav = this.headerStaticInfo.list.subnav_service;
              }
              break;
            case 5:
              this.curSubNav = this.headerStaticInfo.list.subnav_doc;
              break;
            default:
              this.curSubNav = [];
          }
        }, 500);
      }
    },
    open_login_dialog() {
      bus.$emit('show-login-modal');
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
        noteIndex = 3;
      }
      switch (noteIndex) {
        case 0:
          this.backgroundHidden = false;
          this.curpage = 0;
          break;
        case 1:
          this.backgroundHidden = false;
          this.curpage = 1;
          break;
        case 2:
          this.backgroundHidden = false;
          this.curpage = 2;
          break;
        case 3:
          this.backgroundHidden = false;
          this.curpage = 3;
          break;
        default:
          this.curpage = -1;
      }
    },
    userInfoSlide(n) {
      if (n) {
        this.userInfoShow = true;
      } else {
        this.userInfoShow = false;
      }
    },
    logout() {
      bkLogout.logout();
      window.location = `${window.GLOBAL_CONFIG.LOGIN_SERVICE_URL}/?c_url=${window.location.href}`;
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
  },
};
</script>

<style lang="scss" scoped>
    .header-search-result {
        width: 268px;
        background: #FFF;
        margin-top: 5px;

        .search-result-panel {
            box-shadow: 0px 1px 5px #e5e5e5;
            border: 1px solid #EEE;
            border-radius: 2px;
        }

        h3 {
            padding: 10px 15px;
        }

        .paas-search-trigger {
            position: relative;
            top: 5px;
            width: calc(100% - 10px);
            margin: 0 auto;
            line-height: 24px;
            border-radius: 2px;
            background: #F0F1F5;
            font-size: 12px;
            color: #979BA5;
            text-align: center;
            cursor: pointer;
            &:hover {
                color: #3a84ff;
            }
        }
    }

    .ps-header {
        position: fixed;
        left: 0px;
        top: 0px;
        width: 100%;
        z-index: 1001;
        min-width: 1440px;
        transition: all .5s;
        background: #182132;
        box-sizing: border-box;

        > * {
            box-sizing: border-box;
        }

        &::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 0;
            background-color: transparent;
            -webkit-transition: height .2s, background-color .2s;
            transition: height .2s, background-color .2s;
        }

        &:hover::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 50px;
            background: #191929;
            -webkit-transition-timing-function: cubic-bezier(0.2, 1, 0.3, 1);
            transition-timing-function: cubic-bezier(0.2, 1, 0.3, 1);
        }

        .ps-logo {
            float: left;
            width: 296px;
            position: relative;
            margin: 0 0 0 20px;
            padding: 10px 0;
            .logo-warp{
              display: flex;
              align-items: center;
              img {
                  display: inline-block;
                  vertical-align: middle;
                  height: 30px;
              }
              .logo-text{
                color: #EAEBF0;
                font-size: 16px;
                padding-left: 10px;
              }
            }

        }
    }

    .bg-hidden {
        background: transparent;
    }

    .bk-header-static {
        background: #191929;
        transition: all .5s;
    }

    .ps-header-visible {
        overflow: inherit;
        position: relative;
        z-index: 99;
        min-width: 1200px;
    }

    .ps-header a {
        color: #96A2B9;
    }

    .ps-header .active a {
        color: #ffffff;
    }

    .ps-nav {
        overflow: hidden;
        float: left;
    }

    .ps-nav li {
        float: left;
        position: relative;
        margin-right: 40px;
    }

    .ps-nav li> a {
        line-height: 36px;
        position: relative;
        padding: 7px 0;

        &.has-angle {
            padding: 7px 16px 7px 0;
        }
    }

    .ps-nav li>span {
        width: 0;
        height: 3px;
        background: #3976e4;
        position: absolute;
        left: 0;
        bottom: 0;
        transform-origin: 50% 50%;
        transition: all .3s;
    }

    .ps-nav li:hover>span,
    .ps-nav li.active>span {
        width: 100%;
    }

    .ps-nav li .paasng-icon.paasng-angle-down {
        position: absolute;
        right: 0;
        top: 21px;
        font-size: 10px;
        font-weight: bold;
        transform: scale(0.8);
    }

    .ps-head-right {
        position: relative;
        float: right;
        margin: 0;
        padding: 8px 10px;
        display: flex;
        align-items: center;
        color: #96A2B9;

        li {
            float: left;
            // margin: 0 10px;
        }
    }

    .ps-search {
        background: #252F43;
        overflow: hidden;
        border-radius: 2px;
        position: relative;

        input[type="text"] {
            cursor: text;
            width: 240px;
            height: 32px;
            padding: 0 48px 0 14px;
            line-height: 30px;
            background: none;
            float: left;
            color: #D3D9E4;
            border: none;
            z-index: 1;
            transition: all .5s;
            border-radius: 2px;

            &:focus {
                outline: none;
            }

            &::-webkit-input-placeholder {
                color: #D3D9E4;
            }
        }

        .ps-search-icon {
            position: absolute;
            right: 12px;
            top: 8px;
            padding-left: 8px;
            height: 16px;
            border: none;
            z-index: 2;
            border-left: 1px solid #979BA5;
            color: #D3D9E4;
            font-size: 16px;

            .close-cursor {
                cursor: pointer;
            }
        }
    }

    .ps-head-right .notice-button {
        width: 18px;
        height: 24px;
        display: inline-block;
        margin: 6px 0 0 8px;
        position: relative;
        background: url(/static/images/news-icon.png) no-repeat;
        transition: all .5s;
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
        transition: all .5s;
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
        transition: all .5s;
    }

    .hoverStatus2 {
        top: -1px;
        height: 406px !important;
        opacity: 1;
        visibility: visible;
        transition: all .5s;
    }

    .hoverStatus3 {
        top: -1px;
        height: 207px !important;
        opacity: 1;
        visibility: visible;
        transition: all .5s;
    }

    .ps-header-invisible.pl {
        padding-left: 512px;
    }

    .ps-header-invisible>dl {
        width: 139px;
        min-height: 400px;
        float: left;
        line-height: 32px;
        border-left: solid 1px #30303d;
        padding: 5px 0 62px 0;
    }
    .en-header-cls .ps-header-invisible>dl {
        width: 145px;
    }

    .ps-header-invisible>dl:last-child {
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
        color: #3A84FF;
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
        color: #96A2B9;
        font-size: 14px;
        line-height: 34px;
        position: relative;
        transition: all .5s;

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
        transition: all .3s;
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
                color: #3A84FF;
            }
        }
    }

    .user:after,
    .contact:after {
        content: "";
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
        color: #3A84FF;
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
        color: #96A2B9 !important;
        transition: all .0s !important;
        &:hover {
          color: #fff;
          cursor: pointer;
          background: rgba(255,255,255,0.10);
          border-radius: 100%;
          i {
              color: #fff !important;
          }
        }
        i {
            color: #96A2B9 !important;
        }
    }

</style>
<style lang="scss">
.top-bar-popover .tippy-backdrop {
    background: transparent !important;
}
.top-bar-popover .tippy-content {
    box-shadow:0 2px 6px 0 rgba(0,0,0,0.10) !important;
    border: 1px solid #DCDEE5;
    border-radius: 2px;
}
.top-bar-wrapper .header-mind{
    color:#768197;
    font-size:16px;
    position:relative;
    height:32px;
    width:32px;
    display:-webkit-box;
    display:-ms-flexbox;
    display:flex;
    -webkit-box-align:center;
    -ms-flex-align:center;
    align-items:center;
    -webkit-box-pack:center;
    -ms-flex-pack:center;
    justify-content:center;
    margin-right:8px
}
.top-bar-wrapper .header-mind.is-left{
    color:#96A2B9;
    line-height: 34px;
}
.top-bar-wrapper .header-mind.is-left:hover{
    color: #fff;
    background: rgba(255,255,255,0.10);
}
.top-bar-wrapper .header-mind-mark{
    position:absolute;
    right:8px;
    top:8px;
    height:7px;
    width:7px;
    border:1px solid #27334C;
    background-color:#EA3636;
    border-radius:100%
}
.top-bar-wrapper .header-mind-mark.is-left{
border-color:#F0F1F5;
}
.top-bar-wrapper .header-mind:hover{
    background:-webkit-gradient(linear,right top, left top,from(rgba(37,48,71,1)),to(rgba(38,50,71,1)));
    background:linear-gradient(270deg,rgba(37,48,71,1) 0%,rgba(38,50,71,1) 100%);
    border-radius:100%;
    cursor:pointer;
    color:#D3D9E4;
}
.top-bar-wrapper .header-mind .lang-icon{
    font-size:18px;
}
.top-bar-wrapper .header-mind .nav-lang-icon {
    transform: translateY(1px);
}
.top-bar-wrapper .header-help{
    color:#768197;
    font-size:16px;
    position:relative;
    height:32px;
    width:32px;
    display:-webkit-box;
    display:-ms-flexbox;
    display:flex;
    -webkit-box-align:center;
    -ms-flex-align:center;
    align-items:center;
    -webkit-box-pack:center;
    -ms-flex-pack:center;
    justify-content:center;
    margin-right:8px
}
.top-bar-wrapper .header-help.is-left{
    color:#96A2B9;
}
.top-bar-wrapper .header-help.is-left:hover{
    color: #fff;
    background: rgba(255,255,255,0.10);
}
.top-bar-wrapper .header-help:hover{
    background:-webkit-gradient(linear,right top, left top,from(rgba(37,48,71,1)),to(rgba(38,50,71,1)));
    background:linear-gradient(270deg,rgba(37,48,71,1) 0%,rgba(38,50,71,1) 100%);
    border-radius:100%;
    cursor:pointer;
    color:#D3D9E4;
}
.top-bar-wrapper .header-user{
    height:100%;
    display:-webkit-box;
    display:-ms-flexbox;
    display:flex;
    -webkit-box-align:center;
    -ms-flex-align:center;
    align-items:center;
    -webkit-box-pack:center;
    -ms-flex-pack:center;
    justify-content:center;
    color:#96A2B9;
    margin-left:8px;
}
.top-bar-wrapper .header-user .bk-icon{
    margin-left:5px;
    font-size:12px;
}
.top-bar-wrapper .header-user.is-left:hover{
    color: #fff;
}
.top-bar-wrapper .header-user:hover{
    cursor:pointer;
    color:#D3D9E4;
}
.monitor-navigation-admin{
    width:170px #96A2B9;
    display:-webkit-box;
    display:-ms-flexbox;
    display:flex;
    -webkit-box-orient:vertical;
    -webkit-box-direction:normal;
    -ms-flex-direction:column;
    flex-direction:column;
    background:#FFFFFF;
    padding:6px 0;
    margin:0;
    color:#63656E;
}
.monitor-navigation-admin .nav-item{
    -webkit-box-flex:0;
    -ms-flex:0 0 32px;
    flex:0 0 32px;
    display:-webkit-box;
    display:-ms-flexbox;
    display:flex;
    -webkit-box-align:center;
    -ms-flex-align:center;
    align-items:center;
    padding:0 16px;
    list-style:none;
    color: #63656E;
    a {
        color: #63656E;
    }
}
.monitor-navigation-admin .nav-item .lang-icon{
    font-size:18px;
    margin-right:6px;
}
.monitor-navigation-admin .nav-item:hover{
    cursor:pointer;
    background: #F5F7FA;
}
.tippy-popper .tippy-tooltip.navigation-message-theme{
    padding:0;
    border-radius:0;
    -webkit-box-shadow:none;
    box-shadow:none;
}
</style>
