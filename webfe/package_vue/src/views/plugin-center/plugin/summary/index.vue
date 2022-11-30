<template>
  <div class="visible-range">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="summary-plugin-loading"
      :offset-top="20"
      class="app-container overview-middle"
    >
      <div class="app-container middle">
        <paas-plugin-title />
        <div class="overview-main">
          <div class="visual-display">
            <div class="nav-list">
              <div
                class="nav-list-item"
              >
                <span class="item-icon">
                  <i class="paasng-icon paasng-version" />
                </span>
                <div class="item-info">
                  <h3>--</h3>
                  <span class="text">{{ $t('代码质量') }}</span>
                  <i
                    v-bk-tooltips="'由工蜂 Stream 提供数据'"
                    style="color: #C4C6CC;margin-top:1px;"
                    class="paasng-icon paasng-info-line"
                  />
                </div>
              </div>
              <div
                class="nav-list-item"
              >
                <span class="item-icon">
                  <i class="paasng-icon paasng-alert2" />
                </span>
                <div class="item-info">
                  <h3>--</h3>
                  <span class="text">{{ $t('已解决缺陷数') }}</span>
                </div>
              </div>
              <div
                class="nav-list-item"
              >
                <span class="item-icon">
                  <i class="paasng-icon paasng-alert" />
                </span>
                <div class="item-info">
                  <h3>--</h3>
                  <span class="text">{{ $t('质量红线拦截率') }}</span>
                </div>
              </div>
            </div>
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
            <!-- 日期 -->
            </div>
            <div class="chart-box">
              <div class="chart-action">
                <ul class="dimension fl">
                  <li
                    :class="{ 'active': chartFilterType.pv }"
                    @click="handleChartFilte('pv')"
                  >
                    <span class="dot warning" /> {{ $t('提交数') }}
                  </li>
                  <li
                    :class="{ 'active': chartFilterType.uv }"
                    @click="handleChartFilte('uv')"
                  >
                    <span class="dot primary" /> {{ $t('贡献者') }}
                  </li>
                </ul>
              </div>
              <chart
                :key="renderChartIndex"
                ref="chart"
                :options="chartOption"
                auto-resize
                style="width: 100%; height: 440px; background: #1e1e21;"
              />
            </div>
          </div>

          <div class="information-container">
            <div>
              <h3>{{ $t('基本信息') }}</h3>
              <div class="base-info">
                <p>
                  {{ $t('插件类型：') }} <span>{{ curPluginData.pd_name }}</span>
                </p>
                <p>
                  {{ $t('开发语言：') }} <span>{{ curPluginData.language }}</span>
                </p>
                <p class="repos">
                  <span>{{ $t('代码仓库：') }}</span>
                  <span>{{ curPluginData.repository }}</span>
                  <span
                    v-copy="curPluginData.repository"
                    class="copy-text"
                  >
                    {{ $t('复制') }}
                  </span>
                </p>
              </div>
            </div>

            <div class="dynamic-wrapper">
              <div
                class="fright-middle fright-last"
                data-test-id="summary_content_noSource"
              >
                <h3> {{ $t('最新动态') }} </h3>
                <ul class="dynamic-list">
                  <template v-if="operationsList.length">
                    <li
                      v-for="(item, itemIndex) in operationsList"
                      :key="itemIndex"
                    >
                      <p class="dynamic-time">
                        <span
                          v-bk-tooltips="item.updated"
                          class="tooltip-time"
                        >{{ item.created_format }}</span>
                      </p>
                      <p class="dynamic-content">
                        {{ $t('由') }} {{ item.display_text }}
                      <!-- <span class="gruy">{{ item.display_text }}</span> -->
                      </p>
                    </li>
                    <li />
                  </template>
                  <template v-else>
                    <div class="ps-no-result">
                      <div class="text">
                        <p><i class="paasng-icon paasng-empty" /></p>
                        <p> {{ $t('暂无数据') }} </p>
                      </div>
                    </div>
                  </template>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import 'echarts/lib/chart/line';
    import 'echarts/lib/component/tooltip';
    import chartOption from '@/json/plugin-overview-options';
    import { formatDate } from '@/common/tools';
    import moment from 'moment';
    export default {
        components: {
            paasPluginTitle,
            'chart': ECharts
        },
        data () {
            return {
                isLoading: true,
                operationsList: [],
                chartOption: chartOption.stat,
                renderChartIndex: 0,
                chartDataCache: [],
                chartFilterType: {
                    pv: true,
                    uv: true
                },
                initDateTimeRange: [],
                dateRange: {
                    startTime: '',
                    endTime: ''
                },
                dateOptions: {
                    // 大于今天的都不能选
                    disabledDate (date) {
                        return date && date.valueOf() > Date.now() - 86400;
                    }
                },
                shortcuts: [
                    {
                        text: this.$t('今天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            return [start, end];
                        }
                    },
                    {
                        text: this.$t('最近7天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
                            return [start, end];
                        }
                    },
                    {
                        text: this.$t('最近30天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);
                            return [start, end];
                        }
                    }
                ]
            };
        },
        computed: {
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            },
            curPluginData () {
                return this.$store.state.curPluginInfo;
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            }
        },
        watch: {
            dateRange: {
                deep: true,
                handler () {
                    this.refresh();
                }
            },
            '$route' () {
                this.refresh();
            }
        },
        created () {
            this.init();
        },
        mounted () {
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
            this.initDateTimeRange = [start, end];

            this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
            this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
            this.getChartData();
        },
        methods: {
            init () {
                moment.locale(this.localLanguage);
                this.getPluginOperations();
            },

            // 获取动态
            async getPluginOperations () {
                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId
                };
                try {
                    const res = await this.$store.dispatch('plugin/getPluginOperations', params);
                    this.operationsList = [];
                    for (const item of res.results) {
                        item['created_format'] = moment(item.created).startOf('minute').fromNow();
                        this.operationsList.push(item);
                    }
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            async getChartData () {
                const start = this.dateRange.startTime + ' 00:00';
                const end = this.dateRange.endTime + ' 23:59';
                const getEndDate = () => {
                    const curTime = new Date(end).getTime();
                    const nowTime = new Date().getTime();
                    if (curTime > nowTime) {
                        return formatDate(new Date());
                    }
                    return formatDate(end);
                };

                const params = {
                    'begin_time': start,
                    'end_time': getEndDate(),
                    'format': 'json'
                };
                try {
                    const res = await this.$store.dispatch('plugin/getChartData', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        params
                    });
                    this.chartDataCache = res;
                    this.renderChart();
                } catch (e) {
                    const chartRef = this.$refs.chart;
                    chartRef && chartRef.hideLoading();
                    if (e.detail && e.detail !== this.$t('未找到。')) {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail
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
            renderChart () {
                const series = [];
                const xAxisData = [];
                const pv = [];
                const uv = [];
                const chartData = this.chartDataCache;

                chartData.forEach(item => {
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
                                width: 1.5
                            }
                        },
                        symbolSize: 1,
                        showSymbol: false,
                        areaStyle: {
                            normal: {
                                opacity: 0
                            }
                        },
                        data: uv
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
                                width: 1.5
                            }
                        },
                        areaStyle: {
                            normal: {
                                opacity: 0
                            }
                        },
                        data: pv
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
            clearChart () {
                const chartRef = this.$refs.chart;

                chartRef && chartRef.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: [
                        {
                            name: '',
                            type: 'line',
                            smooth: true,
                            areaStyle: {
                                normal: {
                                    opacity: 0
                                }
                            },
                            data: [0]
                        }
                    ]
                });
            },

            refresh () {
                this.clearChart();

                this.$nextTick(() => {
                    this.getChartData();
                });
            },

            handleChartFilte (type) {
                this.chartFilterType[type] = !this.chartFilterType[type];
                this.renderChart();
            },

            handleDateChange (date, type) {
                this.dateRange = {
                    startTime: date[0],
                    endTime: date[1]
                };
            }
        }
    };
</script>
<style lang="scss" scoped>
    .visible-range{
        .desc{
            font-size: 12px;
            color: #979BA5;
        }
    }
    .chart-info {
        margin: 80px 0 20px;
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
                color: #63656E;
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
                border: 1px solid #3A84FF;
                background: #A3C5FD;
                border-radius: 50%;
                vertical-align: middle;
                float: left;
                margin-right: 5px;

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
    .app-container {
        .overview-main {
            margin-top: 20px;
            display: flex;
        }
        .visual-display {
            width: 100%;
        }
        .nav-list {
            display: flex;
            height: 64px;
            background: #FFFFFF;
            border: 1px solid #EAEBF0;
            border-radius: 2px;
            .nav-list-item {
                display: flex;
                align-items: center;
                position: relative;
                flex: 1;
                &::after {
                    content: '';
                    position: absolute;
                    right: 0;
                    width: 1px;
                    height: 48px;
                    background: #EAEBF0;
                }
                &:last-child::after {
                    background: transparent;
                }
                .item-icon {
                    padding: 0 20px;
                    font-size: 32px;
                    color: #C4C6CC;
                }
                .item-info {
                    h3 {
                        font-size: 16px;
                        font-weight: 700;
                        line-height: 24px;
                        color: #313238;
                    }
                    .text {
                        font-size: 12px;
                        color: #63656E;
                        line-height: 20px;
                    }
                }
            }
        }
      .information-container {
          width: 280px;
          min-height: 741px;
          padding-left: 20px;
          margin-left: 24px;
          background: #FAFBFD;
          font-size: 12px;
          border-radius: 2px;
          color: #63656E;
          h3 {
              color: #63656E;
          }
          .base-info {
              margin-right: 15px;
              p {
                  line-height: 30px;
                  white-space: nowrap;
                  text-overflow: ellipsis;
                  overflow: hidden;
                  .copy-text {
                      position: absolute;
                      right: 20px;
                      color: #3A84FF;
                      cursor: pointer;
                  }
              }
              .repos {
                  padding-right: 30px;
              }
          }
          .copy-url {
              color: #3A84FF;
              cursor: pointer;
          }
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
    .dynamic-list {
        max-height: 600px;
        padding-right: 15px;
        overflow-y: auto;
        font-size: 12px;
        color: #63656E;
    }
    .dynamic-list::-webkit-scrollbar {
        width: 4px;
        background-color: hsla(0,0%,80%,0);
    }

    .dynamic-list::-webkit-scrollbar-thumb {
        height: 5px;
        border-radius: 2px;
        background-color: #e6e9ea;
    }

    .dynamic-list li {
        padding-bottom: 15px;
        padding-left: 20px;
        position: relative;
    }

    .dynamic-list li:before {
        position: absolute;
        content: "";
        width: 10px;
        height: 10px;
        top: 3px;
        left: 1px;
        border: solid 1px rgba(87, 163, 241, 1);
        border-radius: 50%;
    }

    .dynamic-list li:after {
        position: absolute;
        content: "";
        width: 1px;
        height: 70px;
        top: 15px;
        left: 6px;
        background: rgba(87, 163, 241, 1);
    }

    .dynamic-list li:nth-child(1):before {
        border: solid 1px rgba(87, 163, 241, 1);
    }

    .dynamic-list li:nth-child(1):after {
        background: rgba(87, 163, 241, 1);
    }

    .dynamic-list li:nth-child(2):before {
        border: solid 1px rgba(87, 163, 241, 0.9);
    }

    .dynamic-list li:nth-child(2):after {
        background: rgba(87, 163, 241, 0.9);
    }

    .dynamic-list li:nth-child(3):before {
        border: solid 1px rgba(87, 163, 241, 0.8);
    }

    .dynamic-list li:nth-child(3):after {
        background: rgba(87, 163, 241, 0.8);
    }

    .dynamic-list li:nth-child(4):before {
        border: solid 1px rgba(87, 163, 241, 0.7);
    }

    .dynamic-list li:nth-child(4):after {
        background: rgba(87, 163, 241, 0.7);
    }

    .dynamic-list li:nth-child(5):before {
        border: solid 1px rgba(87, 163, 241, 0.6);
    }

    .dynamic-list li:nth-child(5):after {
        background: rgba(87, 163, 241, 0.6);
    }

    .dynamic-list li:nth-child(6):before {
        border: solid 1px rgba(87, 163, 241, 0.5);
    }

    .dynamic-list li:nth-child(6):after {
        background: rgba(87, 163, 241, 0.5);
    }

    .dynamic-list li:nth-child(7):before {
        border: solid 1px rgba(87, 163, 241, 0.4);
    }

    .dynamic-list li:nth-child(7):after {
        background: rgba(87, 163, 241, 0.4);
    }

    .dynamic-list li:nth-child(8):before {
        border: solid 1px rgba(87, 163, 241, 0.3);
    }

    .dynamic-list li:nth-child(8):after {
        background: rgba(87, 163, 241, 0.3);
    }

    .dynamic-list li:nth-child(9):before {
        border: solid 1px rgba(87, 163, 241, 0.2);
    }

    .dynamic-list li:nth-child(9):after {
        background: rgba(87, 163, 241, 0.2);
    }

    .dynamic-list li:nth-child(10):before {
        border: solid 1px rgba(87, 163, 241, 0.2);
    }

    .dynamic-list li:nth-child(10):after {
        background: rgba(87, 163, 241, 0.2);
    }

    .dynamic-list li:last-child:before {
        border: solid 1px rgba(87, 163, 241, 0.2);
    }

    .dynamic-list li:last-child:after {
        background: rgba(87, 163, 241, 0);
    }

    .dynamic-time {
        line-height: 18px;
        font-size: 12px;
        color: #c0c9d3;
        cursor: default;
    }

    .dynamic-content {
        line-height: 24px;
        height: 48px;
        overflow: hidden;
        color: #666;
    }

    .summary-content {
        flex: 1;
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
        width: 260px;
        min-height: 741px;
        padding: 0 0 0 20px;
        border-left: solid 1px #e6e9ea;
    }

    .fright-last {
        border-bottom: none;
        padding-top: 0;
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
    .address-zh-cn {
        min-width: 46px;
    }
    .address-en {
        min-width: 66px;
    }

</style>
