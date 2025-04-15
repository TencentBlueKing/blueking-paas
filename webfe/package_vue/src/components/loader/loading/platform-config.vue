<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="440"
    :speed="loadingConf.speed"
    :primaryColor="loadingConf.primaryColor"
    :secondaryColor="loadingConf.secondaryColor"
  >
    <!-- 顶部筛选栏 -->
    <rect
      x="0"
      y="20"
      rx="4"
      ry="4"
      width="80"
      height="32"
    />
    <rect
      x="90"
      y="20"
      rx="4"
      ry="4"
      width="100"
      height="32"
    />
    <rect
      x="200"
      y="20"
      rx="4"
      ry="4"
      width="100"
      height="32"
    />
    <rect
      x="310"
      y="20"
      rx="4"
      ry="4"
      width="300"
      height="32"
    />
    <!-- 表格内容-->
    <rect
      x="0"
      y="68"
      width="100%"
      height="42"
    />
    <rect
      x="0"
      y="118"
      width="100%"
      height="42"
    />
    <rect
      x="0"
      y="168"
      width="100%"
      height="42"
    />
    <rect
      x="0"
      y="218"
      width="100%"
      height="42"
    />
    <rect
      x="0"
      y="268"
      width="100%"
      height="42"
    />
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
