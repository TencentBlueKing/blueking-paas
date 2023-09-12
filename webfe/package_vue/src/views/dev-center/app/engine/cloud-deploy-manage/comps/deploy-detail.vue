<template>
  <div class="deploy-detail">
    <section class="instance-details">
      <div class="instance-item">
        <span class="label">运行实例数：</span>
        <span class="value">{{deployData.total_available_instance_count}}</span>
      </div>
      <div class="instance-item">
        <span class="label">期望实例数：</span>
        <span class="value">{{deployData.total_desired_replicas}}</span>
      </div>
      <div class="instance-item">
        <span class="label">异常实例数：</span>
        <span class="value">{{deployData.total_failed}}</span>
      </div>
    </section>

    <section class="process-table-wrapper">
      <bk-table
        v-bkloading="{ isLoading: isTableLoading }"
        :data="allProcesses"
        class="process-detail-table"
        border
      >
        <bk-table-column :label="$t('进程名称')" :width="190" class-name="table-colum-process-cls">
          <template slot-scope="{ row }">
            <div>
              <span>{{ row.name || '--' }}</span>
              <span class="ml5">{{ row.success }} / {{ row.totalCount }}</span>
              <div class="rejected-count" v-if="row.failed">{{ row.failed }}</div>
              <div class="icon-expand" v-if="row.instances.length > 1">
                <i
                  v-if="row.isExpand"
                  class="paasng-icon paasng-plus-circle"
                  @click="handleExpand(row)">
                </i>
                <i
                  v-else
                  class="paasng-icon paasng-minus-circle"
                  @click="handleExpand(row)">
                </i>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('实例名称')" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
            >
              {{ instance.display_name }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('状态')" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container status"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
            >
              <div
                class="dot"
                :class="instance.state"
              >
              </div>
              {{ instance.state }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('创建时间')" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
            >
              <template v-if="instance.date_time !== 'Invalid date'">
                {{ $t('创建于') }} {{ instance.date_time }}
              </template>
              <template v-else>
                --
              </template>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column label="" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
            >
              <bk-button class="mr10" :text="true" title="primary">
                查看日志
              </bk-button>
              <bk-button :text="true" title="primary">
                访问控制台
              </bk-button>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column label="进程操作" width="120" class-name="table-colum-operation-cls">
          <template slot-scope="{ row }">
            <div class="operation">
              <div class="operate-process-wrapper mr15">
                <div class="round-wrapper" v-if="row.targetStatus === 'start'">
                  <div class="square-icon" @click="handleProcessOperation(row, 'stop')"></div>
                </div>
                <i
                  class="paasng-icon paasng-play-circle-shape start"
                  v-else @click="handleProcessOperation(row, 'start')"></i>
              </div>
              <i class="paasng-icon paasng-log-2 detail mr10"></i>
              <bk-popover
                theme="light"
                ext-cls="more-operations"
                placement="bottom">
                <i class="paasng-icon paasng-ellipsis more"></i>
                <div slot="content" style="white-space: normal;">
                  <div class="option" @click="handleExpansionAndContraction">扩缩容</div>
                </div>
              </bk-popover>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </section>
  </div>
</template>

<script>
import moment from 'moment';
export default {
  props: {
    deploymentInfo: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      isTableLoading: false,
      isColumnExpand: true,
      deployData: {},
      allProcesses: [],
    };
  },

  watch: {
    deploymentInfo: {
      handler(value) {
        this.deployData = value;
        // this.handleDeployInstanceData();
        this.formatProcesses(this.deployData);
      },
      immediate: true,
      deep: true,
    },
  },

  methods: {
    handleExpand(row) {
      row.isExpand = !row.isExpand;
    },
    handleProcessOperation(row, type) {
      row.status = type;
    },
    handleExpansionAndContraction() {
      console.log('click');
    },
    // 处理进程与实例的关系
    // handleDeployInstanceData() {
    //   this.processData = this.deployData.processes.reduce((p, v) => {
    //     const instances = this.deployData.instances.filter((e) => {
    //       if (e.process_type === v.type) {
    //         e.date_time = moment(e.start_time).startOf('minute')
    //           .fromNow();
    //         return true;
    //       }
    //       return false;
    //     });
    //     v.instances = instances;
    //     v.totalCount = v.failed + v.success;
    //     p.push(v);
    //     console.log(p);
    //     return p;
    //   }, []);
    //   console.log(11113, this.processData);
    // },

    // 对数据进行处理
    formatProcesses(processesData) {
      const allProcesses = [];

      // 遍历进行数据组装
      const packages = processesData.proc_specs;
      const { instances } = processesData;

      processesData.processes.forEach((processItem) => {
        const { type } = processItem;
        const packageInfo = packages.find(item => item.name === type);

        const processInfo = {
          ...processItem,
          ...packageInfo,
          instances: [],
        };

        instances.forEach((instance) => {
          if (instance.process_type === type) {
            processInfo.instances.push(instance);
          }
        });

        // 作数据转换，以兼容原逻辑
        const process = {
          name: processInfo.name,
          instance: processInfo.instances.length,
          instances: processInfo.instances,
          targetReplicas: processInfo.target_replicas,
          isStopTrigger: false,
          targetStatus: processInfo.target_status,
          isActionLoading: false, // 用于记录进程启动/停止接口是否已完成
          maxReplicas: processInfo.max_replicas,
          status: 'Stopped',
          cmd: processInfo.command,
          desired_replicas: processInfo.replicas,
          available_instance_count: processInfo.success,
          failed: processInfo.failed,
          resourceLimit: processInfo.resource_limit,
          clusterLink: processInfo.cluster_link,
        };

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute')
            .fromNow();
        });
        allProcesses.push(process);
      });
      this.allProcesses = JSON.parse(JSON.stringify(allProcesses));
      console.log('this.allProcesses', this.allProcesses);
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-detail {

  .instance-details {
    display: flex;
  }

  .instance-item {
    flex: 1;
    display: flex;
    justify-content: center;
    border-right: 1px solid #EAEBF0;
    margin: 12px 0;
    span {
      line-height: 20px;
    }
    &:last-child {
      border-right: none;
      .value {
        color: #EA3636;
      }
    }
  }

  .process-table-wrapper {
    display: flex;
    position: relative;
    margin-bottom: 12px;
    padding: 0 24px;
  }

  .operation {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    i {
      font-size: 14px;
      cursor: pointer;
    }
    .start {
      color: #2DCB56 ;
    }
    .detail {
      color: #979BA5;
    }
    .more {
      transform: rotate(90deg);
      border-radius: 50%;
      padding: 3px;
      color: #63656E;
      &:hover {
        background: #F0F1F5;
      }
    }
  }

  .status-dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.faild {
      background: #EA3636;
      border: 3px solid #fce0e0;
    }
    &.running {
      background: #3FC06D;
      border: 3px solid #daefe4;
    }
  }

  .cell-container {
    position: relative;
    height: 46px;
    line-height: 46px;
  }

  // .process-detail-table {
  //   position: absolute !important;
  // }

  /deep/ .process-detail-table {
    .table-colum-instance-cls {
      border-right: none;
      .cell {
        display: block;
        height: 100%;
        padding: 0;

        .instance-item-cls  {
          border-bottom: 1px solid #dfe0e5;
          display: flex;
          justify-content: center;

          &:last-child {
            border-bottom: none;
          }

          &.status {
            align-items: center;
          }

          &.expand {
            display: block;
            display: flex;
          }

          &.close:nth-child(n + 2) {
            display: none;
          }
          &.close {
            border-bottom: none;
          }
        }
      }
      .bk-table-header-label {
        display: flex;
        justify-content: center;
      }
    }
    .table-colum-operation-cls {
      border-left: 1px solid #dfe0e5;
      border-bottom: 1px solid #dfe0e5;
      .cell {
        display: block;
        height: 100%;
        padding: 0;
      }
      .bk-table-header-label {
        padding: 0 15px;
      }
    }
    .table-colum-process-cls  {
      .cell {
        display: block;
        height: 100%;
        display: flex;
        align-items: center;
      }
    }
  }

  .rejected-count {
    display: inline-block;
    margin-left: 5px;
    width: 18px;
    height: 18px;
    text-align: center;
    line-height: 18px;
    color: #EA3636;
    background: #FEEBEA;
    border-radius: 9px;
  }
  .icon-expand {
    position: absolute;
    right: 0px;
    top: 50%;
    transform: translateY(-50%) translateX(50%);
    z-index: 99;
    cursor: pointer;
    i {
      &.paasng-plus-circle {
        margin-top: 1px;
        font-size: 14px;
        color: #2DCB56;
      }
      &.paasng-minus-circle {
        font-size: 12px;
        color: #FF9C01;
      }
    }
  }

  .operate-process-wrapper {
    cursor: pointer;
    .round-wrapper {
      margin-top: -2px;
      width: 14px;
      height: 14px;
      background: #EA3636;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .square-icon {
        width: 7px;
        height: 7px;
        background: #fff;
        border-radius: 1px;
    }
  }
  .dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.failed {
      background: #EA3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.warning {
      background: #FF9C01;
      border: 3px solid #ffefd6;
    }
    &.Running {
      background: #3FC06D;
      border: 3px solid #daefe4;
    }
  }
}
</style>
