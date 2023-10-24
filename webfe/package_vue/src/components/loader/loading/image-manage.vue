<template>
  <content-loader
    :width="baseWidth"
    :style="{ 'transform': `scaleX(${contentWidth / baseWidth})` }"
    :height="407"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor">
    <rect x="20" y="19" rx="2" ry="2" width="120" height="32" />
    <rect x="940" y="19" rx="2" ry="2" width="240" height="32" />
    <rect x="20" y="67" rx="2" ry="2" :width="baseWidth" height="42" />
    <rect x="20" y="122" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="20" y="163" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="20" y="204" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="20" y="245" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="20" y="286" rx="1" ry="1" :width="baseWidth" height="20" />
    <rect x="20" y="327" rx="1" ry="1" :width="baseWidth" height="20" />
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
