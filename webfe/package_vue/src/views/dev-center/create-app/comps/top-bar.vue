<template>
  <section class="success-top-bar" v-if="visible">
    {{ $t('创建应用') }}
  </section>
</template>

<script>
export default {
  data() {
    return {
      visible: true,
    };
  },
};
</script>

<style lang="scss" scoped>
.success-top-bar {
    position: relative;
    top: calc(var(--app-notice-height) + 50px);
    width: 100%;
    height: 52px;
    font-size: 16px;
    color: #313238;
    text-align: center;
    line-height: 52px;
    background: #FFFFFF;
    box-shadow: 0 1px 0 0 #DCDEE5, 0 3px 4px 0 #4070cb0f;
    i {
        position: absolute;
        right: 30px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 18px;
        color: #63656E;
        cursor: pointer;
    }
}
</style>
