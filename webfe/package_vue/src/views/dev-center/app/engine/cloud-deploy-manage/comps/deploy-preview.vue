<template>
  <div class="deploy-preview">
    <div class="info-item">
      <p>
        <span class="count">5</span>
        <span class="unit">个</span>
      </p>
      <p class="desc">运行实例数</p>
    </div>
    <div class="info-item">
      <p>
        <span class="count">4</span>
        <span class="unit">个</span>
      </p>
      <p class="desc">期望实例数</p>
    </div>
    <div class="info-item">
      <p>
        <span class="count rejected">1</span>
        <span class="unit">个</span>
      </p>
      <p class="desc">异常实例数</p>
    </div>
  </div>
</template>

<script>
export default {

}
</script>

<style lang="scss" scoped>
.deploy-preview {
  display: flex;

  .info-item {
    flex: 1;
    height: 40px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    margin: 14px 0;
    text-align: center;
    border-right: 1px solid #EAEBF0;
    &:last-child {
      border-right: none;
    }

    .count {
      font-size: 24px;
      color: #313238;

      &.rejected {
        color: #EA3636;
      }
    }
    .unit {
      margin-left: 5px;
      font-size: 12px;
      color: #313238;
    }
    .desc {
      margin-top: 5px;
      font-size: 12px;
      color: #979BA5;
    }
  }
}
</style>
