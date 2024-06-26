<template>
  <div :key="routeIndex">
    <cloud-app-top-bar
      :title="$t('应用配置')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
      @right-config-click="toDeployHistory"
    />
    <div class="router-container">
      <router-view :environment="active"></router-view>
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
      isClusterPersistentStorageSupported: false,
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
      // 普通应用不支持 | feature判断
      if (!this.isCloudNativeApp || !this.curAppInfo.feature?.ENABLE_PERSISTENT_STORAGE || !this.isClusterPersistentStorageSupported) {
        panels = panels.filter(tab => tab.name !== 'storage');
      }
      return panels;
    },
  },
  watch: {
    $route: {
      handler(v) {
        if (v.meta.module === 'storage') {
          // 判断当前是否展示持久存储，无需展示默认选择第一项
          if (!this.curAppInfo.feature?.ENABLE_PERSISTENT_STORAGE && !this.isClusterPersistentStorageSupported) {
            this.handleTabChange('market');
          } else {
            this.active = v.meta.module;
          }
        } else {
          this.active = v.meta.module;
        }
      },
      immediate: true,
    },
    async '$route.params.id'() {
      await this.getClusterPersistentStorageFeature();
      this.routeIndex += 1;
      this.handleTabChange(this.active);
    },
  },
  created() {
    this.getClusterPersistentStorageFeature();
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

    // 获取集群特性
    async getClusterPersistentStorageFeature() {
      try {
        const res = await this.$store.dispatch('persistentStorage/getClusterPersistentStorageFeature', {
          appCode: this.appCode,
        });
        this.isClusterPersistentStorageSupported = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>
