<template functional>
  <div class="paasng-api-layout">
    <div class="left">
      <slot />
    </div>
    <div class="right">
      <slot name="right" />
    </div>
  </div>
</template>
<style lang="scss" scoped>
.paasng-api-layout {
  position: relative;
  width: 100%;
  .left {
    position: relative;
    padding: 10px 0;
    margin-right: 16px;
    height: 640px;
    width: 240px;
    background: #fff;
    border: 1px solid #dfe0e5;
    border-radius: 2px;
    display: inline-block;
  }
  .right {
    display: inline-block;
    width: calc(100% - 256px);
    vertical-align: top;
  }
}
</style>
