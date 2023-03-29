<template lang="html">
  <div
    id="summary"
    class="right-main"
  >
    <app-top-bar
      ref="appTopBarRef"
      data-test-id="summary_bar_moduleList"
      :title="$t('应用概览')"
      :is-overview="true"
      :cur-time="curTime"
      :shortcuts="dateShortCut"
      @change-date="handleDateChange"
    />
    <paas-content-loader
      :is-loading="loading"
      placeholder="summary-loading"
      :offset-top="20"
      class="app-container"
    >
      <!-- 应用资源使用信息 -->
      <overview-top-info
        class="default-top-info"
        :app-info="topInfo"
        :is-cloud="isCloudApp"
      />
      <div class="overview-middle">
        <template v-if="!loading">
          <div
            class="summary-content"
          >
            <!-- 访问日志 -->
            <bk-collapse
              v-model="activeName"
              :accordion="true"
              class="paas-module-warp"
              @item-click="handleCollapseClick"
            >
              <bk-collapse-item
                v-for="(item, key) in overViewData"
                :key="key"
                :hide-arrow="false"
                class="paas-module-item"
                :name="key"
              >
                <div class="header-warp">
                  <div
                    v-bk-overflow-tips
                    class="module-name mr20"
                  >
                    <i
                      class="paasng-icon paasng-bold"
                      :class="activeName.includes(key) ? 'paasng-down-shape':'paasng-right-shape'"
                    />
                    <span class="header-title">{{ key }} {{ item.is_default ? $t('(主)') : '' }}</span>
                  </div>
                  <div
                    v-for="(data, k) in item.envs"
                    v-if="!activeName.includes(key)"
                    :key="k"
                    class="header-info"
                  >
                    <span class="header-env">{{ k === 'stag' ? $t('预发布环境') : $t('正式环境') }}:</span>
                    <span :class="['header-env', 'pl10', { 'not-deployed': !data.is_deployed }]">{{ data.is_deployed ? $t('已部署') : $t('未部署') }}</span>
                    <bk-button
                      v-if="data.is_deployed"
                      class="pl10"
                      theme="primary"
                      text
                      @click="handleItemClick(k, 'access', key)"
                    >
                      {{ $t('访问') }}
                    </bk-button>
                    <bk-button
                      class="pl10"
                      theme="primary"
                      text
                      @click="handleItemClick(k, 'deploy', key)"
                    >
                      {{ $t('部署') }}
                    </bk-button>
                  </div>
                </div>
                <div slot="content">
                  <div class="content-warp">
                    <div
                      v-for="(data, k) in item.envs"
                      :key="k"
                      class="content-info"
                    >
                      <div class="info-env mb10">
                        <div class="env-name">
                          {{ k === 'stag' ? $t('预发布环境') : $t('正式环境') }}
                        </div>
                        <span class="span" />
                        <div
                          v-bk-overflow-tips
                          class="env-status pl10 pr320"
                        >
                          {{ data.is_deployed ? releaseInfoText(k) : $t('未部署') }}
                        </div>
                        <bk-button
                          v-if="data.is_deployed"
                          class="pl10"
                          theme="primary"
                          text
                          @click="handleItemClick(k, 'access', key)"
                        >
                          {{ $t('访问') }}
                        </bk-button>
                        <bk-button
                          class="pl10"
                          theme="primary"
                          text
                          @click="handleItemClick(k, 'deploy', key)"
                        >
                          {{ $t('部署') }}
                        </bk-button>
                      </div>
                      <template v-if="!isCloudApp">
                        <!-- 折线图内容 部署了才展示内容-->
                        <div
                          v-if="data.is_deployed"
                          ref="chartWarp"
                          class="chart-warp"
                        >
                          <chart
                            :key="renderChartIndex"
                            :ref="k + key"
                            :options="envChartOption[k]"
                            auto-resize
                            style="width: 100%; height: 220px;"
                          />
                          <ul class="chart-legend">
                            <li
                              :class="{ 'active': chartFilterType.pv }"
                              @click="handleChartFilte('pv', k)"
                            >
                              <span class="dot warning" /> PV
                            </li>
                            <li
                              :class="{ 'active': chartFilterType.uv }"
                              @click="handleChartFilte('uv', k)"
                            >
                              <span class="dot primary" /> UV
                            </li>
                          </ul>
                        </div>
                        <!-- 空状态 -->
                        <div
                          v-else
                          class="empty-warp"
                        >
                          <table-empty empty />
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </bk-collapse-item>
            </bk-collapse>

            <!-- 资源用量 -->
            <bk-collapse
              v-if="curAppInfo.feature.RESOURCE_METRICS"
              v-model="activeResource"
              :accordion="true"
              class="paas-module-warp mt20"
            >
              <div
                v-if="isProcessDataReady && !isChartLoading"
                class="search-chart-wrap"
              >
                <!-- 进程列表 -->
                <bk-select
                  v-if="curEnvProcesses.length"
                  v-model="curProcessName"
                  style="width: 116px; font-weight: normal;"
                  class="fr collapse-select mb10 mr10"
                  :clearable="false"
                  behavior="simplicity"
                  @selected="handlerProcessSelecte('process')"
                >
                  <bk-option
                    v-for="option in curEnvProcesses"
                    :id="option.name"
                    :key="option.name"
                    :name="option.name"
                  />
                </bk-select>
                <!-- 环境列表，该环境没有模块信息，不需要显示 -->
                <bk-select
                  v-if="curProcessEnvList.length"
                  v-model="curEnvName"
                  style="width: 116px; font-weight: normal;"
                  class="fr collapse-select mb10 mr10"
                  :clearable="false"
                  behavior="simplicity"
                  @selected="handlerProcessSelecte('env')"
                >
                  <bk-option
                    v-for="option in curProcessEnvList"
                    :id="option.name"
                    :key="option.name"
                    :name="option.label"
                  />
                </bk-select>
                <bk-select
                  v-model="curModuleName"
                  style="width: 116px; font-weight: normal;"
                  class="fr collapse-select mb10 mr10"
                  :clearable="false"
                  behavior="simplicity"
                  @selected="handlerProcessSelecte('module')"
                >
                  <bk-option
                    v-for="option in curAppModuleList"
                    :id="option.name"
                    :key="option.name"
                    :name="option.name"
                  />
                </bk-select>
              </div>
              <bk-collapse-item
                :hide-arrow="true"
                class="paas-module-item"
                name="1"
              >
                <div class="header-warp justify-between">
                  <div data-test-id="summary_header_select">
                    <i
                      class="paasng-icon paasng-bold"
                      :class="activeResource.length ? 'paasng-down-shape':'paasng-right-shape'"
                    />
                    <span class="header-title">{{ $t('资源用量') }}</span>
                    <span
                      v-if="curEnvName"
                      class="text ml5"
                    >
                      <a
                        href="javascript: void(0);"
                        @click="goProcessDetail"
                      > {{ $t('查看详情') }} </a>
                    </span>
                  </div>
                </div>
                <div
                  slot="content"
                  class="middle pl10 pr10"
                >
                  <div data-test-id="summary_box_cpuCharts">
                    <!-- 使用v-show是因为需要及时获取ref并调用 -->
                    <div
                      v-show="isProcessDataReady || isChartLoading"
                      class="resource-charts active"
                    >
                      <div class="chart-box summary-chart-box">
                        <div class="type-title">
                          {{ $t('CPU使用率') }}
                        </div>
                        <strong class="title"> {{ $t('单位：核') }} </strong>
                        <chart
                          v-show="isResourceChartLine"
                          ref="cpuLine"
                          :options="cpuLine"
                          auto-resize
                          style="width: 100%; height: 235px;"
                        />
                        <div
                          v-if="!isResourceChartLine && !isChartLoading"
                          class="ps-no-result"
                        >
                          <table-empty empty />
                        </div>
                      </div>
                      <div class="chart-box summary-chart-box">
                        <div class="type-title">
                          {{ $t('内存使用量') }}
                        </div>
                        <strong class="title"> {{ $t('单位：MB') }} </strong>
                        <!-- 未部署展示无数据 -->
                        <chart
                          v-show="isResourceChartLine"
                          ref="memLine"
                          :options="memLine"
                          auto-resize
                          style="width: 100%; height: 235px;"
                        />
                        <div
                          v-if="!isResourceChartLine && !isChartLoading"
                          class="ps-no-result"
                        >
                          <table-empty empty />
                        </div>
                      </div>
                    </div>
                    <div
                      v-if="!isProcessDataReady && !isChartLoading"
                      class="ps-no-result"
                    >
                      <table-empty empty />
                    </div>
                  </div>
                </div>
              </bk-collapse-item>
            </bk-collapse>
          </div>

          <div
            class="overview-sub-fright"
            data-test-id="summary_content_detail"
          >
            <dynamic-state
              :operations-list="operationsList"
            />
          </div>
        </template>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import 'echarts/lib/chart/line';
    import 'echarts/lib/component/tooltip';
    import overviewTopInfo from './comps/overview-top-info';
    import moment from 'moment';
    import chartOption from '@/json/process-chart-option';
    import envChartOption from '@/json/analysis-chart-option';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import i18n from '@/language/i18n.js';
    import appTopBar from '@/components/paas-app-bar';
    import { formatDate } from '@/common/tools';
    import dynamicState from './comps/dynamic-state';
    import { cloneDeep } from 'lodash';

    const timeMap = {
        '1d': '24h',
        '3d': '72h',
        '7d': '168h'
    };
    const envMap = ['stag', 'prod'];
    export default {
        components: {
            overviewTopInfo,
            'chart': ECharts,
            appTopBar,
            dynamicState
        },
        mixins: [appBaseMixin],
        props: {
            appInfo: {
                type: Object
            }
        },
        data () {
            return {
                loading: true,
                trunkUrl: '',
                operationsList: [],
                interval: 3600,
                current: -1,
                // 开发语言
                appDevLang: '',
                // 已托管至
                sourceType: '',
                cpuLine: chartOption.cpu,
                memLine: chartOption.memory,
                envChartOption: {
                    'stag': cloneDeep(envChartOption.pv_uv),
                    'prod': cloneDeep(envChartOption.pv_uv)
                },
                isChartLoading: true,
                curProcessName: '',
                processes: [],
                isProcessDataReady: true,
                dateShortCut: [
                    {
                        id: '1d',
                        text: this.$t('今天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime());
                            return [start, end];
                        }
                    },
                    {
                        id: '3d',
                        text: this.$t('最近 3 天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 60 * 1000 * 60 * 24 * 3);
                            return [start, end];
                        }
                    },
                    {
                        id: '7d',
                        text: this.$t('最近 7 天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 60 * 1000 * 60 * 24 * 7);
                            return [start, end];
                        }
                    }
                ],
                activeName: [],
                overViewData: {},
                renderChartIndex: 0,
                dateRange: {
                    startTime: '',
                    endTime: ''
                },
                defaultRange: '1d',
                siteName: 'default',
                chartFilterType: {
                    pv: true,
                    uv: true
                },
                engineEnabled: true,
                backendType: 'ingress',
                envData: [{name: 'prod', label: i18n.t('生产环境')}, {name: 'stag', label: i18n.t('预发布环境')}],
                activeResource: '1',
                curModuleName: '',
                curEnvName: 'prod',
                topInfo: {
                    type: i18n.t('普通应用'),
                    description: i18n.t('平台为该类应用提供应用引擎、增强服务、云API 权限、应用市场等功能。'),
                    data: {}
                },
                curTime: {},
                resourceUsageRange: '24h',
                activeModuleId: '',
                changIndex: 0,
                chartDataCache: {},
                isResourceChartLine: true,
                curProcessEnvList: []
            };
        },
        computed: {
            dateFormat () {
                let isInDay = false; // 是否在一天内
                if (this.dateRange.startTime && this.dateRange.endTime) {
                    const start = this.dateRange.startTime;
                    const end = this.dateRange.endTime;

                    const endSeconds = moment(end).valueOf();
                    const oneEndSeconds = moment(start).add(1, 'days').valueOf(); // 一天后
                    if (oneEndSeconds > endSeconds) {
                        isInDay = true;
                    }
                }

                if (this.defaultRange === '1d') {
                    return 'MM-DD';
                } else if (this.defaultRange === '1h') {
                    if (isInDay) {
                        return 'HH:mm';
                    } else {
                        return 'MM-DD HH:mm';
                    }
                } else if (this.defaultRange === '5m') {
                    if (isInDay) {
                        return 'HH:mm';
                    } else {
                        return 'MM-DD HH:mm';
                    }
                }
                return 'MM-DD';
            },
            // 模块列表
            curAppModuleList () {
                const moduleList = [];
                for (const moduleName in this.overViewData) {
                    // 对应模块下的进程
                    const curProcesses = this.getProcessList(moduleName);
                    if (curProcesses.length) {
                        moduleList.push({ name: moduleName });
                    }
                };
                return moduleList;
            },
            curEnvProcesses () {
                let processes = [];
                for (const moduleName in this.overViewData) {
                    // 当前环境下的进程信息
                    if (this.curModuleName === moduleName) {
                        processes = this.overViewData[moduleName]['envs'][this.curEnvName]['processes'];
                    }
                };
                if (processes.length) {
                    processes = processes.map(process => {
                        const key = Object.keys(process)[0];
                        return process[key];
                    });
                }
                return processes;
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            },
            isCloudApp () {
                return this.curAppInfo.application.type === 'cloud_native';
            }
        },
        watch: {
            '$route' () {
                this.init();
                this.initTopText();
            },
            dateRange: {
                deep: true,
                handler () {
                    // 重新获取数据
                    if (this.changIndex !== 0) {
                        this.$nextTick(() => {
                            this.showInstanceChart(this.activeModuleId);
                            this.showProcessResource();
                            this.getAlarmData();
                        });
                    }
                }
            },
            curEnvProcesses: {
                handler () {
                    if (this.curEnvProcesses.length) {
                        this.curProcessName = this.curEnvProcesses[0].name;
                    } else {
                        this.curProcessName = '';
                    }
                },
                deep: true
            },
            curModuleName (moduleName) {
                // 当前模块下的环境列表
                this.curProcessEnvList = this.getProcessList();
                const curEnvData = this.curProcessEnvList.filter(env => env.name === this.curEnvName);
                // 若当前模块没有对应环境的进程，默认选中第一个
                if (!curEnvData.length) {
                    this.curEnvName = this.curProcessEnvList.length !== 0 ? this.curProcessEnvList[0].name : 'stag';
                }
            }
        },
        created () {
            moment.locale(this.localLanguage);
        },
        mounted () {
            this.init();
            this.initDate();
            this.initTopText();
        },
        methods: {
            async init () {
                this.loading = true;
                this.isChartLoading = true;
                this.isProcessDataReady = false;

                this.curProcessName = '';
                this.appDevLang = this.curAppModule.language;
                await this.getOverViewData();
                // 获取动态
                this.getModuleOperations();
                if (this.curAppModule && this.curAppModule.repo) {
                    this.trunkUrl = this.curAppModule.repo.trunk_url || '';
                    this.sourceType = this.curAppModule.repo.source_type || '';
                }
                if (!this.isCloudApp) {
                    this.getAlarmData();
                }
            },
            initDate () {
                const end = new Date();
                const start = new Date();
                this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
                this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
                this.curTime = this.dateShortCut[0];
            },
            initTopText () {
                if (this.isCloudApp) {
                    this.topInfo.type = this.$t('云原生应用');
                    this.topInfo.description = this.$t('基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力。');
                } else {
                    this.topInfo.type = this.$t('普通应用');
                    this.topInfo.description = this.$t('平台为该类应用提供应用引擎、增强服务、云API 权限、应用市场等功能。');
                }
            },
            // 最新动态
            getModuleOperations () {
                this.$http.get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/operations/?limit=6`).then((response) => {
                    this.operationsList = [];
                    for (const item of response.results) {
                        item['at_friendly'] = moment(item.at).startOf('minute').fromNow();
                        this.operationsList.push(item);
                    }
                });
            },
            getPrcessData () {
                this.$nextTick(() => {
                    this.handleCollapseClick(this.activeName);
                    // 显示图标loading
                    this.showProcessLoading();
                    this.isResourceChartLine = true;
                    if (this.curEnvProcesses.length) {
                        this.showProcessResource();
                    } else {
                        setTimeout(() => {
                            this.isChartLoading = false;
                            this.isProcessDataReady = false;
                            this.hideProcessLoading();
                        }, 1000);
                    }
                });
            },

            /**
             * 切换process时回调
             */
            handlerProcessSelecte (type) {
                this.showProcessResource();
            },

            /**
             * 显示图表加载进度
             */
            showProcessLoading () {
                const chart = this.$refs.cpuLine;
                const memChart = this.$refs.memLine;

                chart && chart.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: []
                });
                memChart && memChart.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: []
                });
                if (chart) {
                    chart.showLoading({
                        text: this.$t('正在加载'),
                        color: '#30d878',
                        textColor: '#fff',
                        maskColor: '#FCFCFD'
                    });
                    // 防止初始渲染图表宽度问题
                    setTimeout(() => {
                        chart.resize();
                    }, 50);
                }
                if (memChart) {
                    memChart.showLoading({
                        text: this.$t('正在加载'),
                        color: '#30d878',
                        textColor: '#fff',
                        maskColor: '#FCFCFD'
                    });
                    setTimeout(() => {
                        memChart.resize();
                    }, 50);
                }
            },

            /**
             * 隐藏图表加载进度
             */
            hideProcessLoading () {
                const cpuRef = this.$refs.cpuLine;
                const memoryRef = this.$refs.memLine;
                cpuRef && cpuRef.hideLoading();
                memoryRef && memoryRef.hideLoading();
            },

            /**
             * 显示进程指标数据
             */
            showProcessResource () {
                const process = this.curEnvProcesses.find(item => {
                    return item.name === this.curProcessName;
                });

                if (process) {
                    this.showProcessLoading();
                    this.getProcessMetric({
                        cpuChart: this.$refs.cpuLine,
                        memChart: this.$refs.memLine,
                        process: process,
                        env: this.curEnvName
                    });
                } else {
                    this.showProcessLoading();
                    this.isResourceChartLine = true;
                    // 清空图表数据
                    this.clearChart();
                    setTimeout(() => {
                        this.isResourceChartLine = false;
                    }, 500);
                }
            },

            /**
             * 从接口获取Metric 数据
             * @param {Object} conf 配置参数
             * @param {String} type
             */
            async getProcessMetric (conf, type = 'all') {
                this.isResourceChartLine = true;
                const fetchData = (metricType) => {
                    const params = {
                        appCode: this.appCode,
                        moduleId: this.curModuleName || 'default',
                        env: conf.env,
                        process_type: this.curProcessName,
                        time_range_str: this.resourceUsageRange,
                        metric_type: metricType
                    };
                    return this.$store.dispatch('processes/getInstanceMetrics', params);
                };
                // 数据处理
                const getData = (payload) => {
                    const datas = [];
                    let limitDatas = null;
                    payload.result.forEach(instance => {
                        const instanceName = instance.display_name;
                        instance.results.forEach(item => {
                            const dataList = item.results;

                            if (item.type_name === 'cpu') {
                                dataList.forEach(data => {
                                    if (data.type_name === 'current') {
                                        data.display_name = `${instanceName}-${data.display_name}`;
                                        datas.push(data);
                                    } else if (data.type_name === 'limit') {
                                        limitDatas = data;
                                    }
                                });
                            } else {
                                dataList.forEach(data => {
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
                    const requestQueue = [];
                    if (type === 'all') {
                        requestQueue.push(fetchData('cpu'));
                        requestQueue.push(fetchData('mem'));
                    } else if (type === 'cpu') {
                        requestQueue.push(fetchData('cpu'));
                    } else {
                        requestQueue.push(fetchData('mem'));
                    }
                    const res = await Promise.all(requestQueue);
                    if (type === 'all') {
                        const [res1, res2] = res;
                        const cpuData = getData(res1);
                        const memData = getData(res2);
                        this.renderChart(cpuData, 'cpu', conf.cpuChart);
                        this.renderChart(memData, 'mem', conf.memChart);
                    } else {
                        const [resData] = res;
                        const curData = getData(resData);
                        this.renderChart(curData, type, type === 'cpu' ? conf.cpuChart : conf.memChart);
                    }
                } catch (e) {
                    this.clearChart();
                    // 未部署显示空状态
                    setTimeout(() => {
                        this.isResourceChartLine = false;
                    }, 500);
                } finally {
                    this.isChartLoading = false;
                    this.isProcessDataReady = true;
                    setTimeout(() => {
                        this.hideProcessLoading();
                    }, 500);
                }
            },

            /**
             * 资源用量图表初始化
             * @param  {Object} instanceData 数据
             * @param  {String} type 类型
             * @param  {Object} ref 图表对象
             */
            renderChart (instanceData, type, ref) {
                this.isResourceChartLine = true;
                const series = [];
                let xAxisData = [];
                instanceData.forEach(item => {
                    const chartData = [];
                    xAxisData = [];
                    item.results.forEach(itemData => {
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
                                    opacity: 0.2
                                }
                            },
                            data: chartData
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
                                    type: 'dashed'
                                }
                            },
                            areaStyle: {
                                normal: {
                                    opacity: 0
                                }
                            },
                            data: chartData
                        });
                    }
                });

                ref.mergeOptions({
                    xAxis: [
                        {
                            data: xAxisData
                        }
                    ],
                    series: series
                });
            },

            /**
             * 清空图表数据
             */
            clearChart () {
                const cpuRef = this.$refs.cpuLine;
                const memRef = this.$refs.memLine;
                // 防止缓存
                this.memLine.xAxis[0].data = [];
                this.memLine.series = [];

                this.cpuLine.xAxis[0].data = [];
                this.cpuLine.series = [];

                this.$nextTick(() => {
                    cpuRef && cpuRef.mergeOptions(this.cpuLine);
                    memRef && memRef.mergeOptions(this.memLine);
                });
            },

            /**
             * 跳转到进程详情页面
             */
            goProcessDetail () {
                const query = {
                    name: this.isCloudApp ? 'appStatus' : 'appProcess',
                    params: {
                        id: this.appCode,
                        moduleId: this.curModuleId
                    },
                    query: {
                        env: this.curEnvName
                    }
                };
                this.$router.push(query);
            },

            // 概览数据接口
            async getOverViewData () {
                try {
                    this.overViewData = await this.$store.dispatch('overview/getOverViewInfo', {appCode: this.appCode});
                    // 默认展开第一个
                    if (Object.keys(this.overViewData).length) {
                        this.activeName = [Object.keys(this.overViewData)[0]];
                        // 第一项为展开数据
                        this.curModuleName = Object.keys(this.overViewData)[0];

                        // 获取资源用量
                        this.topInfo.data = this.computingAppInfo();
                        const processesLen = this.getProcessesLength();
                        this.$set(this.topInfo.data, 'processesLen', processesLen);
                    }
                    // 初始化环境下拉框数据
                    this.curProcessEnvList = this.getProcessList();
                } catch (error) {
                    this.$paasMessage({
                        theme: 'error',
                        message: error.detail
                    });
                } finally {
                    setTimeout(() => {
                        this.loading = false;
                        // 云原生应用不需要对应图表数据
                        this.getPrcessData();
                    }, 300);
                }
            },

            // 获取对应环境下的进程
            getProcessList (moduleName) {
                const curModuleName = moduleName || this.curModuleName;
                return this.envData.filter(env => {
                    const processes = this.overViewData[curModuleName]['envs'][env.name]['processes'] || [];
                    if (processes.length) {
                        return true;
                    }
                });
            },

            handleCollapseClick (data) {
                this.activeModuleId = data[0];
                this.chartFilterType = {
                    pv: true,
                    uv: true
                };
                // 是否有模块
                if (data.length) {
                    this.$nextTick(() => {
                        this.showInstanceChart(this.activeModuleId);
                    });
                }
            },

            /**
             * 显示实例指标数据
             */
            showInstanceChart (module) {
                // 获取对应模块chart实例
                const chartRef = this.getEnvChrtRefs();
                chartRef && chartRef.forEach((refItem, index) => {
                    refItem && refItem.mergeOptions({
                        xAxis: [
                            {
                                data: []
                            }
                        ],
                        series: []
                    });

                    refItem && refItem.showLoading({
                        text: this.$t('正在加载'),
                        color: '#30d878',
                        textColor: '#fff',
                        maskColor: 'rgba(255, 255, 255, 0.8)'
                    });
                    // 避免首次加载出现宽度丢失问题
                    setTimeout(() => {
                        refItem.resize();
                    }, 50);
                });
                // 获取已部署环境的图表数据
                if (this.overViewData[module]) {
                    this.envData.forEach(item => {
                        if (this.overViewData[module]['envs'][item.name].is_deployed) {
                            this.getChartData(item.name);
                        }
                    });
                }
            },

            async getChartData (env) {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.activeModuleId;

                    const { start, end } = this.getEndDate();
                    const backendType = this.backendType;

                    this.defaultRange = this.resourceUsageRange === '24h' ? '1h' : '1d';

                    const params = {
                        'start_time': start,
                        'end_time': end,
                        'interval': this.defaultRange
                    };

                    const res = await this.$store.dispatch('analysis/getChartData', {
                        appCode,
                        moduleId,
                        env,
                        params,
                        backendType,
                        siteName: this.siteName,
                        engineEnabled: this.engineEnabled
                    });
                    this.chartDataCache[env] = res.result.results;
                    // 渲染对应该模块下不同环境图表
                    this.renderEnvChart(env);
                } catch (e) {
                    const chartRef = this.getEnvChrtRefs();
                    chartRef && chartRef.forEach((refItem) => {
                        refItem && refItem.hideLoading();
                        if (e.detail && e.detail !== this.$t('未找到。')) {
                            this.$paasMessage({
                                theme: 'error',
                                message: e.detail
                            });
                        }
                    });
                }
            },

            /**
             * 图表初始化
             * @param  {Object} chartData 数据
             * @param  {String} type 类型
             * @param  {Object} ref 图表对象
             */
            renderEnvChart (env) {
                const series = [];
                const xAxisData = [];
                const pv = [];
                const uv = [];
                const chartData = this.chartDataCache[env];

                chartData.forEach(item => {
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

                // pv
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

                this.envChartOption[env].xAxis[0].data = xAxisData;
                this.envChartOption[env].series = series;
                setTimeout(() => {
                    // 获取对应模块下对应环境的图表实例
                    const chartRef = this.getEnvChrtRefs(env);
                    chartRef && chartRef.forEach(chartItem => {
                        chartItem && chartItem.mergeOptions(this.envChartOption[env], true);
                        chartItem && chartItem.resize();
                        chartItem && chartItem.hideLoading();
                    });
                }, 1000);
            },

            // 获取模块图表实例
            getEnvChrtRefs (chartEnv = 'all') {
                const chartRef = [];
                let envs = envMap;
                // 获取对应环境的图表
                if (chartEnv !== 'all') {
                    envs = envMap.filter(env => env === chartEnv);
                }
                envs.forEach(env => {
                    if (this.$refs[env + this.activeModuleId]) {
                        chartRef.push(this.$refs[env + this.activeModuleId][0]);
                    }
                });

                return chartRef;
            },

            // 文案
            releaseInfoText (env) {
                const appDeployInfo = this.getEnvData(env);
                appDeployInfo.deployment = appDeployInfo.deployment || {};
                return `${appDeployInfo.deployment.operator} ${this.$t('于')} ${this.smartTime(appDeployInfo.deployment.deploy_time, 'smartShorten')} 
                ${appDeployInfo.is_deployed ? this.$t('部署') : this.$t('下架')}`;
            },

            getEnvData (env) {
                const activeModuleName = typeof this.activeName === 'string' ? this.activeName : this.activeName[0];
                if (activeModuleName) {
                    return this.overViewData[activeModuleName]['envs'][env] || { deployment: {} };
                }
                return {};
            },

            // 点击访问或者部署
            handleItemClick (env, type, moduleName) {
                const appRouterInfo = env === 'stag' ? {
                            name: 'appDeploy',
                            params: {
                                id: this.appCode
                            }
                        } : {
                            name: 'appDeployForProd',
                            params: {
                                id: this.appCode
                            },
                            query: {
                                focus: 'prod'
                            }
                        };
                // 访问
                if (type === 'access') {
                    const url = this.overViewData[moduleName]['envs'][env]['exposed_link'].url;
                    window.open(url, '_blank');
                } else {
                    if (this.isCloudApp) {
                        // 应用编排
                        this.toAppOrchestration();
                    } else {
                        const toModule = this.curAppModuleList.find(module => module.name === moduleName);
                        if (toModule) {
                            // 切换对应模块
                            this.$refs.appTopBarRef.handleModuleSelect(toModule);
                        }
                        this.$router.push(appRouterInfo);
                    }
                }
            },

            // 应用编排
            toAppOrchestration () {
                this.$router.push({
                    name: 'cloudAppDeployForProcess',
                    params: {
                        id: this.appCode
                    }
                });
            },

            // 切换pv/uv
            handleChartFilte (type, env) {
                this.chartFilterType[type] = !this.chartFilterType[type];
                this.renderEnvChart(env);
            },

            handleDateChange (date, id) {
                this.changIndex++;
                this.dateRange = {
                    startTime: date[0],
                    endTime: date[1]
                };
                this.curTime = this.dateShortCut.find(t => t.id === id) || {};
                this.resourceUsageRange = timeMap[this.curTime.id];
            },

            // 获取告警数据
            async getAlarmData () {
                const { start, end } = this.getEndDate();

                const params = {
                    code: this.appCode,
                    search: {
                        'start_before': start,
                        'start_after': end
                    }
                };

                try {
                    const res = await this.$store.dispatch('alarm/getPersonalAlarmList', params);
                    this.$set(this.topInfo.data, 'alarmCount', res.count || 0);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            getEndDate () {
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

                return {
                    start,
                    end: getEndDate(end)
                };
            },

            // 计算当前应用使用资源用量
            computingAppInfo () {
                let cpuStag = 0;
                let cpuProd = 0;
                let memStag = 0;
                let memProd = 0;
                const data = this.overViewData;
                for (const key in data) {
                    // 获取 stag processes
                    let stagProcessList = data[key]['envs']['stag']['processes'];
                    if (stagProcessList.length) {
                        for (const i in stagProcessList) {
                            // 每一项 processes
                            const stagProcess = stagProcessList[i];
                            for (const nameStag in stagProcess) {
                                const targetReplicas = stagProcess[nameStag]['target_replicas'];
                                cpuStag += stagProcess[nameStag]['resource_limit_quota']['cpu'] * targetReplicas;
                                memStag += stagProcess[nameStag]['resource_limit_quota']['memory'] * targetReplicas;
                            };
                        };
                    }

                    // 获取 prod processes
                    let prodProcessList = data[key]['envs']['prod']['processes'];
                    if (prodProcessList.length) {
                        for (const i in prodProcessList) {
                            const prodProcess = prodProcessList[i];
                            for (const nameProd in prodProcess) {
                                const targetReplicas = prodProcess[nameProd]['target_replicas'];
                                cpuProd += prodProcess[nameProd]['resource_limit_quota']['cpu'] * targetReplicas;
                                memProd += prodProcess[nameProd]['resource_limit_quota']['memory'] * targetReplicas;
                            };
                        };
                    }
                };

                // 转为显示单位
                return {
                    cpuStag: this.unitConvert(cpuStag, 1000),
                    cpuProd: this.unitConvert(cpuProd, 1000),
                    memStag: this.unitConvert(memStag, 1024),
                    memProd: this.unitConvert(memProd, 1024)
                };
            },

            unitConvert (value, divisor) {
                return parseFloat((value / divisor).toFixed(2));
            },

            getProcessesLength () {
                let processesLen = 0;
                const data = this.overViewData;
                for (const key in data) {
                    processesLen += data[key]['envs']['stag']['processes'].length;
                    processesLen += data[key]['envs']['prod']['processes'].length;
                };
                return processesLen;
            }
        }
    };
</script>

<style scoped lang="scss">
    @import './overview.scss';
</style>

<!-- 折叠板内部样式 -->
<style lang="scss">
    .paas-module-warp{
        .paas-module-item {
            margin-top: 16px;
            border: solid 1px #e6e9ea;
            .bk-collapse-item-header{
                background: #F5F7FA !important;
            }
            .icon-angle-right{
                display: none;
            }
        }
        .collapse-select{
           background: F5F7FA !important;
        }
        .search-chart-wrap .bk-select .bk-select-name {
            padding: 0 18px 0 3px;
        }
    }
</style>
