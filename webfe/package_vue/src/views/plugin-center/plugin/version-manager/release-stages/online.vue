<template>
  <div class="plugin-container">
    <div
      id="release-box"
      class="release-warp"
    >
      <div class="successful-container">
        <i class="bk-icon icon-check-1 icon-finish success-cls" />
        <h3 class="title">
          {{ $t('插件已发布成功') }}
        </h3>
        <span
          class="tips-link mr10"
          @click="handleJumpToUseLink"
        >
          {{ $t('去使用') }}
        </span>
        <span
          class="tips-link"
          @click="goVersionManager"
        >
          {{ $t('返回插件版本列表') }}
        </span>
      </div>
    </div>
  </div>
</template>
<script>
import stageBaseMixin from './stage-base-mixin';

export default {
  mixins: [stageBaseMixin],
  props: {
    stageData: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      winHeight: 300,
    };
  },
  methods: {
    goVersionManager() {
      this.$router.push({
        name: 'pluginVersionManager',
      });
    },
    handleJumpToUseLink() {
      const url = this.stageData.detail?.link;
      window.open(url, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
  .successful-container {
    text-align: center;
    padding: 24px 0;
    .success-cls {
      font-size: 50px;
      line-height: 50px;
      border-radius: 50%;
      color: #fff;
      background-color: #2dcb56;
    }
    .title {
      font-size: 20px;
      font-weight: 400;
      color: #313238;
      line-height: 28px;
      margin: 20px 0 12px;
    }
    .tips-link {
      font-size: 14px;
      color: #3A84FF;
      line-height: 22px;
      cursor: pointer;
    }
  }
</style>
