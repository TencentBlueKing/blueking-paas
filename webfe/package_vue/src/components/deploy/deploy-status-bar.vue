<template>
  <div :class="['deploy-status-bar', statusConfig.theme]">
    <div class="status-icon">
      <round-loading
        v-if="deployment.status === 'pending'"
        size="small"
      />
      <span
        v-else
        :class="['paasng-icon', statusConfig.icon]"
      />
    </div>
    <div class="status-content">
      <p class="status-title">{{ statusConfig.title }}</p>
      <p class="status-description">
        <slot name="description">{{ statusDescription }}</slot>
      </p>
    </div>
    <div
      v-if="showActions"
      class="status-actions"
    >
      <span
        v-if="isDebugActionVisible"
        v-bk-tooltips="{
          content: $t('构建环境已被回收'),
          disabled: !isDebugActionDisabled,
        }"
        class="debug-action-wrapper"
      >
        <bk-button
          :theme="actionTheme"
          :loading="isDebugLoading"
          :disabled="isDebugActionDisabled"
          outline
          @click="handleLoginDebug"
        >
          {{ $t('登录调试') }}
        </bk-button>
      </span>
      <slot
        name="actions"
        :theme="actionTheme"
      >
        <bk-button
          :theme="actionTheme"
          outline
          @click="$emit('redeploy', deployment)"
        >
          {{ $t('重新部署') }}
        </bk-button>
        <bk-button
          :theme="actionTheme"
          outline
          @click="$emit('back')"
        >
          {{ $t('返回') }}
        </bk-button>
      </slot>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  props: {
    appCode: {
      type: [String, Number],
      default: '',
    },
    moduleId: {
      type: [String, Number],
      default: '',
    },
    deployment: {
      type: Object,
      default: () => ({}),
    },
    possibleReason: {
      type: String,
      default: '',
    },
    showActions: {
      type: Boolean,
      default: true,
    },
    showDebugAction: {
      type: Boolean,
      default: true,
    },
    debugDisabled: {
      type: Boolean,
      default: false,
    },
    debugAvailable: {
      type: Boolean,
      default: null,
    },
  },

  data() {
    return {
      isDebugLoading: false,
      isDebugStatusChecked: false,
      internalDebugEnabled: false,
      internalDebugAvailable: false,
      runtimeDebugAvailable: null,
      debugStatusTimer: null,
    };
  },

  computed: {
    ...mapState(['userFeature']),
    // 是否满足构建调试入口的基础展示条件
    isDebugActionEligible() {
      return this.deployment.status === 'failed' && this.showDebugAction && this.userFeature.ALLOW_BUILD_DEBUG === true;
    },
    // 生成首次查询构建调试状态的唯一标识
    debugStatusCheckKey() {
      if (!this.isDebugActionEligible || this.debugAvailable !== null) return '';
      const moduleId = this.deployment.moduleName || this.moduleId;
      return `${this.appCode}:${moduleId}:${this.deployment.deployment_id}`;
    },
    // 构建调试已开启且完成首次状态查询后展示入口
    isDebugActionVisible() {
      if (!this.isDebugActionEligible) return false;
      // 父组件已查询可用性时，showDebugAction 已代表 enabled 状态
      if (this.debugAvailable !== null) return true;
      return this.isDebugStatusChecked && this.internalDebugEnabled;
    },
    // 合并父组件、首次查询和定时刷新得到的可用性
    resolvedDebugAvailable() {
      if (this.runtimeDebugAvailable !== null) return this.runtimeDebugAvailable;
      if (this.debugAvailable !== null) return this.debugAvailable;
      return this.internalDebugAvailable;
    },
    // 构建容器不可用或外部指定禁用时禁用入口
    isDebugActionDisabled() {
      return this.debugDisabled || !this.resolvedDebugAvailable;
    },
    // 生成定时刷新构建调试状态的唯一标识
    debugStatusRefreshKey() {
      if (!this.isDebugActionVisible || this.isDebugActionDisabled) return '';
      const moduleId = this.deployment.moduleName || this.moduleId;
      return `${this.appCode}:${moduleId}:${this.deployment.deployment_id}`;
    },
    actionTheme() {
      return this.statusConfig.theme;
    },
    statusConfig() {
      const config = {
        pending: {
          theme: 'primary',
          icon: '',
          title: this.$t('正在部署中...'),
        },
        successful: {
          theme: 'success',
          icon: 'paasng-check-circle-shape',
          title: this.$t('应用部署成功'),
        },
        failed: {
          theme: 'danger',
          icon: 'paasng-exclamation-circle-shape',
          title: this.$t('部署失败'),
        },
        interrupted: {
          theme: 'warning',
          icon: 'paasng-info-circle-shape',
          title: this.$t('部署已中断'),
        },
      };
      return config[this.deployment.status] || config.pending;
    },
    statusDescription() {
      const { status, name, revision, operator, created } = this.deployment;
      if (status === 'failed') {
        return this.possibleReason || this.$t('暂无解决方案，可前往“标准输出日志”检测是否异常');
      }
      if (status === 'interrupted') {
        const interruptedText = this.$t('手动停止部署');
        return `${this.$t('由')} ${operator?.username || '--'} ${this.$t('于')} ${created || '--'} ${interruptedText}`;
      }
      return `${this.$t('分支：')} ${name || '--'} ${this.$t('版本：')} ${revision || '--'}`;
    },
  },

  watch: {
    // 部署或调试资格变化时重新获取状态
    debugStatusCheckKey: {
      immediate: true,
      handler(value) {
        this.isDebugStatusChecked = false;
        this.internalDebugEnabled = false;
        this.internalDebugAvailable = false;
        this.runtimeDebugAvailable = null;
        if (value) {
          this.checkBuildDebugStatus();
        }
      },
    },
    // 调试入口可用时启动定时刷新
    debugStatusRefreshKey: {
      immediate: true,
      handler(value) {
        this.clearDebugStatusTimer();
        if (value) {
          this.debugStatusTimer = setTimeout(this.refreshBuildDebugAvailability, 30000);
        }
      },
    },
  },

  // 组件销毁时清理构建调试状态定时器
  beforeDestroy() {
    this.clearDebugStatusTimer();
  },

  methods: {
    // 获取构建调试接口的公共请求参数
    getDebugParams() {
      return {
        appCode: this.appCode,
        moduleId: this.deployment.moduleName || this.moduleId,
        deployId: this.deployment.deployment_id,
      };
    },

    // 首次查询构建调试的开启状态和可用性
    async checkBuildDebugStatus() {
      this.isDebugLoading = true;
      try {
        const status = await this.$store.dispatch('deploy/getBuildDebugStatus', this.getDebugParams());
        this.internalDebugEnabled = !!status.enabled;
        this.internalDebugAvailable = this.isBuildDebugStatusAvailable(status);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isDebugStatusChecked = true;
        this.isDebugLoading = false;
      }
    },

    // 定时刷新构建容器可用性，容器回收后禁用入口
    async refreshBuildDebugAvailability() {
      try {
        const status = await this.$store.dispatch('deploy/getBuildDebugStatus', this.getDebugParams());
        if (!this.isBuildDebugStatusAvailable(status)) {
          this.runtimeDebugAvailable = false;
          return;
        }
        this.runtimeDebugAvailable = true;
        this.debugStatusTimer = setTimeout(this.refreshBuildDebugAvailability, 30000);
      } catch (e) {
        this.clearDebugStatusTimer();
      }
    },

    // 判断构建调试是否已开启且构建容器仍然可用
    isBuildDebugStatusAvailable(status) {
      return !!status?.enabled && !!status?.available;
    },

    // 展示构建调试操作的错误提示
    showBuildDebugError(message) {
      this.$paasMessage({
        theme: 'error',
        message: this.$t(message),
      });
    },

    // 清理构建调试状态定时器
    clearDebugStatusTimer() {
      if (this.debugStatusTimer) {
        clearTimeout(this.debugStatusTimer);
        this.debugStatusTimer = null;
      }
    },

    /**
     * 登录构建调试控制台
     */
    async handleLoginDebug() {
      if (!this.isDebugActionVisible || this.isDebugLoading || this.isDebugActionDisabled) return;

      this.isDebugLoading = true;
      const params = this.getDebugParams();
      try {
        const status = await this.$store.dispatch('deploy/getBuildDebugStatus', params);
        if (!this.isBuildDebugStatusAvailable(status)) {
          this.runtimeDebugAvailable = false;
          this.showBuildDebugError('构建环境已被回收');
          return;
        }

        const consoleInfo = await this.$store.dispatch('deploy/createBuildDebugConsole', params);
        const webConsoleUrl = consoleInfo?.web_console_url;
        if (!webConsoleUrl) {
          this.showBuildDebugError('创建构建调试控制台会话失败，请稍后重试');
          return;
        }
        window.open(webConsoleUrl, '_blank');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isDebugLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-status-bar {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  min-height: 65px;
  padding: 12px 20px;
  border-radius: 2px;
  &.primary {
    background: #e1ecff;
    .status-icon {
      color: #3a84ff;
    }
  }
  &.warning {
    background: #fff4e2;
    .status-icon {
      color: #fe9f07;
    }
  }
  &.danger {
    background: #ffecec;
    .status-icon {
      color: #eb3635;
    }
  }
  &.success {
    background: #e7fcfa;
    .status-icon {
      color: #3fc06d;
    }
  }

  .status-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 36px;
    margin-right: 12px;
    font-size: 32px;
  }
  .status-content {
    min-width: 0;
  }
  .status-title {
    font-size: 14px;
    color: #313238;
    font-weight: 700;
    line-height: 22px;
  }
  .status-description {
    margin-top: 4px;
    line-height: 20px;
    font-size: 12px;
    color: #63656e;
  }
  .status-actions {
    display: flex;
    flex-shrink: 0;
    gap: 8px;
    margin-left: auto;
    padding-left: 20px;
    .debug-action-wrapper {
      display: inline-flex;
    }
    .bk-button {
      min-width: 80px;
    }
  }
}
</style>
