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
            <!-- <span class="tips">{{ $t('如 bk-audit.bkapps.woa.com 变更为：bk-audit.bkapps-sz1.woa.com') }}</span> -->
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
          </div>
          <div class="content">
            {{ $t('可搜索应用代码、环境变量中是否有以下内容来确认') }}
          </div>
        </div>
        <bk-alert type="warning" class="alert-tip-cls" :show-icon="false">
          <div slot="title" class="alert-warning">
            <i class="paasng-icon paasng-remind"></i>
            <span>{{ $t('点击“开始迁移”后，应用服务将不会受到任何影响') }}</span>
            <span class="link">
              <i class="paasng-icon paasng-process-file"></i>
              {{ $t('查看迁移文档') }}
            </span>
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
              <span class="title">{{ $t('重新部署应用下每个模块') }}</span>
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
              如果有 Celery 等后台任务，同时部署 2 分可能会导致任务抢占，请确认影响
            </div>
          </div>
          <!-- 后续接口添加 -->
          <!-- <div class="info-item">
            <div class="title-wrapper">
              <bk-checkbox v-model="verifyFunctionality.ip"></bk-checkbox>
              <span class="title">{{ $t('域名解析到 IP') }}</span>
            </div>
            <div class="content">
              --
            </div>
          </div> -->
          <bk-alert type="warning" class="alert-tip-cls" :show-icon="false">
            <div slot="title" class="alert-warning">
              <i class="paasng-icon paasng-remind"></i>
              <span>{{ $t('点击“确认迁移”后，会停掉应用迁移前的进程，并将桌面的访问入口切换为新的访问地址。') }}</span>
              <span class="link">
                <i class="paasng-icon paasng-process-file"></i>
                {{ $t('查看迁移文档') }}
              </span>
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
const defaultStateData = {
  ApplicationTypeMigrator: {
    icon: 'paasng-ellipsis',
    title: '变更应用类型',
    status: 'not-executed',
    errorMsg: '',
  },
  ApplicationClusterMigrator: {
    icon: 'paasng-ellipsis',
    title: '配置部署集群',
    status: 'not-executed',
    errorMsg: '',
  },
  BuildConfigMigrator: {
    icon: 'paasng-ellipsis',
    title: '迁移构建配置',
    status: 'not-executed',
    errorMsg: '',
  },
};
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
  },
  watch: {
    value: {
      handler(newVal) {
        this.visible = newVal;
        if (newVal) {
          console.log('22', this.migrationFailureTip);
          this.isMainLoading = true;
          this.getMigrationProcessesLatest();
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
    // 弹窗关闭处理
    handleCancel() {
      this.$emit('change', false);
      // 停止轮询
      clearInterval(this.timerId);
      this.reset();
    },
    reset() {
      this.currentStep = 1;
      this.processId = null;
      this.isPollingLatest = false;
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
        this.currentStep = 2;
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
    // 开始迁移
    async startMigration(id) {
      try {
        const res = await this.$store.dispatch('migration/triggerMigration', {
          appCode: this.data.code || id,
        });
        this.processId = res.process_id;
        this.currentStep = 2;
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
      try {
        await this.$store.dispatch('migration/migrationProcessesConfirm', {
          id: this.processId,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('迁移成功'),
        });
        this.handleCancel();
        // 迁移成功重新获取应用列表？？
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
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
    handleToDeploy() {
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

    .title-wrapper {
      display: flex;
      align-items: center;
      .title {
        margin: 0 16px 0 12px;
        font-weight: 700;
        font-size: 14px;
        color: #313238;
      }
      .tips {
        font-size: 12px;
        color: #979ba5;
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
