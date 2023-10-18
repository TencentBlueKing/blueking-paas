<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="765"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect x="121" y="141" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="193" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="255" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="307" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="359" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="583" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="670" rx="2" ry="2" width="740" height="32" />
    <rect x="121" y="627" rx="1" ry="1" width="410" height="16" />
    <rect x="121" y="732" rx="2" ry="2" width="69" height="32" />
    <rect x="121" y="411" rx="2" ry="2" width="740" height="90" />
    <rect x="325" y="193" rx="2" ry="2" width="200" height="32" />
    <rect x="121" y="97" rx="1" ry="1" width="330" height="16" />
    <rect x="0" y="52" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="149" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="201" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="263" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="315" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="367" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="590" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="419" rx="1" ry="1" width="90" height="16" />
    <rect x="0" y="678" rx="1" ry="1" width="90" height="16" />
    <rect x="121" y="49" rx="2" ry="2" width="740" height="32" />
    <rect x="0" y="0" rx="1" ry="1" width="68" height="24" />
    <rect x="80" y="0" rx="1" ry="1" width="68" height="24" />
    <rect x="0" y="540" rx="1" ry="1" width="58" height="20" />
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
