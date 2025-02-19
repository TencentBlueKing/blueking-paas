<template>
  <div
    class="details-row"
    :style="{ alignItems: align }"
  >
    <div
      class="label"
      :style="{ width: labelWidth + 'px' }"
    >
      <slot name="label">{{ label }}</slot>
    </div>
    <div
      :class="['value', { full: isFull }]"
      v-bk-overflow-tips
    >
      <slot name="value">{{ value ?? '--' }}</slot>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    label: {
      type: String,
      default: '',
    },
    value: {
      type: [String, Number],
      default: '',
    },
    labelWidth: {
      type: String | Number,
      default: 120,
    },
    align: {
      type: String,
      default: 'center',
    },
    isFull: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {};
  },
};
</script>

<style lang="scss" scoped>
.details-row {
  display: flex;
  .label {
    flex-shrink: 0;
    font-size: 12px;
    color: #4d4f56;
    text-align: right;
    line-height: 32px;
  }
  .value {
    font-size: 12px;
    color: #313238;
    line-height: 32px;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    &.full {
      flex: 1;
    }
  }
}
</style>
