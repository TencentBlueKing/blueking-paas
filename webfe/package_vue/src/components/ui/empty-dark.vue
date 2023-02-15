<template>
  <div class="paas-empty-dark">
    <img src="/static/images/empty-dark.png">
    <p class="empty-tips">
      {{ $t('暂无数据') }}
    </p>
  </div>
</template>

<script>
    export default {
    };
</script>

<style lang="scss" scoped>
  .paas-empty-dark {
      text-align: center;
      .empty-tips {
          font-size: 14px;
          color: #979BA5;
      }
  }
</style>
