<template>
  <div>
    <!-- 区分外链应用 -->
    <cloud-app-top-bar
      :title="$t('访问统计')"
      :active="active"
      :nav-list="curPanels"
      :module-id="curModuleId"
      :app-code="appCode"
      :cur-module="curAppModule"
      :module-list="isEngineEnabled ? curAppModuleList : []"
      @change="handleTabChange"
    />
    <div class="router-container">
      <router-view app-type="cloud_native"></router-view>
    </div>
  </div>
</template>

<script>
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'CloudAppAnalysis',
  components: {
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'web',
    };
  },
  computed: {
    isEngineEnabled() {
      return this.curAppInfo.web_config.engine_enabled;
    },
    panels() {
      if (this.isCloudNativeApp) {
        return [
          { name: 'web', label: this.$t('网站访问统计'), routeName: 'cloudAppWebAnalysis',  feature: 'PA_WEBSITE_ANALYTICS' },
          { name: 'log', label: this.$t('访问日志统计'), routeName: 'cloudAppLogAnalysis', feature: 'PA_INGRESS_ANALYTICS' },
          { name: 'event', label: this.$t('自定义事件统计'), routeName: 'cloudAppEventAnalysis', feature: 'PA_CUSTOM_EVENT_ANALYTICS' },
        ];
      }
      return [
        { name: 'web', label: this.$t('网站访问统计'), routeName: 'appWebAnalysis',  feature: 'PA_WEBSITE_ANALYTICS' },
        { name: 'log', label: this.$t('访问日志统计'), routeName: 'appLogAnalysis', feature: 'PA_INGRESS_ANALYTICS' },
        { name: 'event', label: this.$t('自定义事件统计'), routeName: 'appEventAnalysis', feature: 'PA_CUSTOM_EVENT_ANALYTICS' },
      ];
    },
    curPanels() {
      return this.panels.filter((item) => {
        const key = item.feature;
        // 接入 feature flag
        // eslint-disable-next-line no-prototype-builtins
        if (this.curAppInfo.feature.hasOwnProperty(key)) {
          return this.curAppInfo.feature[key];
        }
        return true;
      });
    },
  },
  watch: {
    $route: {
      handler(route) {
        this.active = route.meta.module;
      },
      immediate: true,
    },
  },
  methods: {
    handleTabChange(name) {
      this.active = name;
      const curPanel = this.panels.find(item => item.name === name);
      this.$router.push({
        name: curPanel.routeName,
        params: {
          id: this.curAppCode,
          moduleId: this.curAppModule.name,
        },
      });
    },
  },
};
</script>
