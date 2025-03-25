<template>
  <div class="migration-process-management">
    <section class="top-warpper">
      <bk-radio-group v-model="curEnvValue">
        <bk-radio-button value="stag">
          {{ $t('预发布环境') }}
        </bk-radio-button>
        <bk-radio-button value="prod">
          {{ $t('生产环境') }}
        </bk-radio-button>
      </bk-radio-group>
      <div class="module-select">
        <bk-select
          v-model="curModuleValue"
          style="width: 240px"
          :clearable="false"
          ext-cls="select-custom"
          @change="handlerModuleChange"
        >
          <bk-option
            v-for="option in curAppModuleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
        </bk-select>
      </div>
    </section>
    <!-- 进程信息 -->
    <section class="process-table-wrapper">
      <bk-table
        :data="allProcesses"
        :outer-border="false"
        size="small"
        ext-cls="app-process-table-cls"
        v-bkloading="{ isLoading: isProcessTableLoading, zIndex: 10 }"
        :row-key="rowKey"
        @expand-change="handleExpandChange"
      >
        <bk-table-column
          type="expand"
          width="30"
        >
          <template slot-scope="props">
            <bk-table
              :data="props.row.instancesList"
              :outer-border="false"
              :header-cell-style="{ background: '#F5F7FA', borderRight: 'none' }"
              ext-cls="process-children-table-cls"
            >
              <bk-table-column
                prop="display_name"
                :label="$t('实例名称')"
              ></bk-table-column>
              <bk-table-column :label="$t('状态')">
                <template slot-scope="{ row }">
                  <span :class="['instance-status', { failed: row.rich_status !== 'Running' }]"></span>
                  <span
                    v-bk-tooltips="{ content: getInstanceStateToolTips(row) }"
                    v-dashed
                  >
                    {{ row.rich_status }}
                  </span>
                </template>
              </bk-table-column>
              <bk-table-column
                prop="start_time"
                :label="$t('创建时间')"
              ></bk-table-column>
            </bk-table>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('进程名称')"
          width="240"
        >
          <template slot-scope="{ row }">
            <div>
              <span>{{ row.type || '--' }}</span>
            </div>
            <div
              class="scaling-dot mt5"
              v-if="row.autoscaling"
            >
              {{ $t('自动扩缩容') }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('实例数')"
          width="100"
        >
          <template slot-scope="{ row }">
            <div>
              <span class="ml5">{{ row.success }} / {{ row.replicas }}</span>
              <span
                class="failed-dot"
                v-if="Number(row.failed) > 0"
              >
                {{ row.failed }}
              </span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('命令')"
          show-overflow-tooltip
          prop="command"
        ></bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          width="240"
        >
          <template slot-scope="{ row }">
            <div class="operation">
              <!-- 启动中 / 停止中展示 -->
              <div
                v-if="!isNormalStatus(row)"
                class="flex-row align-items-center mr10"
              >
                <img
                  src="/static/images/btn_loading.gif"
                  class="loading"
                />
                <span
                  class="pl10"
                  style="white-space: nowrap"
                >
                  <span v-if="isStarting(row)">{{ $t('启动中...') }}</span>
                  <span v-else>{{ $t('停止中...') }}</span>
                </span>
              </div>
              <!-- 进程操作 -->
              <div class="process-operation">
                <div class="operate-process-wrapper mr15">
                  <!-- 必须有进程才能停止进程 -->
                  <bk-popconfirm
                    v-bk-tooltips="$t('停止进程')"
                    v-if="!!row.success"
                    :content="$t('确认停止该进程？')"
                    width="288"
                    trigger="click"
                    @confirm="handleUpdateProcess('stop')"
                  >
                    <div
                      class="round-wrapper"
                      @click="handleProcessOperation(row)"
                    >
                      <div class="square-icon"></div>
                    </div>
                  </bk-popconfirm>
                  <div v-else>
                    <bk-popconfirm
                      v-bk-tooltips="$t('启动进程')"
                      :content="$t('确认启动该进程？')"
                      width="288"
                      trigger="click"
                      @confirm="handleUpdateProcess('start')"
                    >
                      <i
                        class="paasng-icon paasng-play-circle-shape start"
                        @click="handleProcessOperation(row)"
                      ></i>
                    </bk-popconfirm>
                  </div>
                </div>
                <!-- 扩缩容操作 -->
                <bk-popover
                  theme="light"
                  ext-cls="more-operations"
                  placement="bottom"
                  :tippy-options="{ hideOnClick: false }"
                >
                  <i class="paasng-icon paasng-ellipsis more"></i>
                  <div
                    slot="content"
                    style="white-space: normal"
                  >
                    <div
                      class="option"
                      @click="handleExpansionAndContraction(row)"
                    >
                      {{ $t('扩缩容') }}
                    </div>
                  </div>
                </bk-popover>
              </div>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </section>

    <!-- 扩缩容 -->
    <scaling-dialog
      v-model="scalingDialogConfig.visiable"
      :data="scalingData"
      @get-process-list="getProcessesList"
    ></scaling-dialog>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import scalingDialog from './scaling-dialog';

export default {
  name: 'MigrationProcessManagement',
  components: {
    scalingDialog,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      curEnvValue: 'stag',
      curModuleValue: 'default',
      allProcesses: [],
      curProcess: {},
      isProcessTableLoading: false,
      curUpdateProcess: {},
      pollingId: null,
      scalingDialogConfig: {
        visiable: false,
      },
      scalingData: {},
      autoScalDisableConfig: {},
    };
  },
  watch: {
    $route() {
      this.init();
    },
    curEnvValue() {
      this.getProcessesList();
    },
  },
  created() {
    this.init();
  },
  beforeDestroy() {
    this.stopPolling();
  },
  methods: {
    init() {
      if (!this.curAppInfo.migration_status) return;
      this.getProcessesList();
      this.getAutoScalFlag();
    },
    handlerModuleChange() {
      this.getProcessesList();
    },
    // 获取进程列表
    async getProcessesList(isLoading = true) {
      this.isProcessTableLoading = isLoading;
      try {
        const res = await this.$store.dispatch('migration/getProcessesList', {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
          env: this.curEnvValue,
        });
        this.allProcesses = this.formatProcesses(res);

        // 进程列表中的进程状态是否正常，否则轮询进程接口
        let curProcess = null;
        this.allProcesses.forEach((process) => {
          if (!this.isNormalStatus(process)) {
            curProcess = process;
          }
        });
        if (curProcess && !this.pollingId) {
          // 轮询
          this.pollingProcesses(curProcess.type);
        }
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isProcessTableLoading = false;
      }
    },
    // 进程数据处理
    formatProcesses(processesData) {
      if (!Object.keys(processesData).length) {
        return [];
      }
      // processes 进程数据
      // instances 实例数据
      const processes = processesData.processes.items;
      const instances = processesData.instances.items;
      const packages = processesData.process_packages;

      processes.forEach((processeItem) => {
        const packageInfo = packages.find((item) => item.name === processeItem.type) || {};
        processeItem.instancesList = [];
        processeItem.autoscaling = packageInfo.autoscaling;
        // 普通扩缩容
        processeItem.max_replicas = packageInfo.max_replicas;
        processeItem.target_replicas = packageInfo.target_replicas;
        // 自动扩缩容，autoscaling为false时值为null
        processeItem.scaling_config = packageInfo.scaling_config;
        processeItem.resource_limit = packageInfo.resource_limit || {};
        instances.forEach((instanceItem) => {
          if (processeItem.type === instanceItem.process_type) {
            processeItem.instancesList.push(instanceItem);
          }
        });
      });

      return processes;
    },
    // 轮询进程列表
    pollingProcesses(processType) {
      this.pollingId = setInterval(() => {
        const curProcess = this.allProcesses.find((process) => process.type === processType) || {};
        // 正常状态停止轮询
        if (this.isNormalStatus(curProcess)) {
          this.stopPolling();
          return;
        }
        this.getProcessesList(false);
      }, 3000);
    },
    // 停止轮询
    stopPolling() {
      clearInterval(this.pollingId);
      this.pollingId = null;
    },
    // 当前操作进程信息
    handleProcessOperation(row) {
      this.curUpdateProcess = row; // 当前点击的进程
    },
    // 当前进程是否为正常状态
    isNormalStatus(row) {
      // 分母为0的情况, row.success === row.replicas 正常状态
      if (row.replicas === 0) return row.success === row.replicas;
      // row.success / row.replicas === 1 正常状态
      return row.success / row.replicas === 1;
    },
    // 启动中
    isStarting(row) {
      // 分母为0的情况, row.success < row.replicas 启动中
      if (row.replicas === 0) return row.success < row.replicas;
      return row.success / row.replicas < 1;
    },
    // 确认操作
    handleUpdateProcess(status) {
      this.updateProcess(status);
    },
    // 启停进程操作
    async updateProcess(status) {
      const process = this.curUpdateProcess;

      const patchData = {
        process_type: process.type,
        //  start(启动), stop(停止), scale(扩缩容)
        operate_type: status,
      };
      try {
        await this.$store.dispatch('migration/updateProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
          env: this.curEnvValue,
          data: patchData,
        });
        this.getProcessesList(false);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取进程状态 tooltips 展示内容
    getInstanceStateToolTips(instance) {
      if (!(instance.state_message && instance.state_message.length)) {
        return instance.rich_status;
      }
      return instance.state_message;
    },
    // 扩缩容弹窗
    handleExpansionAndContraction(row) {
      this.scalingDialogConfig.visiable = true;
      this.scalingData = {
        appCode: this.appCode,
        env: this.curEnvValue,
        moduleId: this.curModuleValue,
        type: row.type,
        enableAutoscaling: this.autoScalDisableConfig.ENABLE_AUTOSCALING,
        autoscaling: row.autoscaling || false,
        success: row.success,
        maxReplicas: row.max_replicas,
        scalingConfig: row.scaling_config,
      };
    },
    /**
     * 是否支持自动扩缩容
     */
    async getAutoScalFlag() {
      try {
        const res = await this.$store.dispatch('deploy/getAutoScalFlagWithEnv', {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
          env: this.curEnvValue,
        });
        this.autoScalDisableConfig = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 行key
    rowKey(row) {
      return row.module_name;
    },
    handleExpandChange(row, expandedRows) {
      if (expandedRows.length) {
        // 展开实例重新获取进程信息
        this.getProcessesList(false);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.migration-process-management {
  margin: 24px;
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;

  .top-warpper {
    display: inline-flex;
    .module-select {
      margin-left: 16px;
    }
  }

  .process-table-wrapper {
    margin-top: 16px;

    .failed-dot {
      display: inline-block;
      height: 16px;
      line-height: 16px;
      padding: 0 5px;
      border-radius: 10px;
      background: #feebea;
      color: #ea3636;
    }

    .instance-status {
      margin-right: 7px;
      position: relative;
      display: inline-block;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: #3fc06d29;
      transform: translateY(2px);

      &::before {
        content: '';
        position: absolute;
        width: 7px;
        height: 7px;
        background: #3fc06d;
        top: 50%;
        left: 50%;
        border-radius: 50%;
        transform: translate(-50%, -50%);
      }

      &.failed {
        background: #ea363629;
        &::before {
          background: #ea3636;
        }
      }
    }
  }

  .app-process-table-cls {
    .bk-table-expanded-cell {
      background: #dcdee5;
    }
  }
}

.operation {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 10px;
  i {
    font-size: 20px;
    cursor: pointer;
  }
  .start {
    color: #2dcb56;
    font-size: 20px;
  }
  .detail {
    color: #979ba5;

    &:hover {
      color: #63656e;
    }
  }
}

// 进程操作
.process-operation {
  height: 100%;
  display: flex;
  align-items: center;
  i {
    font-size: 20px;
    cursor: pointer;
  }
  .start {
    color: #2dcb56;
    font-size: 20px;
  }
  .detail {
    color: #979ba5;

    &:hover {
      color: #63656e;
    }
  }
  .more {
    transform: rotate(90deg);
    border-radius: 50%;
    padding: 3px;
    color: #63656e;
    &:hover {
      background: #f0f1f5;
    }
  }
  .operate-process-wrapper {
    cursor: pointer;
    .round-wrapper {
      margin-top: -2px;
      width: 20px;
      height: 20px;
      background: #ea3636;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .square-icon {
      width: 8px;
      height: 8px;
      background: #fff;
      border-radius: 1px;
    }
  }
}

// 进程详情侧栏
.slider-detail-wrapper {
  padding: 0 20px 20px 20px;
  line-height: 32px;
  .title {
    display: block;
    padding-bottom: 2px;
    color: #313238;
    border-bottom: 1px solid #dcdee5;
  }
  .detail-item {
    display: flex;
    justify-content: flex-start;
    line-height: 32px;
    .label {
      color: #313238;
    }
  }
}
.action-btn {
  position: relative;
  height: 28px;
  line-height: 28px;
  min-width: 28px;
  display: flex;
  border-radius: 2px;
  cursor: pointer;

  .text {
    min-width: 90px;
    line-height: 28px;
    text-align: left;
    color: #63656e;
    font-size: 12px;
    display: inline-block;
  }

  .left-icon,
  .right-icon {
    width: 28px;
    height: 28px;
    line-height: 28px;
    color: #c4c6cc;
    display: inline-block;
    text-align: center;
  }

  &.refresh {
    width: 28px;
  }
}
</style>

<style lang="scss">
.migration-process-management .process-table-wrapper {
  .app-process-table-cls {
    .bk-table-expanded-cell {
      background: #fafbfd;
      tbody .bk-table-row {
        background-color: #fafbfd;
      }
    }
  }
}
.more-operations .tippy-tooltip .tippy-content {
  cursor: pointer;
  &:hover {
    color: #3a84ff;
  }
}
</style>
