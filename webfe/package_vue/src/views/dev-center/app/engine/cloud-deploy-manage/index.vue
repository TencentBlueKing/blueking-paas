<template>
  <div class="right-main">
    <!-- 部署历史 -->
    <div class="ps-top-bar" v-if="isDeployHistory">
      <div class="top-title flex-row align-items-center">
        <i
          class="paasng-icon paasng-arrows-left icon-cls-back mr5"
          @click="goBack"
        />
        <h3>{{ $t('部署历史') }}</h3>
      </div>
    </div>
    <cloud-app-top-bar
      v-else
      :title="$t('部署管理')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      :right-title="$t('部署历史')"
      @change="handleTabChange"
      @right-config-click="toDeployHistory"
    />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-loading"
      :offset-top="30"
      class="app-container middle overview"
    >
      <!-- <component :is="curComponentsName" :key="curComponentsName"></component> -->
      <!-- 骨架屏 -->
      <router-view :key="routeIndex" :environment="active"></router-view>
    </paas-content-loader>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
// import stag from './comps/stag.vue';
// import prod from './comps/prod.vue';

export default {
  name: 'CloudDeployManagement',
  components: {
    cloudAppTopBar,
    // stag,
    // prod,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      active: 'stag',
      routeIndex: 0,
      panels: [
        { name: 'stag', label: '预发布环境', routeName: 'cloudAppDeployManageStag' },
        { name: 'prod', label: '生产环境', routeName: 'cloudAppDeployManageProd' },
      ],
    };
  },
  computed: {
    isDeployHistory() {
      return this.$route.meta.history;
    },
  },
  watch: {
    '$route'() {
      // eslint-disable-next-line no-plusplus
      this.routeIndex++;
    },
  },
  created() {
    setTimeout(() => {
      this.isLoading = false;
    }, 500);
  },
  methods: {
    handleTabChange(name) {
      this.active = name;
      const curEnv = this.panels.find(item => item.name === name);
      this.$router.push({
        name: curEnv.routeName,
      });
    },

    /** 部署历史 */
    toDeployHistory() {
      this.$router.push({
        name: 'cloudAppDeployHistory',
      });
    },

    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>
<style lang="scss" scoped>
.right-main {
  .top-title {
    padding-left: 24px;
    h3 {
      font-size: 16px;
      color: #313238;
      font-weight: 400;
      margin-left: 4px;
    }
    .icon-cls-back{
      color: #3A84FF;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
  }
}
.cloud-deploy-management{
  padding-top: 0px;
  margin: 0;
  margin-top: 0 !important;
}
</style>
