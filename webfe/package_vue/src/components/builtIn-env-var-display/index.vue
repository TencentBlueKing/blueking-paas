<template>
  <div
    class="env-var-display-container"
    v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
  >
    <bk-alert
      type="info"
      class="mb16"
    >
      <span slot="title">
        {{ $t('增强服务也会写入内置环境变量，详情请查看增强服务页面。更多说明请参考') }}
        <a
          class="ml5"
          :href="GLOBAL.DOC.ENV_VAR_INLINE"
          target="_blank"
        >
          {{ $t('内置环境变量说明') }}
          <i class="paasng-icon paasng-jump-link"></i>
        </a>
      </span>
    </bk-alert>
    <div class="info-header">
      <div class="var">{{ $t('变量') }}</div>
      <div class="description">{{ $t('描述') }}</div>
    </div>
    <EnvVarInfo
      v-for="(item, index) in builtInEnvVars"
      v-bind="item"
      :key="`env-var-${index}`"
    />
  </div>
</template>

<script>
import EnvVarInfo from './display-info.vue';

// 定义环境变量类型常量
const ENV_VAR_TYPES = {
  BASIC: 'basicInfo',
  RUNTIME: 'appRuntimeInfo',
  PLATFORM: 'bkPlatformInfo',
  OTHER: 'otherBuiltInfo',
};

export default {
  name: 'EnvVarContent',
  components: {
    EnvVarInfo,
  },
  props: {
    appCode: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      isLoading: false,
      builtInEnvVarInfo: Object.keys(ENV_VAR_TYPES).reduce((acc, key) => {
        acc[ENV_VAR_TYPES[key]] = [];
        return acc;
      }, {}),
    };
  },
  computed: {
    builtInEnvVars() {
      return [
        {
          title: this.$t('应用基本信息'),
          data: this.builtInEnvVarInfo[ENV_VAR_TYPES.BASIC],
        },
        {
          title: this.$t('应用运行时信息'),
          data: this.builtInEnvVarInfo[ENV_VAR_TYPES.RUNTIME],
        },
        {
          title: this.$t('蓝鲸体系内平台地址'),
          data: this.builtInEnvVarInfo[ENV_VAR_TYPES.PLATFORM],
          type: 'bk',
        },
        {
          title: this.$t('其他'),
          data: this.builtInEnvVarInfo[ENV_VAR_TYPES.OTHER],
          type: 'bk',
          shadow: true,
        },
      ];
    },
  },
  created() {
    this.loadEnvVariables();
  },
  methods: {
    // 加载所有环境变量
    async loadEnvVariables() {
      this.isLoading = true;
      try {
        await Promise.all([
          this.fetchEnvData('getBasicInfo', ENV_VAR_TYPES.BASIC),
          this.fetchEnvData('getAppRuntimeInfo', ENV_VAR_TYPES.RUNTIME),
          this.fetchEnvData('getBkPlatformInfo', ENV_VAR_TYPES.PLATFORM),
          this.fetchEnvData('getOtherBuiltInEnvVars', ENV_VAR_TYPES.OTHER),
        ]);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 通用方法：获取环境变量数据
     * @param {String} action - store action名称
     * @param {String} dataKey - 存储数据的key
     */
    async fetchEnvData(action, dataKey) {
      try {
        const data = await this.$store.dispatch(`envVar/${action}`, { appCode: this.appCode });
        this.builtInEnvVarInfo[dataKey] = this.formatEnvData(data);
      } catch (error) {
        throw error;
      }
    },

    /**
     * 格式化环境变量数据
     * @param {Object} data - 原始数据
     * @returns {Array} 格式化后的数组
     */
    formatEnvData(data) {
      return Object.keys(data).map((key) => ({
        label: key,
        value: data[key],
        isTips: true,
      }));
    },
  },
};
</script>

<style lang="scss" scoped>
.env-var-display-container {
  .mb16 {
    margin-bottom: 16px;
  }
  .info-header {
    display: flex;
    align-items: center;
    height: 42px;
    background: #fafbfd;
    font-size: 12px;
    color: #313238;
    .var,
    .description {
      padding-left: 16px;
    }
    .var {
      width: 338px;
    }
    .description {
      flex: 1;
    }
  }
  i.paasng-jump-link {
    font-size: 14px;
    transform: translateY(0px);
  }
}
</style>
