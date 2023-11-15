<template>
  <content-loader
    :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
    :width="baseWidth"
    :height="360"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor">
    <rect x="0" y="0" rx="2" ry="2" :width="150" height="30" />
    <rect x="180" y="0" rx="2" ry="2" :width="100" height="30" />
    <rect x="0" y="50" rx="2" ry="2" :width="baseWidth" height="62" />
    <rect x="0" y="134" rx="2" ry="2" :width="baseWidth" height="62" />
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

