<template>
  <div class="env-var-display-container">
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
    <env-var-info
      v-if="basicInfo.length"
      :title="$t('应用基本信息')"
      :data="basicInfo"
    />
    <env-var-info
      v-if="appRuntimeInfo.length"
      :title="$t('应用运行时信息')"
      :data="appRuntimeInfo"
    />
    <env-var-info
      v-if="bkPlatformInfo.length"
      type="bk"
      :shadow="true"
      :title="$t('蓝鲸体系内平台地址')"
      :data="bkPlatformInfo"
    />
  </div>
</template>

<script>
import envVarInfo from './display-info.vue';
export default {
  name: 'EnvVarContent',
  components: {
    envVarInfo,
  },
  props: {
    basicInfo: {
      type: Array,
      default: () => [],
    },
    appRuntimeInfo: {
      type: Array,
      default: () => [],
    },
    bkPlatformInfo: {
      type: Array,
      default: () => [],
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
