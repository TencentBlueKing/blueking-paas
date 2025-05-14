<template>
  <div class="plugin-false-positive-list">
    <paas-plugin-title />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="roles-loading"
      :offset-top="20"
      class="app-container overview-middle ignored-container"
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
      isLoading: true,
    };
  },
  computed: {
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    iframeUrl() {
      return this.curPluginInfo.overview_page?.ignored_url;
    },
  },
  mounted() {
    setTimeout(() => {
      this.isLoading = false;
    }, 1000);
  },
};
</script>

<style lang="scss" scoped>
.plugin-false-positive-list {
  height: 100%;
  .ignored-container {
    height: 100%;
  }
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
