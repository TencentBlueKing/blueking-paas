<template>
  <div>
    <cloud-app-top-bar
      :title="$t('应用配置')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
      @right-config-click="toDeployHistory"
    />
    <div class="router-container">
      <router-view :key="routeIndex" :environment="active"></router-view>
    </div>
  </div>
</template>
<script>
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'AppConfigs',
  components: {
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'market',
      routeIndex: 0,
    };
  },
  computed: {
    isEngineEnabled() {
      return this.curAppInfo.web_config.engine_enabled;
    },
    panels() {
      let panels = [
        { name: 'market', label: this.$t('应用市场'), routeName: 'appMarket' },
        { name: 'storage', label: this.$t('持久存储'), routeName: 'appPersistentStorage' },
        { name: 'appMobileMarket', label: this.$t('应用市场 (移动端)'), routeName: 'appMobileMarket' },
        { name: 'member', label: this.$t('成员管理'), routeName: 'appMembers' },
        { name: 'info', label: this.$t('基本信息'), routeName: 'appBasicInfo' },
      ];
      // tencent、云原生、为开启引擎应用不展示应用市场 (移动端)
      if (this.curAppModule?.region !== 'ieod' || this.isCloudNativeApp || !this.isEngineEnabled) {
        panels = panels.filter(tab => tab.name !== 'appMobileMarket');
      }
      // 普通应用不支持
      if (!this.isCloudNativeApp) {
        panels = panels.filter(tab => tab.name !== 'storage');
      }
      return panels;
    },
  },
  watch: {
    $route: {
      handler(v) {
        this.active = v.meta.module;
      },
      immediate: true,
    },
  },
  methods: {
    handleTabChange(name) {
      this.active = name;
      const curEnv = this.panels.find(item => item.name === name) || this.panels[0];
      this.$router.push({
        name: curEnv.routeName,
        params: {
          id: this.curAppCode,
        },
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
</style>
