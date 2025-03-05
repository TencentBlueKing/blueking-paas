<template>
  <div class="sandbox-config-info-box">
    <p class="alert mb10">
      <i class="paasng-icon paasng-info-line"></i>
      <span>{{ $t('沙箱环境复用 “预发布环境” 的增强服务和环境变量') }}</span>
    </p>
    <div class="info">
      <div class="info-item">
        <div class="label">{{ $t('代码仓库') }}：</div>
        <div class="value">{{ repoUrl }}</div>
      </div>
      <div class="info-item">
        <div class="label">{{ $t('代码分支') }}：</div>
        <div class="value">{{ repoBranch }}</div>
      </div>
      <div class="info-item">
        <div class="label">{{ $t('增强服务') }}：</div>
        <div class="value">{{ serviceName }}</div>
      </div>
      <div class="info-item">
        <div class="label">{{ $t('环境变量') }}：</div>
        <div class="value">{{ $t('共 {n} 个', { n: envVarLength }) }}</div>
      </div>
    </div>
    <bk-input
      :clearable="true"
      :placeholder="$t('请输入关键字搜索环境变量')"
      :right-icon="'bk-icon icon-search'"
      v-model="searchValue"
      ext-cls="env-search"
    ></bk-input>
    <!-- 环境变量 -->
    <ul class="env-variables-box">
      <li
        class="item"
        v-for="(item, index) in displayEnvVars"
        :key="index"
        v-bk-overflow-tips="{ content: `${item[0]}=${item[1]}`, allowHTML: true }"
      >
        <span>{{ item[0] }}</span>
        <span>=</span>
        <span>{{ item[1] }}</span>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'SandboxConfigInfo',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    serviceName: {
      type: String,
      default: '',
    },
    env: {
      type: String,
    },
  },
  data() {
    return {
      infoList: [{ label: this.$t('基础镜像'), value: 'Ubuntu18' }],
      searchValue: '',
    };
  },
  computed: {
    repoUrl() {
      return this.data?.repo?.url || "--"
    },
    repoBranch() {
      return this.data?.repo?.version_info?.version_name || "--"
    },
    envVarLength() {
      return Object.keys(this.data?.env_vars || {})?.length;
    },
    envVars() {
      const vars = this.data?.env_vars || {};
      return Object.entries(vars);
    },
    displayEnvVars() {
      if (!this.searchValue) {
        return this.envVars;
      }
      const search = this.searchValue.toLocaleLowerCase();
      return this.envVars.filter(
        (item) => item[0].toLocaleLowerCase().includes(search) || item[1].toLocaleLowerCase().includes(search)
      );
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-config-info-box {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px 24px;
  .alert {
    color: #979ba5;
    font-size: 12px;
    i {
      color: #979ba5;
      font-size: 14px;
      margin-right: 10px;
    }
  }
  .env-search /deep/ input {
    background: #1a1a1a;
  }
  .info {
    .info-item {
      display: flex;
      font-size: 14px;
      height: 40px;
      line-height: 40px;
      .label {
        flex-shrink: 0;
        color: #979ba5;
      }
      .value {
        color: #dcdee5;
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;
      }
    }
  }
  .env-variables-box {
    flex: 1;
    overflow-y: auto;
    margin-top: 8px;
    color: #63656e;
    &::-webkit-scrollbar {
      width: 4px;
      background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
      height: 5px;
      border-radius: 2px;
      background-color: #dcdee5;
    }
    .item {
      padding: 0 16px;
      height: 36px;
      line-height: 36px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #f5f7fa;
      &:nth-child(odd) {
        background: #2e2e2e;
      }
    }
  }
}
</style>
