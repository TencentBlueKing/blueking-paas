<template>
  <div
    class="service-item-container flex-row"
    :class="{ disabled: !isEnabled }"
  >
    <div class="service-img flex-row align-items-center justify-content-center">
      <img :src="data.logo" />
    </div>
    <div class="service-info">
      <div
        class="g-sub-title sub-title f12 mb-4 text-ellipsis"
        v-bk-overflow-tips
      >
        {{ data.display_name }}
      </div>
      <p
        class="f12 desc g-tip"
        v-bk-overflow-tips
      >
        {{ data.description }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
    isEnabled: {
      type: Boolean,
      default: true,
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';

.service-item-container {
  max-width: 315px;
  height: 80px;
  background: #fff;
  border: 1px solid #dcdee5;
  border-radius: 2px;

  &:not(.disabled):hover {
    cursor: pointer;
    border-color: #3a84ff;
    .sub-title {
      color: #3a84ff;
    }
  }
}
.service-img {
  width: 66px;
  height: 100%;
  background: #fafbfd;

  img {
    width: 42px;
    height: 42px;
    object-fit: contain;
  }
}
.service-info {
  flex: 1;
  padding: 12px;
  overflow: hidden;
  .desc {
    line-height: 16px;
    max-height: 40px;
    @include multiline-ellipsis;
  }
}
</style>
