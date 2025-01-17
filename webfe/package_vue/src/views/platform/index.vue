<template lang="html">
  <div class="platform-content">
    <div class="left-navigation">
      <paasNav
        :nav-categories="navCategories"
        :nav-items="navItems"
        :groups="groups"
      />
    </div>
    <div class="right-content">
      <TopBar
        :title="title"
        :tab-panels="panels"
        :key="routeIndex"
        @tab-change="handleTabChange"
      ></TopBar>
      <div class="content-area">
        <router-view :tab-active="active" />
      </div>
    </div>
  </div>
</template>

<script>
import paasNav from '@/components/paasNav';
import { processNavData } from '@/common/utils';
import { bus } from '@/common/bus';
import platformNavigationData from '@/json/platform-navigation-data';
import TopBar from './comps/top-bar.vue';

export default {
  components: {
    TopBar,
    paasNav,
  },
  data() {
    return {
      minHeight: 700,
      navCategories: [],
      navItems: [],
      groups: [{ platform: this.$t('服务接入') }],
      active: '',
      routeIndex: 0,
    };
  },
  computed: {
    title() {
      return this.$route.meta.title;
    },
    panels() {
      return this.$route.meta?.panels || [];
    },
    routeTabActive() {
      return this.$route.query.active;
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
  },
  watch: {
    $route() {
      this.routeIndex += 1;
    },
  },
  created() {
    bus.$on('tool-table-change', (active) => {
      this.handleTabChange(active);
    });
    this.setDefaultTabActive();
    // 组件销毁前
    this.$once('hook:beforeDestroy', () => {
      bus.$off('tool-table-change');
    });
  },
  mounted() {
    const { navCategories = [], navItems = [] } = processNavData(platformNavigationData);
    this.navCategories = navCategories;
    this.navItems = navItems;
    const HEADER_HEIGHT = 52;
    // 通知中心高度
    const NOTICE_HEIGHT = this.isShowNotice ? this.GLOBAL.NOTICE_HEIGHT : 0;
    const winHeight = window.innerHeight;
    const contentHeight = winHeight - HEADER_HEIGHT - NOTICE_HEIGHT;
    if (contentHeight > this.minHeight) {
      this.minHeight = contentHeight;
    }
  },
  methods: {
    setDefaultTabActive() {
      const defaultActive = this.panels[0]?.name || '';
      this.active = this.routeTabActive || defaultActive;
      this.handleTabChange(this.active);
    },
    handleTabChange(active) {
      this.$router.push({
        path: this.$route.path,
        query: {
          active,
        },
      });
      this.active = active;
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-content {
  display: flex;
  margin-top: var(--app-content-pd);
  height: calc(100vh - var(--app-content-pd));
  .left-navigation {
    flex-shrink: 0;
    width: 240px;
    background: #fff;
    border-right: 1px solid rgb(220, 222, 229);
    height: 100%;
  }
  .right-content {
    flex: 1;
    min-width: 0;
    height: 100%;
    background: #f5f7fa;
    // .content-area {
    //   overflow: auto;
    //   height: calc(100% - 52px);
    // }
  }
}
</style>
