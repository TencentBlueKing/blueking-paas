<template>
  <div class="plugin-overview flex-row flex-column">
    <paas-plugin-title
      :is-plugin-doc="true"
      :doc-url="curSchemas.plugin_type?.docs"
    >
      <div class="top-box">
        <span class="title">{{ $t('概览') }}</span>
        <bk-select
          v-if="isBkSaas"
          :clearable="false"
          :disabled="false"
          :loading="isDashboardLoading"
          v-model="curDashboard"
          style="width: 240px"
          ext-cls="dashboard-select-cls"
          ext-popover-cls="dashboard-select-popover"
          @change="handleChange"
        >
          <bk-option
            v-for="option in dashboardList"
            :key="option.name"
            :id="option.name"
            :name="option.display_name"
          ></bk-option>
          <div
            slot="extension"
            class="select-extension-cls"
            @click="redirectPage(dashboardLink)"
          >
            <i class="paasng-icon paasng-app-store"></i>
            {{ $t('查看更多仪表盘') }}
          </div>
        </bk-select>
      </div>
    </paas-plugin-title>
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="summary-plugin-loading"
      :offset-top="20"
      class="app-container overview-middle"
    >
      <div class="plugin-overview-main flex-row flex-column">
        <!-- bk-saas 展示 alert -->
        <bk-alert
          v-if="isBkSaas"
          type="info"
          class="alert-cls"
          :show-icon="false"
        >
          <div slot="title">
            {{
              $t(
                '平台内置了开发框架仪表盘，应用需开启 Metric 配置并在代码中上报 Metric 数据后，才可在仪表盘中查看相关数据'
              )
            }}
            <bk-button
              ext-cls="guidelines-cls"
              text
              size="small"
              @click="redirectPage(`${GLOBAL.DOC.MONITORING_METRICS_GUIDE}#13-蓝鲸应用插件标准运维插件`)"
            >
              {{ $t('Metric 上报指引') }}
              <i class="paasng-icon paasng-jump-link"></i>
            </bk-button>
          </div>
        </bk-alert>
        <div class="content">
          <div :class="['visual-display', 'card-style', { exception: isDashboardProvided }]">
            <!-- 暂不支持仪表盘 -->
            <FunctionalDependency
              v-if="isDashboardProvided"
              class="functional-dependency"
              mode="page"
              :title="$t('暂无仪表盘功能')"
              :functional-desc="
                $t(
                  '仪表盘可以提供插件运行指标，如执行次数、执行成功率和失败率等，帮助您了解插件的运行状态。GO 语言的蓝鲸应用插件暂未提供内置仪表盘功能，您可以参考相关指引自行实现该功能。'
                )
              "
              @gotoMore="redirectPage(GLOBAL.DOC.MONITORING_METRICS_GUIDE)"
            />
            <section
              v-else-if="iframeUrl"
              :class="['iframe-container', pdId]"
            >
              <!-- 嵌入 iframe -->
              <iframe
                id="iframe-embed"
                :src="iframeUrl"
                scrolling="no"
                frameborder="0"
              />
            </section>
            <section
              class="exception-box"
              v-else-if="isBkSaas"
            >
              <bk-exception
                class="exception-wrap-item dashboards-exception-part"
                type="empty"
                scene="part"
              >
                <p class="title">{{ $t('暂无仪表盘') }}</p>
                <p class="tips">{{ $t('插件发布成功后，才会内置仪表盘') }}</p>
                <bk-button
                  :theme="'primary'"
                  @click="toPublish"
                >
                  {{ $t('去发布') }}
                </bk-button>
              </bk-exception>
            </section>
            <!-- 默认图表 -->
            <template v-else>
              <div class="chart-info">
                <span class="title">{{ $t('代码提交统计') }}</span>
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
              <div class="chart-box">
                <div class="chart-action">
                  <ul class="dimension fl">
                    <li
                      :class="{ active: chartFilterType.pv }"
                      @click="handleChartFilte('pv')"
                    >
                      <span class="dot warning" />
                      {{ $t('提交数') }}
                    </li>
                    <li
                      :class="{ active: chartFilterType.uv }"
                      @click="handleChartFilte('uv')"
                    >
                      <span class="dot primary" />
                      {{ $t('贡献者') }}
                    </li>
                  </ul>
                </div>
                <chart
                  :key="renderChartIndex"
                  ref="chart"
                  :options="chartOption"
                  auto-resize
                  style="width: 100%; height: 440px; background: #1e1e21"
                />
              </div>
            </template>
          </div>

          <div class="information-container card-style">
            <!-- 基本信息 -->
            <base-info :data="curPluginInfo" />
            <!-- 代码质量 -->
            <code-quality :view-info="viewInfo" />
          </div>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import chartOption from '@/json/plugin-overview-options';
import { formatDate } from '@/common/tools';
import moment from 'moment';
import CodeQuality from './code-quality.vue';
import BaseInfo from './base-info.vue';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
export default {
  components: {
    paasPluginTitle,
    chart: ECharts,
    CodeQuality,
    BaseInfo,
    FunctionalDependency,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isLoading: true,
      chartOption: chartOption.stat,
      renderChartIndex: 0,
      chartDataCache: [],
      chartFilterType: {
        pv: true,
        uv: true,
      },
      initDateTimeRange: [],
      curSchemas: {
        plugin_type: {},
      },
      dateRange: {
        startTime: '',
        endTime: '',
      },
      dateOptions: {
        // 大于今天的都不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      viewInfo: {},
      isDashboardLoading: false,
      curDashboard: '',
      dashboardList: [],
      displayDashboardData: {},
      dashboardLink: '',
      shortcuts: [
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
        {
          text: this.$t('最近半年'),
          value() {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 180);
            return [start, end];
          },
        },
      ],
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    isBkSaas() {
      return this.pdId === 'bk-saas';
    },
    iframeUrl() {
      if (this.isBkSaas) {
        return this.displayDashboardData?.dashboard_url;
      }
      return this.curPluginInfo.overview_page?.bottom_url;
    },
    // 暂未提供仪表盘
    isDashboardProvided() {
      const unsupportedLanguage = ['go'];
      const curLanguage = this.curPluginInfo.language?.toLocaleLowerCase();
      return this.isBkSaas && unsupportedLanguage.includes(curLanguage);
    },
  },
  watch: {
    dateRange: {
      deep: true,
      handler() {
        this.refresh();
      },
    },
    $route() {
      this.refresh();
    },
  },
  created() {
    this.init();
  },
  mounted() {
    this.initTime();
    this.getChartData();
  },
  methods: {
    init() {
      // 蓝鲸应用插件
      if (this.isBkSaas) {
        this.getBuiltinDashboards();
        this.getAppDashboardInfo();
      }
      moment.locale(this.localLanguage);
      this.getStoreOverview();
      this.fetchPluginTypeList();
    },

    initTime() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
      this.initDateTimeRange = [start, end];

      this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
      this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
    },

    // 获取仪表盘数据
    async getBuiltinDashboards() {
      this.isDashboardLoading = true;
      try {
        const res = await this.$store.dispatch('getBuiltinDashboards', {
          appCode: this.pluginId,
        });
        this.dashboardList = res ?? [];
        if (this.dashboardList.length) {
          this.displayDashboardData = this.dashboardList[0];
          this.curDashboard = this.displayDashboardData.name;
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isDashboardLoading = false;
      }
    },

    // 获取仪表盘链接
    async getAppDashboardInfo() {
      try {
        const res = await this.$store.dispatch('baseInfo/getAppDashboardInfo', {
          appCode: this.pluginId,
        });
        this.dashboardLink = res.dashboard_url || '';
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 获取插件仓库概览信息
    async getStoreOverview() {
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
      };
      try {
        const res = await this.$store.dispatch('plugin/getStoreOverview', params);
        if (res.codeCheckInfo) {
          for (const key in res.codeCheckInfo) {
            if (res.codeCheckInfo[key] === 0) {
              res.codeCheckInfo[key] = `${res.codeCheckInfo[key]}`;
            }
          }
        }
        if (res.qualityInfo) {
          for (const key in res.qualityInfo) {
            if (res.qualityInfo[key] === 0) {
              res.qualityInfo[key] = `${res.qualityInfo[key]}`;
            }
          }
        }
        this.viewInfo = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取插件类型数据
    async fetchPluginTypeList() {
      try {
        const typeList = await this.$store.dispatch('plugin/getPluginsTypeList');
        this.curSchemas = typeList.find((t) => t.plugin_type.id === this.curPluginInfo.pd_id);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async getChartData() {
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
        begin_time: start,
        end_time: getEndDate(),
        format: 'json',
      };
      try {
        const res = await this.$store.dispatch('plugin/getChartData', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          params,
        });
        this.chartDataCache = res;
        // 由于API不能同一天的数据，使用默认值
        if (!res.length) {
          this.chartDataCache = [
            {
              commit_count: 0,
              commit_user_count: 0,
              day: params.begin_time,
            },
          ];
        }
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
      } finally {
        this.isLoading = false;
      }
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
        xAxisData.push(moment(item.day).format('MM-DD'));
        uv.push(item.commit_user_count);
        pv.push(item.commit_count);
      });

      if (this.chartFilterType.uv) {
        series.push({
          name: this.$t('贡献者'),
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

      // 提交者
      if (this.chartFilterType.pv) {
        series.push({
          name: this.$t('提交者'),
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

    /**
     * 清空图表数据
     */
    clearChart() {
      const chartRef = this.$refs.chart;

      chartRef &&
        chartRef.mergeOptions({
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

    refresh() {
      this.clearChart();

      this.$nextTick(() => {
        this.getChartData();
      });
    },

    handleChartFilte(type) {
      this.chartFilterType[type] = !this.chartFilterType[type];
      this.renderChart();
    },

    handleDateChange(date, type) {
      this.dateRange = {
        startTime: date[0],
        endTime: date[1],
      };
    },
    // 切换仪表盘
    handleChange(name) {
      this.displayDashboardData = this.data.find((v) => v.name === name);
    },
    toPublish() {
      this.$router.push({
        name: 'pluginVersionManager',
      });
    },
    redirectPage(url) {
      window.open(url, '_blank');
    },
  },
};
</script>
<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';

.plugin-overview {
  height: 100%;
  .desc {
    font-size: 12px;
    color: #979ba5;
  }
}
.chart-info {
  margin: 24px 0 20px;
  .title {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 5px;
    color: #313238;
    line-height: 1;
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
      color: #63656e;
      margin-right: 30px;
      cursor: pointer;
      opacity: 0.4;
      line-height: 12px;

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
      border: 1px solid #3a84ff;
      background: #a3c5fd;
      border-radius: 50%;
      vertical-align: middle;
      float: left;
      margin-right: 5px;

      &.warning {
        border: 1px solid #ff9c01;
        background: #ffd695;
      }
    }
  }

  .time {
    li {
      display: inline-block;
      font-size: 12px;
      color: #63656e;
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
.app-container {
  height: 100%;
  .guidelines-cls {
    height: auto;
    line-height: unset;
  }
  .alert-cls {
    margin-bottom: 16px;
  }
  .plugin-overview-main {
    min-height: 0;
    height: 100%;
    min-height: 664px;
    .content {
      display: flex;
      height: 100%;
    }
  }
  .visual-display {
    padding: 24px;
    width: 100%;
    background: #fff;
    overflow: hidden;
    &.exception {
      display: flex;
      align-items: center;
      .functional-dependency {
        flex: 1;
      }
    }
    .exception-box {
      display: flex;
      align-items: center;
      height: 100%;
    }
  }
  .information-container {
    width: 280px;
    padding: 12px 16px;
    margin-left: 24px;
    font-size: 12px;
  }
  .chart-container {
    display: flex;
    margin-top: 150px;
    h2 {
      font-size: 18px;
      font-weight: 700;
    }
  }
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

.svn-a {
  line-height: 20px;
  padding: 10px 0;
}

.overview-sub-fright {
  width: 260px;
  min-height: 741px;
  padding: 0 0 0 20px;
  border-left: solid 1px #e6e9ea;
}

.fright-last {
  border-bottom: none;
  padding-top: 0;
  height: 100%;
}
.summary_text {
  display: inline-block;
  margin-left: 10px;
}
.bk-tooltip .bk-tooltip-ref p {
  width: 193px !important;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.iframe-margin {
  height: 20px;
  background: #ffff;
  position: relative;
  z-index: 99;
}

.iframe-container {
  /* resize and min-height are optional, allows user to resize viewable area */
  -webkit-resize: vertical;
  -moz-resize: vertical;
  resize: vertical;
  height: 100%;
  &.bk-code-cc-new {
    transform: translateY(2px);
    margin-top: -70px;
  }
  iframe#iframe-embed {
    width: 100%;
    height: 100%;
    min-height: 795px;

    /* resize seems to inherit in at least Firefox */
    -webkit-resize: none;
    -moz-resize: none;
    resize: none;
  }
}
.dashboards-exception-part {
  /deep/ .part-img img {
    height: 200px;
  }
  .title {
    font-size: 24px;
    color: #4d4f56;
    line-height: 32px;
    margin-bottom: 16px;
  }
  .tips {
    font-size: 14px;
    color: #979ba5;
    line-height: 22px;
    margin-bottom: 24px;
  }
}
.top-box {
  display: flex;
  align-items: center;
  font-size: 16px;
  .title {
    margin-right: 24px;
  }
  .dashboard-select-cls:not(.is-focus) {
    background: #f0f1f5;
    border: none;
  }
}
.dashboard-select-popover {
  .select-extension-cls {
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    color: #4d4f56;
    i {
      font-size: 12px;
      margin-right: 5px;
      transform: translateY(0px);
    }
  }
}
</style>
