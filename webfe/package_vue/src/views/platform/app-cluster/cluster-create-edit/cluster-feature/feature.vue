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
        v-for="(item, index) in featureMaps"
        :key="index"
        class="feature-item"
      >
        <bk-checkbox v-model="featureFlags[item.key]">
          {{ $t(item.name) }}
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
      featureMaps: [],
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
  created() {
    this.getClusterFeatureFlags();
  },
  methods: {
    async getClusterFeatureFlags() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterFeatureFlags');
        this.featureMaps = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
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
