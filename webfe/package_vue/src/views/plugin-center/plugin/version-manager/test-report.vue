<template>
  <div class="plugin-test-report">
    <paas-plugin-title />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="summary-plugin-loading"
      :offset-top="20"
      class="app-container overview-middle test-container"
    >
      <section class="iframe-container">
        <iframe
          id="iframe-embed"
          :src="iframeUrl"
          scrolling="no"
          frameborder="0"
        />
      </section>
    </paas-content-loader>
  </div>
</template>

<script>
import paasPluginTitle from '@/components/pass-plugin-title';
export default {
  name: 'PluginTestReport',
  components: {
    paasPluginTitle,
  },
  data() {
    return {
      isLoading: false,
    };
  },
  computed: {
    iframeUrl() {
      return this.$route.query.url;
    },
  },
};
</script>

<style lang="scss" scoped>
.test-container {
  height: 100%;
}
.plugin-test-report {
  height: 100%;
  .iframe-container {
    width: 100%;
    height: 100%;
    iframe#iframe-embed {
      width: 100%;
      height: 100%;
      /* resize seems to inherit in at least Firefox */
      -webkit-resize: none;
      -moz-resize: none;
      resize: none;
    }
  }
}
</style>
