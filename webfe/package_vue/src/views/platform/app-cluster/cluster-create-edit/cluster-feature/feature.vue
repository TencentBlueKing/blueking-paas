<template>
  <section
    class="card-style"
    v-bkloading="{ isLoading, zIndex: 10 }"
  >
    <div class="card-title">
      <span>{{ $t('集群特性') }}</span>
      <span class="sub-tip ml8">
        {{ $t('已经根据集群的版本和平台相关设置给集群配置了相关特性。') }}
      </span>
    </div>
    <div class="card-content">
      <div
        v-for="(val, key) in featureMap"
        :key="val"
        class="feature-item"
      >
        <bk-checkbox v-model="featureFlags[key]">
          {{ val }}
        </bk-checkbox>
      </div>
    </div>
  </section>
</template>

<script>
import { cloneDeep } from 'lodash';
export default {
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      isLoading: false,
      details: {},
      featureFlags: {},
      featureMap: {
        ENABLE_BCS_EGRESS: this.$t('支持提供出口 IP'),
        ENABLE_MOUNT_LOG_TO_HOST: this.$t('允许挂载日志到主机'),
        INGRESS_USE_REGEX: this.$t('Ingress 路径是否使用正则表达式'),
        ENABLE_BK_LOG_COLLECTOR: this.$t('使用蓝鲸日志平台方案采集日志'),
        ENABLE_BK_MONITOR: this.$t('使用蓝鲸监控获取资源使用指标'),
        ENABLE_AUTOSCALING: this.$t('支持自动扩缩容'),
      },
    };
  },
  watch: {
    data: {
      handler(newValue) {
        if (Object.keys(newValue)?.length) {
          this.featureFlags = cloneDeep(newValue.feature_flags);
        } else {
          this.setDefault();
        }
      },
      deep: true,
      immediate: true,
    },
  },
  methods: {
    setDefault() {
      this.featureFlags = {
        ENABLE_BCS_EGRESS: false,
        ENABLE_MOUNT_LOG_TO_HOST: false,
        INGRESS_USE_REGEX: false,
        ENABLE_BK_LOG_COLLECTOR: false,
        ENABLE_BK_MONITOR: false,
        ENABLE_AUTOSCALING: false,
      };
    },
    getData() {
      return {
        ...this.featureFlags,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.card-content {
  padding-left: 68px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
