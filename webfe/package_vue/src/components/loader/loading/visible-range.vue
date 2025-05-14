<template>
  <content-loader
    :width="baseWidth"
    :style="{ 'transform': `scaleX(${isTransform ? contentWidth / baseWidth : 1})` }"
    :height="350"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor">
    <rect x="50" y="0" rx="2" ry="2" width="150" height="42" />
    <rect x="230" y="0" rx="2" ry="2" :width="baseWidth - 200" height="42" />
    <rect x="50" y="72" rx="2" ry="2" width="150" height="42" />
    <rect x="230" y="72" rx="2" ry="2" width="240" height="42" />
    <rect x="230" y="142" rx="2" ry="2" width="240" height="60" />
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
    isTransform: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    loadingConf() {
      return this.$store.state.loadingConf;
    },
  },
};
</script>
