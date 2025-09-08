<template>
  <div
    class="service-item-container flex-row align-items-center"
    :class="{ disabled: !isEnabled }"
  >
    <div class="service-img mr-12">
      <img :src="data.logo" />
    </div>
    <div class="service-info">
      <p class="g-sub-title sub-title">{{ data.name }}</p>
      <p
        class="f12 desc g-tip"
        v-bk-overflow-tips
      >
        {{ data.display_name }}
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
  height: 90px;
  padding: 0 12px;
  background: #f5f7fa;
  border-radius: 2px;
  &.disabled {
    img {
      -webkit-filter: grayscale(1);
      filter: grayscale(1);
      opacity: 0.6;
    }
    .sub-title,
    .desc {
      color: #979ba5 !important;
    }
  }
  .service-img {
    width: 42px;
    height: 42px;
    border-radius: 2px;
    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }
  .service-info {
    flex: 1;
    .desc {
      line-height: 16px;
      max-height: 40px;
      @include multiline-ellipsis;
    }
  }
}
</style>
