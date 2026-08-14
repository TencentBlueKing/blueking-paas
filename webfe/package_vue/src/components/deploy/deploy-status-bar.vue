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
      <bk-button
        :theme="actionTheme"
        :loading="isDebugLoading"
        :disabled="debugDisabled"
        outline
        @click="handleLoginDebug"
      >
        {{ $t('登录调试') }}
      </bk-button>
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
    debugDisabled: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      isDebugLoading: false,
    };
  },

  computed: {
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

  methods: {
    /**
     * 登录构建调试控制台
     */
    async handleLoginDebug() {
      if (this.isDebugLoading || this.debugDisabled) return;

      this.isDebugLoading = true;
      const params = {
        appCode: this.appCode,
        moduleId: this.deployment.moduleName || this.moduleId,
        deployId: this.deployment.deployment_id,
      };
      try {
        const status = await this.$store.dispatch('deploy/getBuildDebugStatus', params);
        if (!status.enabled) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('该部署未开启构建调试'),
          });
          return;
        }
        if (!status.available) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('构建调试窗口不可用'),
          });
          return;
        }

        const res = await this.$store.dispatch('deploy/createBuildDebugConsole', params);
        if (!res?.web_console_url) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('创建构建调试控制台会话失败，请稍后重试'),
          });
          return;
        }
        window.open(res.web_console_url, '_blank');
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
    .bk-button {
      min-width: 80px;
    }
  }
}
</style>
