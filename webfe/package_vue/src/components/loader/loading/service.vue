<template>
  <content-loader
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :width="baseWidth"
    :height="200"
    :speed="loadingConf.speed"
    :primaryColor="loadingConf.primaryColor"
    :secondaryColor="loadingConf.secondaryColor"
  >
    <rect
      x="0"
      y="0"
      rx="2"
      ry="2"
      width="286"
      height="168"
    />
    <rect
      x="298"
      y="0"
      rx="2"
      ry="2"
      width="286"
      height="168"
    />
    <rect
      x="596"
      y="0"
      rx="2"
      ry="2"
      width="286"
      height="168"
    />
    <rect
      x="894"
      y="0"
      rx="2"
      ry="2"
      width="286"
      height="168"
    />
  </content-loader>
</template>
<script>
import { ContentLoader } from 'vue-content-loader';
export default {
  components: {
    ContentLoader,
  },
  props: {
    baseWidth: {
      type: Number,
      default: 1180,
    },
    contentWidth: {
      type: Number,
      default: 1180,
    },
  },
  computed: {
    loadingConf() {
      return this.$store.state.loadingConf;
    },
  },
};
</script>
