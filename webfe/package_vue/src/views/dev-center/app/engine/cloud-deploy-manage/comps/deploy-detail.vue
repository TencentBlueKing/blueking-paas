<template>
  <div class="deploy-detail">
    <section class="instance-details">
      <div class="instance-item">
        <span class="label">{{$t('运行实例数')}}：</span>
        <span class="value">{{deployData.total_available_instance_count}}</span>
      </div>
      <div class="instance-item">
        <span class="label">{{$t('期望实例数')}}：</span>
        <span class="value">{{deployData.total_desired_replicas}}</span>
      </div>
      <div class="instance-item">
        <span class="label">{{$t('异常实例数')}}：</span>
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
              <span class="ml5">{{ row.available_instance_count }} / {{ row.targetReplicas }}</span>
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
                {{$t('查看日志')}}
              </bk-button>
              <bk-button :text="true" title="primary">
                {{$t('访问控制台')}}
              </bk-button>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('进程操作')" width="120" class-name="table-colum-operation-cls" :render-header="$renderHeader">
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
              <i
                v-bk-tooltips="$t('进程详情')"
                class="paasng-icon paasng-log-2 detail mr10"
                @click="showProcessDetailDialog(row)"></i>
              <bk-popover
                theme="light"
                ext-cls="more-operations"
                placement="bottom">
                <i class="paasng-icon paasng-ellipsis more"></i>
                <div slot="content" style="white-space: normal;">
                  <div class="option" @click="handleExpansionAndContraction">{{$t('扩缩容')}}</div>
                </div>
              </bk-popover>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </section>

    <bk-sideslider
      :width="750"
      :is-show.sync="chartSlider.isShow"
      :title="chartSlider.title"
      :quick-close="true"
      :before-close="handleChartBeforeClose"
      @hidden="handlerChartHide"
    >
      <div
        slot="content"
        class="p0 chart-wrapper"
      >
        <div
          v-if="curAppInfo.feature.RESOURCE_METRICS"
          v-bk-clickoutside="hideDatePicker"
          class="action-box"
        >
          <bk-form
            form-type="inline"
            style="float: right;"
          >
            <bk-date-picker
              v-model="initDateTimeRange"
              style="margin-top: 4px;"
              :shortcuts="dateShortCut"
              :shortcuts-type="'relative'"
              :format="'yyyy-MM-dd HH:mm:ss'"
              :placement="'bottom-end'"
              :placeholder="$t('选择日期时间范围')"
              :shortcut-close="true"
              :type="'datetimerange'"
              :options="datePickerOption"
              :open="isDatePickerOpen"
              @change="handlerChange"
              @pick-success="handlerPickSuccess"
            >
              <div
                slot="trigger"
                style="width: 310px; height: 28px;"
                @click="toggleDatePicker"
              >
                <button class="action-btn timer fr">
                  <i class="left-icon paasng-icon paasng-clock f16" />
                  <span class="text">{{ $t(timerDisplay) }}</span>
                  <i class="right-icon paasng-icon paasng-down-shape f12" />
                </button>
              </div>
            </bk-date-picker>
          </bk-form>
        </div>
        <div
          v-if="curAppInfo.feature.RESOURCE_METRICS"
          class="chart-box"
        >
          <strong class="title"> {{ $t('CPU使用') }} <span class="sub-title"> {{ $t('（单位：核）') }} </span></strong>
          <chart
            ref="cpuLine"
            :options="cpuLine"
            auto-resize
            style="width: 750px; height: 300px; background: #1e1e21;"
          />
        </div>
        <div
          v-if="curAppInfo.feature.RESOURCE_METRICS"
          class="chart-box"
        >
          <strong class="title"> {{ $t('内存使用') }} <span class="sub-title"> {{ $t('（单位：MB）') }} </span></strong>
          <chart
            ref="memoryLine"
            :options="memoryLine"
            auto-resize
            style="width: 750px; height: 300px; background: #1e1e21;"
          />
        </div>
        <div class="slider-detail-wrapper">
          <label class="title"> {{ $t('详细信息') }} </label>
          <section class="detail-item">
            <label class="label"> {{ $t('类型：') }} </label>
            <div class="content">
              {{ processPlan.processType }}
            </div>
          </section>
          <section class="detail-item">
            <label class="label"> {{ $t('实例数上限：') }} </label>
            <div class="content">
              {{ processPlan.maxReplicas }}
            </div>
          </section>
          <section class="detail-item">
            <label class="label"> {{ $t('单实例资源配额：') }} </label>
            <div class="content">
              {{ $t('内存:') }} {{ processPlan.memLimit }} / CPU: {{ processPlan.cpuLimit }}
            </div>
          </section>
          <section class="detail-item">
            <label class="label"> {{ $t('进程间访问链接：') }} </label>
            <div class="content">
              {{ processPlan.clusterLink }}
            </div>
          </section>
          <p style="padding-left: 112px; margin-top: 5px; color: #c4c6cc;">
            {{ $t('注意：进程间访问链接地址只能用于同集群内的不同进程间通信，可在 “模块管理” 页面查看进程的集群信息。更多进程间通信的说明。请参考') }} <a
              target="_blank"
              :href="GLOBAL.DOC.PROCESS_SERVICE"
            > {{ $t('进程间通信') }} </a>
          </p>
        </div>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import moment from 'moment';
import appBaseMixin from '@/mixins/app-base-mixin';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import chartOption from '@/json/instance-chart-option';
import ECharts from 'vue-echarts/components/ECharts.vue';

// let maxReplicasNum = 0;

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours')
  .format('YYYY-MM-DD HH:mm:ss');
let timeRangeCache = '';
let timeShortCutText = '';
export default {
  components: {
    // dropdown,
    // tooltipConfirm,
    // numInput,
    chart: ECharts,
  },
  mixins: [appBaseMixin, sidebarDiffMixin],
  props: {
    deploymentInfo: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    const dateShortCut = [
      {
        text: this.$t('最近5分钟'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 60 * 1000 * 5);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '5m';
          timeShortCutText = this.$t('最近5分钟');
        },
      },
      {
        text: this.$t('最近1小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 1);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1h';
          timeShortCutText = this.$t('最近1小时');
        },
      },
      {
        text: this.$t('最近3小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 3);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '3h';
          timeShortCutText = this.$t('最近3小时');
        },
      },
      {
        text: this.$t('最近12小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 12);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '12h';
          timeShortCutText = this.$t('最近12小时');
        },
      },
      {
        text: this.$t('最近1天'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 24);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1d';
          timeShortCutText = this.$t('最近1天');
        },
      },
    ];
    return {
      isTableLoading: false,
      isColumnExpand: true,
      deployData: {},
      allProcesses: [],
      chartSlider: {
        isShow: false,
        title: '',
      },
      curChartTimeRange: '1h',
      curLogTimeRange: '1h',
      chartRangeList: [
        {
          id: '1h',
          name: this.$t('最近1小时'),
        },
        {
          id: '6h',
          name: this.$t('最近6小时'),
        },
        {
          id: '12h',
          name: this.$t('最近12小时'),
        },
        {
          id: '1d',
          name: this.$t('最近24小时'),
        },
      ],
      currentClickObj: {
        operateIconTitle: '',
        index: 0,
      },
      prevProcessVersion: 0,
      prevInstanceVersion: 0,
      serverTimeout: 30,
      cloudServerEvent: null,

      timerDisplay: this.$t('最近1小时'),
      datePickerOption: {
        // 小于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      dateParams: {
        start_time: initStartDate,
        end_time: initEndDate,
      },
      dateShortCut,
      initDateTimeRange: [initStartDate, initEndDate],
      isDatePickerOpen: false,
      cpuLine: chartOption.cpu,
      memoryLine: chartOption.memory,
      processPlan: {
        processType: 'unkonwn',
        targetReplicas: 0,
        maxReplicas: 0,
      },
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
      console.log(row);
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
          cpuLimit: processInfo.cpu_limit,
          memLimit: processInfo.memory_limit,
          clusterLink: processInfo.cluster_link,
          isExpand: true,
          type,
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

    // 进程详情
    showProcessDetailDialog(process) {
      console.log('process', process);
      this.processPlan = {
        replicas: process.instance,
        processType: process.type,
        targetReplicas: process.targetReplicas,
        maxReplicas: process.maxReplicas,
        status: process.status,
        cpuLimit: this.transfer_cpu_unit(process.cpuLimit),
        memLimit: process.memLimit,
        clusterLink: process.clusterLink,
      };
      this.curProcess = process;
      this.curProcessKey = process.name;
      this.chartSlider.title = `${this.$t('进程')} ${process.name}${this.$t('详情')}`;
      this.chartSlider.isShow = true;
      if (this.curAppInfo.feature.RESOURCE_METRICS) {
        this.getInstanceChart(process);
      }
    },

    transfer_cpu_unit(cpuLimit) {
      if (cpuLimit.endsWith('m')) {
        cpuLimit = parseInt(/^\d+/.exec(cpuLimit)) / 1000;
      }
      return cpuLimit + this.$t('核');
    },

    /**
     * 显示实例指标数据
     */
    getInstanceChart(processes) {
      this.$nextTick(() => {
        const cpuRef = this.$refs.cpuLine;
        const memRef = this.$refs.memoryLine;

        cpuRef && cpuRef.mergeOptions({
          xAxis: [
            {
              data: [],
            },
          ],
          series: [],
        });

        memRef && memRef.mergeOptions({
          xAxis: [
            {
              data: [],
            },
          ],
          series: [],
        });

        cpuRef && cpuRef.showLoading({
          text: this.$t('正在加载'),
          color: '#30d878',
          textColor: '#fff',
          maskColor: 'rgba(255, 255, 255, 0.8)',
        });

        memRef && memRef.showLoading({
          text: this.$t('正在加载'),
          color: '#30d878',
          textColor: '#fff',
          maskColor: 'rgba(255, 255, 255, 0.8)',
        });

        this.fetchMetric({
          cpuRef,
          memRef,
          processes,
        });
      });
    },

    async handleBeforeClose() {
      return this.$isSidebarClosed(JSON.stringify(this.curLogTimeRange));
    },

    async handleChartBeforeClose() {
      const time = this.initDateTimeRange.map(time => moment(time).format('YYYY-MM-DD HH:mm:ss'));
      return this.$isSidebarClosed(JSON.stringify(time));
    },

    /**
     * 图标侧栏隐藏回调处理
     */
    handlerChartHide() {
      this.dateParams = Object.assign({}, {
        start_time: initStartDate,
        end_time: initEndDate,
      });
      this.initDateTimeRange = [initStartDate, initEndDate];
      this.isDatePickerOpen = false;
      this.clearChart();
    },

    hideDatePicker() {
      this.isDatePickerOpen = false;
    },

    handlerChange(dates) {
      this.dateParams.start_time = dates[0];
      this.dateParams.end_time = dates[1];
      this.dateParams.time_range = timeRangeCache || 'customized';
      if (timeShortCutText) {
        this.timerDisplay = timeShortCutText;
      } else {
        this.timerDisplay = `${dates[0]} - ${dates[1]}`;
      }
      this.isDateChange = true;
      timeShortCutText = ''; // 清空
      timeRangeCache = ''; // 清空
    },

    handlerPickSuccess() {
      this.isDatePickerOpen = false;
      if (this.isDateChange) {
        this.getInstanceChart(this.curProcess);
        this.isDateChange = false;
      }
    },

    toggleDatePicker() {
      this.isDatePickerOpen = !this.isDatePickerOpen;
    },


    async fetchMetric(conf) {
      // 请求数据
      const fetchData = (type, processType) => {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          metric_type: type,
          process_type: processType,
          start_time: this.dateParams.start_time,
          end_time: this.dateParams.end_time,
        };
        return this.$store.dispatch('processes/getInstanceMetrics', params);
      };
      // 数据处理
      const getData = (payload) => {
        const datas = [];
        let limitDatas = null;
        payload.result.forEach((instance) => {
          const instanceName = instance.display_name;
          instance.results.forEach((item) => {
            const dataList = item.results;

            if (item.type_name === 'cpu') {
              dataList.forEach((data) => {
                if (data.type_name === 'current') {
                  data.display_name = `${instanceName}-${data.display_name}`;
                  datas.push(data);
                } else if (data.type_name === 'limit') {
                  limitDatas = data;
                }
              });
            } else {
              dataList.forEach((data) => {
                if (data.type_name === 'current') {
                  data.display_name = `${instanceName}-${data.display_name}`;
                  datas.push(data);
                } else if (data.type_name === 'limit') {
                  limitDatas = data;
                }
              });
            }
          });
        });
        limitDatas && (datas.unshift(limitDatas));
        return datas;
      };
      try {
        const res = await Promise.all([fetchData('cpu', conf.processes.type), fetchData('mem', conf.processes.type)]);
        const [res1, res2] = res;
        const cpuData = getData(res1);
        const memData = getData(res2);
        this.renderChartNew(cpuData, 'cpu', conf.cpuRef);
        this.renderChartNew(memData, 'mem', conf.memRef);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
        this.clearChart();
      } finally {
        this.isChartLoading = false;
        conf.cpuRef.hideLoading();
        conf.memRef.hideLoading();
      }
    },

    /**
      * 清空图表数据
    */
    clearChart() {
      const cpuRef = this.$refs.cpuLine;
      const memRef = this.$refs.memoryLine;

      cpuRef && cpuRef.mergeOptions({
        xAxis: [
          {
            data: [],
          },
        ],
        series: [
          {
            name: '',
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
              normal: {
                opacity: 0,
              },
            },
            data: [0],
          },
        ],
      });

      memRef && memRef.mergeOptions({
        xAxis: [
          {
            data: [],
          },
        ],
        series: [
          {
            name: '',
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
              normal: {
                opacity: 0,
              },
            },
            data: [0],
          },
        ],
      });
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
