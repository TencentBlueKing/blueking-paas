<template>
  <div
    :class="['usage-guide-wrapper', { 'not-cloud-native-app': !isCloudNative }]"
    :style="{
      '--default-height': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 102 : 102}px`,
      '--cloud-height': `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 136 : 136}px`,
      'width': `${isExpand ? '400px' : 0}`,
    }"
  >
    <div
      :class="['usage-guide-content', { 'not-cloud-native-app': !isCloudNative }, { hide: !isExpand }]"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <div
        id="markdown"
        class="data-store-use"
      >
        <div
          class="markdown-body"
          v-html="data"
        />
      </div>
    </div>
    <ul class="ellipsis">
      <li
        v-for="i in 4"
        :key="i"
      ></li>
    </ul>
    <div
      :class="['floating-button', { expand: isExpand }]"
      @click="isExpand = !isExpand"
    >
      <!-- 需要处理英文情况 -->
      <span :class="{ 'vertical-rl': localLanguage === 'en' }">{{ $t('使用指南') }}</span>
      <i class="paasng-icon paasng-angle-line-up"></i>
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
      isExpand: true,
    };
  },
  computed: {
    // 是否显示通知中心
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
};
</script>

<style lang="scss" scoped>
.usage-guide-wrapper {
  position: relative;
  &.not-cloud-native-app {
    .usage-guide-content {
      padding: 24px 24px 80px;
    }
    .floating-button,
    .ellipsis {
      top: calc(50% - 24px);
    }
  }
}

.usage-guide-content {
  position: absolute !important;
  top: 0px;
  right: 0;
  width: 400px;
  // 减去通知中心的高度
  height: 100%;
  background: #ffffff;
  overflow-y: auto;
  box-shadow: 0 2px 4px 0 #1919290d;
  padding-bottom: 50px;

  .hide {
    display: none;
  }
}
.ellipsis {
  position: absolute;
  left: 8px;
  top: calc(50% - 34px);
  transform: translateY(-50%);
  width: 2px;
  li {
    width: 2px;
    height: 2px;
    background: #63656e;
    margin-bottom: 2px;
  }
}
.floating-button {
  width: 24px;
  position: absolute;
  padding: 11px 0;
  text-align: center;
  font-size: 12px;
  color: #63656e;
  line-height: 13px;
  left: -24px;
  top: calc(50% - 34px);
  transform: translateY(-50%);
  background: #fafbfd;
  border: 1px solid #dcdee5;
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  &.expand {
    i {
      transform: rotateZ(90deg);
    }
  }
  i {
    margin-top: 5px;
    color: #979ba5;
    transform: rotateZ(-90deg);
  }
  &:hover {
    color: #3A84FF;
    i {
      color: #3A84FF;
    }
  }
  .vertical-rl {
    writing-mode: vertical-rl;
  }
}
</style>
