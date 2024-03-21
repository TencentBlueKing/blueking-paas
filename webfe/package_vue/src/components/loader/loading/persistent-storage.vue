<template>
  <content-loader
    :width="baseWidth"
    :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
    :height="500"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect x="0" y="0" rx="1" ry="1" width="600" height="32" />
    <rect x="0" y="48" rx="1" ry="1" :width="baseWidth" height="65" />
    <rect x="0" y="132" rx="1" ry="1" :width="baseWidth" height="65" />
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
