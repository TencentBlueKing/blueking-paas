<template lang="html">
  <div class="right-main">
    <template v-if="appType !== 'cloud_native'">
      <app-top-bar
        v-if="engineEnabled"
        :title="$t('自定义事件统计')"
        :can-create="canCreateModule"
        :cur-module="curAppModule"
        :module-list="curAppModuleList"
      />
      <div
        v-else
        class="ps-top-bar"
      >
        <h2> {{ $t('自定义事件统计') }} </h2>
      </div>
    </template>
    <paas-content-loader
      :is-loading="isPageLoading"
      placeholder="analysis-loading"
      :offset-top="20"
      class="app-container middle event-analy-container"
    >
      <div class="ps-top-card mt20">
        <section class="content no-border">
          <div
            :class="['content-header', { 'mt15': engineEnabled }]"
          >
            <div
              v-if="engineEnabled"
              class="bk-button-group fl"
            >
              <bk-button
                theme="primary"
                style="width: 101px;"
                :outline="curEnv !== 'stag'"
                @click="curEnv = 'stag'"
              >
                {{ $t('预发布环境') }}
              </bk-button>
              <bk-button
                theme="primary"
                style="width: 101px;"
                :outline="curEnv !== 'prod'"
                @click="curEnv = 'prod'"
              >
                {{ $t('生产环境') }}
              </bk-button>
            </div>
            <div
              v-else
              class="f12 fl"
              style="color: #666;"
            >
              {{ $t('基于网站嵌入的统计脚本进行访问量统计') }}
              <bk-button
                text
                class="info-button"
                @click.stop="isShowSideslider = true"
              >
                {{ $t('接入指引') }}
              </bk-button>
            </div>
            <bk-date-picker
              v-model="initDateTimeRange"
              class="fr"
              :placeholder="$t('选择日期范围')"
              :type="'daterange'"
              placement="bottom-end"
              :shortcuts="shortcuts"
              :shortcut-close="true"
              :options="dateOptions"
              @change="handleDateChange"
            />
          </div>

          <div
            v-if="engineEnabled"
            class="desc f12 fix"
          >
            {{ $t('基于网站嵌入的统计脚本进行访问量统计') }}
            <bk-button
              text
              class="info-button"
              @click.stop="isShowSideslider = true"
            >
              {{ $t('接入指引') }}
            </bk-button>
          </div>

          <div
            class="analysis-box"
            :class="!engineEnabled ? 'set-margin-top' : ''"
          >
            <div class="summary">
              <div class="pv">
                <strong class="title">{{ summaryData.ev || 0 }}</strong>
                <p class="desc">
                  {{ $t('事件总数') }}
                </p>
              </div>
              <div class="uv">
                <strong class="title">{{ summaryData.ue || 0 }}</strong>
                <p class="desc">
                  {{ $t('唯一身份事件数') }}
                  <i
                    v-bk-tooltips="tootipsText"
                    class="paasng-icon paasng-exclamation-circle event-tips"
                  />
                </p>
              </div>
            </div>
            <div class="chart-wrapper">
              <div class="chart-box">
                <div class="chart-action">
                  <ul class="dimension fl">
                    <li
                      :class="{ 'active': chartFilterType.ue }"
                      @click="handleChartFilte('ue')"
                    >
                      <span class="dot warning" /> {{ $t('事件总数') }}
                    </li>
                    <li
                      :class="{ 'active': chartFilterType.ev }"
                      @click="handleChartFilte('ev')"
                    >
                      <span class="dot primary" /> {{ $t('唯一身份事件数') }}
                    </li>
                  </ul>

                  <ul class="time fr">
                    <li
                      v-if="allowRanges.includes('5m')"
                      :class="{ 'active': defaultRange === '5m' }"
                      @click="handleRangeChange('5m')"
                    >
                      {{ $t('5分钟') }}
                    </li>
                    <li
                      v-if="allowRanges.includes('1h')"
                      :class="{ 'active': defaultRange === '1h', 'disabled': !allowRanges.includes('1h') }"
                      @click="handleRangeChange('1h')"
                    >
                      {{ $t('小时') }}
                    </li>
                    <li
                      v-if="allowRanges.includes('1d')"
                      :class="{ 'active': defaultRange === '1d' }"
                      @click="handleRangeChange('1d')"
                    >
                      {{ $t('天') }}
                    </li>
                  </ul>
                </div>
                <chart
                  ref="chart"
                  :options="chartOption"
                  auto-resize
                  style="width: 100%; height: 240px; background: #1e1e21;"
                />
              </div>
            </div>
          </div>

          <div class="content-header mt15">
            <div class="event-title-wrapper">
              <span
                :class="['title', { 'has-cursor': curCategory !== '' }]"
                @click="handleBackEventList"
              > {{ $t('类别列表') }} </span>
              <i
                v-if="curCategory !== ''"
                class="paasng-icon paasng-ps-arrow-right"
              />
              <span
                v-if="curCategory !== ''"
                class="cur-event-name"
              >{{ curCategory }}</span>
            </div>
            <bk-button
              class="export-button"
              theme="default"
              :disabled="!pathData.length"
              :loading="exportLoading"
              @click="handleExportToExcel"
            >
              {{ $t('导出') }}
            </bk-button>
          </div>
          <bk-table
            v-bkloading="{ isLoading: isPathDataLoading }"
            style="margin-top: 15px;"
            :data="pathData"
            :size="'small'"
            :pagination="pagination"
            @page-change="pageChange"
            @page-limit-change="limitChange"
            @sort-change="sortChange"
          >
            <div slot="empty">
              <table-empty empty />
            </div>
            <bk-table-column
              v-for="field of fieldList"
              :key="field.prop"
              :column-key="field.prop"
              :label="$t(field.name)"
              :prop="field.prop"
              :sortable="field.sortable"
              :render-header="$renderHeader"
            >
              <template slot-scope="{ row }">
                <span
                  v-if="field.prop === 'category'"
                  class="display-name"
                  @click.stop="handleViewDetail(row[field.prop])"
                >
                  {{ row[field.prop] }}
                </span>
                <span v-else>
                  {{ row[field.prop] }}
                </span>
              </template>
            </bk-table-column>
          </bk-table>
        </section>
      </div>
      <render-sideslider
        is-event
        :is-show.sync="isShowSideslider"
        :title="sidesliderTitle"
        :engine-enable="curAppInfo.web_config.engine_enabled"
        :site-name="siteDisplayName"
      />
    </paas-content-loader>
  </div>
</template>

<script> import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';

import moment from 'moment';
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import RenderSideslider from './comps/access-guide-sideslider';
import chartOption from '@/json/analysis-chart-option';
// eslint-disable-next-line
    import { export_json_to_excel } from '@/common/Export2Excel'
import { formatDate } from '@/common/tools';

export default {
  components: {
    appTopBar,
    // appAnalysis: analysis,
    chart: ECharts,
    RenderSideslider,
  },
  mixins: [appBaseMixin],
  props: {
    appType: {
      type: String,
      default: 'normal'
    }
  },
  data() {
    return {
      engineEnabled: true,
      isPathDataLoading: false,
      curEnv: 'stag',
      daterange: [new Date(), new Date()],
      page: '',
      pageList: [],
      pathData: [],
      fieldList: [],
      defaultRange: '1d',
      dateRange: {
        startTime: '',
        endTime: '',
      },
      chartFilterType: {
        ue: true,
        ev: true,
      },
      curTab: 'webAnalysis',
      initDateTimeRange: [],
      dateOptions: {
        // 大于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      summaryData: {
        ev: '--',
        ue: '--',
      },
      pageAnalysisData: [],
      isPageLoading: true,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        ordering: '',
      },
      currentBackup: 1,
      chartOption: chartOption.pv_uv,
      dimensionType: 'action',
      shortcuts: [
        {
          text: this.$t('今天'),
          value() {
            const end = new Date();
            const start = new Date();
            return [start, end];
          },
        },
        {
          text: this.$t('最近7天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
            return [start, end];
          },
        },
        {
          text: this.$t('最近30天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);
            return [start, end];
          },
        },
      ],
      exportLoading: false,
      isEditLoading: false,
      isShowSideslider: false,
      tootipsText: this.$t('一天内一个用户对一个事件(相同类型、ID和操作)多次操作仅被计算为1次。'),
      analysisConfig: null,
      curCategory: '',

      requestQueue: ['evuv', 'config', 'chart', 'event'],
    };
  },
  computed: {
    isLoading() {
      return this.requestQueue.length > 0;
    },
    dateFormat() {
      let isInDay = false; // 是否在一天内
      if (this.dateRange.startTime && this.dateRange.endTime) {
        const start = this.dateRange.startTime;
        const end = this.dateRange.endTime;

        const endSeconds = moment(end).valueOf();
        const oneEndSeconds = moment(start).add(1, 'days')
          .valueOf(); // 一天后
        if (oneEndSeconds > endSeconds) {
          isInDay = true;
        }
      }

      if (this.defaultRange === '1d') {
        return 'MM-DD';
      } if (this.defaultRange === '1h') {
        if (isInDay) {
          return 'HH:mm';
        }
        return 'MM-DD HH:mm';
      } if (this.defaultRange === '5m') {
        if (isInDay) {
          return 'HH:mm';
        }
        return 'MM-DD HH:mm';
      }
      return 'MM-DD';
    },
    chartData() {
      const data = this.$store.state.log.chartData;
      return data;
    },
    hasChartData() {
      if (this.chartData.series.length && this.chartData.series[0].data.length) {
        return true;
      }
      return false;
    },
    allowRanges() {
      if (this.dateRange.startTime && this.dateRange.endTime) {
        const start = this.dateRange.startTime;
        const end = this.dateRange.endTime;
        const now = moment().format('YYYY-MM-DD');

        const startSeconds = moment(start).valueOf();
        const endSeconds = moment(end).valueOf();
        const oneEndSeconds = moment(start).add(1, 'days')
          .valueOf(); // 一天后
        const threeEndSeconds = moment(start).add(3, 'days')
          .valueOf(); // 三天后
        const sevenEndSeconds = moment(now).add(-7, 'days')
          .valueOf(); // 七天后

        // 精度规则:
        // if 时间选择器选择访问 < 1d
        // then 允许选择 5min、1h的精度
        // else if 1d < 时间选择器选择访问 < 3d
        // then 允许选择 1h、1d的精度
        // else if 3d < 时间选择器选择访问
        // then 允许选择 1h、1d的精度
        // 7天之前的数据不允许分钟精度
        if (threeEndSeconds <= endSeconds) {
          // 大于3天
          return ['1h', '1d'];
        }
        if (oneEndSeconds <= startSeconds) {
          // 大于1天小于3天
          return ['1h', '1d'];
        }
        if (startSeconds <= sevenEndSeconds) {
          return ['1h'];
        }
        // 小于1天
        return ['5m', '1h'];
      }
      return ['5m', '1h', '1d'];
    },
    siteDisplayName() {
      return this.analysisConfig ? this.analysisConfig.site.name : '';
    },
    sidesliderTitle() {
      const curEnvText = this.curEnv === 'stag' ? this.$t('预发布环境') : this.$t('生产环境');
      return this.engineEnabled ? `${this.$t('自定义事件统计')}-${curEnvText}` : '';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    dateRange: {
      deep: true,
      handler() {
        this.refresh();
      },
    },
    defaultRange() {
      this.showInstanceChart();
    },
    curEnv() {
      this.refresh();
    },
    allowRanges() {
      this.defaultRange = this.allowRanges[this.allowRanges.length - 1];
    },
    '$route'() {
      this.engineEnabled = this.curAppInfo.web_config.engine_enabled;
      this.refresh();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
  },
  created() {
    moment.locale(this.localLanguage);
    window.moment = moment;
    this.siteName = 'default';
    this.engineEnabled = this.curAppInfo.web_config.engine_enabled;
  },
  mounted() {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
    this.initDateTimeRange = [start, end];

    this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
    this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
    this.init();
  },
  methods: {
    init() {
      this.getEvUv();
      this.getAnalysisConfig();
      this.showInstanceChart();
      this.getEventData();
    },

    handleBackEventList() {
      if (this.curCategory === '') {
        return;
      }
      this.curCategory = '';
      this.pagination = Object.assign({}, {
        current: 1,
        count: 0,
        limit: 10,
        ordering: '',
      });
      this.getEventData();
    },

    handleViewDetail(payload) {
      if (this.curCategory === payload) {
        return;
      }
      this.curCategory = payload;
      this.pagination = Object.assign({}, {
        current: 1,
        count: 0,
        limit: 10,
        ordering: '',
      });
      this.getEventData();
    },

    async handleExportToExcel() {
      this.exportLoading = true;
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const env = this.curEnv;
        const dimension = this.dimensionType;
        const category = this.curCategory;
        const params = {
          limit: 10000,
          offset: 0,
          start_time: this.dateRange.startTime,
          end_time: this.dateRange.endTime,
        };

        params.ordering = this.pagination.ordering || '-ev';
        const url = category !== '' ? 'analysis/getEventDetail' : 'analysis/getEventOverview';
        const requestParams = {
          appCode,
          moduleId,
          env,
          params,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        };
        if (category !== '') {
          requestParams.dimension = dimension;
          requestParams.category = category;
        }
        const res = await this.$store.dispatch(url, requestParams);
        const fields = this.fieldList.map(item => item.name);
        const props = this.fieldList.map(item => item.prop);
        const data = this.formatJson(props, res.resources);
        const fileName = this.engineEnabled ? `${appCode}_${this.curModuleId}_custom_event_statistics_${this.dimensionType}` : `${appCode}_custom_event_statistics_${this.dimensionType}`;
        export_json_to_excel(fields, data, fileName);
      } catch (e) {
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      } finally {
        this.exportLoading = false;
      }
    },

    formatJson(filterVal, jsonData) {
      return jsonData.map(v => filterVal.map(j => v[j]));
    },

    refresh() {
      this.clearData();
      this.requestQueue = ['evuv', 'config', 'chart', 'event'];
      const promises = [
        this.getEvUv(),
        this.getAnalysisConfig(),
        this.showInstanceChart(),
        this.getEventData(),
      ];

      this.$nextTick(() => {
        Promise.all(promises).finally(() => {
          this.isPageLoading = false;
        });
      });
    },

    clearData() {
      this.summaryData = {
        ev: '--',
        ue: '--',
      };

      this.pagination = {
        current: 1,
        count: 0,
        limit: 10,
        ordering: '',
      };

      this.curCategory = '';
      this.pathData = [];
      this.clearChart();
    },

    async getEvUv() {
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const env = this.curEnv;

        const params = {
          start_time: this.dateRange.startTime,
          end_time: this.dateRange.endTime,
          interval: this.defaultRange,
        };
        const res = await this.$store.dispatch('analysis/getEventEvUv', {
          appCode,
          moduleId,
          env,
          params,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        });
        this.summaryData = res.result.results;
      } catch (e) {
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      } finally {
        this.requestQueue.shift();
      }
    },

    async getAnalysisConfig() {
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const env = this.curEnv;

        const res = await this.$store.dispatch('analysis/getEventAnalysisConfig', {
          appCode,
          moduleId,
          env,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        });
        this.analysisConfig = res;
      } catch (e) {
        console.error(e);
      } finally {
        this.requestQueue.shift();
      }
    },

    async getEventData(page) {
      this.isPathDataLoading = true;
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const env = this.curEnv;
        const dimension = this.dimensionType;
        const category = this.curCategory;
        const curPage = page || this.pagination.current;

        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
          start_time: this.dateRange.startTime,
          end_time: this.dateRange.endTime,
        };

        params.ordering = this.pagination.ordering || '-ev';
        const url = category !== '' ? 'analysis/getEventDetail' : 'analysis/getEventOverview';
        const requestParams = {
          appCode,
          moduleId,
          env,
          params,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        };
        if (category !== '') {
          requestParams.dimension = dimension;
          requestParams.category = category;
        }
        const res = await this.$store.dispatch(url, requestParams);

        const fieldList = [];
        const { schemas } = res.meta;
        schemas.forEach((item) => {
          fieldList.push({
            name: item.display_name,
            prop: item.name,
            sortable: item.sortable ? 'custom' : false,
          });
        });
        this.pathData = res.resources;
        this.fieldList = fieldList;
        this.pagination.count = res.meta.pagination.total;
      } catch (e) {
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      } finally {
        this.isPathDataLoading = false;
        this.requestQueue.shift();
      }
    },

    /**
             * 显示实例指标数据
             */
    showInstanceChart(instance, processes) {
      const chartRef = this.$refs.chart;

      chartRef && chartRef.mergeOptions({
        xAxis: [
          {
            data: [],
          },
        ],
        series: [],
      });

      chartRef && chartRef.showLoading({
        text: this.$t('正在加载'),
        color: '#30d878',
        textColor: '#fff',
        maskColor: 'rgba(255, 255, 255, 0.8)',
      });

      this.getChartData();
    },

    async getChartData() {
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const env = this.curEnv;
        const start = `${this.dateRange.startTime} 00:00`;
        const end = `${this.dateRange.endTime} 23:59`;
        const getEndDate = () => {
          const curTime = new Date(end).getTime();
          const nowTime = new Date().getTime();
          if (curTime > nowTime) {
            return formatDate(new Date());
          }
          return formatDate(end);
        };

        const params = {
          start_time: start,
          end_time: getEndDate(),
          interval: this.defaultRange,
        };

        const res = await this.$store.dispatch('analysis/getEventChartData', {
          appCode,
          moduleId,
          env,
          params,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        });
        this.chartDataCache = res.result.results;
        this.renderChart();
      } catch (e) {
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      } finally {
        this.requestQueue.shift();
      }
    },

    /**
             * 图表初始化
             * @param  {String} type 类型
             * @param  {Object} ref 图表对象
             */
    renderChart() {
      const series = [];
      const xAxisData = [];
      const ev = [];
      const ue = [];
      const chartData = this.chartDataCache;

      chartData.forEach((item) => {
        xAxisData.push(moment(item.time).format(this.dateFormat));
        ue.push(item.ue);
        ev.push(item.ev);
      });

      // ue
      if (this.chartFilterType.ue) {
        series.push({
          name: 'ue',
          type: 'line',
          smooth: true,
          lineStyle: {
            color: '#699df4',
            normal: {
              color: '#699df4',
              width: 1.5,
            },
          },
          symbolSize: 1,
          showSymbol: false,
          areaStyle: {
            normal: {
              opacity: 0,
            },
          },
          data: ue,
        });
      }

      // ev
      if (this.chartFilterType.ev) {
        series.push({
          name: 'ev',
          type: 'line',
          smooth: true,
          symbolSize: 1,
          showSymbol: false,
          lineStyle: {
            color: '#ffb849',
            normal: {
              color: '#ffb849',
              width: 1.5,
            },
          },
          areaStyle: {
            normal: {
              opacity: 0,
            },
          },
          data: ev,
        });
      }

      this.chartOption.xAxis[0].data = xAxisData;
      this.chartOption.series = series;
      setTimeout(() => {
        const chartRef = this.$refs.chart;
        chartRef && chartRef.mergeOptions(this.chartOption, true);
        chartRef && chartRef.resize();
        chartRef && chartRef.hideLoading();
      }, 1000);
    },

    handleChartFilte(type) {
      this.chartFilterType[type] = !this.chartFilterType[type];
      this.renderChart();
    },

    /**
             * 清空图表数据
             */
    clearChart() {
      const chartRef = this.$refs.chart;

      chartRef && chartRef.mergeOptions({
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

    sortPV(data1, data2) {
      const pv1 = data1.pv;
      const pv2 = data2.pv;
      return Number(pv1) > Number(pv2);
    },

    sortUV(data1, data2) {
      const uv1 = data1.uv;
      const uv2 = data2.uv;
      return Number(uv1) > Number(uv2);
    },

    handleDateChange(date, type) {
      this.dateRange = {
        startTime: date[0],
        endTime: date[1],
      };
    },

    handleRangeChange(type) {
      // const end = moment().subtract(0, 'days').format('YYYY-MM-DD')
      // let start = moment().subtract(1, 'days').format('YYYY-MM-DD')
      // if (type === 'week') {
      //     start = moment().subtract(7, 'days').format('YYYY-MM-DD')
      // }
      if (!this.allowRanges.includes(type)) {
        return false;
      }
      this.defaultRange = type;
      // this.dateRange = {
      //     startTime: start,
      //     endTime: end
      // }
    },

    limitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getEventData(this.pagination.current);
    },

    pageChange(newPage) {
      this.pagination.current = newPage;
      this.getEventData(newPage);
    },

    sortChange(params) {
      if (params.order === 'descending') {
        this.pagination.ordering = `-${params.prop}`;
      } else if (params.order === 'ascending') {
        this.pagination.ordering = `${params.prop}`;
      } else {
        this.pagination.ordering = '';
      }
      this.getEventData();
    },
  },
};
</script>
<style lang="scss" scoped>
    .event-analy-container{
        background: #fff;
        margin: 16px auto 30px;
        padding: 1px 24px;
        width: calc(100% - 50px);
        padding-bottom: 24px;
    }
    .content-header {
        position: relative;
        height: 32px;
        .export-button {
            position: absolute;
            top: 0;
            right: 0;
        }

        .event-title-wrapper {
            position: absolute;
            line-height: 32px;
            .title {
                font-size: 14px;
                font-weight: 700;
                &.has-cursor {
                    cursor: pointer;
                }
            }
            .cur-event-name {
                color: #3a84ff;
            }
        }
    }

    .fix {
        line-height: 40px;
        color: #666;
    }

    .analysis-box {
        height: 285px;
        border: 1px solid #DCDEE5;
        display: flex;
        border-radius: 2px;
        overflow: hidden;
        &.set-margin-top {
            margin-top: 16px;
        }

        .summary {
            padding: 20px 0 20px 20px;

            .title {
                font-weight: normal;
                color: #313238;
                font-size: 28px;
            }

            .desc {
                color: #63656E;
                font-size: 12px;
            }

            .pv {
                padding: 33px 0 0 30px;
                width: 200px;
                height: 119px;
                border-radius: 2px;
                background: #f5f6fa;
            }

            .uv {
                padding: 33px 0 0 30px;
                margin-top: 2px;
                width: 200px;
                height: 119px;
                border-radius: 2px;
                background: #f5f6fa;
            }
        }

        .chart-wrapper {
            flex: 1;
            overflow: hidden;
        }

        .event-tips {
            margin-left: 2px;
            color: #63656e;
        }
    }

    .bk-table {
        .display-name {
            color: #3a84ff;
            cursor: pointer;
            &:hover {
                color: #699df4;
            }
        }
    }

    .chart-box {
        width: 100%;
        min-height: 150px;

        .chart-action {
            height: 20px;
            margin-top: 15px;
            padding: 0 30px;
        }

        .dimension {
            li {
                display: inline-block;
                font-size: 12px;
                color: #63656E;
                margin-right: 30px;
                cursor: pointer;
                opacity: 0.4;

                &.active {
                    opacity: 1;
                }

                &:last-child {
                    margin-right: 0;
                }
            }

            .dot {
                width: 10px;
                height: 10px;
                display: inline-block;
                border: 1px solid #3A84FF;
                background: #A3C5FD;
                border-radius: 50%;
                vertical-align: middle;
                float: left;
                margin: 3px 5px 0 0;

                &.warning {
                    border: 1px solid #FF9C01;
                    background: #FFD695;
                }
            }
        }

        .time {
            li {
                display: inline-block;
                font-size: 12px;
                color: #63656E;
                margin-right: 20px;
                font-weight: bold;
                cursor: pointer;
                padding: 0 2px;
                border-bottom: 2px solid #fff;

                &:last-child {
                    margin-right: 0;
                }

                &.active {
                    border-bottom: 2px solid #3a84ff;
                }

                &.disabled {
                    color: #ccc;
                    cursor: not-allowed;
                    border-bottom: 2px solid #fff;
                }
            }
        }
    }

    .info-button {
        height: 30px;
        padding: 0 5px;
        line-height: 30px;
        font-size: 12px;
    }
</style>
