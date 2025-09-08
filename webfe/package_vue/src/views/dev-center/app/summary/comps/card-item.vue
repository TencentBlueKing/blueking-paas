<template>
  <div class="card-info-item-container card-style">
    <div class="flex-row justify-content-between align-items-center">
      <slot name="title">
        <span class="card-title">{{ title }}</span>
      </slot>
      <div class="flex-0">
        <slot name="title-extra"></slot>
      </div>
    </div>
    <div class="card-content">
      <slot></slot>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    title: {
      type: String,
      default: '',
    },
  },
};
</script>

<style lang="scss" scoped>
.card-info-item-container {
  padding: 12px 16px;
  .card-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
}
</style>
