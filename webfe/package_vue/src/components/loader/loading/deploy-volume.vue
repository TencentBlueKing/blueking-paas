<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="571"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect x="0" y="30" rx="2" ry="2" width="120" height="30" />
    <rect x="0" y="80" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="125" rx="2" ry="2" :width="baseWidth" height="30" />
    <rect x="0" y="160" rx="2" ry="2" :width="baseWidth" height="30" />
    <rect x="0" y="195" rx="2" ry="2" :width="baseWidth" height="30" />
    <rect x="0" y="230" rx="2" ry="2" :width="baseWidth" height="30" />
    <rect x="0" y="265" rx="2" ry="2" :width="baseWidth" height="30" />
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
