<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="571"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect x="0" y="0" rx="2" ry="2" width="80" height="28" />
    <rect x="100" y="0" rx="2" ry="2" width="80" height="28" />
    <rect x="0" y="48" rx="2" ry="2" :width="baseWidth" height="28" />
    <rect x="0" y="89" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="0" y="122" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="0" y="155" rx="1" ry="1" :width="baseWidth" height="20" />
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
