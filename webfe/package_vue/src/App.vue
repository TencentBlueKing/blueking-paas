<template>
  <div
    id="app"
    :style="{
      '--app-notice-height': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT : 0}px`,
      '--app-content-pd': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 52 : 52}px`,
      'background-color': appBackgroundColor,
    }"
  >
    <!-- 通知中心 -->
    <notice-component
      v-if="isBkNotice"
      class="notice-cls"
      :api-url="apiUrl"
      @show-alert-change="showAlertChange"
    />
    <div class="paas-app-main-container flex-row flex-column flex-1">
      <paas-header />
      <div
        class="view-content-box"
        :class="{
          'hiden-footer-page': !showPaasFooter,
          'plugin-min-width': isPlugin,
          'sandbox-page': sandboxPage,
        }"
      >
        <router-view />
        <paas-footer v-if="showPaasFooter" />
      </div>
    </div>
  </div>
</template>

<script>
import { bus } from '@/common/bus';
import paasHeader from '@/components/paas-header';
import paasFooter from '@/components/paas-footer';
import NoticeComponent from '@blueking/notice-component-vue2';
import { showLoginModal as showLoginPopup } from '@blueking/login-modal';
import '@blueking/notice-component-vue2/dist/style.css';
import getPlatformConfig from '@/common/platform-config';

export default {
  components: {
    paasHeader,
    paasFooter,
    NoticeComponent,
  },
  data() {
    return {
      apiUrl: `${BACKEND_URL}/notice/announcements/`,
    };
  },
  computed: {
    isPlugin() {
      return this.$route.path.includes('/plugin-center');
    },
    isGray() {
      return ['myApplications', 'appLegacyMigration'].includes(this.$route.name);
    },
    isBkNotice() {
      return this.$store.state.platformFeature.BK_NOTICE;
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    isDefaultBackgroundColor() {
      return this.$route.meta?.isDefaultBackgroundColor;
    },
    appBackgroundColor() {
      const color = this.$route.meta?.appBackgroundColor || '#f5f7fa';
      return this.isDefaultBackgroundColor ? color : '';
    },
    sandboxPage() {
      return this.$route.meta?.sandboxPage;
    },
    showPaasFooter() {
      return this.$route.meta?.isFooterShown;
    },
  },
  watch: {
    isPlugin: {
      handler(isPlugin) {
        document.body.style.backgroundColor = isPlugin ? '#F5F6FA' : '';
      },
      immediate: true,
    },
  },
  created() {
    bus.$on('show-login-modal', () => {
      this.openLoginWindow();
    });
    // 获取平台通用配置
    getPlatformConfig(this);
  },
  methods: {
    // 公告列表change事件回调， isShow代表是否含有跑马灯类型公告
    async showAlertChange(isShow) {
      // 更新store数据
      const isShowNotice = isShow && this.isBkNotice;
      await this.$store.commit('updataNoticeStatus', isShowNotice);
    },
    // 打开登录窗口
    openLoginWindow() {
      const loginCallbackURL = `${window.location.origin}/static/login_success.html?is_ajax=1`;
      const loginUrl = `${window.GLOBAL_CONFIG.LOGIN_SERVICE_URL}/plain/?size=big&app_code=1&c_url=${loginCallbackURL}`;

      showLoginPopup({ loginUrl });
    },
  },
};
</script>

<style lang="scss">
@import './assets/css/patch.scss';
@import './assets/css/ps-style.scss';
@import './assets/css/custom-component-styles.scss';
@import '~@/assets/css/mixins/dashed.scss';
@import '~@/assets/css/mixins/ellipsis.scss';
#app {
  height: 100%;
  display: flex;
  flex-direction: column;
  .view-content-box {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    &:not(.hiden-footer-page) {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    // 沙箱环境页面
    &.sandbox-page {
      height: 100%;
    } 
  }
  .paas-app-main-container {
    min-height: 0;
  }
}

.notice-cls {
  position: fixed;
  top: 0px;
  left: 0px;
  height: 40px;
  width: 100%;
  z-index: 1001;
}

.gray-bg {
  background: #fafbfd;
}

.notice {
  position: fixed;
  left: 0px;
  top: 0px;
  width: 100%;
  z-index: 1001;
  text-align: center;
  line-height: 32px;
  background-color: #ff9600;
  color: #fff;
  max-height: 32px;
}

.plugin-min-width {
  min-width: 1366px;
}

.table-header-tips-cls {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.success-dividing-line {
  position: relative;
  top: -1px;
  margin: 0 5px;
}
</style>
