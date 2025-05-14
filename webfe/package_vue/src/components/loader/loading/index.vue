<template>
  <content-loader
    :width="baseWidth"
    :height="850"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor">
    <rect x="0" y="9" rx="1" ry="1" width="180" height="32" />
    <rect :x="baseWidth - 100" y="9" rx="1" ry="1" width="100" height="32" />
    <rect :x="baseWidth - 258" y="9" rx="1" ry="1" width="140" height="32" />
    <rect x="0" y="55" rx="2" ry="2" :width="baseWidth / 2" height="200" />
    <rect :x="baseWidth / 2 + 20" y="55" rx="2" ry="2" :width="baseWidth / 2" height="200" />
    <rect x="0" y="280" rx="1" ry="1" width="140" height="32" />
    <rect x="0" y="330" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="370" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="410" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="450" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="490" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="550" rx="1" ry="1" width="140" height="32" />
    <rect x="0" y="590" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="630" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="670" rx="1" ry="1" :width="baseWidth" height="32" />
    <rect x="0" y="710" rx="1" ry="1" :width="baseWidth" height="32" />
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
