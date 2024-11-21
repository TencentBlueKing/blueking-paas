<template>
  <content-loader
    :style="{ transform: `scaleX(${contentWidth / baseWidth})`, 'margin-top': '-40px' }"
    :width="baseWidth"
    :height="600"
    :speed="loadingConf.speed"
    :primaryColor="loadingConf.primaryColor"
    :secondaryColor="loadingConf.secondaryColor"
  >
    <rect
      x="0"
      y="0"
      rx="1"
      ry="1"
      :width="baseWidth"
      height="32"
    />
    <rect
      x="0"
      y="42"
      rx="1"
      ry="1"
      :width="70"
      height="32"
    />
    <rect
      x="80"
      y="42"
      rx="1"
      ry="1"
      :width="60"
      height="32"
    />
    <rect
      x="165"
      y="42"
      rx="1"
      ry="1"
      :width="70"
      height="32"
    />
    <rect
      x="245"
      y="42"
      rx="1"
      ry="1"
      :width="60"
      height="32"
    />
    <rect
      x="325"
      y="42"
      rx="1"
      ry="1"
      :width="70"
      height="32"
    />
    <rect
      x="405"
      y="42"
      rx="1"
      ry="1"
      :width="60"
      height="32"
    />
    <rect
      x="0"
      y="84"
      rx="1"
      ry="1"
      :width="(baseWidth - 20) / 3"
      height="130"
    />
    <rect
      :x="(baseWidth - 20) / 3 + 10"
      y="84"
      rx="1"
      ry="1"
      :width="(baseWidth - 20) / 3"
      height="130"
    />
    <rect
      :x="2 * ((baseWidth - 20) / 3) + 20"
      y="84"
      rx="1"
      ry="1"
      :width="(baseWidth - 20) / 3"
      height="130"
    />
    <rect
      x="0"
      y="224"
      rx="1"
      ry="1"
      :width="(baseWidth - 10) / 2"
      height="220"
    />
    <rect
      :x="(baseWidth - 10) / 2 + 10"
      y="224"
      rx="1"
      ry="1"
      :width="(baseWidth - 10) / 2"
      height="220"
    />
    <rect
      x="0"
      y="454"
      rx="1"
      ry="1"
      :width="(baseWidth - 10) / 2"
      height="220"
    />
    <rect
      :x="(baseWidth - 10) / 2 + 10"
      y="454"
      rx="1"
      ry="1"
      :width="(baseWidth - 10) / 2"
      height="220"
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
