<template>
  <div class="status-bar">
    <div
      class="wrapper
      release-info-box
      flex-row
      justify-content-between
      align-items-center"
      :class="type"
    >
      <div class="info-left-warp flex-row">
        <slot name="left"></slot>
      </div>
      <div class="info-right-warp">
        <slot name="right"></slot>
      </div>
    </div>
  </div>
</template>
<script>
  export default {
    props: {
      type: {
        type: String,
        default: 'primary'
      }
    }
  };
</script>
