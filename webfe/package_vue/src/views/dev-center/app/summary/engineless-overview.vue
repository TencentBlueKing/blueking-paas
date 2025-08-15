<template lang="html">
  <div
    id="summary"
    class="right-main"
  >
    <app-top-bar
      data-test-id="summary_bar_moduleList"
      :title="$t('应用概览')"
      :is-overview="curFeatureAnalytics"
      :cur-time="curTime"
      :shortcuts="shortcuts"
      @change-date="handleDateChange"
    />
    <paas-content-loader
      :is-loading="loading"
      placeholder="summary-loading"
      :offset-top="20"
      class="app-container overview-middle"
    >
      <div class="summary-content">
        <overview-top-info
          :app-info="topInfo"
          :view-data="viewData"
          :is-module="curFeatureAnalytics"
        />
        <!-- 有数据统计模块 -->
        <div
          v-if="curFeatureAnalytics"
          class="chart-wrapper"
        >
          <div class="desc">
            {{ $t('网站访问统计') }}
            <bk-button
              text
              class="info-button"
              @click.stop="isShowSideslider = true"
            >
              {{ $t('接入指引') }}
            </bk-button>
          </div>
          <chart
            :key="renderChartIndex"
            ref="chart"
            :options="chartOption"
            auto-resize
            style="width: 100%; height: 320px"
          />
        </div>
        <!-- 无数据统计模块 -->
        <div
          v-else
          class="not-stats-module"
        >
          <div class="desc">
            {{ $t('已申请权限的 API') }}
          </div>
          <!-- 是否显示 使用骨架屏遮挡 -->
          <chart
            v-if="gatewayLegth !== 0"
            :key="renderChartIndex"
            ref="notModuleChart"
            :options="notEnginelessOption"
            auto-resize
            style="width: 100%; height: 420px"
          />
          <div
            v-else
            class="chart-empty"
          >
            <table-empty empty />
          </div>
        </div>
      </div>
      <!-- right -->
      <div
        class="overview-sub-fright card-style"
        data-test-id="summary_content_detail"
      >
        <dynamic-state :operations-list="operationsList" />
      </div>
    </paas-content-loader>
    <render-sideslider
      :is-show.sync="isShowSideslider"
      :engine-enable="curAppInfo.web_config.engine_enabled"
      :site-name="siteDisplayName"
    />
  </div>
</template>

<script>
import overviewTopInfo from './comps/overview-top-info';
import dynamicState from './comps/dynamic-state';
import appBaseMixin from '@/mixins/app-base-mixin';
import chartOption from '@/json/analysis-chart-option';
import appTopBar from '@/components/paas-app-bar';
import notEnginelessChartOption from '@/json/engineless-chart-option';
import RenderSideslider from '../engine/analysis/comps/access-guide-sideslider.vue';
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import moment from 'moment';
import { formatDate } from '@/common/tools';
export default {
  components: {
    overviewTopInfo,
    dynamicState,
    chart: ECharts,
    appTopBar,
    RenderSideslider,
  },
  mixins: [appBaseMixin],
  porps: {
    engineEnabled: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      loading: true,
      isChartLoading: false,
      operationsList: [],
      topInfo: {
        type: this.$t('外链应用'),
        description: this.$t('平台为该类应用提供云 API 权限、应用市场等功能'),
      },
      chartOption: chartOption.pv_uv,
      notEnginelessOption: notEnginelessChartOption.config,
      renderChartIndex: 0,
      chartFilterType: {
        pv: true,
        uv: true,
      },
      siteName: 'default',
      chartDataCache: [],
      defaultRange: '1d',
      isShowSideslider: false,
      shortcuts: [
        {
          id: '1d',
          text: this.$t('今天'),
          value() {
            const end = new Date();
            const start = new Date();
            return [start, end];
          },
        },
        {
          id: '3d',
          text: this.$t('最近 3 天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 3);
            return [start, end];
          },
        },
        {
          id: '7d',
          text: this.$t('最近 7 天'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
            return [start, end];
          },
        },
      ],
      dateRange: {
        startTime: '',
        endTime: '',
      },
      summaryData: {
        pv: 0,
        uv: 0,
      },
      apiNumber: 0,
      getawayNumber: 0,
      curDispatchMethod: 'getAppPermissions',
      gatewayList: [],
      gatewayLegth: 1,
      curTime: {},
      analysisConfig: null,
    };
  },
  computed: {
    dateFormat() {
      if (!this.dateRange.startTime || !this.dateRange.endTime) {
        return 'MM-DD'; // 返回一个默认格式
      }
      const start = this.dateRange.startTime;
      const end = this.dateRange.endTime;

      const endSeconds = moment(end).valueOf();
      const oneEndSeconds = moment(start).add(1, 'days').valueOf();
      const isInDay = oneEndSeconds > endSeconds;

      switch (this.defaultRange) {
        case '1d':
          return 'MM-DD';
        case '1h':
        case '5m':
          return isInDay ? 'HH:mm' : 'MM-DD HH:mm';
        default:
          return 'MM-DD';
      }
    },
    chartData() {
      const data = this.$store.state.log.chartData;
      return data;
    },
    viewData() {
      if (this.curFeatureAnalytics) {
        return { ...this.summaryData, apiNumber: this.apiNumber };
      }
      return { gateway: this.getawayNumber, apiNumber: this.apiNumber };
    },
    // 是否有数据统计模块的版本
    curFeatureAnalytics() {
      return this.$store.state.userFeature && this.$store.state.userFeature.ANALYTICS;
    },
    siteDisplayName() {
      return this.analysisConfig ? this.analysisConfig.site.name : '';
    },
    isOperador() {
      return this.curAppInfo.role?.name === 'operator';
    },
  },
  watch: {
    $route() {
      if (this.curFeatureAnalytics) {
        this.refresh();
        this.getAnalysisConfig();
      } else {
        this.getAppliedPermissionApi();
      }
    },
    dateRange: {
      deep: true,
      handler() {
        if (this.curFeatureAnalytics) {
          this.refresh();
        }
      },
    },
  },
  created() {
    this.initDate();
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      try {
        if (this.curFeatureAnalytics) {
          await this.getAnalysisConfig();
        }
        await Promise.all([this.getModuleOperations(), this.getAppliedPermissionApi()]);
      } catch (error) {
        console.error(error);
      } finally {
        this.loading = false;
      }
    },
    initDate() {
      moment.locale(this.localLanguage);
      const end = new Date();
      const start = new Date();

      this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
      this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
      this.curTime = this.shortcuts[0];
    },
    // 获取最新动态
    getModuleOperations() {
      this.$http
        .get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/audit/records/?limit=6`)
        .then((response) => {
          this.operationsList = [];
          for (const item of response.results) {
            item.at_friendly = moment(item.at).startOf('minute').fromNow();
            this.operationsList.push(item);
          }
        });
    },
    /**
     * 图表初始化
     * @param  {Object} chartData 数据
     * @param  {String} type 类型
     * @param  {Object} ref 图表对象
     */
    renderChart() {
      const series = [];
      const xAxisData = [];
      const pv = [];
      const uv = [];
      const chartData = this.chartDataCache;

      chartData.forEach((item) => {
        xAxisData.push(moment(item.time).format(this.dateFormat));
        uv.push(item.uv);
        pv.push(item.pv);
      });

      if (this.chartFilterType.uv) {
        series.push({
          name: 'uv',
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
          data: uv,
        });
      }

      if (this.chartFilterType.pv) {
        series.push({
          name: 'pv',
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
          data: pv,
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

    // 获取网站访问量(外链应用无需指定环境)
    async getChartData() {
      try {
        const { appCode } = this;
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

        this.defaultRange = this.curTime.id === '1d' ? '1h' : '1d';

        const params = {
          start_time: start,
          end_time: getEndDate(),
          interval: this.defaultRange,
        };

        const res = await this.$store.dispatch('analysis/getChartData', {
          appCode,
          params,
          siteName: this.siteName,
          engineEnabled: false,
        });
        this.chartDataCache = res.result.results;
        this.renderChart();
      } catch (e) {
        const chartRef = this.$refs.chart;
        chartRef && chartRef.hideLoading();
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      }
    },

    // 获取pv/uv
    async getPvUv() {
      try {
        const { appCode } = this;

        const params = {
          start_time: this.dateRange.startTime,
          end_time: this.dateRange.endTime,
          interval: this.defaultRange,
        };
        const res = await this.$store.dispatch('analysis/getPvUv', {
          appCode,
          params,
          siteName: this.siteName,
          engineEnabled: false,
        });
        this.summaryData = res.result.results;
      } catch (e) {
        if (e.detail && e.detail !== this.$t('未找到。')) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail,
          });
        }
      }
    },

    handleDateChange(date, id) {
      this.dateRange = {
        startTime: date[0],
        endTime: date[1],
      };
      this.curTime = this.shortcuts.find((t) => t.id === id) || {};
    },

    /**
     * 显示实例指标数据
     */
    showInstanceChart(instance, processes) {
      const chartRef = this.$refs.chart;

      if (chartRef) {
        chartRef.mergeOptions({
          xAxis: [{ data: [] }],
          series: [],
        });

        // loading
        chartRef.showLoading({
          text: this.$t('正在加载'),
          color: '#30d878',
          textColor: '#fff',
          maskColor: 'rgba(255, 255, 255, 0.8)',
        });
      }

      this.getChartData();
    },

    refresh() {
      this.clearData();

      this.$nextTick(() => {
        const promises = [];
        promises.push(this.getPvUv());
        promises.push(this.showInstanceChart());

        Promise.all(promises).finally(() => {
          this.loading = false;
        });
      });
    },

    clearData() {
      this.summaryData = {
        pv: 0,
        uv: 0,
      };

      this.clearChart();
    },

    /**
     * 清空图表数据
     */
    clearChart() {
      const chartRef = this.$refs.chart;

      if (chartRef) {
        chartRef.mergeOptions({
          xAxis: [{ data: [] }],
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
      }
    },

    // 获取网关API
    async getAppliedPermissionApi() {
      // 无数据统计模块的版本
      if (!this.curFeatureAnalytics) {
        this.clearHistogramData();
        this.openHistogramLoading();
      }
      // 外链应用&当前角色为运营者无需请求
      if (this.isOperador) {
        return;
      }
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDispatchMethod}`, { appCode: this.appCode });
        this.gatewayList = res.data;
        this.apiNumber = this.gatewayList.length;
        if (!this.curFeatureAnalytics) {
          this.renderHistogram();
        }
      } catch (e) {
        const chartRef = this.$refs.notModuleChart;
        chartRef && chartRef.hideLoading();
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 开启柱状图loading
    openHistogramLoading() {
      this.$nextTick(() => {
        const chartRef = this.$refs.notModuleChart;
        if (chartRef) {
          chartRef.showLoading({
            text: this.$t('正在加载'),
            color: '#30d878',
            textColor: '#fff',
            maskColor: 'rgba(255, 255, 255, 0.8)',
          });
        }
      });
    },

    formatHistogramData() {
      const gatewayData = {};
      this.gatewayList.forEach((item) => {
        if (gatewayData[item.api_name]) {
          gatewayData[item.api_name]++;
        } else {
          gatewayData[item.api_name] = 1;
        }
      });
      this.getawayNumber = Object.keys(gatewayData).length || 0;
      const labels = [];
      const data = [];
      for (const key in gatewayData) {
        labels.push(key);
        data.push(gatewayData[key]);
      }
      return { labels, data };
    },

    // 设置柱状图
    renderHistogram() {
      const chartData = this.formatHistogramData();
      setTimeout(() => {
        this.loading = false;
        // 是否无数据
        this.gatewayLegth = this.gatewayList.length;
        this.notEnginelessOption.series[0].data = chartData.data;
        this.notEnginelessOption.xAxis.data = chartData.labels;
        const chartRef = this.$refs.notModuleChart;
        chartRef && chartRef.resize();
        chartRef && chartRef.hideLoading();
      }, 1000);
    },

    // 清空图标数据
    clearHistogramData() {
      this.notEnginelessOption.series[0].data = [];
      this.notEnginelessOption.xAxis.data = [];
    },

    async getAnalysisConfig() {
      try {
        const { appCode } = this;

        const res = await this.$store.dispatch('analysis/getAnalysisConfig', {
          appCode,
          siteName: this.siteName,
          engineEnabled: this.engineEnabled,
        });
        this.analysisConfig = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style scoped lang="scss">
.chart-wrapper,
.not-stats-module {
  background: #ffffff;
  border: 1px solid #dcdee5;
  border-radius: 2px;
  padding: 16px 16px 42px;

  .desc {
    font-size: 14px;
    font-weight: bold;
    color: #313238;
  }
  .info-button {
    font-size: 12px;
    font-weight: normal;
  }
}

.middle h3 span.text {
  font-size: 12px;
  color: #999;
  padding: 0 5px;
  font-weight: normal;
}

.overview-middle {
  // max-width: 1180px;
  display: flex;
  .summary-wrapper,
  .coding {
    flex: 1;
  }

  .header-warp {
    display: flex;
    .paasng-down-shape {
      float: left !important;
      line-height: 45px !important;
      color: #63656e !important;
    }
    .header-title {
      font-weight: 700;
      font-size: 14px;
      color: #313238;
    }
    .header-env {
      font-size: 12px;
      color: #979ba5;
    }
  }

  .header-info {
    display: flex;
  }

  .header-info:nth-of-type(2) {
    margin-left: 40px;
  }
  .header-info:nth-of-type(3) {
    margin-left: 140px;
  }
  .content-warp {
    display: flex;
    align-items: center;
    .content-info {
      padding: 12px 0px;
      flex: 1;
      .info-env {
        display: flex;
        align-items: center;
        .env-name {
          color: #313238;
        }
        .env-status {
          font-size: 12px;
          color: #979ba5;
        }
      }
    }
    .content-info:nth-of-type(1) {
      padding-right: 10px;
      border-right: solid 1px #f5f7fa;
    }
    .content-info:nth-of-type(2) {
      padding-left: 10px;
    }
    .empty-warp {
      text-align: center;
      height: 220px;
      .empty-img {
        margin-top: 20px;
      }
      .empty-tips {
        font-size: 12px;
      }
    }
  }
}

.paasng-cog,
.paasng-down-shape,
.paasng-up-shape {
  float: right;
  line-height: 22px;
  cursor: pointer;
  position: relative;
  color: #a4a6ae;
  margin: 0 3px;
  font-size: 12px;
}

.checkout-code {
  position: relative;
}

.code-checkout {
  width: 430px;
}

.code-checkout h2 {
  background: #fafafa;
  line-height: 40px;
  padding: 0 20px;
  height: 40px;
  overflow: hidden;
  color: #52525d;
  font-size: 14px;
  border-bottom: solid 1px #e5e5e5;
}

.paasng-icon.paasng-download:hover,
.paasng-icon.paasng-clipboard:hover {
  color: #3a84ff;
}

.paasng-angle-up,
.paasng-angle-down {
  padding-left: 6px;
  transition: all 0.5s;
}

.svn-input-container {
  width: 100%;
  display: table;
  box-sizing: border-box;

  input.svn-input {
    display: table-cell;
    float: left;
    width: 100%;
    height: 30px;
    color: #7b7d8a;
    font-size: 13px;
    box-sizing: border-box;
  }

  div.svn-input-button-group {
    display: table-cell;
    width: 62px;
    white-space: nowrap;
    box-sizing: border-box;
    position: relative;

    a {
      display: inline-block;
      float: left;
    }
  }
}

.btn-source-more {
  float: right;
  margin-top: 12px;
}

a.btn-deploy-panel-action {
  padding-left: 24px;
  padding-right: 24px;
  float: left;
  margin: 16px 10px 16px 0;
}

div.none-summary-controls a {
  width: 216px;
  box-sizing: border-box;
  margin: 36px 8px 0;
}

a.btn-deploy-panel-action {
  padding-left: 24px;
  padding-right: 24px;
  float: left;
  margin: 16px 10px 16px 0;
}

.dateSelector {
  input {
    color: #666;
  }
}

.visited-charts {
  display: none;
  width: 638px;
  height: 309px;
  margin-bottom: 40px;
  margin-top: 36px;
  position: relative;
  padding-top: 48px;
}

.visited-charts.active {
  display: block;
}

.resource-charts {
  display: flex;
  position: relative;
  padding-bottom: 20px;

  .title {
    font-size: 12px;
    font-weight: normal;
    margin-bottom: 5px;
  }
}

.ps-btn-checkout-code {
  width: 100%;
  padding-left: 0;
  padding-right: 0;
}

.checkout_center {
  display: table;
  margin: 0 auto;
}

.summary-content {
  padding-top: 20px;
  flex: 1;
  .overview-warp {
    display: flex;
    padding: 25px 16px;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    font-size: 12px;
    .over-fs {
      font-weight: 700;
      font-size: 24px;
      color: #313238;
    }
    .desc-text {
      padding-top: 13px;
    }
    .info {
      padding-right: 90px;
      border-right: 1px solid #f5f7fa;
      .type-desc {
        line-height: 20px;
      }
    }
    .process {
      padding-right: 48px;
      border-right: 1px solid #f5f7fa;
    }
    .img-warp {
      width: 48px;
      height: 48px;
      background: #f0f5ff;
      border-radius: 4px;
      text-align: center;
      img {
        margin-top: 8px;
        width: 32px;
        height: 32px;
      }
    }
  }
}

.coding {
  text-align: center;
  line-height: 36px;
  color: #666;
  padding: 58px 0;
  flex: 1;
}

.coding h2 {
  font-size: 22px;
  color: #333;
  line-height: 46px;
}

.middle-list li {
  width: 100%;
  line-height: 32px;
  color: #666;
  overflow: hidden;
  border-bottom: solid 1px #e6e9ea;
  padding-bottom: 24px;
}

.middle-list li.lilast {
  border-bottom: none;
}

.middle-list li p {
  padding-left: 25px;
  position: relative;
}

.middle-list dl {
  overflow: hidden;
  margin-left: -25px;
  position: relative;
}

.middle-list dd {
  width: 320px;
  float: left;
  padding-left: 25px;
  line-height: 32px;
}

.middle-list dt {
  line-height: 32px;
}

.middle-list dl:after {
  content: '';
  position: absolute;
  left: 50%;
  margin-left: -26px;
  top: 10px;
  width: 1px;
  height: 100px;
  background: #e9edee;
}

.middle-list .green {
  color: #5bd18b;
  padding: 0 6px;
}

.middle-list .danger {
  color: #ff7979;
  padding: 0 6px;
}

.http-list-fleft {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  width: 400px;
}

.http-list-fright {
  width: 234px;
  text-align: right;
}

.middle-http-list li {
  overflow: hidden;
  height: 42px;
  line-height: 42px;
  background: #fff;
  color: #666;
  font-size: 12px;
  padding: 0 10px;
}

.middle-http-list li:nth-child(2n-1) {
  background: #fafafa;
}

.fright-middle {
  padding: 0 0 24px 0;
  line-height: 30px;
  color: #666;
  border-bottom: solid 1px #e6e9ea;
}

.fright-middle h3 {
  padding-bottom: 8px;
}

.svn-a {
  line-height: 20px;
  padding: 10px 0;
}

.overview-sub-fright {
  width: 280px;
  min-height: 741px;
  padding: 0px;
  margin-left: 24px;
  margin-top: 20px;
  // border-left: solid 1px #e6e9ea;
}

.fright-last {
  border-bottom: none;
  padding-top: 0;
  padding: 0 20px 20px 20px;
}

.visited-span {
  position: absolute;
  right: 0;
  top: 8px;
  border: solid 1px #e9edee;
  border-right: none;
  border-radius: 2px;
  overflow: hidden;
  line-height: 33px;
}

.visited-span a,
.visited-span span {
  line-height: 33px;
  padding: 0 18px;
  color: #333;
  border-right: solid 1px #e9edee;
  float: left;
  font-weight: normal;
}
</style>
