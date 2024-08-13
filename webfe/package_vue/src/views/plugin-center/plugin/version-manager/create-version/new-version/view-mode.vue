<template>
  <div class="view-mode-container">
    <slot />
  </div>
</template>

<script>
export default {
  name: 'ViewMode',
  props: {
    labelWidth: {
      type: String | Number,
      default: 120,
    },
  },
  mounted() {
    this.$el.style.setProperty('--custom-label-width', `${this.labelWidth}px`);
  },
  beforeDestroy() {
    this.$el.style.removeProperty('--custom-label-width');
  },
};
</script>

<style lang="scss" scoped>
.view-mode-container {
  .item {
    display: flex;
    min-height: 32px;
    line-height: 32px;
    margin-bottom: 6px;
    font-size: 12px;
    &:last-child {
      margin-bottom: 0px;
    }
    .label {
      width: var(--custom-label-width);
      text-align: right;
    }
    .value {
      margin-left: 8px;
      color: #313238;
    }
  }
}
</style>
