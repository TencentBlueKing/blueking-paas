<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${contentWidth / baseWidth})` }"
    :height="350"
    :speed="loadingConf.speed"
    :primaryColor="loadingConf.primaryColor"
    :secondaryColor="loadingConf.secondaryColor"
  >
    <rect
      x="0"
      y="48"
      rx="2"
      ry="2"
      width="236"
      height="293"
    />
    <rect
      x="262"
      y="48"
      rx="2"
      ry="2"
      width="116"
      height="32"
    />
    <rect
      x="388"
      y="48"
      rx="2"
      ry="2"
      width="88"
      height="32"
    />
    <rect
      x="486"
      y="48"
      rx="2"
      ry="2"
      width="101"
      height="32"
    />
    <rect
      x="930"
      y="48"
      rx="2"
      ry="2"
      width="250"
      height="32"
    />
    <path
      d="M 262 97 h 918 v 42 H 262 z M 262 153 h 918 v 20 H 262 z M 262 195 h 918 v 20 H 262 z M 262 237 h 918 v 20 H 262 z M 262 279 h 918 v 20 H 262 z M 262 321 h 918 v 20 H 262 z"
    />
    <rect
      x="0"
      y="0"
      rx="1"
      ry="1"
      width="63"
      height="16"
    />
    <rect
      x="83"
      y="0"
      rx="1"
      ry="1"
      width="63"
      height="16"
    />
    <rect
      x="166"
      y="0"
      rx="1"
      ry="1"
      width="63"
      height="16"
    />
    <rect
      x="249"
      y="0"
      rx="1"
      ry="1"
      width="63"
      height="16"
    />
    <rect
      x="0"
      y="27"
      rx="1"
      ry="1"
      width="1180"
      height="2"
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
