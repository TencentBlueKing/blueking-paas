<template>
  <bk-popover
    placement="bottom"
    :tippy-options="{ theme: 'light' }"
  >
    <i class="paasng-icon paasng-exclamation-circle ml10" />
    <div slot="content">
      <div>
        {{$t('最大资源限制')}}：
        <span>cpu：{{data.limit?.cpu}} </span>
        <span>{{$t('内存')}}：{{data.limit?.memory}} </span>
      </div>
      <div>
        {{$t('最小资源请求')}}：
        <span>cpu：{{data.request?.cpu}} </span>
        <span>{{$t('内存')}}：{{data.request?.memory}} </span>
      </div>
    </div>
  </bk-popover>
</template>

<script>
export default {
  props: {
    data: {
      type: Object,
      default: () => ({
        limit: {},
        request: {},
      }),
    },
  },
};
</script>

<style lang="scss" scoped>
.paasng-exclamation-circle {
  line-height: 32px;
}
</style>
