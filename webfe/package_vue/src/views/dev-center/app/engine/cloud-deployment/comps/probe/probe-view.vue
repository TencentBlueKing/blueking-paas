<template>
  <div class="view-panel">
    <div class="title">{{ title }}</div>
    <div class="content">
      <div class="item">
        <label>{{ $t('探测方法') }}：</label>
        <span class="value">{{ isHttpGet ? 'HTTP Get' : 'TCP Socket' }}</span>
      </div>
      <div class="item">
        <label>{{ $t('检查端口') }}：</label>
        <span class="value">{{ isHttpGet ? viewData.http_get.port : viewData.tcp_socket.port }}</span>
      </div>
      <div
        class="item"
        v-if="isHttpGet"
      >
        <label>{{ $t('检查路径') }}：</label>
        <span class="value">{{ viewData.http_get.path }}</span>
      </div>
      <div class="item">
        <label>{{ $t('延迟探测时间') }}：</label>
        <span class="value">{{ viewData.initial_delay_seconds }} {{ $t('秒') }}</span>
      </div>
      <div class="item">
        <label>{{ $t('探测超时时间') }}：</label>
        <span class="value">{{ viewData.timeout_seconds }} {{ $t('秒') }}</span>
      </div>
      <div class="item">
        <label>{{ $t('探测频率') }}：</label>
        <span class="value">{{ viewData.period_seconds }} {{ $t('秒/次') }}</span>
      </div>
      <div class="item">
        <label>{{ $t('连续探测成功次数') }}：</label>
        <span class="value">{{ viewData.success_threshold }} {{ $t('次') }}</span>
      </div>
      <div class="item">
        <label>{{ $t('连续探测失败次数') }}：</label>
        <span class="value">{{ viewData.failure_threshold }} {{ $t('次') }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProbeView',
  props: {
    title: {
      type: String,
      default: '',
    },
    data: {
      type: Object,
      default: () => {},
    },
    probeType: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      viewData: {},
    };
  },
  computed: {
    isHttpGet() {
      return this.viewData.http_get !== null;
    },
  },
  watch: {
    data: {
      handler(newVal) {
        this.viewData = newVal.probes[this.probeType];
      },
      deep: true,
    },
  },
  created() {
    this.viewData = this.data.probes[this.probeType];
  },
};
</script>

<style lang="scss" scoped>
.view-panel {
  width: 420px;
  background: #fafbfd;
  border-radius: 2px;
  font-size: 14px;
  color: #63656e;
  .title {
    padding-left: 16px;
    line-height: 32px;
    height: 32px;
    background: #f0f1f5;
    border-radius: 2px 2px 0 0;
    color: #313238;
  }
  .content {
    padding: 8px 0 16px;
    .item {
      height: 40px;
      display: flex;
      align-items: center;
    }
    label {
      display: inline-block;
      width: 150px;
      text-align: right;
      vertical-align: middle;
      line-height: 32px;
      color: #63656e;
      padding: 0 8px 0 0;
    }
    .value {
      color: #313238;
    }
  }
}
</style>
