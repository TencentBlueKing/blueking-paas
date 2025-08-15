<template lang="html">
  <div class="top-info-wrapper">
    <div class="text-wrapper">
      <h3 class="app-type">{{ $t('应用类型') }}：{{ appInfo.type }}</h3>
      <p>{{ appInfo.description }}</p>
    </div>
    <!-- 普通应用 -->
    <template v-if="isEngineless">
      <div class="process-info flex-more">
        <div class="left">
          <div class="icon-box mr8">
            <i class="paasng-icon paasng-process-2" />
          </div>
          <div class="description">
            <h4>{{ appInfo.data.processesLen }}</h4>
            <p>{{ $t('进程') }}</p>
          </div>
        </div>
        <div class="right">
          <p>
            <span
              v-bk-tooltips="getResourceTips('CPU')"
              v-dashed
            >
              CPU:
            </span>
            {{ displayCpuText }}
          </p>
          <p>
            <span
              v-bk-tooltips="getResourceTips('Memory')"
              v-dashed
            >
              {{ $t('内存') }}:
            </span>
            {{ displayMemoryText }}
          </p>
        </div>
      </div>
      <div
        v-if="userFeature.MONITORING"
        class="alarm"
      >
        <div class="icon-box mr8">
          <i class="paasng-icon paasng-alert" />
        </div>
        <div class="description">
          <h4>{{ appData.alarmCount }}</h4>
          <p>{{ $t('告警数量') }}</p>
        </div>
      </div>
    </template>
    <!-- 外链应用 -->
    <template v-else>
      <div
        v-for="item in viewList"
        :key="item.text"
        class="alarm engineless"
      >
        <div
          class="icon-box mr8"
          style="cursor: pointer"
          @click="toDataDetails(item)"
        >
          <i :class="`paasng-icon paasng-${item.icon}`" />
        </div>
        <div class="description">
          <h4>{{ item.quantity }}</h4>
          <p>{{ item.text }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  props: {
    appInfo: {
      type: Object,
    },
    viewData: {
      type: Object,
    },
    isModule: {
      type: Boolean,
    },
    isCloud: {
      type: Boolean,
    },
  },
  data() {
    return {
      enginelessList: [
        {
          icon: 'pv',
          quantity: 0,
          text: this.$t('访问数(pv)'),
          id: 'pv',
        },
        {
          icon: 'member',
          quantity: 0,
          text: this.$t('访客数(uv)'),
          id: 'uv',
        },
        {
          icon: 'api-2',
          quantity: 0,
          text: this.$t('已申请权限的API数'),
          id: 'apiNumber',
        },
      ],
      notAnalyticsList: [
        {
          icon: 'wangguan',
          quantity: 0,
          text: this.$t('已申请权限的网关数'),
          id: 'gateway',
        },
        {
          icon: 'api-2',
          quantity: 0,
          text: this.$t('已申请权限的API数'),
          id: 'apiNumber',
        },
      ],
    };
  },
  computed: {
    ...mapState(['curAppInfo', 'userFeature', 'curAppModule']),
    isEngineless() {
      return this.curAppInfo.web_config.engine_enabled;
    },
    isOperador() {
      return this.curAppInfo.role?.name === 'operator';
    },
    viewList() {
      return (this.isModule ? this.enginelessList : this.notAnalyticsList).filter(
        (item) => !(this.isOperador && item.id === 'apiNumber')
      );
    },
    appCode() {
      return this.$route.params.id;
    },
    curModuleId() {
      return this.curAppModule.name;
    },
    // 应用数据（cpu、内存）
    appData() {
      return this.appInfo.data || {};
    },
    // 获取 CPU 文案
    displayCpuText() {
      return this.formatResourceText('Cpu', '核');
    },
    // 获取内存文案
    displayMemoryText() {
      return this.formatResourceText('Memory', 'GB');
    },
  },
  watch: {
    viewData() {
      if (!this.isEngineless) {
        this.seteEnginelessList();
      }
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      if (!this.isEngineless) {
        this.seteEnginelessList();
      }
    },
    seteEnginelessList() {
      const curList = this.isModule ? this.enginelessList : this.notAnalyticsList;
      curList.forEach((item) => {
        item.quantity = this.viewData[item.id];
        item.quantity = this.formatNumber(item.quantity);
      });
    },
    // 访问量转为显示单位
    formatNumber(num) {
      num = Number(num);
      return num >= 1e3 && num < 1e4 ? `${(num / 1e3).toFixed(1)}k` : num >= 1e4 ? `${(num / 1e4).toFixed(1)}w` : num;
    },
    /**
     * 格式化资源文本（CPU/内存）
     * @param {string} resourceType - 资源类型，如 'Cpu' 或 'Memory'
     * @param {string} unit - 单位，如 '核' 或 'GB'
     * @returns {string} 格式化后的文本
     */
    formatResourceText(resourceType, unit) {
      const { stag, prod, hasAutoscaling } = this.appData;
      const minProp = `min${resourceType}`;
      const maxProp = `max${resourceType}`;

      // 格式化单个环境的资源文本
      const formatEnvResource = (env, envName) => {
        const minValue = env?.[minProp];
        const maxValue = env?.[maxProp];

        if (hasAutoscaling) {
          // 启用扩缩容时显示范围
          const rangeText = minValue && maxValue ? `${minValue} ~ ${maxValue}` : '--';
          return `${rangeText} ${this.$t(`${unit}（${envName}）`)}`;
        } else {
          // 未启用扩缩容时只显示单个值
          const valueText = minValue || '--';
          return `${valueText} ${this.$t(`${unit}（${envName}）`)}`;
        }
      };

      const prodText = formatEnvResource(prod, '生产环境');
      const stagText = formatEnvResource(stag, '预发布环境');

      return `${prodText}、${stagText}`;
    },
    getResourceTips(resourceType) {
      const baseText = this.$t('所有进程 {n} limit 的总和', { n: resourceType });
      if (this.appData.hasAutoscaling) {
        const autoscalingText = this.$t('已启用自动扩缩容，按弹性范围展示');
        return `${baseText}（${autoscalingText}）`;
      }
      return baseText;
    },
    toDataDetails(data) {
      if (data.id === 'apiNumber' || data.id === 'gateway') {
        this.$router.push({
          name: 'appCloudAPI',
          params: {
            id: this.appCode,
            tabActive: 'appPerm',
          },
        });
      } else {
        this.$router.push({
          name: 'appWebAnalysis',
          params: {
            id: this.appCode,
            moduleId: this.curModuleId,
          },
        });
      }
    },
  },
};
</script>
<style lang="scss" scoped>
@import '~@/assets/css/mixins/dashed.scss';
@mixin flex {
  display: flex;
  align-items: center;
}
.default-top-info.top-info-wrapper {
  margin-bottom: 0;
}
.top-info-wrapper {
  display: flex;
  min-height: 100px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #dcdee5;
  border-radius: 2px;
  background: #fff;
  font-size: 12px;
  color: #63656e;
  .text-wrapper,
  .process-info {
    flex: 1;
    border-right: 1px solid #f5f7fa;
  }
  .icon-box {
    width: 48px;
    height: 48px;
    background: #f0f5ff;
    border-radius: 4px;
    @include flex;
    justify-content: center;
    i {
      font-size: 32px;
      color: #3a84ff;
    }
  }
  .description {
    h4 {
      font-size: 24px;
      color: #313238;
    }
  }
  .text-wrapper {
    padding-right: 34px;
    .app-type {
      font-size: 12px;
      color: #313238;
      line-height: 22px;
    }
    p {
      line-height: 22px;
    }
  }
  .process-info {
    padding-left: 24px;
    @include flex;
    .left {
      display: flex;
      align-items: center;
      margin-right: 15px;
    }
    .right {
      height: 48px;
      display: flex;
      flex-direction: column;
      justify-content: space-around;
    }
  }
  .alarm {
    flex: 1;
    padding-left: 24px;
    @include flex;
  }
  .mr8 {
    margin-right: 8px;
  }
  .flex-more {
    flex: 1.5;
  }
}
</style>
