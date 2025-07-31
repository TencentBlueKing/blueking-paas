<template>
  <bk-dialog
    v-model="visible"
    width="960"
    theme="primary"
    header-position="left"
    :mask-close="false"
    ext-cls="app-migration-dialog-cls"
    @after-leave="handleCancel"
  >
    <section slot="header">
      <span class="dialog-migration-title mr10">{{ `${data.name} ${$t('迁移为云原生应用')}` }}</span>
      <!-- 迁移中 -->
      <round-loading v-if="migrationData.status === 'on_migration'" class="migration-title-loading" />
    </section>
    <div class="app-migration-main" v-bkloading="{ isLoading: isMainLoading, zIndex: 10 }">
      <!-- 开始迁移 -->
      <section v-if="currentStep === 1">
        <p class="migration-title no-margin">{{ $t('迁移风险') }}</p>
        <div class="info-item mt16">
          <div class="title-wrapper">
            <bk-checkbox v-model="migrationRisk.address"></bk-checkbox>
            <span class="title">{{ $t('变更应用访问地址') }}</span>
            <span class="tips" v-bk-overflow-tips v-dompurify-html="domainsTips"></span>
          </div>
          <div class="content">
            <p>1. {{ $t('应用间不同模块间若通过 API 访问，需要修改调用地址') }}</p>
            <p>2. {{ $t('应用若对外提供了接口，需要通知所有调用方修改调用地址') }}</p>
            <p>3. {{ $t('应用若在 API 网关上注册了资源，可直接在 API 网关上修改，调用方不需要调整') }}</p>
          </div>
        </div>
        <div class="info-item">
          <div class="title-wrapper">
            <bk-checkbox v-model="migrationRisk.process"></bk-checkbox>
            <span class="title">{{ $t('变更进程间通信地址') }}</span>
            <span class="tips"
              v-bk-overflow-tips
              v-dompurify-html="namespaceTips"
            >
            </span>
          </div>
          <div class="content">
            {{ $t('可搜索应用代码、环境变量中是否有以下内容来确认') }}：
            <p>{{ `http://${data.region}-bkapp-${data.code}-` }}</p>
          </div>
        </div>
        <div class="info-item" v-if="appChecklistInfo.rcs_bindings">
          <div class="title-wrapper">
            <bk-checkbox v-model="migrationRisk.ip" disabled></bk-checkbox>
            <span class="title">{{ $t('变更出口 IP ') }}</span>
          </div>
          <div class="content">
            {{ $t('当前应用绑定了出口 IP，暂不支持迁移。并且无法勾选') }}
          </div>
        </div>
        <bk-alert type="warning" class="alert-tip-cls" :show-icon="false">
          <div slot="title" class="alert-warning">
            <i class="paasng-icon paasng-remind"></i>
            <span>{{ $t('点击“开始迁移”后，应用服务将不会受到任何影响') }}</span>
            <a
              target="_blank"
              :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/cloud_native_migration'"
              class="link"
            >
              <i class="paasng-icon paasng-process-file"></i>
              {{ $t('查看迁移文档') }}
            </a>
          </div>
        </bk-alert>
      </section>
      <!-- 确定迁移 -->
      <section v-else>
        <div class="migration-status">
          <!-- 成功、失败、未执行 -->
          <div class="item mt10" v-for="(item, index) in migrateStateData" :key="index">
            <div
              class="dot-status mr10"
              :class="item.status"
              v-bk-tooltips="{ content: item.errorMsg, disabled: item.status !== 'failed' }">
              <img src="/static/images/not-executed-icon.png" v-if="item.status === 'not-executed'">
              <i :class="['paasng-icon', item.icon]" v-else></i>
            </div>
            <span class="title">{{ item.title }}</span>
          </div>
        </div>
        <template v-if="isMigrationStepSuccessful">
          <!-- 当前状态成功，表示后台已经把这应用转成了 云原生应用 -->
          <p class="migration-title">{{ $t('部署应用并验证功能') }}</p>
          <div class="info-item mt16">
            <div class="title-wrapper">
              <!-- 监测模块没有部署，则不能进行勾选 -->
              <bk-checkbox v-model="verifyFunctionality.module"></bk-checkbox>
              <span class="title">{{ $t('已成功部署应用下每个模块') }}</span>
              <bk-button
                :text="true"
                title="primary"
                @click="handleToDeploy"
              >
                {{ $t('去部署') }}
              </bk-button>
            <!-- 重新部署 -->
            </div>
            <div class="content">
              {{ $t('如果有 Celery 等后台任务，同时部署(普通和云原生进程都存在时)可能会导致任务抢占，请确认影响。') }}
            </div>
          </div>
          <bk-alert type="warning" class="alert-tip-cls" :show-icon="false">
            <div slot="title" class="alert-warning">
              <i class="paasng-icon paasng-remind"></i>
              <span>{{ $t('点击“确认迁移”后，会停掉应用迁移前的进程，并将桌面的访问入口切换为新的访问地址。') }}</span>
              <a
                target="_blank"
                :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/cloud_native_migration'"
                class="link"
              >
                <i class="paasng-icon paasng-process-file"></i>
                {{ $t('查看迁移文档') }}
              </a>
            </div>
          </bk-alert>
        </template>
        <section v-else class="migration-status-diagram">
          <!-- 迁移失败 -->
          <bk-exception
            v-if="isMigrationStepFailed"
            class="migration-exception-wrap"
            type="500"
          >
            <span class="title">{{ $t('云原生迁移失败') }}</span>
            <div class="msg">{{ migrationFailureTip }}</div>
          </bk-exception>
          <!-- 迁移中 -->
          <div class="migrating" v-else>
            <img src="/static/images/migrating.png">
            <p>{{ $t('云原生应用迁移中') }}…</p>
          </div>
        </section>
      </section>
    </div>
    <section slot="footer">
      <bk-button
        v-if="isMigrationStepFailed"
        class="ml10"
        :theme="'primary'"
        @click="handleReMigrate(migrationData.id)">
        {{ $t('重试') }}
      </bk-button>
      <bk-button
        v-else
        class="ml10"
        :theme="'primary'"
        :loading="isConfirmMigrationLoading"
        :disabled="isMigrationDisabled"
        @click="handleAppMigration">
        {{ isStartMigration ? $t('开始迁移') : $t('确定迁移') }}
      </bk-button>
      <bk-button
        class="ml10"
        :theme="'default'"
        type="submit"
        @click="handleCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </section>
  </bk-dialog>
</template>

<script>
import { cloneDeep } from 'lodash';
import i18n from '@/language/i18n.js';
const defaultStateData = {
  WlAppBackupMigrator: {
    icon: 'paasng-ellipsis',
    title: i18n.t('备份应用配置'),
    status: 'not-executed',
    errorMsg: '',
  },
  ApplicationTypeMigrator: {
    icon: 'paasng-ellipsis',
    title: i18n.t('变更应用类型'),
    status: 'not-executed',
    errorMsg: '',
  },
  ApplicationClusterMigrator: {
    icon: 'paasng-ellipsis',
    title: i18n.t('配置部署集群'),
    status: 'not-executed',
    errorMsg: '',
  },
  BuildConfigMigrator: {
    icon: 'paasng-ellipsis',
    title: i18n.t('迁移构建配置'),
    status: 'not-executed',
    errorMsg: '',
  },
};
const MAX_ATTEMPTS = 60;
export default {
  name: 'AppMigrationDialog',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
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
      visible: false,
      currentStep: 1,
      // 单选框数据结构
      timerId: null,
      processId: null,
      isMigrationCompleted: false,
      isStopPolling: false,
      migrationData: {
        details: {},
      },
      // 迁移风险
      migrationRisk: {
        address: false,
        process: false,
        ip: false,
      },
      verifyFunctionality: {
        module: false,
      },
      migrateStateData: cloneDeep(defaultStateData),
      isMigrating: false,
      isPollingLatest: false,
      isMainLoading: false,
      dialogConfig: {
        isReMigrateLoading: false,
      },
      appChecklistInfo: {},
      initStatus: '',
      attempts: 0,
      confirmMigrationIntervalId: null,
      isConfirmMigrationLoading: false,
    };
  },
  computed: {
    isStartMigration() {
      return this.currentStep === 1;
    },
    isMigrationDisabled() {
      // 开始迁移
      if (this.isStartMigration) {
        const areAllChecked = this.handleAreAllChecked(this.migrationRisk);
        return !areAllChecked;
      }
      if (this.currentStep === 2) {
        const areAllChecked = this.handleAreAllChecked(this.verifyFunctionality);
        // 确定迁移
        return this.migrationData.status === 'migration_succeeded' ? !areAllChecked : true;
      }
      // 确定迁移
      return true;
    },
    migrationsList() {
      return this.migrationData.details?.migrations || [];
    },
    // 迁移成功
    isMigrationStepSuccessful() {
      return this.migrationData.status === 'migration_succeeded';
    },
    // 迁移失败
    isMigrationStepFailed() {
      return this.migrationData.status === 'migration_failed';
    },
    // 已确定迁移为云原生应用
    isMigrationConfirmed() {
      return this.migrationData.status === 'confirmed';
    },
    migrationFailureTip() {
      for (const key in this.migrateStateData) {
        if (this.migrateStateData[key].errorMsg !== '') {
          return this.migrateStateData[key].errorMsg;
        }
      }
      return '--';
    },
    domainsTips() {
      return this.$t('如 {l} 变更为：<em>{c}</em>', { l: this.appChecklistInfo.rootDomainsLegacy || '--', c: this.appChecklistInfo.rootDomainsCnative || '--' });
    },
    namespaceTips() {
      return this.$t('如 {l} 变更为：<em>{c}</em>', {
        l: '{region}-bkapp-{appId}-m-{moduleName}-{env}-{processName}',
        c: '{appId}-m-{moduleName}-{processName}',
      });
    },
  },
  watch: {
    value: {
      async handler(newVal) {
        this.visible = newVal;
        if (newVal) {
          this.isMainLoading = true;
          await Promise.all([this.getMigrationProcessesLatest(), this.getChecklistInfo()]);
          // 初始状态
          this.initStatus = this.migrationData.status;
        }
      },
      immediate: true,
    },
    migrationsList(list) {
      list.forEach((item) => {
        if (this.migrateStateData[item.migrator_name]) {
          this.migrateStateData[item.migrator_name].status = item.is_succeeded ? 'success' : 'failed';
          this.migrateStateData[item.migrator_name].icon = item.is_succeeded ? 'paasng-correct' : 'paasng-icon-close';
          this.migrateStateData[item.migrator_name].errorMsg = item.error_msg;
        }
      });
      // list为空数组处理
    },
  },
  methods: {
    // 迁移处理
    handleAppMigration() {
      if (this.isStartMigration) {
        this.startMigration(); // 开始迁移
      } else {
        this.migrationProcessesConfirm(); // 确定迁移
      }
    },
    // 当前事项是否勾选
    handleAreAllChecked(data) {
      return Object.values(data).every(value => value === true);
    },
    // 刷新操作
    async handleWindowReload() {
      // 当前状态与进入时的初始状态不同，且为迁移成功状态，需要刷新当前页
      if (this.initStatus !== this.migrationData.status && (this.isMigrationStepSuccessful || this.isMigrationConfirmed)) {
        if (this.$route.name === 'myApplications') {
          // 列表页直接刷新
          window.location.reload();
        } else {
          await this.$router.push({
            name: 'cloudAppSummary',
            params: {
              id: this.data.code,
            },
          });
          window.location.reload();
        }
      }
    },
    // 弹窗关闭处理
    async handleCancel(isReload = true) {
      this.$emit('change', false);
      // 确定迁移阶段
      if (this.confirmMigrationIntervalId) {
        clearInterval(this.confirmMigrationIntervalId);
        this.reset();
        return;
      }
      // 停止轮询
      clearInterval(this.timerId);
      if (isReload) {
        await this.handleWindowReload();
      }
      this.reset();
    },
    reset() {
      this.currentStep = 1;
      this.processId = null;
      this.isPollingLatest = false;
      this.isConfirmMigrationLoading = false;
      this.migrateStateData = cloneDeep(defaultStateData);
      this.migrationData = { details: {} };
      Object.keys(this.migrationRisk).forEach((key) => {
        this.migrationRisk[key] = false;
      });
      Object.keys(this.verifyFunctionality).forEach((key) => {
        this.verifyFunctionality[key] = false;
      });
    },
    // 获取当前应用最近的迁移状态
    async getMigrationProcessesLatest() {
      try {
        const res = await this.$store.dispatch('migration/getMigrationProcessesLatest', {
          appCode: this.data.code,
        });
        // 迁移失败停止轮询
        this.isStopPolling = res.status !== 'on_migration';
        this.migrationData = res;
        this.processId = res.id;
        this.currentStep = res.status === 'rollback_succeeded' ? 1 : 2;
        // 是否正在迁移
        this.isMigrating = res.status === 'on_migration';
        if (this.isMigrating && !this.isPollingLatest) {
          // 如果当前应用正在迁移中，直接轮询当前接口
          this.pollingStatus();
        }
      } catch (e) {
        // 接口 404 表示当前应用未迁移
        if (e.status === 404) {
          this.currentStep = 1;
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
    // 迁移前的 check_list 信息接口
    async getChecklistInfo() {
      try {
        const res = await this.$store.dispatch('migration/getChecklistInfo', {
          appCode: this.data.code,
        });
        this.appChecklistInfo = res;
        // root_domains 变更应用访问地址
        if (res.root_domains) {
          const { legacy, cnative } = res.root_domains;
          this.appChecklistInfo.rootDomainsLegacy = legacy.length ? legacy.map(v => `*.${v}`).join() : '--';
          this.appChecklistInfo.rootDomainsCnative = cnative.length ? cnative.map(v => `*.${v}`).join() : '--';
        }
        // 变更出口 IP
        if (!this.appChecklistInfo.rcs_bindings) {
          delete this.migrationRisk.ip;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 开始迁移
    async startMigration(id) {
      try {
        const res = await this.$store.dispatch('migration/triggerMigration', {
          appCode: this.data.code || id,
        });
        this.processId = res.process_id;
        this.currentStep = 2;
        this.queryMigrationStatus();
        // 查询状态
        this.pollingStatus();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.dialogConfig.isReMigrateLoading = false;
        this.isMainLoading = false;
      }
    },
    // 轮询状态
    pollingStatus() {
      this.timerId = setInterval(() => {
        // 是否轮询
        if (this.isStopPolling) {
          clearInterval(this.timerId);
          return;
        }
        if (this.isMigrating) {
          this.getMigrationProcessesLatest();
          this.isPollingLatest = true;
        } else {
          this.queryMigrationStatus();
        }
      }, 2000);
    },
    // 查询状态
    async queryMigrationStatus() {
      try {
        const res = await this.$store.dispatch('migration/queryMigrationStatus', {
          id: this.processId,
        });
        this.migrationData = res;
        // res.status
        // 迁移失败（migration_failed）
        // 迁移中（on_migration）
        // 迁移成功（migration_succeeded）
        // 已经确认迁移 （confirmed）
        // 其他清空停止轮询
        this.isStopPolling = res.status !== 'on_migration';
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 确定迁移
    async migrationProcessesConfirm() {
      this.isConfirmMigrationLoading = true;
      try {
        await this.$store.dispatch('migration/migrationProcessesConfirm', {
          id: this.processId,
        });
        // 确定迁移轮询状态
        this.confirmMigrationPolling();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        this.isConfirmMigrationLoading = false;
      }
    },
    // 确定迁移轮询
    confirmMigrationPolling() {
      this.confirmMigrationIntervalId = setInterval(async () => {
        this.attempts++;
        this.queryMigrationStatus();

        // 检查是否达到最大尝试次数，或已经确定迁移成功
        if (this.attempts >= MAX_ATTEMPTS || this.isMigrationConfirmed) {
          clearInterval(this.confirmMigrationIntervalId);
          this.confirmMigrationIntervalId = null;
          this.handleCancel();
        }
      }, 2000); // 每隔2秒轮询一次
    },
    // 重新迁移
    handleReMigrate(id) {
      if (this.dialogConfig.isReMigrateLoading) {
        return;
      }
      this.dialogConfig.isReMigrateLoading = true;
      this.isMainLoading = true;
      this.isStopPolling = false;
      this.currentStep = 2;
      this.startMigration(id);
    },
    // 部署
    async handleToDeploy() {
      // 重新获取当前应用信息
      const appCode = this.data.code || this.$route.params.id;
      await Promise.all([this.$store.dispatch('getAppInfo', { appCode }), this.$store.dispatch('getAppFeature', { appCode })]);
      this.handleCancel(false);
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.data.code,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.app-migration-main {
  .migration-title {
    margin-top: 24px;
    font-weight: 700;
    font-size: 16px;
    color: #313238;

    &.no-margin {
      margin-top: 10px;
    }
  }
  .alert-tip-cls {
    margin-top: 24px;
  }
  .migration-status {
    padding-bottom: 24px;
    border-bottom: 1px solid #dcdee5;
    .item {
      display: flex;
      align-items: center;
      .title {
        color: #313238;
      }
      .retry-wrapper {
        margin-left: 15px;
        color: #3A84FF;
        cursor: pointer;

        i, span {
          user-select: none;
          margin-right: 3px;
          font-size: 14px;
          &.paasng-refresh-line {
            transform: translateY(-1px);
          }
        }
      }
    }
    .dot-status {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 21px;
      height: 21px;
      border-radius: 50%;
      color: #63656E;
      background-color: #F5F7FA;

      img {
        width: 21px;
        height: 21px;
      }

      &.success {
        color: #3FC06D;
        background-color: #E5F6EA;
      }

      &.failed {
        color: #EA3636;
        background-color: #FFDDDD;
      }
    }
    i {
      font-size: 16px;
      transform: translateY(0px);
    }
  }
  .migration-status-diagram {
    display: flex;
    justify-content: center;
    margin: 100px 0;

    .migrating {
      font-size: 14px;
      color: #63656E;
      text-align: center;
      img {
        width: 220px;
        height: 100px;
      }
    }

    .migration-exception-wrap {
      height: 158px;
      :deep(.bk-exception-img) .exception-image {
        height: 100px;
      }
      .title {
        font-size: 14px;
        color: #63656E;
      }
      .msg {
        font-size: 12px;
        color: #979BA5;
      }

    }
  }
  .alert-warning {
    font-size: 12px;
    color: #63656E;
    i.paasng-remind {
      font-size: 14px;
      color: #FF9C01;
      margin-right: 10px;
      transform: translateY(0);
    }
    .link {
      i {
        margin-left: 5px;
      }
      color: #3A84FF;
      cursor: pointer;
    }
  }

  .mt16 {
    margin-top: 16px !important;
  }

  .info-item {
    margin-top: 32px;
    :deep(.tips) {
      em {
        font-weight: 700;
      }
    }

    .title-wrapper {
      display: flex;
      align-items: center;
      .bk-form-checkbox {
        flex-shrink: 0;
      }
      .title {
        margin: 0 16px 0 12px;
        font-weight: 700;
        font-size: 14px;
        color: #313238;
        flex-shrink: 0;
      }
      .tips {
        font-size: 12px;
        color: #979ba5;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
    }

    .content {
      margin-top: 8px;
      padding: 12px 24px;
      background: #f5f7fa;
      border-radius: 2px;
      font-size: 12px;
      color: #63656E;
      line-height: 20px;
    }
  }
}
</style>

<style lang="scss">
.app-migration-dialog-cls.bk-dialog-wrapper .header-on-left {
  padding: 3px 24px 10px;
  .dialog-migration-title {
    font-size: 20px;
    color: #313238;
  }
  .migration-title-loading {
    transform: translateY(-2px);
  }
}
</style>
