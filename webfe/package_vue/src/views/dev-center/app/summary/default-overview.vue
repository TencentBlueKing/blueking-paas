<template lang="html">
  <div
    id="summary"
    class="right-main"
  >
    <app-top-bar
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
        v-if="releaseStatusStag.hasDeployed || releaseStatusProd.hasDeployed"
        class="default-top-info"
        :app-info="topInfo"
      />
      <div class="overview-middle">
        <template v-if="!loading">
          <div
            v-if="releaseStatusStag.hasDeployed || releaseStatusProd.hasDeployed"
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
                    <span class="header-env">{{ k === 'stag' ? $t('预发布环境') : $t('正式环境') }}</span>
                    <span :class="['header-env', 'pl10', { 'not-deployed': !data.is_deployed }]">{{ data.is_deployed ? $t('已部署') : $t('未部署') }}</span>
                    <bk-button
                      v-if="data.is_deployed"
                      class="pl10"
                      theme="primary"
                      text
                      @click="handleItemClick(k, 'access')"
                    >
                      {{ $t('访问') }}
                    </bk-button>
                    <bk-button
                      class="pl10"
                      theme="primary"
                      text
                      @click="handleItemClick(k, 'deploy')"
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
                          @click="handleItemClick(k, 'access')"
                        >
                          {{ $t('访问') }}
                        </bk-button>
                        <bk-button
                          class="pl10"
                          theme="primary"
                          text
                          @click="handleItemClick(k, 'deploy')"
                        >
                          {{ $t('部署') }}
                        </bk-button>
                      </div>

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
                        <ul class="chart-legend">
                          <li>
                            <span class="dot warning" /> PV
                          </li>
                          <li>
                            <span class="dot primary" /> UV
                          </li>
                        </ul>
                      </div>
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
                <bk-select
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
                <bk-select
                  v-model="curEnvName"
                  style="width: 116px; font-weight: normal;"
                  class="fr collapse-select mb10 mr10"
                  :clearable="false"
                  behavior="simplicity"
                  @selected="handlerProcessSelecte('env')"
                >
                  <bk-option
                    v-for="option in envData"
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
                    <span class="header-title">{{ $t('资源用量') }}</span>
                    <span
                      v-if="curEnvName"
                      class="text ml5"
                    >
                      <a
                        href="javascript: void(0);"
                        @click="goProcessView"
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
                          ref="cpuLine"
                          :options="cpuLine"
                          auto-resize
                          style="width: 100%; height: 235px;"
                        />
                      </div>
                      <div class="chart-box summary-chart-box">
                        <div class="type-title">
                          {{ $t('内存使用量') }}
                        </div>
                        <strong class="title"> {{ $t('单位：MB') }} </strong>
                        <!-- 未部署展示无数据 -->
                        <chart
                          ref="memLine"
                          :options="memLine"
                          auto-resize
                          style="width: 100%; height: 235px;"
                        />
                      </div>
                    </div>
                    <!-- 是否需要空状态 -->
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

          <!-- 没有部署tips -->
          <div
            v-else
            class="coding"
            data-test-id="summary_box_empty"
          >
            <template v-if="!loading">
              <h2> {{ $t('应用尚未部署，暂无运行数据！') }} </h2>
              <p> {{ $t('你可以根据以下操作解决此问题') }} </p>
              <div class="none-summary-controls">
                <router-link
                  :to="{ name: 'appDeployForStag', params: { id: appCode, moduleId: curModuleId } }"
                  class="bk-button bk-primary bk-button-large"
                >
                  {{ $t('部署至预发布环境') }}
                </router-link>
              </div>
            </template>
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

    // A data formatter for released info
    class ReleasedInfoFormatter {
        constructor (envName, respData) {
            this.envName = envName;
            this.respData = respData;
        }

        format () {
            const latestInfo = this.respData.deployment || this.respData.offline;
            const result = {
                env: this.envName,
                hasDeployed: true,
                branch: latestInfo.repo.name,
                username: latestInfo.operator.username,
                time: latestInfo.created,
                url: this.respData.exposed_link.url,
                proc: [],
                isEnvOfflined: !this.respData.deployment
            };

            this.respData.processes.forEach((item) => {
                result.proc.push(this.formatProcess(item));
            });
            return result;
        }

        formatProcess (data) {
            for (const processName in data) {
                const details = data[processName];
                let statusText = i18n.t('正在运行');
                if (details.target_status === 'stop') {
                    statusText = i18n.t('已停止');
                }

                return {
                    name: processName,
                    status: statusText
                };
            }
        }
    }

    const DEFAULT_RELEASE_STATUS = {
        hasDeployed: false,
        branch: 'trunk',
        isEnvOfflined: true,
        username: '',
        time: '',
        url: '',
        proc: []
    };

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
                releaseStatusStag: { ...DEFAULT_RELEASE_STATUS },
                releaseStatusProd: { ...DEFAULT_RELEASE_STATUS },
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
                curCpuActive: '1h',
                curMemActive: '1h',
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
                    description: i18n.t('平台为该类应用提供应用引擎、增强服务、云API 权限、应用市场等功能'),
                    data: {}
                },
                curTime: {},
                resourceUsageRange: '24h',
                activeModuleId: '',
                changIndex: 0,
                chartDataCache: {}
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
            curEnv () {
                if (!this.releaseStatusProd.isEnvOfflined) {
                    return 'prod';
                } else if (!this.releaseStatusStag.isEnvOfflined) {
                    return 'stag';
                }
                return 'stag';
            },
            curEnvProcesses () {
                if (this.releaseStatusProd && !this.releaseStatusProd.isEnvOfflined) {
                    return this.releaseStatusProd.proc.filter(item => item.status === this.$t('正在运行'));
                } else if (this.releaseStatusStag && !this.releaseStatusStag.isEnvOfflined) {
                    return this.releaseStatusStag.proc.filter(item => item.status === this.$t('正在运行'));
                }
                return [];
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            }
        },
        watch: {
            '$route' () {
                this.init();
            },
            dateRange: {
                deep: true,
                handler () {
                    // 重新获取数据
                    if (this.changIndex !== 0) {
                        this.$nextTick(() => {
                            this.showInstanceChart(this.activeModuleId);
                            this.showProcessResource(this.curEnvName);
                        });
                    }
                }
            }
        },
        created () {
            moment.locale(this.localLanguage);
        },
        mounted () {
            this.init();
            this.initDate();
        },
        methods: {
            async init () {
                this.loading = true;
                this.isChartLoading = true;
                this.isProcessDataReady = false;

                this.curProcessName = '';
                this.releaseStatusStag = { ...DEFAULT_RELEASE_STATUS };
                this.releaseStatusProd = { ...DEFAULT_RELEASE_STATUS };
                this.appDevLang = this.curAppModule.language;
                await this.getOverViewData();
                this.fetchAllDeployedInfos();
                // 获取动态
                this.getModuleOperations();
                if (this.curAppModule && this.curAppModule.repo) {
                    this.trunkUrl = this.curAppModule.repo.trunk_url || '';
                    this.sourceType = this.curAppModule.repo.source_type || '';
                }
            },
            initDate () {
                const end = new Date();
                const start = new Date();
                this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
                this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
                this.curTime = this.dateShortCut[0];
            },
            fetchDeployedInfo (envName) {
                const info = new Promise((resolve, reject) => {
                    this.$http.get(BACKEND_URL + '/api/bkapps/applications/' + this.appCode + '/modules/' + this.curModuleId + '/envs/' + envName + '/released_state/?with_processes=true')
                        .then((resp) => {
                            resolve(new ReleasedInfoFormatter(envName, resp).format());
                        }, (res) => {
                            reject(new Error('not deployed'));
                        });
                });
                return info;
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
            async fetchAllDeployedInfos () {
                try {
                    this.releaseStatusStag = await this.fetchDeployedInfo('stag');
                } catch (e) {
                    this.releaseStatusStag.hasDeployed = false;
                    this.loading = false;
                }

                try {
                    this.releaseStatusProd = await this.fetchDeployedInfo('prod');
                } catch (e) {
                    this.releaseStatusProd.hasDeployed = false;
                } finally {
                    setTimeout(() => {
                        this.loading = false;
                    }, 500);
                }

                if (!this.curModuleName) {
                    this.getOverViewData();
                }

                // 资源视图优先展示生产环境
                this.$nextTick(async () => {
                    this.handleCollapseClick(Object.keys(this.overViewData));
                    this.showProcessLoading();
                    const prodProcess = this.releaseStatusProd.proc.find(item => item.status === this.$t('正在运行'));
                    const stagProcess = this.releaseStatusStag.proc.find(item => item.status === this.$t('正在运行'));
                    if (!this.releaseStatusProd.isEnvOfflined && prodProcess) {
                        this.curProcessName = prodProcess.name;
                        // 获取资源用量图表数据
                        this.showProcessResource('prod');
                    } else if (!this.releaseStatusStag.isEnvOfflined && stagProcess) {
                        this.curProcessName = stagProcess.name;
                        this.showProcessResource('stag');
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
                // 清空图标数据
                this.showProcessResource(this.curEnvName);
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
                    chart.resize();
                    chart.showLoading({
                        text: this.$t('正在加载'),
                        color: '#30d878',
                        textColor: '#fff',
                        maskColor: '#FCFCFD'
                    });
                }
                if (memChart) {
                    memChart.resize();
                    memChart.showLoading({
                        text: this.$t('正在加载'),
                        color: '#30d878',
                        textColor: '#fff',
                        maskColor: '#FCFCFD'
                    });
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
            showProcessResource (env) {
                const process = this.curEnvProcesses.find(item => {
                    return item.name === this.curProcessName;
                });

                if (process) {
                    this.showProcessLoading();
                    this.getProcessMetric({
                        cpuChart: this.$refs.cpuLine,
                        memChart: this.$refs.memLine,
                        process: process,
                        env: env
                    });
                }
            },

            /**
             * 从接口获取Metric 数据
             * @param {Object} conf 配置参数
             * @param {String} type
             */
            async getProcessMetric (conf, type = 'all') {
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
                } finally {
                    this.isChartLoading = false;
                    this.isProcessDataReady = true;
                    this.hideProcessLoading();
                }
            },

            /**
             * 资源用量图表初始化
             * @param  {Object} instanceData 数据
             * @param  {String} type 类型
             * @param  {Object} ref 图表对象
             */
            renderChart (instanceData, type, ref) {
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
            goProcessView () {
                this.$router.push({
                    name: 'appProcess',
                    params: {
                        id: this.appCode,
                        moduleId: this.curModuleId
                    },
                    query: {
                        focus: this.curEnv
                    }
                });
            },

            // 概览数据接口
            async getOverViewData () {
                try {
                    this.overViewData = await this.$store.dispatch('overview/getOverViewInfo', {appCode: this.appCode});
                    // 默认展开第一个
                    if (Object.keys(this.overViewData).length) {
                        this.activeName = Object.keys(this.overViewData)[0];
                        this.curModuleName = Object.keys(this.overViewData)[0];

                        // 获取资源用量
                        this.topInfo.data = this.computingAppInfo();
                        const processesLen = this.getProcessesLength();
                        this.$set(this.topInfo.data, 'processesLen', processesLen);
                    }
                } catch (error) {
                    this.$paasMessage({
                        theme: 'error',
                        message: error.detail
                    });
                } finally {
                    setTimeout(() => {
                        this.loading = false;
                    }, 500);
                }
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
                    const backendType = this.backendType;

                    this.defaultRange = this.resourceUsageRange === '24h' ? '1h' : '1d';

                    const params = {
                        'start_time': start,
                        'end_time': getEndDate(),
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
                const appDeployInfo = env === 'stag' ? this.releaseStatusStag : this.releaseStatusProd;
                return `${appDeployInfo.username} 于 ${this.smartTime(appDeployInfo.time, 'smartShorten')} 
                ${appDeployInfo.isEnvOfflined ? this.$t('下架') : this.$t('部署')}`;
            },

            // 点击访问或者部署
            handleItemClick (env, type) {
                const appDeployInfo = env === 'stag' ? this.releaseStatusStag : this.releaseStatusProd;
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
                if (type === 'access') { // 访问
                    window.open(appDeployInfo.url, '_blank');
                } else { // 部署
                    this.$router.push(appRouterInfo);
                }
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
                console.log('time', timeMap[this.curTime.id]);
                this.resourceUsageRange = timeMap[this.curTime.id];
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
                                const maxReplicas = stagProcess[nameStag]['max_replicas'];
                                cpuStag += stagProcess[nameStag]['resource_limit_quota']['cpu'] * maxReplicas;
                                memStag += stagProcess[nameStag]['resource_limit_quota']['memory'] * maxReplicas;
                            };
                        };
                    }

                    // 获取 prod processes
                    let prodProcessList = data[key]['envs']['prod']['processes'];
                    if (prodProcessList.length) {
                        for (const i in prodProcessList) {
                            const prodProcess = prodProcessList[i];
                            for (const nameProd in prodProcess) {
                                const maxReplicas = prodProcess[nameProd]['max_replicas'];
                                cpuProd += prodProcess[nameProd]['resource_limit_quota']['cpu'] * maxReplicas;
                                memProd += prodProcess[nameProd]['resource_limit_quota']['memory'] * maxReplicas;
                            };
                        };
                    }
                };

                // 转为显示单位
                return {
                    cpuStag: Math.floor(cpuStag / 1000),
                    cpuProd: Math.floor(cpuProd / 1000),
                    memStag: memStag / 1024,
                    memProd: memProd / 1024
                };
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
    }
</style>
