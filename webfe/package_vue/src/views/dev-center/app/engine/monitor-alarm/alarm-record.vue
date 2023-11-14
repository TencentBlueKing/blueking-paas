<template>
  <div class="paas-monitor-alarm-wrapper">
    <section class="search-wrapper">
      <div class="search-select" v-if="isSourceSelect">
        <div class="select mr10">
          <bk-select
            v-model="curSourceValue"
            style="width: 120px"
            :clearable="false"
          >
            <bk-option
              v-for="option in sourceList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </div>
      </div>
      <div class="search-select">
        <div class="select">
          <bk-select
            v-model="curEnv"
            :placeholder="$t('环境')"
            style="width: 120px"
          >
            <bk-option
              v-for="option in envList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </div>
      </div>
      <div class="search-select ml">
        <div class="select">
          <bk-input
            v-model="keyword"
            clearable
            :placeholder="$t('输入关键字')"
            style="width: 180px"
          />
        </div>
      </div>
      <div v-bk-clickoutside="hideDatePicker" class="search-select ml">
        <div class="select">
          <bk-date-picker
            v-model="initDateTimeRange"
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
            <div slot="trigger" style="width: 310px" @click="toggleDatePicker">
              <button class="action-btn timer">
                <i class="left-icon paasng-icon paasng-clock f16" />
                <span class="text">{{ timerDisplay }}</span>
                <i class="right-icon paasng-icon paasng-down-shape f12" />
              </button>
            </div>
          </bk-date-picker>
        </div>
      </div>
      <div
        :class="['search-action', { 'not-source': !isSourceSelect }, { 'reset-right': curDateType !== 'custom' }]"
      >
        <bk-button theme="primary" @click="handleSearch">
          {{ $t("查询") }}
        </bk-button>
      </div>
    </section>
    <bk-table
      v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
      :data="tableData"
      size="small"
      :ext-cls="tableLoading ? 'is-being-loading' : ''"
      :pagination="pagination"
      @page-change="pageChange"
      @page-limit-change="limitChange"
    >
      <div slot="empty">
        <table-empty
          :keyword="tableEmptyConf.keyword"
          :abnormal="tableEmptyConf.isAbnormal"
          @reacquire="getCurrentFun"
          @clear-filter="clearFilter"
        />
      </div>
      <bk-table-column
        :label="$t('告警开始时间')"
        :prop="isBkMonitor ? 'start_time' : 'start'"
        width="160"
        :render-header="renderTypeHeader"
      />
      <bk-table-column
        :label="isBkMonitor ? $t('告警名称') : $t('类型')" width="180"
        :show-overflow-tooltip="true"
      >
        <template slot-scope="{ row }">
          <span v-if="isBkMonitor">{{ row.alert_name || '--' }}</span>
          <span v-else v-bk-tooltips="row.genre.name">{{ row.genre.name }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('环境')" width="90">
        <template slot-scope="{ row }">
          <span v-if="row.env">{{
            row.env === "stag" ? $t("预发布环境") : $t("生产环境")
          }}</span>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('内容')">
        <template slot-scope="{ row }">
          <span v-if="isBkMonitor" v-bk-tooltips="row.description">{{ row.description || '--' }}</span>
          <span v-else v-bk-tooltips="row.message">{{ row.message || "--" }}</span>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('操作')" width="150">
        <template slot-scope="{ row }">
          <section>
            <bk-button theme="primary" text @click="handleDetail(row)">
              {{ $t("详情") }}
            </bk-button>
          </section>
        </template>
      </bk-table-column>
    </bk-table>

    <bk-sideslider
      :is-show.sync="isShowDetailSlider"
      :title="$t('告警详情')"
      ext-cls="paas-alarm-detail-slider"
      :width="700"
      :quick-close="true"
      @hidden="handlerChartHide"
      @animation-end="handleSliderAfterClose"
    >
      <div
        slot="content"
        v-bkloading="{ isLoading: sliderLoading, opacity: 1 }"
        class="alarm-detail-slider-content"
      >
        <div class="detail-content">
          <div
            v-bkloading="{ isLoading: metricsLoading, opacity: 1 }"
            :class="[
              'chart-box',
              { 'is-loading': metricsLoading },
              { 'is-empty': !isShowMetrics },
            ]"
          >
            <template v-if="isShowMetrics && !metricsLoading">
              <chart
                ref="alarmMetrics"
                :options="alarmMetrics"
                auto-resize
                style="width: 660px; height: 300px; background: #1e1e21"
              />
              <div class="legend-info">
                <p>
                  <span class="blue" />
                  {{ alarmMetricsTitle }}
                  <span class="red" />
                  {{ $t("阈值") }}
                  <span class="circle" />
                  {{ $t("告警开始时间") }}
                </p>
              </div>
            </template>
            <template v-else-if="!isShowMetrics && !metricsLoading">
              <div class="metrics-empty">
                <table-empty empty />
              </div>
            </template>
            <template v-else>
              <div class="metrics-empty">
                <table-empty empty />
              </div>
            </template>
          </div>
          <template v-if="!sliderLoading">
            <a
              v-if="
                curDetailData.genre &&
                  curDetailData.genre.name === 'GCS-MySQL 慢查询'
              "
              style="line-height: 28px"
              :href="GLOBAL.DOC.CHECK_SQL"
              target="_blank"
            >
              {{ $t("文档：如何查看慢查询的 SQL 语句") }}
            </a>
            <div class="detail-item">
              <div class="item-title">
                {{ $t("告警开始时间：") }}
              </div>
              <div class="item-content">
                {{ curDetailData.start || "--" }}
              </div>
            </div>
            <div class="detail-item pd">
              <div class="item-title">
                {{ $t("告警内容：") }}
              </div>
              <div class="item-content">
                {{ curDetailData.message || "--" }}
              </div>
            </div>
            <div
              v-for="(item, index) in curDetailData.status"
              :key="index"
              class="status-item"
            >
              <div class="detail-item">
                <div class="item-title">
                  {{ $t("处理步骤：") }}
                </div>
                <div class="item-content">
                  {{ executorMap[item.executor] }}
                </div>
              </div>
              <template v-if="item.details">
                <div class="detail-item">
                  <div class="item-title">
                    {{ $t("通知人员：") }}
                  </div>
                  <div class="item-content">
                    {{ item.details.receiver || "--" }}
                  </div>
                </div>
                <div class="detail-item">
                  <div class="item-title">
                    {{ $t("通知方式：") }}
                  </div>
                  <div class="item-content">
                    {{ noticeTypeMap[item.details.type] || "--" }}
                  </div>
                </div>
              </template>
              <div class="detail-item">
                <div class="item-title">
                  {{ $t("通知时间：") }}
                </div>
                <div class="item-content">
                  {{ item.created || "--" }}
                </div>
              </div>
              <div class="detail-item">
                <div class="item-title">
                  {{ $t("处理结果：") }}
                </div>
                <div class="item-content">
                  {{ item.status === "Failed" ? $t("失败") : $t("成功") }}
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </bk-sideslider>
  </div>
</template>
<script>import _ from 'lodash';
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import 'echarts/lib/component/markLine';
import 'echarts/lib/component/markPoint';
import moment from 'moment';
import chartOption from '@/json/alarm-record-chart-option';
import i18n from '@/language/i18n';

const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment()
  .subtract(1, 'days')
  .format('YYYY-MM-DD HH:mm:ss');

// console.warn(initEndDate)
// console.warn(initStartDate)

let timeRangeCache = '';
let timeShortCutText = '';
export default {
  name: '',
  components: {
    chart: ECharts,
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
        onClick(picker) {
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
        onClick(picker) {
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
        onClick(picker) {
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
        onClick(picker) {
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
        onClick(picker) {
          timeRangeCache = '1d';
          timeShortCutText = i18n.t('最近1天');
        },
      },
      {
        text: i18n.t('最近7天'),
        value() {
          const end = new Date();
          const start = new Date();
          start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
          return [start, end];
        },
        onClick(picker) {
          timeRangeCache = '7d';
          timeShortCutText = i18n.t('最近7天');
        },
      },
    ];

    return {
      alarmRecordList: [],
      tableLoading: false,
      isShowDetailSlider: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      curData: {},
      isTypeSort: true,
      curEnv: '',
      envList: [
        {
          name: i18n.t('预发布环境'),
          id: 'stag',
        },
        {
          name: i18n.t('生产环境'),
          id: 'prod',
        },
      ],
      selectLoading: false,
      currentBackup: 1,
      keyword: '',

      datePickerOption: {
        // 小于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      dateShortCut,
      initDateTimeRange: [initStartDate, initEndDate],
      dateParams: {
        start_time: initStartDate,
        end_time: initEndDate,
      },
      timerDisplay: this.$t('最近1天'),
      isDatePickerOpen: false,
      searchParams: {
        code: '',
        module: '',
        env: '',
        uuid: '',
        search: '',
        is_active: false,
        genre: '',
        start_after: initStartDate,
        start_before: initEndDate,
        ordering: '-start',
      },
      curDetailData: {},
      executorMap: {
        notify: this.$t('发送通知'),
      },
      noticeTypeMap: {
        qywx: this.$t('企业微信'),
        email: this.$t('邮件'),
        wx: this.$t('微信'),
      },
      curDateType: 'custom',
      requestQueue: ['detail'],
      isShowMetrics: true,
      alarmMetrics: chartOption,
      alarmMetricsTitle: '',
      metricsList: [],
      metricsThreshold: '',
      metricsLoading: false,
      pageRequestQueue: ['list'],
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      curSourceValue: 'BK',
      curTableSources: 'BK',
      sourceList: [
        { id: 'BK', name: this.$t('蓝鲸监控') },
        { id: 'BCS', name: this.$t('BCS 监控') },
      ],
      bkAlarmRecordList: [],
      // 默认为升序
      sortDirection: 'asc',
    };
  },
  computed: {
    sliderLoading() {
      return this.requestQueue.length > 0;
    },
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    // 云原生app
    isCloudNativeApp() {
      return this.curAppInfo.application.type === 'cloud_native';
    },
    // 是否显示来源
    isSourceSelect() {
      // 非云原生 & te
      return !this.isCloudNativeApp && this.$isInternalVersion;
    },
    // 下拉框是否为蓝鲸监控
    selectValueBK() {
      return this.curSourceValue === 'BK';
    },
    // 数据为蓝鲸监控
    isBkMonitor() {
      return this.curTableSources === 'BK';
    },
    tableData() {
      // 蓝鲸监控全量数据前端分页
      return this.isBkMonitor ? this.curBkPageData : this.alarmRecordList;
    },
    // 蓝鲸监控当前页数据
    curBkPageData() {
      // 当前页数
      const page = this.pagination.current;
      // limit 页容量
      let startIndex = (page - 1) * this.pagination.limit;
      let endIndex = page * this.pagination.limit;
      if (startIndex < 0) {
        startIndex = 0;
      }
      if (endIndex > this.bkAlarmRecordList.length) {
        endIndex = this.bkAlarmRecordList.length;
      }

      // 默认升序
      return this.bkAlarmRecordList.slice(startIndex, endIndex).sort((a, b) => (this.sortDirection === 'asc' ? a.start_time.localeCompare(b.start_time) : b.start_time.localeCompare(a.start_time)));
    },
  },
  watch: {
    $route() {
      this.handleInit();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
    metricsLoading(val) {
      if (!val && this.isShowDetailSlider && this.metricsList.length > 0) {
        this.$nextTick(() => {
          this.handleRenderChart(this.metricsList);
        });
      }
    },
    pageRequestQueue(value) {
      if (value.length < 1) {
        this.$emit('data-ready');
      }
    },
  },
  created() {
    this.handleInit();
  },
  methods: {
    async handleInit() {
      this.keyword = '';
      this.isTypeSort = true;
      this.pagination.current = 1;
      this.pagination.limit = 10;
      this.curDateType = 'custom';
      this.handleResetSearchParams();
      await this.getCurrentFun();
      // 存在query参数时应先触发打开侧边栏的逻辑
      setTimeout(() => {
        if (this.$route.query.record) {
          this.curData = {
            app: this.$route.params.id,
            uuid: this.$route.query.record,
          };
          this.isShowDetailSlider = true;
          this.requestQueue = ['detail'];
          this.fetchAlarmDetail(() => {
            this.fetchAlarmMetrics();
          });
        }
      });
    },

    hideDatePicker() {
      this.isDatePickerOpen = false;
    },

    handleResetSearchParams() {
      const { query } = this.$route;

      if (query.start_after && query.start_before) {
        this.initDateTimeRange = [query.start_after, query.start_before];
        this.dateParams = Object.assign(
          {},
          {
            start_time: query.start_after,
            end_time: query.start_before,
          },
        );
        this.timerDisplay = `${query.start_after} - ${query.start_before}`;
        this.searchParams.start_after = query.start_after;
        this.searchParams.start_before = query.start_before;
        this.curDateType = 'date';
      } else {
        this.initDateTimeRange = [initStartDate, initEndDate];
        this.dateParams = Object.assign(
          {},
          {
            start_time: initStartDate,
            end_time: initEndDate,
          },
        );
        this.timerDisplay = this.$t('最近1天');
        this.searchParams.start_after = initStartDate;
        this.searchParams.start_before = initEndDate;
      }

      timeShortCutText = ''; // 清空
      timeRangeCache = ''; // 清空

      this.searchParams.env = query.env ? query.env : '';
      this.curEnv = query.env ? query.env : '';
      this.searchParams.search = query.search ? query.search : '';
      this.keyword = query.search ? query.search : '';
      this.searchParams.genre = query.genre ? query.genre : '';
      this.searchParams.code = this.$route.params.id;
      this.searchParams.module = this.$route.params.moduleId || '';
      this.pageRequestQueue = ['list'];
    },

    async getCurrentFun() {
      this.selectValueBK ? await this.getBkRecordList() : await this.fetchRecordList(true);
    },

    // 获取BCS监控数据
    async fetchRecordList(isTableLoading = false) {
      this.tableLoading = isTableLoading;
      this.curTableSources = 'BCS';
      const params = {
        ...this.searchParams,
        offset: this.pagination.limit * (this.pagination.current - 1),
        limit: this.pagination.limit,
      };
      try {
        const res = await this.$store.dispatch('alarm/getAlarmList', params);
        this.pagination.count = res.count;
        this.alarmRecordList.splice(
          0,
          this.alarmRecordList.length,
          ...(res.results || []),
        );
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取告警记录失败： ')}${e.detail}`,
        });
      } finally {
        this.tableLoading = false;
        this.pageRequestQueue.shift();
      }
    },

    // 获取蓝鲸监控
    async getBkRecordList() {
      this.tableLoading = true;
      // 当前数据源为蓝鲸监控
      this.curTableSources = 'BK';

      // 请求参数格式化
      const data = {
        start_time: this.searchParams.start_after,
        end_time: this.searchParams.start_before,
      };
      if (this.searchParams.env) {
        data.environment = this.searchParams.env;
      }
      if (this.searchParams.search) {
        data.keyword = this.searchParams.search;
      }
      try {
        const alarmList = await this.$store.dispatch('alarm/getBkAlarmList', {
          appCode: this.searchParams.code,
          data,
        });

        // 全量数据前端分页
        this.pagination.count = alarmList.length;
        this.bkAlarmRecordList = alarmList;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取告警记录失败： ')}${e.detail}`,
        });
      } finally {
        this.tableLoading = false;
        this.pageRequestQueue.shift();
      }
    },

    timestampToTime(timestamp) {
      let time = '';
      if (timestamp) {
        time = new Date(timestamp);
      } else {
        time = new Date();
      }
      const Y = `${time.getFullYear()}-`;
      const M = `${time.getMonth() + 1 < 10 ? `0${time.getMonth() + 1}` : time.getMonth() + 1}-`;
      const D = time.getDate() < 10 ? `0${time.getDate()}` : time.getDate();
      const h = `${time.getHours() < 10 ? `0${time.getHours()}` : time.getHours()}:`;
      const m = `${time.getMinutes() < 10 ? `0${time.getMinutes()}` : time.getMinutes()}:`;
      const s = time.getSeconds() < 10 ? `0${time.getSeconds()}` : time.getSeconds();
      return `${Y + M + D} ${h}${m}${s}`;
    },

    async fetchAlarmMetrics() {
      const { app, start, uuid } = this.curData;
      const getTime = (value) => {
        const time = new Date(start).getTime() + value;
        return this.timestampToTime(time);
      };
      // 查询当前时间的前40分钟后20分钟的数据
      const params = {
        code: app,
        record: uuid,
        step: '1m',
        start: getTime(-60 * 1000 * 40),
        end: getTime(+60 * 1000 * 20),
      };
      this.metricsLoading = true;
      try {
        const res = await this.$store.dispatch('alarm/getAlarmMetrics', params);
        this.isShowMetrics = true;
        this.alarmMetricsTitle = res.name;
        this.metricsThreshold = res.threshold;
        this.metricsList.splice(
          0,
          this.metricsList.length,
          ...(res.results || []),
        );
        // this.$nextTick(() => {
        //     this.handleRenderChart(this.metricsList)
        // })
      } catch (e) {
        this.isShowMetrics = false;
        // this.$paasMessage({
        //     limit: 1,
        //     theme: 'error',
        //     message: `获取告警记录指标趋势失败： ${e.detail}`
        // })
      } finally {
        this.metricsLoading = false;
      }
    },

    handleRenderChart(payload) {
      const xAxisData = [];
      const series = [];
      const chartData = [];
      const curTime = new Date(this.curData.start).getTime();
      payload.forEach((item) => {
        const { values } = item;
        values.forEach((val) => {
          xAxisData.push(moment(val[0] * 1000).format('MM-DD HH:mm:ss'));
          chartData.push(val[1]);
        });
        const curValues =          values.find(val => val[0] === curTime / 1000) || values[0];
        series.push({
          name: this.alarmMetricsTitle,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: {
            normal: {
              color: '#3a84ff',
              width: 1,
            },
          },
          markLine: {
            symbol: 'none',
            data: [
              {
                name: '',
                yAxis: this.metricsThreshold,
              },
            ],
            lineStyle: {
              normal: {
                color: '#c23531',
              },
            },
          },
          markPoint: {
            symbol: 'circle',
            symbolSize: 10,
            data: [
              {
                name: '',
                coord: [
                  moment(curTime).format('MM-DD HH:mm:ss'),
                  curValues[1].toFixed(2),
                ],
                label: {
                  normal: {
                    show: false,
                  },
                },
              },
            ],
            itemStyle: {
              normal: {
                color: '#1768ef',
              },
            },
          },
          data: chartData,
        });
      });
      const metricsRef = this.$refs.alarmMetrics;
      metricsRef.mergeOptions({
        xAxis: [
          {
            data: xAxisData,
          },
        ],
        series,
      });
    },

    clearChart() {
      const metricsRef = this.$refs.alarmMetrics;

      metricsRef
        && metricsRef.mergeOptions({
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
              lineStyle: {
                normal: {
                  color: '#3a84ff',
                  width: 1,
                },
              },
              data: [0],
            },
          ],
        });
    },

    handlerChartHide() {
      // this.clearChart()
      this.alarmMetrics = _.cloneDeep(chartOption);
    },

    async fetchAlarmDetail(callback) {
      const { app, uuid } = this.curData;
      const params = {
        appCode: app,
        record: uuid,
      };
      try {
        const res = await this.$store.dispatch('alarm/getAlarmDetail', params);
        this.curDetailData = JSON.parse(JSON.stringify(res));
        this.curData.start = this.curDetailData.start;
        callback && callback();
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取告警记录详情失败： ')}${e.detail}`,
        });
      } finally {
        this.requestQueue.shift();
      }
    },

    /**
     * 选择自定义时间
     */
    handlerChange(dates, type) {
      this.curDateType = !type ? 'custom' : type;
      this.dateParams.start_time = dates[0];
      this.dateParams.end_time = dates[1];
      this.dateParams.time_range = timeRangeCache || 'customized';
      if (timeShortCutText) {
        this.timerDisplay = timeShortCutText;
      } else {
        this.timerDisplay = `${dates[0]} - ${dates[1]}`;
      }
      timeShortCutText = ''; // 清空
      timeRangeCache = ''; // 清空
    },

    toggleDatePicker() {
      this.isDatePickerOpen = !this.isDatePickerOpen;
    },

    /**
     * 选择自定义时间，并确定
     */
    handlerPickSuccess() {
      this.isDatePickerOpen = false;
    },

    // 查询回调
    handleSearch() {
      this.searchParams.start_after = this.dateParams.start_time;
      this.searchParams.start_before = this.dateParams.end_time;
      this.searchParams.env = this.curEnv;
      this.searchParams.search = this.keyword;
      this.getCurrentFun();
    },

    // 告警记录排序
    handleTypeSort() {
      if (!this.pagination.count) {
        return;
      }
      // 蓝鲸监控排序
      if (this.isBkMonitor) {
        // 前端排序
        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        return;
      }
      this.isTypeSort = !this.isTypeSort;
      this.searchParams.ordering = this.isTypeSort ? '-start' : 'start';
      this.pagination.current = 1;
      this.pagination.limit = 10;
      this.getCurrentFun();
    },

    renderTypeHeader(h, { column }) {
      return h(
        'div',
        {
          on: {
            click: this.handleTypeSort,
          },
          style: {
            cursor: this.pagination.count ? 'pointer' : 'not-allowed',
          },
        },
        [
          h('span', {
            domProps: {
              innerHTML: i18n.t('告警开始时间'),
            },
          }),
          h('img', {
            style: {
              position: 'relative',
              top: '1px',
              left: '1px',
              transform: this.isTypeSort ? 'rotate(0)' : 'rotate(180deg)',
            },
            attrs: {
              src: '/static/images/sort-icon.png',
            },
          }),
        ],
      );
    },

    handleDetail(payload) {
      // 蓝鲸监控，新标签页
      if (this.isBkMonitor) {
        window.open(payload.detail_link, '_blank');
        return;
      }

      this.curData = JSON.parse(JSON.stringify(payload));
      this.isShowDetailSlider = true;
      this.requestQueue = ['detail'];

      const metricsRef = this.$refs.alarmMetrics;

      metricsRef
        && metricsRef.mergeOptions({
          xAxis: [
            {
              data: [],
            },
          ],
          series: [],
        });

      this.fetchAlarmDetail();
      this.fetchAlarmMetrics();
    },

    handleSliderAfterClose() {
      this.curData = {};
      this.curDetailData = {};
      this.alarmMetricsTitle = '';
      this.metricsList = [];
      this.metricsThreshold = '';
      this.metricsLoading = false;
    },

    /**
     * 分页页码 chang 回调
     *
     * @param {Number} page 页码
     */
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
      // bcs监控
      if (!this.isBkMonitor) {
        this.getCurrentFun();
      } else {
        this.tableLoading = true;
        // 前端视觉分页loading
        setTimeout(() => {
          this.tableLoading = false;
        }, 200);
      }
    },

    /**
     * 分页limit chang 回调
     *
     * @param {Number} currentLimit 新limit
     * @param {Number} prevLimit 旧limit
     */
    limitChange(currentLimit, prevLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      // bcs监控
      if (!this.isBkMonitor) {
        this.getCurrentFun();
      } else {
        this.tableLoading = true;
        // 前端视觉分页loading
        setTimeout(() => {
          this.tableLoading = false;
        }, 200);
      }
    },

    // 清空搜索条件
    clearFilter() {
      this.keyword = '';
      this.curEnv = '';
      this.getCurrentFun();
    },

    updateTableEmptyConfig() {
      const time = this.initDateTimeRange.some(Boolean);
      if (this.keyword || this.curEnv) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      } if (time) {
        this.tableEmptyConf.keyword = '$CONSTANT';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>
<style lang="scss">
.paas-monitor-alarm-wrapper {
  .search-wrapper {
    position: relative;
    .search-select {
      display: inline-block;
      &.ml {
        margin-left: 10px;
      }
      .label,
      .select {
        display: inline-block;
        vertical-align: middle;
      }
    }
    .action-btn {
      height: 32px;
      background: #f5f6fa;
      line-height: 32px;
      min-width: 28px;
      display: flex;
      border-radius: 2px;
      cursor: pointer;
      position: relative;

      .text {
        min-width: 90px;
        line-height: 32px;
        text-align: left;
        color: #63656e;
        font-size: 12px;
        display: inline-block;
      }

      .left-icon,
      .right-icon {
        width: 28px;
        height: 28px;
        line-height: 32px;
        color: #c4c6cc;
        display: inline-block;
        text-align: center;
      }

      &.refresh {
        width: 28px;
      }
    }
    .search-action {
      position: absolute;
      top: 0;
      left: 612px;
      &.reset-right {
        left: 754px;

        &.not-source {
          left: 624px;
        }
      }
      &.not-source {
        left: 482px;
      }
    }
  }
  .bk-table {
    margin-top: 16px;
    &.is-being-loading {
      border-bottom: 1px solid #dfe0e5;
    }
  }
}
.paas-alarm-detail-slider {
  color: #63656e;
  .bk-sideslider-wrapper {
    padding-bottom: 0;
  }
  .alarm-detail-slider-content {
    padding: 20px;
    height: calc(100vh - 61px);
    .status-item {
      padding: 5px 0;
      border-top: 1px solid #dcdee5;
    }
    .chart-box {
      position: relative;
      margin-bottom: 6px;
      width: 660px;
      height: 327px;
      border-bottom: 1px solid #dde4eb;
      background-color: #fff !important;
      &.is-loading {
        border: none;
      }
      &.is-empty {
        border: 1px solid #dde4eb;
      }
      .legend-info {
        margin-bottom: 10px;
        font-size: 12px;
        p {
          text-align: center;
        }
        .blue {
          position: relative;
          top: -3px;
          display: inline-block;
          width: 15px;
          height: 2px;
          background: #3a84ff;
        }
        .red {
          position: relative;
          top: -3px;
          margin-left: 8px;
          display: inline-block;
          width: 15px;
          height: 2px;
          background: #c23531;
        }
        .circle {
          position: relative;
          top: -1px;
          margin-left: 8px;
          display: inline-block;
          width: 8px;
          height: 8px;
          background: #3a84ff;
          border-radius: 50%;
        }
      }
      .metrics-empty {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 12px;
        i {
          font-size: 65px;
          color: #c3cdd7;
        }
        .text {
          text-align: center;
        }
      }
    }
    .detail-item {
      display: flex;
      justify-content: flex-start;
      line-height: 28px;
      &.pd {
        padding-bottom: 5px;
      }
      .item-title {
        flex: 0 0 auto;
        color: #313238;
      }
      .item-content {
        max-width: calc(100% - 70px);
        word-break: break-all;
      }
    }
  }
}
</style>
