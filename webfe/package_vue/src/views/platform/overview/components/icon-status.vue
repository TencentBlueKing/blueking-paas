<template>
  <span class="icon-status-wrapper">
    <i
      style="color: #18c0a1"
      class="paasng-icon paasng-circle-correct-filled circle"
      v-if="configured"
    ></i>
    <i
      style="color: #c4c6cc"
      class="paasng-icon paasng-time-filled"
      v-else
    ></i>
  </span>
</template>

<script>
export default {
  props: {
    configured: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss" scoped>
.icon-status-wrapper i {
  font-size: 21px;
}
</style>
