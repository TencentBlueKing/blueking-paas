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
        <bk-table-column
          :label="$t('进程名称')"
          :width="180"
          class-name="table-colum-process-cls default-background"
        >
          <template slot-scope="{ row }">
            <div>
              <span>{{ row.name || '--' }}</span>
              <span class="ml5">{{ row.available_instance_count }} / {{ row.targetReplicas }}</span>
              <!-- <div class="rejected-count" v-if="row.failed">{{ row.failed }}</div> -->
              <div class="icon-expand" v-if="row.instances.length > 1">
                <img
                  v-if="row.isExpand"
                  class="image-icon"
                  @click="handleExpand(row)"
                  src="/static/images/tableminus.svg"
                >
                <img
                  v-else
                  class="image-icon"
                  @click="handleExpand(row)"
                  src="/static/images/tableplus.svg"
                >
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('实例名称')"
          class-name="table-colum-instance-cls"
        >
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
                @mouseenter="handleMouseEnter(instance.display_name)"
                @mouseleave="rowDisplayName = ''"
              >
                <div
                  class="content"
                  :class="{ hoverBackground: rowDisplayName === instance.display_name }"
                >
                  {{ instance.display_name }}
                </div>
              </div>
            </div>
            <div v-else class="instance-item-cls-empty cell-container">--</div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('状态')" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container status"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
                @mouseenter="handleMouseEnter(instance.display_name)"
                @mouseleave="rowDisplayName = ''"
              >
                <div
                  class="content"
                  :class="{ hoverBackground: rowDisplayName === instance.display_name }"
                >
                  <div
                    class="dot"
                    :class="instance.state"
                  >
                  </div>
                  <span
                    v-dashed="{disabled: instance.state === 'Running'}"
                    v-bk-tooltips="instance.state_message || ''">
                    {{ instance.state || '--' }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="instance-item-cls-empty cell-container">--</div>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('创建时间')" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
                @mouseenter="handleMouseEnter(instance.display_name)"
                @mouseleave="rowDisplayName = ''"
              >
                <template v-if="instance.date_time !== 'Invalid date'">
                  <div
                    class="content"
                    :class="{ hoverBackground: rowDisplayName === instance.display_name }"
                  >
                    {{ $t('创建于') }} {{ instance.date_time }}
                  </div>
                </template>
                <template v-else>
                  --
                </template>
              </div>
            </div>
            <div v-else class="instance-item-cls-empty cell-container">--</div>
          </template>
        </bk-table-column>
        <bk-table-column label="" class-name="table-colum-instance-cls">
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
              @mouseenter="handleMouseEnter(instance.display_name)"
              @mouseleave="rowDisplayName = ''"
            >
              <div
              >
                <div v-show="rowDisplayName === instance.display_name">
                  <bk-button
                    class="mr10"
                    :text="true"
                    title="primary"
                    @click="showInstanceLog(instance)">
                    {{$t('查看日志')}}
                  </bk-button>
                  <bk-button
                    :text="true"
                    title="primary"
                    v-if="curAppInfo.feature.ENABLE_WEB_CONSOLE"
                    @click="showInstanceConsole(instance, row)">
                    {{$t('访问控制台')}}
                  </bk-button>
                </div>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('进程操作')"
          width="170"
          class-name="table-colum-operation-cls default-background"
        >
          <template slot-scope="{ row }">
            <div class="operation">
              <div
                v-if="row.status === 'Running' && !row.autoscaling"
                class="flex-row align-items-center mr10"
              >
                <img
                  src="/static/images/btn_loading.gif"
                  class="loading"
                >
                <span class="pl10">
                  {{ row.targetStatus === 'start' ? $t('启动中...') : $t('停止中...') }}
                </span>
              </div>
              <div class="operate-process-wrapper mr15">
                <bk-popconfirm
                  v-bk-tooltips="$t('停止进程')"
                  v-if="row.targetStatus === 'start'"
                  :content="$t('确认停止该进程？')"
                  width="288"
                  trigger="click"
                  @confirm="handleUpdateProcess">
                  <div class="round-wrapper" @click="handleProcessOperation(row)">
                    <div class="square-icon">
                    </div>
                  </div>
                </bk-popconfirm>
                <div v-else>
                  <bk-popconfirm
                    v-bk-tooltips="$t('启动进程')"
                    :content="$t('确认启动该进程？')"
                    width="288"
                    trigger="click"
                    @confirm="handleUpdateProcess">
                    <i
                      class="paasng-icon paasng-play-circle-shape start"
                      @click="handleProcessOperation(row)"></i>
                  </bk-popconfirm>
                </div>
              </div>
              <i
                v-bk-tooltips="$t('进程详情')"
                class="paasng-icon paasng-log-2 detail mr10"
                @click="showProcessDetailDialog(row)"></i>
              <!-- 暂时不展示 -->
              <!-- <bk-popover
                theme="light"
                ext-cls="more-operations"
                placement="bottom">
                <i class="paasng-icon paasng-ellipsis more"></i>
                <div slot="content" style="white-space: normal;">
                  <div class="option" @click="handleExpansionAndContraction(row)">{{$t('扩缩容')}}</div>
                </div>
              </bk-popover> -->
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
    <!-- 日志侧栏 -->
    <bk-sideslider
      :width="800"
      :is-show.sync="processSlider.isShow"
      :title="processSlider.title"
      :quick-close="true"
      :before-close="handleBeforeClose"
    >
      <div
        id="log-container"
        slot="content"
        class="p0 instance-log-wrapper paas-log-box"
      >
        <div class="action-box">
          <bk-button
            :key="isLogsLoading"
            class="fr p0 f12 refresh-btn"
            style="width: 32px; min-width: 32px;"
            :disabled="isLogsLoading"
            @click="loadInstanceLog"
          >
            <span class="bk-icon icon-refresh f18" />
          </bk-button>

          <bk-form
            form-type="inline"
            class="fr mr5"
          >
            <bk-form-item :label="$t('时间段：')">
              <bk-select
                v-model="curLogTimeRange"
                style="width: 250px;"
                :clearable="false"
                :disabled="isLogsLoading"
              >
                <bk-option
                  v-for="(option, i) in chartRangeList"
                  :id="option.id"
                  :key="i"
                  :name="option.name"
                />
              </bk-select>
            </bk-form-item>
          </bk-form>
        </div>
        <div class="instance-textarea">
          <div
            class="textarea"
            style="height: 100%;"
          >
            <template v-if="!isLogsLoading && instanceLogs.length">
              <ul>
                <li
                  v-for="(log, idx) of instanceLogs"
                  :key="idx"
                  class="stream-log"
                >
                  <span
                    class="mr10"
                    style="min-width: 140px;"
                  >{{ log.timestamp }}</span>
                  <span class="pod-name">{{ log.podShortName }}</span>
                  <pre
                    class="message"
                    v-html="log.message || '--'"
                  />
                </li>
              </ul>
            </template>
            <template v-else-if="isLogsLoading">
              <div class="log-loading-container">
                <div class="log-loading">
                  {{ $t('日志获取中...') }}
                </div>
              </div>
            </template>
            <template v-else>
              <p>
                {{ $t('暂时没有日志记录') }}
              </p>
            </template>
          </div>
        </div>
      </div>
    </bk-sideslider>


    <!-- 无法使用控制台 -->
    <bk-dialog
      v-model="processRefuseDialog.visiable"
      width="650"
      :title="$t('无法使用控制台功能')"
      :theme="'primary'"
      :mask-close="false"
      :loading="processRefuseDialog.isLoading"
    >
      <div>
        {{ processRefuseDialog.description }}
        <div class="mt10">
          <a
            :href="processRefuseDialog.link"
            target="_blank"
          > {{ $t('文档：') }} {{ processRefuseDialog.title }}</a>
        </div>
      </div>
    </bk-dialog>
    <!-- 无法使用控制台 end -->

    <!-- 扩缩容 -->
    <!-- <scale-dialog
      :key="moduleName" :ref="`${moduleName}ScaleDialog`"
      @updateStatus="handleProcessStatus"
    >
    </scale-dialog> -->
  </div>
</template>

<script>import moment from 'moment';
import appBaseMixin from '@/mixins/app-base-mixin';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import chartOption from '@/json/instance-chart-option';
import ECharts from 'vue-echarts/components/ECharts.vue';
// import scaleDialog from './scale-dialog';
import i18n from '@/language/i18n.js';
import { bus } from '@/common/bus';

moment.locale('zh-cn');
// let maxReplicasNum = 0;

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours')
  .format('YYYY-MM-DD HH:mm:ss');
let timeRangeCache = '';
let timeShortCutText = '';
export default {
  components: {
    chart: ECharts,
    // scaleDialog,
  },
  mixins: [appBaseMixin, sidebarDiffMixin],
  props: {
    deploymentInfo: {
      type: Object,
      default: () => ({}),
    },
    environment: {
      type: String,
      default: () => 'stag',
    },
    rvData: {
      type: Object,
      default: () => ({}),
    },
    moduleName: {
      type: String,
      default: 'default',
    },
    index: {
      type: Number,
      default: () => 0,
    },
  },
  data() {
    const dateShortCut = [
      {
        text: i18n.t('最近5分钟'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 60 * 1000 * 5);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '5m';
          timeShortCutText = i18n.t('最近5分钟');
        },
      },
      {
        text: i18n.t('最近1小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 1);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1h';
          timeShortCutText = i18n.t('最近1小时');
        },
      },
      {
        text: i18n.t('最近3小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 3);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '3h';
          timeShortCutText = i18n.t('最近3小时');
        },
      },
      {
        text: i18n.t('最近12小时'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 12);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '12h';
          timeShortCutText = i18n.t('最近12小时');
        },
      },
      {
        text: i18n.t('最近1天'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 24);
          return [start, end];
        },
        onClick() {
          timeRangeCache = '1d';
          timeShortCutText = i18n.t('最近1天');
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
      watchServerTimer: null,
      curUpdateProcess: {},
      processSlider: {
        isShow: false,
        title: '',
      },
      isLogsLoading: false,
      instanceLogs: [],
      processRefuseDialog: {
        isLoading: false,
        visiable: false,
        description: '',
        title: '',
        link: '',
      },
      rowDisplayName: '',
      // EventSource handler
      serverProcessEvent: undefined,
    };
  },
  computed: {
    curModuleId() {
      // 当前模块的名称
      return this.deploymentInfo.module_name;
    },
    isWatchProcess() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },

  watch: {
    deploymentInfo: {
      handler(value) {
        this.deployData = value;
        // this.handleDeployInstanceData();
        this.formatProcesses(this.deployData);
      },
      immediate: true,
      // deep: true,
    },
  },
  mounted() {
    moment.locale(this.localLanguage === 'en' ? 'en' : 'zh-cn');
    // 进入页面启动事件流
    if (this.index === 0) {   // 只需要启动一次stream
      if (this.serverProcessEvent === undefined || this.serverProcessEvent.readyState === EventSource.CLOSED) {
        this.watchServerPush();
      }
    }
  },

  beforeDestroy() {
    // 页面销毁 关闭stream
    this.closeServerPush();
  },

  methods: {
    handleExpand(row) {
      row.isExpand = !row.isExpand;
    },
    handleProcessOperation(row) {
      this.curUpdateProcess = row;    // 当前点击的进程
    },

    handleUpdateProcess() {
      this.updateProcess();
    },
    handleExpansionAndContraction(row) {
      this.curUpdateProcess = row;    // 当前点击的进程
      const refName = `${this.moduleName}ScaleDialog`;
      this.$refs[refName].handleShowDialog(row, this.environment);
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
      // 如果是下架的进程则processesData.proc_specs会有数据
      if (!processesData.processes.length && processesData.proc_specs.length) {
        processesData.processes = [   // 默认值
          {
            module_name: 'default',
            name: '',
            type: 'web',
            command: '',
            replicas: 0,
            success: 0,
            failed: 0,
            version: 0,
            cluster_link: '',
          },
        ];
      }
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
          autoscaling: processInfo.autoscaling,
          type,
        };
        this.updateProcessStatus(process);

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute')
            .fromNow();
        });
        allProcesses.push(process);
      });
      allProcesses.forEach((processe) => {
        processe.instances.forEach((instance) => {
          instance.isOperate = false;
        });
      });
      this.allProcesses = JSON.parse(JSON.stringify(allProcesses));
      console.log('this.allProcesses', this.allProcesses);
    },

    // 进程详情
    showProcessDetailDialog(process) {
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

    /**
     * 图表初始化
     * @param  {Object} instanceData 数据
     * @param  {String} type 类型
     * @param  {Object} ref 图表对象
     */
    renderChartNew(instanceData, type, ref) {
      const series = [];
      let xAxisData = [];
      instanceData.forEach((item) => {
        const chartData = [];
        xAxisData = [];
        item.results.forEach((itemData) => {
          xAxisData.push(moment(itemData[0] * 1000).format('MM-DD HH:mm'));
          // 内存由Byte转MB
          if (type === 'mem') {
            const dataMB = Math.ceil(itemData[1] / 1024 / 1024);
            chartData.push(dataMB);
          } else {
            chartData.push(itemData[1]);
          }
        });

        if (item.type_name === 'current') {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            areaStyle: {
              normal: {
                opacity: 0.2,
              },
            },
            data: chartData,
          });
        } else {
          series.push({
            name: item.display_name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
              normal: {
                width: 1,
                type: 'dashed',
              },
            },
            areaStyle: {
              normal: {
                opacity: 0,
              },
            },
            data: chartData,
          });
        }
      });

      ref.mergeOptions({
        xAxis: [
          {
            data: xAxisData,
          },
        ],
        series,
      });
    },

    async updateProcess() {
      const process = this.curUpdateProcess;
      // 判断上次操作是否结束
      // if (process.isActionLoading) {
      //   this.$paasMessage({
      //     theme: 'error',
      //     message: this.$t('进程操作过于频繁，请间隔 3 秒再试'),
      //   });
      //   return false;
      // }
      // process.isActionLoading = true;


      // // 判断是否已经下架
      // if (this.isAppOfflined) {
      //   return false;
      // }

      // process.isShowTooltipConfirm = false;
      // if (!process.operateIconTitle) {
      //   process.operateIconTitle = process.operateIconTitleCopy;
      // }

      // this.currentClickObj = Object.assign({}, {
      //   operateIconTitle: process.operateIconTitle,
      //   index,
      // });

      const processType = process.name;
      const { targetStatus } = process;
      const patchForm = {
        process_type: processType,
        operate_type: targetStatus === 'start' ? 'stop' : 'start',
      };

      try {
        await this.$store.dispatch('processes/updateProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: patchForm,
        });

        // 更新当前操作状态
        if (targetStatus === 'start') {
          process.targetStatus = 'stop';
        } else {
          process.targetStatus = 'start';
        }
        if (!this.watchServerTimer) {
          this.watchServerPush();
        }
      } catch (err) {
        this.$paasMessage({
          theme: 'error',
          message: err.message,
        });
      } finally {
        // 请求列表数据
        bus.$emit('get-release-info');
        process.isActionLoading = false;
      }
    },


    // 监听进程事件流
    watchServerPush() {
      console.log('监听');
      // 停止轮询的标志
      if (this.watchServerTimer) {
        clearTimeout(this.watchServerTimer);
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/envs/${this.environment}/processes/watch/?rv_proc=${this.rvData.rvProc}&rv_inst=${this.rvData.rvInst}&timeout_seconds=${this.serverTimeout}`;

      const serverProcessEvent = new EventSource(url, {
        withCredentials: true,
      });
      if (this.serverProcessEvent !== undefined) {
        this.serverProcessEvent.close();
      }
      this.serverProcessEvent = serverProcessEvent;

      // 收藏服务推送消息
      serverProcessEvent.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(this.$t('接受到推送'), data);
        if (data.object_type === 'process') {
          if (data.object.module_name !== this.curModuleId) return;   // 更新当前模块的进程
          this.updateProcessData(data);
        } else if (data.object_type === 'instance') {
          if (data.object.module_name !== this.curModuleId) return;   // 更新当前模块的进程
          this.updateInstanceData(data);
        } else if (data.type === 'ERROR') {
          // 判断 event.type 是否为 ERROR 即可，如果是 ERROR，就等待 2 秒钟后，重新发起 list/watch 流程
          clearTimeout(this.timer);
          this.timer = setTimeout(() => {
            // this.getProcessList(this.releaseId, false);
          }, 2000);
        }
      };

      // 服务异常
      serverProcessEvent.onerror = (event) => {
        // 异常后主动关闭，否则会继续重连
        console.error(this.$t('推送异常'), event);
        serverProcessEvent.close();

        // 推迟调用，防止过于频繁导致服务性能问题
        // this.watchServerTimer = setTimeout(() => {
        //   this.watchServerPush();
        // }, 3000);
      };

      // 服务结束
      serverProcessEvent.addEventListener('EOF', () => {
        serverProcessEvent.close();
        if (this.serverProcessEvent === serverProcessEvent) {
          // 服务结束请求列表接口
          bus.$emit('get-release-info');
          this.watchServerTimer = setTimeout(() => {
            this.watchServerPush();
          }, 3000);
        }
      });
    },

    // 更新进程
    updateProcessData(data) {
      const processData = data.object || {};
      this.prevProcessVersion = data.resource_version || 0;

      if (data.type === 'ADDED') {
        // ADDED 是要将 process 添加到 allProcesses 里面
        // 重新拉一次 list 接口也可以间接实现
        bus.$emit('get-release-info');
      } else if (data.type === 'MODIFIED') {
        this.allProcesses.forEach((process) => {
          if (process.name === processData.type) {
            process.available_instance_count = processData.success;
            process.desired_replicas = processData.replicas;
            process.failed = processData.failed;
            this.updateProcessStatus(process);
          }
        });
      } else if (data.type === 'DELETED') {
        this.allProcesses = this.allProcesses.filter(process => process.name !== processData.type);
      }
    },

    // 更新实例
    updateInstanceData(data) {
      const instanceData = data.object || {};
      this.prevInstanceVersion = data.resource_version || 0;

      instanceData.date_time = moment(instanceData.start_time).startOf('minute')
        .fromNow();
      this.allProcesses.forEach((process) => {
        if (process.type === instanceData.process_type) {
          // 新增
          if (data.type === 'ADDED') {
            // 防止在短时间内重复推送
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                process.instances.splice(index, 1);
              }
            });
            process.instances.push(instanceData);
          } else {
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                if (data.type === 'DELETED') {
                  // 删除
                  process.instances.splice(index, 1);
                } else {
                  // 更新
                  process.instances.splice(index, 1, instanceData);
                }
              }
            });
          }
          this.updateProcessStatus(process);
        }
      });
    },

    updateProcessStatus(process) {
      /*
        * 设置进程状态
        * targetStatus: 进行的操作，start\stop\scale
        * status: 操作状态，Running\stoped
        *
        * 如何判断进程当前是否为操作中（繁忙状态）？
        * 主要根据 process_packages 里面的 target_status 判断：
        * 如果 target_status 为 stop，仅当 processes 里面的 success 为 0 且实例为 0 时正常，否则为操作中
        * 如果 target_status 为 start，仅当 success 与 target_replicas 一致，而且 failed 为 0 时正常，否则为操作中
        */
      if (process.targetStatus === 'stop') {
        process.operateIconTitle = this.$t('启动进程');
        process.operateIconTitleCopy = this.$t('启动进程');
        if (process.available_instance_count === 0 && process.instances.length === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      } else if (process.targetStatus === 'start') {
        process.operateIconTitle = this.$t('停止进程');
        process.operateIconTitleCopy = this.$t('停止进程');
        if (process.available_instance_count === process.targetReplicas && process.failed === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      }
    },


    /**
     * 展示实例日志侧栏
     * @param {Object} instance 实例对象
    */
    showInstanceLog(instance) {
      this.curInstance = instance;
      this.instanceLogs = [];
      this.processSlider.isShow = true;
      this.processSlider.title = `${this.$t('实例')} ${this.curInstance.display_name}${this.$t('控制台输出日志')}`;
      this.loadInstanceLog();
      // 收集初始状态
      this.initSidebarFormData(this.curLogTimeRange);
    },

    /**
     * 加载实例日志
     */
    async loadInstanceLog() {
      if (this.isLogsLoading) {
        return false;
      }

      this.isLogsLoading = true;
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const params = this.getParams();
        const filter = this.getFilterParams();

        const res = await this.$store.dispatch('log/getStreamLogList', {
          appCode,
          moduleId,
          params,
          filter,
        });
        const data = res.logs.reverse();
        data.forEach((item) => {
          item.podShortName = item.pod_name.split('-').reverse()[0];
        });
        this.instanceLogs = data;
        // 滚动到底部
        setTimeout(() => {
          const container = document.getElementById('log-container');
          container.scrollTop = container.scrollHeight;
        }, 500);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      } finally {
        this.isLogsLoading = false;
      }
    },

    /**
     * 显示进程webConsole
     * @param {Object} instance, processes
    */
    async showInstanceConsole(instance, processes) {
      this.processRefuseDialog.isLoading = true;
      try {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          instanceName: instance.name,
          processType: processes.type,
        };
        const res = await this.$store.dispatch('processes/getInstanceConsole', params);
        if (res.web_console_url) {
          window.open(res.web_console_url);
        }
      } catch (e) {
        if (e.status === 403) {
          this.processRefuseDialog.visiable = true;
          this.processRefuseDialog.isLoading = false;
          this.processRefuseDialog.description = e.description;
          this.processRefuseDialog.title = e.title;
          this.processRefuseDialog.link = e.link;
        } else {
          this.$paasMessage({
            theme: 'error',
            message: e.message,
          });
        }
      }
    },

    getParams() {
      return {
        start_time: '',
        end_time: '',
        time_range: this.curLogTimeRange,
        log_type: 'STANDARD_OUTPUT',
      };
    },

    /**
     * 构建过滤参数
     */
    getFilterParams() {
      const params = {
        query: {
          terms: {},
        },
      };

      params.query.terms.pod_name = [this.curInstance.name];
      params.query.terms.environment = [this.environment];

      return params;
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
        if (this.watchServerTimer) {
          clearTimeout(this.watchServerTimer);
        };
      }
    },

    // 处理进程状态
    handleProcessStatus() {
      // 进程之后请求列表数据
      // bus.$emit('get-release-info');
    },

    handleMouseEnter(name) {
      this.rowDisplayName = name;
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
    .label {
      color: #63656E;
    }
    .value {
      color: #313238;
    }
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
    padding: 0 10px;
    i {
      font-size: 20px;
      cursor: pointer;
    }
    .start {
      color: #2DCB56;
      font-size: 20px;
    }
    .detail {
      color: #979BA5;

      &:hover {
        color: #63656E;
      }
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

        .instance-item-cls-empty{
          position: absolute;
          width: 50%;
          left: 65%;
          top: 50%;
          text-align: left;
          padding-left: 5px;
          transform: translate(-50%, -50%);
        }

        .instance-item-cls  {
          border-bottom: 1px solid #dfe0e5;
          transition: .25s ease;

          .content {
            position: absolute;
            width: 50%;
            left: 65%;
            top: 50%;
            padding-left: 5px;
            transform: translate(-50%, -50%);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          // .hoverBackground {
          //   background-color: #FAFBFD;
          // }

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
        // display: flex;
        // justify-content: center;
        position: absolute;
        width: 50%;
        left: 65%;
        top: 50%;
        padding-left: 5px;
        transform: translate(-50%, -50%);
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
        padding: 0 10px;
      }
      &.default-background {
        background: #FAFBFD;
      }
    }
    .table-colum-process-cls  {
      .cell {
        display: block;
        height: 100%;
        display: flex;
        align-items: center;
      }
      &.default-background {
        background: #FAFBFD;
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
    .image-icon{
      width: 14px;
      height: 14px;
    }
  }

  .operate-process-wrapper {
    cursor: pointer;
    .round-wrapper {
      margin-top: -2px;
      width: 20px;
      height: 20px;
      background: #EA3636;
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
  .dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.Failed {
      background: #EA3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.Pending {
      background: #FF9C01;
      border: 3px solid #ffefd6;
    }
    &.Running {
      background: #3FC06D;
      border: 3px solid #daefe4;
    }
  }

  .chart-wrapper {
      height: 100%;
      overflow: auto;
      background: #fafbfd;

      .chart-box {
          margin-bottom: 10px;
          border-top: 1px solid #dde4eb;
          border-bottom: 1px solid #dde4eb;

          .title {
              font-size: 14px;
              display: block;
              color: #666;
              font-weight: normal;
              padding: 10px 20px;
          }

          .sub-title {
              font-size: 12px;
          }
          background-color: #fff !important;
      }
  }

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
          color: #63656E;
          font-size: 12px;
          display: inline-block;
      }

      .left-icon,
      .right-icon {
          width: 28px;
          height: 28px;
          line-height: 28px;
          color: #C4C6CC;
          display: inline-block;
          text-align: center;
      }

      &.refresh {
          width: 28px;
      }
  }
  .instance-log-wrapper {
      height: 100%;
      overflow: auto;

      .instance-textarea {
          border: none;
      }
  }
  .instance-textarea {
      border-radius: 2px;
      line-height: 19px;
      font-size: 12px;
      padding: 10px 20px 10px 20px;

      p {
          padding: 0px 0;
          padding-bottom: 5px;
      }
    }
  .action-box {
    position: absolute;
    top: 12px;
    right: 10px;
  }
}

.process-detail-table {
  /deep/ .bk-table-body-wrapper .hover-row>td {
    background: #FFFFFF !important;
  }
  /deep/ .bk-table-body-wrapper .hover-row>.default-background {
    background: #FAFBFD !important;
  }
}
</style>

<style lang="scss">
.more-operations .tippy-tooltip .tippy-content {
  cursor: pointer;
  &:hover {
    color: #3a84ff;
  }
}
</style>
