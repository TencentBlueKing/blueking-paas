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
  data: function () {
    return {
      winHeight: 300
    };
  },
  methods: {
    goVersionManager () {
      this.$router.push({
          name: 'pluginVersionManager'
      });
    }
  }
};
</script>
