<template>
  <bk-dialog
    v-model="visible"
    width="480"
    theme="primary"
    header-position="left"
    :show-footer="false"
    :mask-close="false"
    ext-cls="rollback-app-dialog-cls"
    @after-leave="handleCancel"
  >
    <section>
      <div class="status-wrapper">
        <!-- 回退中 -->
        <template v-if="isRollingBack || isRollbackSuccessful">
          <div class="center rollback-title-wrapper">
            <round-loading
              class="icon-cls loading"
              size="large"
            />
            <div class="dialog-title">{{ $t('回退为普通应用中') }}…</div>
          </div>
          <div class="tips">{{ $t('回退完成后到“应用引擎-进程管理”页面检查每个进程状态') }}</div>
        </template>
        <!-- 回退失败 -->
        <template v-else-if="isRollbackFailed">
          <div class="center rollback-title-wrapper">
            <div class="icon-cls center fail">
              <i class="paasng-icon paasng-bold-close"></i>
            </div>
            <div class="dialog-title">{{ $t('回退应用失败') }}</div>
          </div>
          <div class="tips">{{ `${$t('失败原因')}：${migrationData.error_msg}` }}</div>
        </template>
        <template v-else>
          <div class="center rollback-title-wrapper">
            <div class="icon-cls center warning">
              <bk-icon type="exclamation" />
            </div>
            <div class="dialog-title">{{ $t('确认回退应用') }}</div>
          </div>
          <div class="info-item">
            <div class="app-info-cls">
              <span class="lable">{{ $t('云原生应用') }}：</span>
              <span class="app-code">{{ appCode }}</span>
            </div>
            <div class="tips">{{ $t('回退后会将当前应用回退到普通应用的状态，并撤销所有云原生应用部署而分配的资源') }}</div>
          </div>
        </template>
      </div>
    </section>
    <section
      class="center dialog-operate"
      v-if="!isRollingBack && !isRollbackSuccessful"
    >
      <!-- 回滚失败 -->
      <bk-button
        v-if="isRollbackFailed"
        theme="default"
        type="submit"
        @click="handleCancel"
      >
        {{ $t('确定') }}
      </bk-button>
      <template v-else>
        <bk-button
          theme="danger"
          type="submit"
          @click="handleRollback"
        >
          {{ $t('回退') }}
        </bk-button>
        <bk-button
          class="ml10"
          theme="default"
          type="submit"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </section>
  </bk-dialog>
</template>

<script>
export default {
  name: 'RollbackAppDialog',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    appCode: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      visible: false,
      isMainLoading: false,
      isStopPolling: false,
      processId: '',
      migrationData: {
        details: {},
      },
      stopPollingStatus: ['rollback_succeeded', 'rollback_failed'],
      timerId: null,
      rollbackFailedMsg: '',
    };
  },
  computed: {
    // 回滚中
    isRollingBack() {
      return this.migrationData.status === 'on_rollback';
    },
    // 回滚成功
    isRollbackSuccessful() {
      return this.migrationData.status === 'rollback_succeeded';
    },
    // 回滚失败
    isRollbackFailed() {
      return this.migrationData.status === 'rollback_failed';
    },
  },
  watch: {
    value: {
      handler(newVal) {
        this.visible = newVal;
        if (newVal) {
          this.isMainLoading = true;
          this.getMigrationProcessesLatest();
        }
      },
      immediate: true,
    },
  },
  methods: {
    // 弹窗关闭处理
    handleCancel() {
      this.$emit('change', false);
      // 停止轮询
      clearInterval(this.timerId);
    },
    // 应用回退
    async handleRollback() {
      try {
        const res = await this.$store.dispatch('migration/rollback', {
          appCode: this.appCode,
        });
        this.processId = res.process_id;
        // 查询状态
        this.queryMigrationStatus();
        this.pollingStatus('id');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 查询状态
    async queryMigrationStatus() {
      try {
        const res = await this.$store.dispatch('migration/queryMigrationStatus', {
          id: this.processId,
        });
        // 回滚成功
        if (res.status === 'rollback_succeeded') {
          this.handleRollbackSuccessful();
        }
        this.migrationData = res;
        // 是否停止轮询
        this.isStopPolling = this.stopPollingStatus.includes(res.status);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取当前应用最近的迁移状态
    async getMigrationProcessesLatest() {
      try {
        const res = await this.$store.dispatch('migration/getMigrationProcessesLatest', {
          appCode: this.appCode,
        });
        if (res.status === 'rollback_succeeded') {
          this.handleRollbackSuccessful();
        }
        this.migrationData = res;
        // 是否允许轮询
        this.isStopPolling = this.stopPollingStatus.includes(res.status);
        if (res.status === 'on_rollback') {
          // 如果当前应用正在回滚中，直接轮询当前接口
          this.pollingStatus();
        }
      } catch (e) {
        // 接口 404 表示当前应用未迁移
        if (e.status === 404) {
          this.isStopPolling = false;
          return;
        }
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isMainLoading = false;
        }, 500);
      }
    },
    // 轮询状态
    pollingStatus(queryId) {
      this.timerId = setInterval(() => {
        // 是否轮询
        if (this.isStopPolling) {
          clearInterval(this.timerId);
          return;
        }
        if (queryId) {
          this.queryMigrationStatus();
        } else {
          this.getMigrationProcessesLatest();
        }
      }, 2000);
    },
    handleRollbackSuccessful() {
      const newPath = `/developer-center/apps/${this.appCode}/default/summary`;
      window.history.replaceState(null, null, newPath);
      window.location.reload();
    },
  },
};
</script>

<style lang="scss" scoped>
.rollback-app-dialog-cls {
  font-size: 14px;
  .center {
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .rollback-title-wrapper {
    flex-direction: column;
  }
  .status-wrapper {
    .icon-cls {
      width: 42px;
      height: 42px;
      border-radius: 50%;

      &.warning {
        background-color: #ffe8c3;
        font-size: 18px;
        color: #ff9c01;
      }
      &.loading {
        transform: scale(0.6);
      }
      &.fail {
        background-color: #ffdddd;
        color: #ea3636;
        i {
          font-size: 28px;
          transform: translateY(0px);
        }
      }
    }
  }
  .dialog-title {
    margin-top: 19px;
    font-size: 20px;
    color: #313238;
  }
  .app-info-cls {
    .label {
      color: #63656e;
    }
    .app-code {
      color: #313238;
    }
  }
  .tips {
    margin-top: 16px;
    padding: 12px 16px;
    background: #f5f6fa;
    border-radius: 2px;
  }
}
.dialog-operate {
  margin-top: 24px;
  button {
    padding: 0 20px;
  }
}
</style>
