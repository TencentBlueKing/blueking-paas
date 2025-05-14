<template>
  <div class="key-value-row">
    <div
      class="custom-key"
      :style="{ width: `${labelWidth}px` }"
    >
      <slot name="key"></slot>
    </div>
    <div class="custom-value">
      <slot name="value"></slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'KeyValueRow',
  props: {
    labelWidth: {
      type: [Number, String],
      default: 100,
    },
  },
};
</script>

<style scoped>
.key-value-row {
  display: flex;
  align-items: center;
  height: 22px;
  line-height: 22px;
  font-size: 14px;
  margin-bottom: 18px;
}
.custom-key {
  color: #4d4f56;
  text-align: right;
  margin-right: 8px;
}
.custom-value {
  color: #313238;
}
</style>
