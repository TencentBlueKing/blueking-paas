<template lang="html">
  <div class="overview-content">
    <!-- 工具页面 -->
    <div class="overview-main">
      <div class="overview-fleft">
        <paasNav
          :nav-categories="navCategories"
          :nav-items="navItems"
          :groups="groups"
        />
      </div>
      <div class="overview-fright">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script>
import paasNav from '@/components/paasNav';
import { processNavData } from '@/common/utils';
import { psServiceNavInfo } from '@/mixins/ps-static-mixin';
import toolsNavigationData from '@/json/tools-navigation-data';

export default {
  components: {
    paasNav,
  },
  mixins: [psServiceNavInfo],
  data() {
    return {
      minHeight: 700,
      navCategories: [],
      navItems: [],
      groups: [{ devTools: this.$t('开发者工具') }, { serve: this.$t('服务') }],
    };
  },
  computed: {
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
  },
  mounted() {
    const result = processNavData(toolsNavigationData);
    this.navCategories = result.navCategories;
    this.navItems = result.navItems;

    const HEADER_HEIGHT = 50;
    const FOOTER_HEIGHT = 0;
    // 通知中心高度
    const NOTICE_HEIGHT = this.isShowNotice ? this.GLOBAL.NOTICE_HEIGHT : 0;
    const winHeight = window.innerHeight;
    const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT - NOTICE_HEIGHT;
    if (contentHeight > this.minHeight) {
      this.minHeight = contentHeight;
    }
    document.body.className = 'ps-service-detail';
  },

  beforeDestroy() {
    document.body.className = '';
  },
};
</script>

<style lang="scss" scoped>
.overview-content {
  height: 100%;
  .overview-main {
    height: 100%;
    min-height: 0;
    .overview-fright {
      overflow: auto;
      .right-main {
        height: auto;
      }
    }
  }
}

.service-title {
  line-height: 50px;
}

.service-title .overview-title-pic {
  margin: 14px 14px 10px 20px;
  height: auto;
}
</style>
