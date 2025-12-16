<template lang="html">
  <div class="right-main">
    <div
      class="log-middle"
      style="width: 1180px; margin: 0 auto; padding-bottom: 0"
    >
      <div
        class="nofound"
        style="width: 1180px; margin: 0 auto"
      >
        <img :src="notFoundImg" />
        <p>{{ $t('页面找不到了！') }}</p>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  data() {
    return {
      notFoundImg: require('@static/images/404.png'),
    };
  },
};
</script>

<style lang="css" scoped>
.nofound {
  padding-top: 150px;
  text-align: center;
}

.nofound p {
  font-size: 20px;
  color: #979797;
  line-height: 80px;
}
</style>
