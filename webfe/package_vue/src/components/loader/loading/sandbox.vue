<template>
  <content-loader
    :width="baseWidth"
    :height="500"
    :speed="loadingConf.speed"
    :primaryColor="loadingConf.primaryColor"
    :secondaryColor="loadingConf.secondaryColor"
  >
    <rect
      x="0"
      y="0"
      rx="1"
      ry="1"
      :width="baseWidth"
      height="32"
    />
    <rect
      x="0"
      y="48"
      rx="1"
      ry="1"
      :width="baseWidth - 330"
      height="600"
    />
    <rect
      :x="baseWidth - 300"
      y="48"
      rx="1"
      ry="1"
      :width="350"
      height="600"
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
