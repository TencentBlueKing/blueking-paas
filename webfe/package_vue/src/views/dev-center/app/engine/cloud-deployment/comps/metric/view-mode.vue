<template>
  <div
    class="metric-view-mode-container"
    v-if="Object.keys(data).length"
  >
    <div class="info-item">
      <div class="label">{{ $t('端口名称') }}：</div>
      <div class="value">{{ data.metric.service_name }}</div>
    </div>
    <div class="info-item">
      <div class="label">Metric {{ $t('路径') }}：</div>
      <div class="value">{{ data.metric.path }}</div>
    </div>
    <div class="info-item">
      <div class="label">Metric {{ $t('参数') }}：</div>
      <div
        class="value"
        v-if="Object.keys(data.metric.params).length"
      >
        <div
          v-for="(key, value) in data.metric.params"
          :key="key"
        >
          <span>{{ key }}</span>
          =
          <span>{{ value }}</span>
        </div>
      </div>
      <div v-else>--</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MetricViewMode',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
};
</script>

<style lang="scss" scoped>
.metric-view-mode-container {
  width: 420px;
  padding: 12px 0;
  background: #f5f7fa;
  border-radius: 2px;
  .info-item {
    display: flex;
    margin-bottom: 9px;
    font-size: 14px;
    &:last-child {
      margin-bottom: 0;
    }
    .label {
      width: 150px;
      text-align: right;
      color: #63656e;
    }
    .value {
      flex: 1;
      color: #313238;
    }
  }
}
</style>
