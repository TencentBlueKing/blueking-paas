<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="328"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect :x="tableX" y="48" rx="2" ry="2" :width="tableWidth" height="42" />
    <rect :x="tableX" y="103" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect :x="tableX" y="144" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect :x="tableX" y="185" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect :x="tableX" y="226" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect :x="tableX" y="267" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect :x="tableX" y="308" rx="1" ry="1" :width="tableWidth" height="20" />
    <rect x="0" y="0" rx="2" ry="2" width="238" height="328" />
    <rect x="263" y="0" rx="2" ry="2" width="116" height="32" />
    <rect x="389" y="0" rx="2" ry="2" width="88" height="32" />
    <rect x="487" y="0" rx="2" ry="2" width="100" height="32" />
    <rect :x="rightOperationX" y="0" rx="2" ry="2" width="238" height="32" />
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
    tableX() {
      return 263;
    },
    tableWidth() {
      return this.baseWidth - this.tableX;
    },
    rightOperationX() {
      return this.baseWidth - 249;
    },
  },
};
</script>
