<template>
  <content-loader
    :width="baseWidth"
    :height="657"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor">
    <rect x="0" y="58" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="328" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="100" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="370" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="412" rx="2" ry="2" :width="baseWidth" height="40" />
    <rect x="0" y="454" rx="2" ry="2" :width="baseWidth" height="150" />
    <rect x="1" y="24" rx="1" ry="1" width="340" height="16" />
    <rect x="1" y="294" rx="1" ry="1" width="340" height="16" />
    <rect x="1" y="270" rx="1" ry="1" width="100" height="20" />
    <rect x="1" y="0" rx="1" ry="1" width="100" height="20" />
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
