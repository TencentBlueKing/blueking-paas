<template>
  <div :class="['usage-guide-wrapper', { 'not-cloud-native-app': !isCloudNative }]">
    <!-- 设置相对高度防止出现双重滚动条 -->
    <div
      class="usage-guide-content"
      :class="isCloudNative ? 'cloud-guide-height' : 'default-guide-height'"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <div
        id="markdown"
        class="data-store-use"
      >
        <div
          class="markdown-body"
          v-dompurify-html="data"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InstanceUsageGuide',
  props: {
    data: {
      type: String,
    },
    isCloudNative: {
      type: Boolean,
      default: false,
    },
    isLoading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
    };
  },
};
</script>

<style lang="scss" scoped>
.usage-guide-wrapper {
  position: relative;
  height: 100%;
  background: #fff;
  &.not-cloud-native-app {
    .usage-guide-content {
      padding: 24px 24px 80px;
    }
  }
  &.isExpand {
    display: none;
  }
}

.usage-guide-content {
  width: 100%;
  height: 100%;
  background: #ffffff;
  overflow-y: auto;
  box-shadow: 0 2px 4px 0 #1919290d;
  padding-bottom: 50px;
  box-shadow: none;
  &.cloud-guide-height {
    height: calc(100vh - 158px);
  }
  &.default-guide-height {
    height: calc(100vh - 105px);
  }
}
.markdown-body {
  font-size: 12px;
}
</style>
