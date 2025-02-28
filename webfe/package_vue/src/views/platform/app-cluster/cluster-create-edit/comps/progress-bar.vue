<template>
  <div class="progress-bar-container card-style">
    <bk-steps
      line-type="solid"
      :steps="steps"
      :cur-step="curStep"
      ext-cls="custom-icon"
    ></bk-steps>
  </div>
</template>

<script>
export default {
  name: 'ProgressBar',
  props: {
    curStep: {
      type: Number,
    },
  },
  data() {
    return {
      steps: [
        { title: this.$t('选择集群'), icon: 1 },
        { title: this.$t('组件配置'), icon: 2 },
        { title: this.$t('组件安装'), icon: 3 },
      ],
    };
  },
};
</script>

<style lang="scss" scoped>
.progress-bar-container {
  margin-bottom: 16px;
  padding: 16px;
  display: flex;
  justify-content: center;
  .bk-steps {
    width: 66%;
    /deep/ .bk-step {
      .bk-step-number {
        background: #eaebf0;
        border: none;
        color: #4d4f56;
      }
      &.current .bk-step-number {
        background: #3a84ff;
        color: #fff;
      }
      &.done .bk-step-number {
        background: #e1ecff;
        color: #3a84ff;
      }
    }
  }
}
</style>
