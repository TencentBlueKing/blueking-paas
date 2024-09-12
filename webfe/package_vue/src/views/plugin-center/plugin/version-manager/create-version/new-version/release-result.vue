<template>
  <section class="iframe-container" :style="{ height: iframeHeight + 'px' }">
    <iframe
      id="iframe-embed"
      :src="url"
      scrolling="no"
      frameborder="0"
    />
  </section>
</template>

<script>

export default {
  name: 'ReleaseResult',
  props: {
    url: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      iframeHeight: 100,
    };
  },
  created() {
    window.addEventListener('message', this.messageEvent);
  },
  beforeDestroy() {
    window.removeEventListener('message', this.messageEvent);
  },
  methods: {
    messageEvent(event) {
      if (!event.data || event.data?.type !== 'gray-result-height') return;
      this.iframeHeight = event.data.data;
    },
  },
};
</script>

<style lang="scss" scoped>
.iframe-container {
  margin-top: 16px;
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
</style>
