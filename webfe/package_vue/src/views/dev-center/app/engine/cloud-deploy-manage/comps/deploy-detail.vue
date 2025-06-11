<template>
  <div class="deploy-detail">
    <section class="instance-details">
      <div class="instance-item">
        <span class="label">{{ $t('运行实例数') }}：</span>
        <span class="value">{{ runningInstanceLength }}</span>
      </div>
      <div class="instance-item">
        <span class="label">{{ $t('期望实例数') }}：</span>
        <span class="value">{{ deploymentInfo?.total_desired_replicas }}</span>
      </div>
      <div class="instance-item">
        <span class="label">{{ $t('异常实例数') }}：</span>
        <span class="value">{{ deployData.total_failed }}</span>
      </div>
    </section>

    <section class="process-table-wrapper">
      <bk-table
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
              <span
                class="ml5"
                v-if="!row.autoscaling"
              >
                {{ (row.instances || []).filter((item) => item.ready).length }} / {{ row.available_instance_count }}
              </span>
              <!-- <div class="rejected-count" v-if="row.failed">{{ row.failed }}</div> -->
              <div
                class="icon-expand"
                v-if="row.instances.length > 1"
              >
                <img
                  v-if="row.isExpand"
                  class="image-icon"
                  @click="handleExpand(row)"
                  src="/static/images/tableminus.svg"
                />
                <img
                  v-else
                  class="image-icon"
                  @click="handleExpand(row)"
                  src="/static/images/tableplus.svg"
                />
              </div>
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
          :label="$t('实例名称')"
          class-name="table-colum-instance-cls colum-instance-name"
        >
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container instance-name"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
              >
                <div
                  class="text-ellipsis"
                  v-bk-overflow-tips
                >
                  {{ instance.display_name }}
                </div>
              </div>
            </div>
            <div
              v-else
              class="instance-item-cls-empty cell-container pl30"
            >
              --
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('状态')"
          class-name="table-colum-instance-cls"
        >
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container status"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
              >
                <div class="text-ellipsis">
                  <span
                    class="dot"
                    :class="instance.rich_status"
                  ></span>
                  <span v-bk-tooltips="instance.state_message || ''">
                    <em
                      v-dashed="{ disabled: instance.rich_status === 'Running' }"
                      class="instance-item-status"
                    >
                      {{ instance.rich_status || '--' }}
                    </em>
                  </span>
                </div>
              </div>
            </div>
            <div
              v-else
              class="instance-item-cls-empty cell-container"
            >
              --
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('重启次数')"
          class-name="table-colum-instance-cls"
          width="80"
          :render-header="$renderHeader"
        >
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
              >
                <span
                  v-bk-tooltips="{
                    content: instance.terminated_info?.reason,
                    placement: 'bottom',
                    offset: '0, -10',
                    disabled: !instance.terminated_info?.reason,
                  }"
                  :class="{ tip: instance.terminated_info?.reason }"
                >
                  {{ instance.restart_count }}
                </span>
              </div>
            </div>
            <div
              v-else
              class="instance-item-cls-empty cell-container"
            >
              --
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建时间')"
          class-name="table-colum-instance-cls"
        >
          <template slot-scope="{ row }">
            <div v-if="row.instances.length">
              <div
                class="instance-item-cls cell-container"
                :class="row.isExpand ? 'expand' : 'close'"
                v-for="instance in row.instances"
                :key="instance.process_name"
              >
                <template v-if="instance.date_time !== 'Invalid date'">
                  <div class="text-ellipsis">{{ instance.date_time }}</div>
                </template>
                <template v-else>--</template>
              </div>
            </div>
            <div
              v-else
              class="instance-item-cls-empty cell-container"
            >
              --
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          label=""
          class-name="table-colum-instance-cls"
          :width="220"
        >
          <template slot-scope="{ row }">
            <div
              class="instance-item-cls cell-container operation-column"
              :class="row.isExpand ? 'expand' : 'close'"
              v-for="instance in row.instances"
              :key="instance.process_name"
            >
              <bk-button
                class="mr10"
                :text="true"
                title="primary"
                @click="showInstanceConsole(instance, row)"
              >
                WebConsole
              </bk-button>
              <bk-button
                class="mr10"
                :text="true"
                title="primary"
                @click="showInstanceLog(instance, row)"
              >
                {{ $t('日志') }}
              </bk-button>
              <bk-popover
                class="table-more-popover-cls"
                theme="light"
                ext-cls="more-operations"
                placement="bottom"
              >
                <i class="paasng-icon paasng-ellipsis more"></i>
                <div
                  slot="content"
                  class="more-content"
                  style="white-space: normal"
                >
                  <div
                    class="option"
                    @click="showInstanceEvents(instance, row.name, $index)"
                  >
                    {{ $t('查看事件') }}
                  </div>
                  <div
                    class="option"
                    @click="showRestartPopup('instance', instance, $index)"
                  >
                    {{ $t('重启实例') }}
                  </div>
                </div>
              </bk-popover>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('进程操作')"
          :width="195"
          class-name="table-colum-operation-cls default-background"
        >
          <template slot-scope="{ row, $index }">
            <div class="operation">
              <div
                v-if="!row.autoscaling && row.instances.length !== row.available_instance_count"
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
                  <span v-if="row.instances.length < row.available_instance_count">
                    {{ $t('启动中...') }}
                  </span>
                  <span v-else>{{ $t('停止中...') }}</span>
                </span>
              </div>
              <div class="operate-process-wrapper mr15">
                <bk-popconfirm
                  v-bk-tooltips="$t('停止进程')"
                  v-if="!!row.available_instance_count"
                  :content="$t('确认停止该进程？')"
                  width="288"
                  trigger="click"
                  @confirm="handleUpdateProcess"
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
                    @confirm="handleUpdateProcess"
                  >
                    <i
                      class="paasng-icon paasng-play-circle-shape start"
                      @click="handleProcessOperation(row)"
                    ></i>
                  </bk-popconfirm>
                </div>
              </div>
              <i
                v-bk-tooltips="$t('进程详情')"
                class="paasng-icon paasng-log-2 detail mr10"
                @click="showProcessDetailDialog(row)"
              ></i>
              <bk-popover
                theme="light"
                ext-cls="more-operations"
                placement="bottom"
              >
                <i class="paasng-icon paasng-ellipsis more"></i>
                <div
                  slot="content"
                  class="more-content"
                  style="white-space: normal"
                >
                  <div
                    class="option"
                    @click="handleExpansionAndContraction(row, $index)"
                  >
                    {{ $t('扩缩容') }}
                  </div>
                  <!-- 重启进程 -->
                  <div
                    class="option"
                    @click="showRestartPopup('process', row, $index)"
                  >
                    {{ $t('滚动重启') }}
                  </div>
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
      @hidden="handlerChartHide"
    >
      <div
        slot="content"
        class="p0 chart-wrapper"
      >
        <div
          v-if="platformFeature.RESOURCE_METRICS"
          v-bk-clickoutside="hideDatePicker"
          class="action-box"
        >
          <bk-form
            form-type="inline"
            style="float: right"
          >
            <bk-date-picker
              v-model="initDateTimeRange"
              style="margin-top: 4px"
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
                style="width: 310px; height: 28px"
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
          v-if="platformFeature.RESOURCE_METRICS"
          class="chart-box"
        >
          <strong class="title">
            {{ $t('CPU使用') }}
            <span class="sub-title">{{ $t('（单位：核）') }}</span>
          </strong>
          <chart
            ref="cpuLine"
            :options="cpuLine"
            auto-resize
            style="width: 750px; height: 300px; background: #1e1e21"
          />
        </div>
        <div
          v-if="platformFeature.RESOURCE_METRICS"
          class="chart-box"
        >
          <strong class="title">
            {{ $t('内存使用') }}
            <span class="sub-title">{{ $t('（单位：MB）') }}</span>
          </strong>
          <chart
            ref="memoryLine"
            :options="memoryLine"
            auto-resize
            style="width: 750px; height: 300px; background: #1e1e21"
          />
        </div>
        <div class="slider-detail-wrapper">
          <label class="title">{{ $t('详细信息') }}</label>
          <section class="detail-item">
            <label class="label">{{ $t('类型：') }}</label>
            <div class="content">
              {{ processPlan.processType }}
            </div>
          </section>
          <section class="detail-item">
            <label class="label">{{ $t('实例数上限：') }}</label>
            <div class="content">
              {{ processPlan.maxReplicas }}
            </div>
          </section>
          <section class="detail-item">
            <label class="label">{{ $t('单实例资源配额：') }}</label>
            <div class="content">{{ $t('内存:') }} {{ processPlan.memLimit }} / CPU: {{ processPlan.cpuLimit }}</div>
          </section>
          <section class="detail-item">
            <label class="label">{{ $t('进程间访问链接：') }}</label>
            <div class="content">
              {{ processPlan.clusterLink }}
            </div>
          </section>
          <p style="padding-left: 112px; margin-top: 5px; color: #c4c6cc">
            {{
              $t(
                '注意：进程间访问链接地址只能用于同集群内的不同进程间通信，可在 “模块管理” 页面查看进程的集群信息。更多进程间通信的说明。请参考'
              )
            }}
            <a
              target="_blank"
              :href="GLOBAL.DOC.PROCESS_SERVICE"
            >
              {{ $t('进程间通信') }}
            </a>
          </p>
        </div>
      </div>
    </bk-sideslider>

    <!-- 查看事件 -->
    <eventDetail
      v-model="instanceEventConfig.isShow"
      :width="computedWidth"
      :config="instanceEventConfig"
      :env="environment"
      :module-id="curModuleId"
    />

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
          >
            {{ $t('文档：') }} {{ processRefuseDialog.title }}
          </a>
        </div>
      </div>
    </bk-dialog>
    <!-- 无法使用控制台 end -->

    <!-- 扩缩容 -->
    <scale-dialog
      :key="moduleName"
      :ref="`${moduleName}ScaleDialog`"
      @updateStatus="handleProcessStatus"
    ></scale-dialog>

    <!-- 日志弹窗 -->
    <process-log
      v-if="logConfig.visiable"
      v-model="logConfig.visiable"
      :title="logConfig.title"
      :logs="logConfig.logs"
      :loading="logConfig.isLoading"
      :selection-list="logSelectionList"
      :params="logConfig.params"
      :is-direct="true"
      :default-condition="'400'"
      @close="handleClose"
      @change="refreshLogs"
      @refresh="refreshLogs"
      @download="downloadInstanceLog"
    ></process-log>

    <!-- 功能依赖项展示 -->
    <FunctionalDependency
      :show-dialog.sync="showFunctionalDependencyDialog"
      mode="dialog"
      :title="$t('暂无访问控制台功能')"
      :functional-desc="
        $t('访问控制台可以让您进入应用进程的容器，查看线上运行的代码、进行在线调试以及执行一次性命令等操作。')
      "
      :guide-title="$t('如需使用该功能，需要：')"
      :guide-desc-list="[$t('1. 安装 BCS 套餐'), $t('2. 将应用集群来源修改为: BCS 集群')]"
      @gotoMore="gotoMore"
    />
  </div>
</template>

<script>
import moment from 'moment';
import appBaseMixin from '@/mixins/app-base-mixin';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import chartOption from '@/json/instance-chart-option';
import ECharts from 'vue-echarts/components/ECharts.vue';
import scaleDialog from './scale-dialog';
import i18n from '@/language/i18n.js';
import { bus } from '@/common/bus';
import eventDetail from './event-detail.vue';
import { downloadTxt } from '@/common/tools';
import processLog from '@/components/process-log-dialog/log.vue';
import { cloneDeep, isEqual } from 'lodash';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';

moment.locale('zh-cn');
// let maxReplicasNum = 0;

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours').format('YYYY-MM-DD HH:mm:ss');
let timeRangeCache = '';
let timeShortCutText = '';
export default {
  components: {
    chart: ECharts,
    scaleDialog,
    eventDetail,
    processLog,
    FunctionalDependency,
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
    isDialogShowSideslider: {
      type: Boolean,
      default: () => false,
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
      deployData: {},
      allProcesses: [],
      chartSlider: {
        isShow: false,
        title: '',
      },
      curTailLines: '400',
      logSelectionList: [
        {
          id: '400',
          name: this.$t('最近 {n} 条', { n: 400 }),
        },
        {
          id: '800',
          name: this.$t('最近 {n} 条', { n: 800 }),
        },
        {
          id: '2000',
          name: this.$t('最近 {n} 条', { n: 2000 }),
        },
        {
          id: '5000',
          name: this.$t('最近 {n} 条', { n: 5000 }),
        },
        {
          id: '10000',
          name: this.$t('最近 {n} 条', { n: 10000 }),
        },
      ],
      currentClickObj: {
        operateIconTitle: '',
        index: 0,
      },
      prevProcessVersion: 0,
      prevInstanceVersion: 0,
      serverTimeout: 30,
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
      processRefuseDialog: {
        isLoading: false,
        visiable: false,
        description: '',
        title: '',
        link: '',
      },
      // EventSource handler
      serverProcessEvent: undefined,
      scaleTargetReplicas: 0,
      instanceEventConfig: {
        isShow: false,
        name: '',
        instanceName: '',
      },
      logConfig: {
        visiable: false,
        isLoading: false,
        title: '',
        logs: [],
        parmas: {},
      },
      showFunctionalDependencyDialog: false,
    };
  },
  computed: {
    curModuleId() {
      // 当前模块的名称
      return this.deploymentInfo.module_name;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    runningInstanceLength() {
      return this.allProcesses.reduce((p, v) => {
        const readyInstancesCount = v.instances.filter((instance) => instance.ready).length;
        return p + readyInstancesCount;
      }, 0);
    },
    // 滑框的宽度
    computedWidth() {
      const defaultWidth = 980;
      const maxWidth = window.innerWidth * 0.8;
      return Math.min(defaultWidth, maxWidth);
    },
    platformFeature() {
      return this.$store.state.platformFeature;
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
    rvData: {
      handler(newVal, oldVal) {
        if (this.isDialogShowSideslider || !oldVal) return;
        // 进入页面启动事件流
        if (
          !isEqual(newVal, oldVal) &&
          (this.serverProcessEvent === undefined || this.serverProcessEvent.readyState === EventSource.CLOSED)
        ) {
          this.watchServerPush();
        }
      },
      immediate: true,
    },
  },
  mounted() {
    moment.locale(this.localLanguage === 'en' ? 'en' : 'zh-cn');
    // 进入页面启动事件流
    // if (this.serverProcessEvent === undefined || this.serverProcessEvent.readyState === EventSource.CLOSED) {
    //   this.watchServerPush();
    // }
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
      this.curUpdateProcess = row; // 当前点击的进程
    },

    handleUpdateProcess() {
      this.updateProcess();
    },
    handleExpansionAndContraction(row, i) {
      this.curUpdateProcess = row; // 当前点击的进程
      const refName = `${this.moduleName}ScaleDialog`;
      this.$refs[refName].handleShowDialog(row, this.environment, this.moduleName);
    },

    // 对数据进行处理
    formatProcesses(processesData) {
      const allProcesses = [];
      const { proc_specs: packages, instances, processes } = processesData;
      // 如果是下架的进程则 processesData.proc_specs 会有数据
      if (packages.length > 0) {
        const processNames = processes.map((e) => e.type);
        packages.forEach((e) => {
          if (!processNames.includes(e.name)) {
            processes.push({
              module_name: e.plan_name,
              name: '',
              type: e.name,
              command: '',
              replicas: 0,
              success: 0,
              failed: 0,
              version: 0,
              cluster_link: '',
              available_instance_count: e.target_replicas,
            });
          }
        });
      }
      processes.forEach((processItem) => {
        const { type, name } = processItem;
        const packageInfo = packages.find((item) => item.name === type) || {};
        const relatedInstances = instances.filter((instance) => instance.process_type === type);

        const processInfo = {
          ...processItem,
          ...packageInfo,
          instances: relatedInstances,
        };

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
          available_instance_count: processInfo.target_status === 'stop' ? 0 : processInfo.target_replicas,
          failed: processInfo.failed,
          resourceLimit: processInfo.resource_limit,
          cpuLimit: processInfo.resource_limit?.cpu,
          memLimit: processInfo.resource_limit?.memory,
          clusterLink: processInfo.cluster_link,
          isExpand: true,
          autoscaling: processInfo.autoscaling,
          type,
          scalingConfig: processInfo.scaling_config,
          processName: name,
        };
        this.updateProcessStatus(process);

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute').fromNow();
          item.isOperate = false;
        });
        allProcesses.push(process);
      });
      this.allProcesses = cloneDeep(allProcesses);
    },

    // 进程详情
    showProcessDetailDialog(process) {
      this.processPlan = {
        replicas: process.instance,
        processType: process.type,
        targetReplicas: process.targetReplicas,
        maxReplicas: process.maxReplicas,
        status: process.status,
        cpuLimit: this.transferCpuUnit(process.cpuLimit),
        memLimit: process.memLimit,
        clusterLink: process.clusterLink,
      };
      this.curProcess = process;
      this.curProcessKey = process.name;
      this.chartSlider.title = `${this.$t('进程')} ${process.name}${this.$t('详情')}`;
      this.chartSlider.isShow = true;
      if (this.platformFeature.RESOURCE_METRICS) {
        this.getInstanceChart(process);
      }
    },

    transferCpuUnit(cpuLimit) {
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

        cpuRef &&
          cpuRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        memRef &&
          memRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        cpuRef &&
          cpuRef.showLoading({
            text: this.$t('正在加载'),
            color: '#30d878',
            textColor: '#fff',
            maskColor: 'rgba(255, 255, 255, 0.8)',
          });

        memRef &&
          memRef.showLoading({
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

    /**
     * 图标侧栏隐藏回调处理
     */
    handlerChartHide() {
      this.dateParams = Object.assign(
        {},
        {
          start_time: initStartDate,
          end_time: initEndDate,
        }
      );
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
        limitDatas && datas.unshift(limitDatas);
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
          message: e.detail || e.message || this.$t('接口异常'),
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

      cpuRef &&
        cpuRef.mergeOptions({
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

      memRef &&
        memRef.mergeOptions({
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

      const { name: processType, targetStatus } = process;
      const patchForm = {
        process_type: processType,
        operate_type: targetStatus === 'start' ? 'stop' : 'start',
      };

      try {
        const res = await this.$store.dispatch('processes/updateProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: patchForm,
        });

        process.available_instance_count = res.target_status === 'start' ? res.target_replicas : 0;

        // 更新当前操作状态
        process.targetStatus = targetStatus === 'start' ? 'stop' : 'start';
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
      if (this.watchServerTimer) {
        clearTimeout(this.watchServerTimer);
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/envs/${this.environment}/processes/watch/?rv_proc=${this.rvData.rvProc}&rv_inst=${this.rvData.rvInst}&timeout_seconds=${this.serverTimeout}`;

      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
      }
      this.serverProcessEvent = new EventSource(url, { withCredentials: true });

      // 服务推送消息处理
      this.serverProcessEvent.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 如果模块名称不匹配，直接返回
          if (data.object.module_name !== this.curModuleId) return;

          // 根据对象类型更新数据
          if (['process', 'instance'].includes(data.object_type)) {
            this.updateProcessData(data);
          }
        } catch (e) {
          console.error(e);
        }
      };

      // 服务异常
      this.serverProcessEvent.onerror = () => {
        this.serverProcessEvent.close();
      };

      // 服务结束
      this.serverProcessEvent.addEventListener('EOF', () => {
        this.serverProcessEvent.close();
        if (this.serverProcessEvent === this.serverProcessEvent) {
          // 服务结束请求列表接口
          bus.$emit('get-release-info');
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
            // process.available_instance_count = processData.success;
            process.desired_replicas = processData.replicas;
            process.failed = processData.failed;
            this.updateProcessStatus(process);
          }
        });
      } else if (data.type === 'DELETED') {
        this.allProcesses = this.allProcesses.filter((process) => process.name !== processData.type);
      }
    },

    // 更新实例
    updateInstanceData(data) {
      const instanceData = data.object || {};
      this.prevInstanceVersion = data.resource_version || 0;

      instanceData.date_time = moment(instanceData.start_time).startOf('minute').fromNow();
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
     * 展示实例/重启日志弹窗
     * @param {Object} instance  实例对象
     * @param {Object} row
     */
    showInstanceLog(instance, row) {
      this.curInstance = instance;
      this.logConfig.visiable = true;
      this.logConfig.isLoading = true;
      this.logConfig.params = {
        appCode: this.appCode,
        moduleId: this.curModuleId,
        env: this.environment,
        processType: row.name,
        instanceName: instance.name,
      };
      this.logConfig.title = `${this.$t('实例')} ${this.curInstance.display_name} ${this.$t('控制台输出日志')}`;
      this.$nextTick(() => {
        this.getInstanceLog(false);
      });
    },

    // 无日志提示
    noLogMessage() {
      this.$paasMessage({
        theme: 'warning',
        message: this.$t('暂时没有日志记录'),
      });
    },

    /**
     * 获取实时日志 | 最后一次重启日志
     * @param {Boolean} previous false=实时日志、true=最后一次重启日志
     */
    async getInstanceLog(previous = false) {
      const { params } = this.logConfig;
      try {
        const res = await this.$store.dispatch('log/getInstanceLog', {
          ...params,
          previous,
          lines: this.curTailLines,
        });
        this.logConfig.logs = res.map((log) => {
          return { message: log };
        });
      } catch (e) {
        this.logConfig.logs = [];
        if (e.status === 404) {
          this.this.noLogMessage();
        }
        this.catchErrorHandler(e);
      } finally {
        this.logConfig.isLoading = false;
      }
    },

    // 下载日志重启日志，云原生
    async downloadInstanceLog(type) {
      const { params } = this.logConfig;
      try {
        const logs = await this.$store.dispatch('log/downloadInstanceLog', {
          ...params,
          previous: type !== 'realtime',
        });
        if (!logs) {
          this.noLogMessage();
          return;
        }
        downloadTxt(logs, params.instanceName);
      } catch (e) {
        if (e.status === 404) {
          this.this.noLogMessage();
        }
        this.catchErrorHandler(e);
      }
    },

    /**
     * 显示进程webConsole
     * @param {Object} instance, processes
     */
    async showInstanceConsole(instance, processes) {
      // 暂无访问控制台功能
      if (!this.platformFeature.WEB_CONSOLE) {
        this.showFunctionalDependencyDialog = true;
        return;
      }
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
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      }
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
        if (this.watchServerTimer) {
          clearTimeout(this.watchServerTimer);
        }
      }
    },

    // 处理进程状态
    handleProcessStatus(v, isChangeScaleType = false) {
      this.scaleTargetReplicas = v || 0;
      // 处理进程期望实例数
      this.allProcesses.forEach((e) => {
        if (e.name === this.curUpdateProcess.name) {
          e.available_instance_count = this.scaleTargetReplicas;
        }
      });
      // 切换了扩缩容方式之后立即请求列表数据
      if (isChangeScaleType) {
        bus.$emit('get-release-info');
      }
    },

    // 显示查看事件
    showInstanceEvents(data, processName) {
      this.instanceEventConfig.isShow = true;
      this.instanceEventConfig.name = data.display_name;
      this.instanceEventConfig.processName = processName;
      this.instanceEventConfig.instanceName = data.name;
    },

    handleClose() {
      this.logConfig.visiable = false;
      this.curTailLines = '400';
      this.logConfig.logs = [];
    },

    // 刷新日志
    refreshLogs(data) {
      this.$set(this.logConfig, 'isLoading', true);
      this.curTailLines = data.value;
      this.getInstanceLog(data.type !== 'realtime');
    },

    // 重启进程、实例弹窗
    showRestartPopup(type, row, i) {
      const restartInstance = type === 'instance';
      this.$bkInfo({
        title: restartInstance ? this.$t('确认重启当前实例？') : this.$t('确认滚动重启当前进程下所有实例？'),
        confirmFn: () => {
          if (restartInstance) {
            this.handleRestartInstance(row);
          } else {
            this.handleRestartProcess(row);
          }
        },
      });
    },

    // 滚动重启
    async handleRestartProcess(row) {
      try {
        await this.$store.dispatch('processes/restartProcess', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          processName: row.processName,
        });
        bus.$emit('get-release-info');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 重启实例
    async handleRestartInstance(instance) {
      try {
        await this.$store.dispatch('processes/restartInstance', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          instanceName: instance.name,
        });
        bus.$emit('get-release-info');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 查看更多-访问控制台
    gotoMore() {
      window.open(this.GLOBAL.DOC.WEB_CONSOLE, '_blank');
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
    border-right: 1px solid #eaebf0;
    margin: 12px 0;
    .label {
      color: #63656e;
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
        color: #ea3636;
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

  i.more {
    transform: rotate(90deg);
    border-radius: 50%;
    padding: 3px;
    color: #63656e;
    cursor: pointer;
    &:hover {
      background: #f0f1f5;
    }
  }

  .status-dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.faild {
      background: #ea3636;
      border: 3px solid #fce0e0;
    }
    &.running {
      background: #3fc06d;
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

        .instance-item-cls-empty {
          padding: 0 10px;
        }

        .operation-column {
          align-items: center;
          justify-content: end;
          padding-right: 12px;
          .more {
            font-size: 16px;
          }
          .bk-primary.bk-button-text {
            height: auto;
          }
          .table-more-popover-cls {
            height: 22px;
            .bk-tooltip-ref {
              height: 22px;
              display: flex;
              align-items: center;
            }
          }
        }

        .instance-item-cls {
          border-bottom: 1px solid #dfe0e5;
          transition: 0.25s ease;
          padding: 0 10px;

          &.instance-name {
            padding-left: 30px;
          }

          .instance-item-status {
            padding-bottom: 2px;
          }

          .text-ellipsis {
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
          }

          span.tip {
            position: relative;
            &::before {
              content: '';
              position: absolute;
              width: 100%;
              height: 1px;
              bottom: 15px;
              border-bottom: 1px dashed;
            }
          }

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

      &.colum-instance-name .bk-table-header-label {
        padding-left: 30px;
      }

      .bk-table-header-label {
        padding: 0 10px;
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
        background: #fafbfd;
      }
    }
    .bk-table-body .table-colum-process-cls {
      .cell {
        align-items: flex-start;
        flex-direction: column;
        justify-content: center;
        .scaling-dot {
          height: 16px;
          line-height: 16px;
          padding: 0 4px;
          font-size: 10px;
          color: #14a568;
          background: #e4faf0;
          border-radius: 2px;
        }
      }
    }
    .table-colum-process-cls {
      .cell {
        display: block;
        height: 100%;
        display: flex;
      }
      &.default-background {
        background: #fafbfd;
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
    color: #ea3636;
    background: #feebea;
    border-radius: 9px;
  }
  .icon-expand {
    position: absolute;
    right: 0px;
    top: 50%;
    transform: translateY(-50%) translateX(50%);
    z-index: 99;
    cursor: pointer;
    .image-icon {
      display: block;
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
  .dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 5px;
    flex-shrink: 0;
    transform: translateY(2px);

    &.Failed,
    &.Error {
      background: #ea3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.Pending,
    &.CrashLoopBackOff {
      background: #ff9c01;
      border: 3px solid #ffefd6;
    }
    &.Running {
      background: #3fc06d;
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
  .action-box {
    position: absolute;
    top: 12px;
    right: 10px;
  }
}

.process-detail-table {
  /deep/ .bk-table-body-wrapper .hover-row > td {
    background: #ffffff !important;
  }
  /deep/ .bk-table-body-wrapper .hover-row > .default-background {
    background: #fafbfd !important;
  }
}
</style>

<style lang="scss">
.more-operations {
  .tippy-tooltip {
    padding: 0;
    .tippy-content {
      cursor: pointer;
      .more-content {
        padding: 6px 0;
        .option {
          padding: 0 16px;
          height: 32px;
          line-height: 32px;
          &:hover {
            background-color: #eaf3ff;
            color: #3a84ff;
          }
        }
      }
    }
  }
}
</style>
