<template>
  <div class="metrics-data-item">
    <p class="f28 count">{{ value }}</p>
    <p class="f12">
      <span>{{ text }}</span>
      <i
        v-if="tip"
        v-bk-tooltips="tip"
        class="paasng-icon paasng-exclamation-circle"
      />
    </p>
  </div>
</template>

<script>
export default {
  props: {
    value: {
      type: [String, Number],
      default: '--',
    },
    text: {
      type: String,
      required: true,
    },
    tip: {
      type: String,
      default: '',
    },
  },
};
</script>

<style lang="scss" scoped>
.metrics-data-item {
  min-height: 76px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding-left: 24px;
  background: #f5f7fa;
  border-radius: 2px;
  .count {
    color: #313238;
    line-height: 32px;
  }
  i {
    color: #979ba5;
  }
}
</style>
