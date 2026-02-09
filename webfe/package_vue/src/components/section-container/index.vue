<template>
  <div
    class="section-container"
    :class="containerClass"
  >
    <div class="section-header">
      <slot name="header">{{ title }}</slot>
    </div>
    <div class="section-content">
      <slot name="content">
        <slot></slot>
      </slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SectionContainer',
  props: {
    title: {
      type: String,
      default: '',
    },
    containerClass: {
      type: [String, Array, Object],
      default: '',
    },
  },
};
</script>

<style lang="scss" scoped>
.section-container {
  flex: 1;
  margin-right: 104px;

  &.flex-1 {
    flex: 1;
  }

  &.mr0 {
    margin-right: 0;
  }

  .plan-select-cls {
    background-color: #fff;
  }

  .section-header {
    height: 32px;
    line-height: 32px;
    padding: 0 16px;
    color: #313238;
    background-color: #f0f1f5;
  }

  .section-content {
    padding: 24px;
    background-color: #f5f7fa;

    i.paasng-info-line {
      color: #979ba5;
    }

    /deep/ .bk-form-item.is-error .PrefixSelect-cls {
      position: relative;
      z-index: 99;
    }

    /deep/ .details-row .value {
      padding-left: 10px;
    }
  }
}
</style>
