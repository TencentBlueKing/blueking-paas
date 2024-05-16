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
              <bk-table-column
                prop="name"
                :label="$t('操作')"
              >
                <template slot-scope="{ row }">
                  <div class="instance-item-cls cell-container operation-column">
                    <bk-button
                      class="mr10"
                      :text="true"
                      title="primary"
                      @click="showInstanceLog(row)"
                    >
                      {{ $t('查看日志') }}
                    </bk-button>
                    <bk-button
                      :text="true"
                      title="primary"
                      v-if="curAppInfo.feature.ENABLE_WEB_CONSOLE"
                      @click="showInstanceConsole(row, props.row)"
                    >
                      {{ $t('访问控制台') }}
                    </bk-button>
                  </div>
                </template>
              </bk-table-column>
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
                >
                <span class="pl10" style="white-space: nowrap;">
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
                    <div class="round-wrapper" @click="handleProcessOperation(row)">
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
                        @click="handleProcessOperation(row)"></i>
                    </bk-popconfirm>
                  </div>
                </div>
                <i
                  v-bk-tooltips="$t('进程详情')"
                  class="paasng-icon paasng-log-2 detail mr10"
                  @click="showProcessDetailDialog(row)"
                ></i>
                <!-- 扩缩容操作 -->
                <bk-popover
                  theme="light"
                  ext-cls="more-operations"
                  placement="bottom"
                  :tippy-options="{ 'hideOnClick': false }">
                  <i class="paasng-icon paasng-ellipsis more"></i>
                  <div slot="content" style="white-space: normal;">
                    <div class="option" @click="handleExpansionAndContraction(row)">{{$t('扩缩容')}}</div>
                  </div>
                </bk-popover>
              </div>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </section>

    <!-- 进程详情 -->
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
          v-if="curAppInfo.feature.RESOURCE_METRICS"
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
          v-if="curAppInfo.feature.RESOURCE_METRICS"
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

    <!-- 实例日志 -->
    <bk-sideslider
      :width="800"
      :is-show.sync="instanceSliderConfig.isShow"
      :title="instanceSliderConfig.title"
      :quick-close="true"
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
            style="width: 32px; min-width: 32px"
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
                style="width: 250px"
                :clearable="false"
                :disabled="isLogsLoading"
              >
                <bk-option
                  v-for="(option, index) in chartRangeList"
                  :id="option.id"
                  :key="index"
                  :name="option.name"
                />
              </bk-select>
            </bk-form-item>
          </bk-form>
        </div>
        <div class="instance-textarea">
          <div
            class="textarea"
            style="height: 100%"
          >
            <template v-if="!isLogsLoading && instanceLogs.length">
              <ul>
                <li
                  v-for="(log, index) of instanceLogs"
                  :key="index"
                  class="stream-log"
                >
                  <span
                    class="mr10"
                    style="min-width: 140px"
                  >
                    {{ log.timestamp }}
                  </span>
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
          >
            {{ $t('文档：') }} {{ processRefuseDialog.title }}
          </a>
        </div>
      </div>
    </bk-dialog>

    <!-- 扩缩容 -->
    <scaling-dialog
      v-model="scalingDialogConfig.visiable"
      :data="scalingData"
      @get-process-list="getProcessesList"
    >
    </scaling-dialog>
  </div>
</template>

<script>
import moment from 'moment';
import i18n from '@/language/i18n.js';
import chartOption from '@/json/instance-chart-option';
import appBaseMixin from '@/mixins/app-base-mixin';
import ECharts from 'vue-echarts/components/ECharts.vue';
import scalingDialog from './scaling-dialog';

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours')
  .format('YYYY-MM-DD HH:mm:ss');

let timeRangeCache = '';
let timeShortCutText = '';

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
export default {
  name: 'MigrationProcessManagement',
  components: {
    chart: ECharts,
    scalingDialog,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      curEnvValue: 'stag',
      curModuleValue: 'default',
      allProcesses: [],
      chartSlider: {
        isShow: false,
        title: '',
      },
      curProcess: {},
      initDateTimeRange: [initStartDate, initEndDate],
      processPlan: {
        processType: 'unkonwn',
        targetReplicas: 0,
        maxReplicas: 0,
      },
      dateParams: {
        start_time: initStartDate,
        end_time: initEndDate,
      },
      cpuLine: chartOption.cpu,
      memoryLine: chartOption.memory,
      isDatePickerOpen: false,
      dateShortCut,
      datePickerOption: {
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      timerDisplay: this.$t('最近1小时'),
      curLogTimeRange: '1h',
      chartRangeList: [
        {
          id: '1h',
          name: i18n.t('最近1小时'),
        },
        {
          id: '6h',
          name: i18n.t('最近6小时'),
        },
        {
          id: '12h',
          name: i18n.t('最近12小时'),
        },
        {
          id: '1d',
          name: i18n.t('最近24小时'),
        },
      ],
      processRefuseDialog: {
        isLoading: false,
        visiable: false,
        description: '',
        title: '',
        link: '',
      },
      curInstance: {
        name: '',
      },
      // 实例日志
      instanceSliderConfig: {
        isShow: false,
        title: '',
        isLoading: false,
      },
      instanceLogs: [],
      isLogsLoading: false,
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
    curLogTimeRange() {
      this.loadInstanceLog();
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
        if (curProcess && !this.pollingId) { // 轮询
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
      // processes 进程数据
      // instances 实例数据
      const processes = processesData.processes.items;
      const instances = processesData.instances.items;
      const packages = processesData.process_packages;

      processes.forEach((processeItem) => {
        const packageInfo = packages.find(item => item.name === processeItem.type);
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
        const curProcess = this.allProcesses.find(process => process.type === processType) || {};
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
      this.curUpdateProcess = row;    // 当前点击的进程
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
      } finally {
        // 请求列表数据
        // bus.$emit('get-release-info');
        // process.isActionLoading = false;
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
    /**
     * 展示实例日志侧栏
     * @param {Object} instance 实例对象
     */
    showInstanceLog(instance) {
      this.curInstance = instance;
      this.instanceLogs = [];
      this.instanceSliderConfig.isShow = true;
      this.instanceSliderConfig.title = `${this.$t('实例')} ${this.curInstance.display_name} ${this.$t('控制台输出日志')}`;
      this.loadInstanceLog();
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
      params.query.terms.environment = [this.curEnvValue];
      return params;
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
        const params = {
          start_time: '',
          end_time: '',
          time_range: this.curLogTimeRange,
          log_type: 'STANDARD_OUTPUT',
        };
        const filter = this.getFilterParams();

        const res = await this.$store.dispatch('log/getStreamLogList', {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
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
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLogsLoading = false;
      }
    },
    /**
     * 访问控制台
     * @param {Object} instance, processe
     */
    async showInstanceConsole(instance, processe) {
      this.processRefuseDialog.isLoading = true;
      try {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
          env: this.curEnvValue,
          instanceName: instance.name,
          processType: processe.type,
        };
        const res = await this.$store.dispatch('processes/getInstanceConsole', params);
        // 借口哦成功跳转
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
    transfer_cpu_unit(cpuLimit) {
      if (cpuLimit.endsWith('m')) {
        cpuLimit = parseInt(/^\d+/.exec(cpuLimit)) / 1000;
      }
      return cpuLimit + this.$t('核');
    },
    // 进程详情
    showProcessDetailDialog(process) {
      // 进程详情侧栏需要的展示数据
      this.processPlan = {
        replicas: process.instancesList.length,
        processType: process.type,
        targetReplicas: process.target_replicas,
        maxReplicas: process.max_replicas,
        cpuLimit: this.transfer_cpu_unit(process.resource_limit.cpu),
        memLimit: process.resource_limit.memory,
        clusterLink: process.cluster_link,
      };
      this.curProcess = process;
      this.curProcessKey = process.name;
      this.chartSlider.title = `${this.$t('进程')} ${process.type} ${this.$t('详情')}`;
      this.chartSlider.isShow = true;
      // this.initSidebarFormData(this.initDateTimeRange);
      if (this.curAppInfo.feature.RESOURCE_METRICS) {
        this.getInstanceChart(process);
      }
    },

    async fetchMetric(conf) {
      // 请求数据
      const fetchData = (type, processType) => {
        const params = {
          appCode: this.appCode,
          moduleId: this.curModuleValue,
          env: this.curEnvValue,
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

    /**
     * 图标侧栏隐藏回调处理
     */
    handlerChartHide() {
      this.dateParams = Object.assign(
        {},
        {
          start_time: initStartDate,
          end_time: initEndDate,
        },
      );
      this.initDateTimeRange = [initStartDate, initEndDate];
      this.isDatePickerOpen = false;
      this.clearChart();
    },

    /**
     * 显示实例指标数据
     */
    getInstanceChart(processes) {
      this.$nextTick(() => {
        const cpuRef = this.$refs.cpuLine;
        const memRef = this.$refs.memoryLine;

        cpuRef
          && cpuRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        memRef
          && memRef.mergeOptions({
            xAxis: [
              {
                data: [],
              },
            ],
            series: [],
          });

        cpuRef
          && cpuRef.showLoading({
            text: this.$t('正在加载'),
            color: '#30d878',
            textColor: '#fff',
            maskColor: 'rgba(255, 255, 255, 0.8)',
          });

        memRef
          && memRef.showLoading({
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
     * 清空图表数据
     */
    clearChart() {
      const cpuRef = this.$refs.cpuLine;
      const memRef = this.$refs.memoryLine;

      cpuRef
        && cpuRef.mergeOptions({
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

      memRef
        && memRef.mergeOptions({
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

    hideDatePicker() {
      this.isDatePickerOpen = false;
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

// 进程详情样式
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

// 实例日志
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
  padding: 50px 20px 10px 20px;

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
