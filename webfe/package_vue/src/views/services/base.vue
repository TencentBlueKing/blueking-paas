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
import { mapState } from 'vuex';
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
      navCategories: [],
      navItems: [],
      groups: [{ devTools: this.$t('开发者工具') }, { serve: this.$t('服务') }],
    };
  },
  computed: {
    ...mapState(['userFeature']),
  },
  watch: {
    'userFeature.SMART_APP_BUILDER': {
      handler() {
        this.initNavData();
      },
    },
  },
  mounted() {
    this.initNavData();
    document.body.className = 'ps-service-detail';
  },
  beforeDestroy() {
    document.body.className = '';
  },
  methods: {
    initNavData() {
      const navData = JSON.parse(JSON.stringify(toolsNavigationData));
      const filteredNavData = navData.filter(
        (item) => item.name !== 'smartBuildTool' || this.userFeature?.SMART_APP_BUILDER !== false
      );
      const result = processNavData(filteredNavData);
      this.navCategories = result.navCategories;
      this.navItems = result.navItems;
    },
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
