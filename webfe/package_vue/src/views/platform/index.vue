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
        @tab-change="handleTabChange"
      >
        <template
          v-if="isSubTitle"
          slot="extra"
        >
          <span class="sub-title">
            <span class="line"></span>
            <span>{{ $route.meta.subTitle }}：{{ $route.query?.id }}</span>
          </span>
        </template>
      </TopBar>
      <div class="content-area">
        <router-view
          :tab-active="active"
          :key="routeIndex"
        />
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
      groups: [
        { platform: this.$t('服务接入') },
        { operations: this.$t('运营管理') },
        { config: this.$t('配置管理') },
        { user: this.$t('用户管理') },
      ],
      active: '',
      routeIndex: 0,
    };
  },
  computed: {
    title() {
      const { name, path, params } = this.$route;
      if (name === 'clusterCreateEdit') {
        return path.endsWith('/add') ? this.$t('添加集群') : this.$t('编辑集群');
      }
      if (name === 'platformAppDetails') {
        return `${this.$t('应用详情')}: ${params.code}`;
      }
      return this.$route.meta.title;
    },
    isSubTitle() {
      const { name, path, meta } = this.$route;
      return meta?.subTitle && name === 'clusterCreateEdit' && path.endsWith('/edit');
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
    panels(newValue) {
      if (newValue?.length) {
        this.setDefaultTabActive();
      }
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
    checkIfEndsWithAddOrEdit(url) {
      return url.endsWith('/add') || url.endsWith('/edit');
    },
    handleTabChange(active) {
      const { path, query } = this.$route;
      let newQuery = {};
      if (this.checkIfEndsWithAddOrEdit(path)) {
        newQuery = { ...query };
      } else {
        newQuery = {
          ...query,
          ...(active === 'list' && query),
          ...(active && { active }),
        };
      }
      this.$router.push({
        path,
        query: newQuery,
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
    z-index: 999;
  }
  .right-content {
    overflow: auto;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    height: 100%;
    background: #f5f7fa;
    .content-area {
      flex: 1;
      min-height: 0;
    }
    .sub-title {
      display: flex;
      align-items: center;
      font-size: 14px;
      color: #979ba5;
      .line {
        display: inline-block;
        width: 1px;
        height: 14px;
        background-color: #dcdee5;
        margin: 0 8px;
      }
    }
  }
}
</style>
<style lang="scss">
.pt-json-editor-custom-cls {
  .jse-main .jse-message.jse-error {
    display: none;
  }
  // 隐藏模式切换
  .jse-menu {
    button.jse-group-button,
    .jse-separator {
      display: none;
    }
  }
}
.platform-content {
  .border-tag,
  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    font-size: 12px;
    color: #4d4f56;
    padding: 0 8px;
    border-radius: 2px;
  }
  .tag {
    background: #f0f1f5;
    &.yes {
      background: #daf6e5;
      color: #299e56;
    }
  }
  .border-tag {
    background: #fafbfd;
    border: 1px solid #dcdee5;
  }
}
</style>
