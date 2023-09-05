<template>
  <div class="right-main">
    <cloud-app-top-bar
      :title="$t('部署管理')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
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
  },
};
</script>
<style lang="scss" scoped>
.cloud-deploy-management{
  padding-top: 0px;
  margin: 0;
  margin-top: 0 !important;
}
</style>
