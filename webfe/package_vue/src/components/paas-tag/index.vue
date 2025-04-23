<template>
  <bk-tag
    v-bind="$attrs"
    :class="`paas-tag--${size}`"
  >
    <slot></slot>
  </bk-tag>
</template>

<script>
export default {
  name: 'PaasTag',
  props: {
    size: {
      type: String,
      default: 'normal',
      validator(value) {
        const allowedValues = ['small', 'normal'];
        const isValid = allowedValues.includes(value);
        if (!isValid) {
          console.warn(
            `Invalid prop: custom validator check failed for prop "size". Expected one of ["small", "normal", "large"], got "${value}".`
          );
        }
        return isValid;
      },
    },
  },
};
</script>

<style lang="scss" scoped>
/* small 样式 */
.paas-tag--small {
  height: 16px;
  line-height: 16px;
  padding: 0 4px;
  font-size: 10px;
}
</style>
