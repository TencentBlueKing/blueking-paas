<template lang="html">
  <div class="right-main">
    <div class="overview-tit">
      <h2>403</h2>
    </div>
    <div
      class="log-middle"
      style="width: 1180px; margin: 0 auto; padding-bottom: 0"
    >
      <div
        class="nofound"
        style="width: 1180px; margin: 0 auto;"
      >
        <img src="/static/images/permissions.png">
        <p> {{ $t('您没有访问当前应用该功能的权限') }} </p>
      </div>
    </div>
  </div>
</template>

<style lang="css" scoped>
    .nofound {
        width: 939px;
        padding-top: 150px;
        text-align: center;
    }

    .nofound p {
        font-size: 20px;
        color: #979797;
        line-height: 80px;
    }
</style>
