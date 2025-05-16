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
      isLoading: true,
      details: {},
      featureFlags: {},
      featureMaps: [],
      // 默认配置
      clusterDefaultConfigs: {},
    };
  },
  watch: {
    data: {
      handler(newValue) {
        if (Object.keys(newValue)?.length) {
          const depFeatureFlags = cloneDeep(newValue.feature_flags);
          if (Object.keys(depFeatureFlags)?.length) {
            this.featureFlags = depFeatureFlags;
          } else { // 接口默认值
            this.featureFlags = this.clusterDefaultConfigs.feature_flags || {};
          }
        } else {
          this.setDefault();
        }
      },
      deep: true,
      immediate: true,
    },
  },
  created() {
    Promise.all([this.getClusterDefaultConfigs(), this.getClusterFeatureFlags()]).finally(() => {
      this.isLoading = false;
    });
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
    // 获取集群默认配置项
    async getClusterDefaultConfigs() {
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDefaultConfigs');
        this.clusterDefaultConfigs = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    setDefault() {
      this.featureFlags = this.clusterDefaultConfigs?.feature_flags || {
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
