<template>
  <div>
    <cloud-app-top-bar
      :title="$t('访问统计')"
      :active="active"
      :nav-list="curPanels"
      :module-id="curModuleId"
      :app-code="appCode"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
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
  name: 'cloudAppAnalysis',
  components: {
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      panels: [
        { name: 'web', label: this.$t('网站访问统计'), routeName: 'cloudAppWebAnalysis',  feature: 'PA_WEBSITE_ANALYTICS' },
        { name: 'log', label: this.$t('访问日志统计'), routeName: 'cloudAppLogAnalysis', feature: 'PA_INGRESS_ANALYTICS' },
        { name: 'event', label: this.$t('自定义事件统计'), routeName: 'cloudAppEventAnalysis', feature: 'PA_CUSTOM_EVENT_ANALYTICS' },
      ],
      active: 'web',
    };
  },
  computed: {
    curPanels () {
      return this.panels.filter(item => {
        const key = item.feature;
        // 接入 feature flag
        if (this.curAppInfo.feature.hasOwnProperty(key)) {
          return this.curAppInfo.feature[key];
        }
        return true;
      });
    }
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
      const curPanel = this.panels.find((item) => item.name === name);
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
