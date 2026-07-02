<template>
  <content-loader
    :width="baseWidth"
    :style="{ transform: `scaleX(${resolvedScale})` }"
    :height="height"
    :speed="loadingConf.speed"
    :primary-color="loadingConf.primaryColor"
    :secondary-color="loadingConf.secondaryColor"
  >
    <rect
      v-for="index in operationCount"
      :key="`operation-${index}`"
      :x="(index - 1) * (operationWidth + 20)"
      y="0"
      rx="2"
      ry="2"
      :width="operationWidth"
      height="28"
    />
    <rect
      :x="x"
      :y="resolvedTableTop"
      rx="2"
      ry="2"
      :width="tableWidth"
      :height="resolvedHeaderHeight"
    />
    <rect
      v-for="index in rows"
      :key="index"
      :x="x"
      :y="getRowY(index)"
      rx="1"
      ry="1"
      :width="tableWidth"
      :height="rowPlaceholderHeight"
    />
  </content-loader>
</template>

<script>
import { ContentLoader } from 'vue-content-loader';

const SIZE_MAP = {
  small: 32,
  medium: 42,
  large: 56,
};

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
    height: {
      type: Number,
      default: 520,
    },
    tableTop: {
      type: Number,
    },
    rows: {
      type: Number,
      default: 5,
    },
    size: {
      type: String,
      default: 'medium',
      validator: value => ['small', 'medium', 'large'].includes(value),
    },
    headerHeight: {
      type: Number,
      default: 32,
    },
    x: {
      type: Number,
      default: 0,
    },
    width: {
      type: Number,
    },
    rowOffset: {
      type: Number,
      default: 13,
    },
    rowStep: {
      type: Number,
    },
    rowPlaceholderHeight: {
      type: Number,
      default: 22,
    },
    rowYList: {
      type: Array,
      default: () => [],
    },
    operationCount: {
      type: Number,
      default: 0,
    },
    operationWidth: {
      type: Number,
      default: 140,
    },
    isTransform: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    loadingConf() {
      return this.$store.state.loadingConf;
    },
    resolvedSize() {
      return SIZE_MAP[this.size];
    },
    resolvedHeaderHeight() {
      return this.headerHeight || this.resolvedSize;
    },
    resolvedTableTop() {
      if (this.tableTop !== undefined) {
        return this.tableTop;
      }
      return this.operationCount > 0 ? 48 : 0;
    },
    resolvedRowStep() {
      return this.rowStep || this.resolvedSize;
    },
    tableWidth() {
      return this.width || this.baseWidth;
    },
    resolvedScale() {
      if (!this.isTransform) {
        return 1;
      }
      return Math.max(this.contentWidth / this.baseWidth, 1);
    },
  },
  methods: {
    getRowY(index) {
      if (this.rowYList[index - 1] !== undefined) {
        return this.rowYList[index - 1];
      }
      return this.resolvedTableTop + this.resolvedHeaderHeight + this.rowOffset + (index - 1) * this.resolvedRowStep;
    },
  },
};
</script>
