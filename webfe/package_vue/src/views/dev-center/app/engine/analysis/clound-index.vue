<template>
  <div>
    <cloud-app-top-bar
      :title="$t('访问统计')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
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
        { name: 'web', label: this.$t('网站访问统计'), routeName: 'cloudAppWebAnalysis' },
        { name: 'log', label: this.$t('访问日志统计'), routeName: 'cloudAppLogAnalysis' },
        { name: 'event', label: this.$t('自定义事件统计'), routeName: 'cloudAppEventAnalysis' },
      ],
      active: 'web',
    };
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
        },
      });
    },
  },
};
</script>
