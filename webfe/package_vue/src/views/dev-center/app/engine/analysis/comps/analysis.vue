<template lang="html">
  <section>
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
          v-if="engineEnabled && tabName === 'webAnalysis'"
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
          v-if="tabName === 'logAnalysis'"
          class="desc f12 fix"
        >
          {{ $t('基于应用访问日志进行访问量统计') }}
          <a
            :href="GLOBAL.DOC.PA_ANALYSIS_INGRESS"
            target="_blank"
            class="f12 ml5 mr15"
          > {{ $t('数据说明') }} </a>
          <bk-popover v-if="!isLogEnabled">
            <a
              href="javascript: void(0);"
              class="f12 ml5 mr15"
              @click="handleEnableLog"
            >
              <div class="icon-wrapper">
                <i
                  v-if="!isEditLoading"
                  class="paasng-icon paasng-cog"
                  style="vertical-align: middle;"
                />
                <round-loading
                  v-else
                  ext-cls="analysis-round-loading"
                />
              </div>
              {{ $t('手动开启') }}
            </a>
            <div
              slot="content"
              style="width: 300px; text-align: left;"
            >
              {{ $t('日志统计功能会在应用部署后自动打开，你也可以点这手动开启。该功能打开后暂不支持关闭') }}
            </div>
          </bk-popover>
        </div>

        <div
          class="analysis-box"
          :class="!engineEnabled && tabName === 'webAnalysis' ? 'set-margin-top' : ''"
        >
          <div class="summary">
            <div class="pv">
              <strong class="title">{{ summaryData.pv || 0 }}</strong>
              <p class="desc">
                {{ $t('访问数（PV）') }}
              </p>
            </div>
            <div class="uv">
              <strong class="title">{{ summaryData.uv || 0 }}</strong>
              <p class="desc">
                {{ $t('独立访客数（UV）') }}
                <i
                  v-if="tabName === 'webAnalysis'"
                  v-bk-tooltips="tootipsText"
                  class="paasng-icon paasng-exclamation-circle uv-tips"
                />
                <bk-popover
                  placement="top"
                  :transfer="true"
                >
                  <i
                    v-if="tabName === 'logAnalysis'"
                    class="paasng-icon paasng-exclamation-circle uv-tips"
                  />
                  <div slot="content">
                    <p>
                      {{ $t('独立访客数通过 IP 和 User-Agent 数据计算而来') }}
                      <a
                        :href="GLOBAL.DOC.PA_ANALYSIS_INGRESS_UV"
                        target="_blank"
                        class="ps-link"
                      >
                        <i class="paasng-icon paasng-angle-double-right" /> {{ $t('查看详细规则') }}
                      </a>
                    </p>
                  </div>
                </bk-popover>
              </p>
            </div>
          </div>
          <div class="chart-wrapper">
            <div class="chart-box">
              <div class="chart-action">
                <ul class="dimension fl">
                  <li
                    :class="{ 'active': chartFilterType.pv }"
                    @click="handleChartFilte('pv')"
                  >
                    <span class="dot warning" /> PV
                  </li>
                  <li
                    :class="{ 'active': chartFilterType.uv }"
                    @click="handleChartFilte('uv')"
                  >
                    <span class="dot primary" /> UV
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
                :key="renderChartIndex"
                ref="chart"
                :options="chartOption"
                auto-resize
                style="width: 100%; height: 240px; background: #1e1e21;"
              />
            </div>
          </div>
        </div>

        <div class="content-header mt15">
          <bk-select
            v-model="dimensionType"
            style="width: 202px;"
            :placeholder="$t('选择分组维度')"
            :searchable="false"
            :clearable="false"
            @selected="handleDimensionChange"
          >
            <bk-option
              v-for="option in dimensionList"
              :id="option.value"
              :key="option.value"
              :name="option.name"
            />
          </bk-select>
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
          <bk-table-column
            v-for="field of fieldList"
            :key="field.prop"
            :column-key="field.prop"
            :label="$t(field.name)"
            :prop="field.prop"
            :sortable="field.sortable"
          >
            <template slot-scope="{ row }">
              <span
                v-if="row.display_name && field.prop === 'name'"
                v-bk-tooltips="row.description"
                class="display-name"
              >
                {{ row.display_name }}
              </span>
              <span v-else>
                {{ row[field.prop] }}
              </span>
              <template v-if="field.prop === 'name' && row.display_name && row.link">
                ，<a
                  target="_blank"
                  :href="row.link"
                > {{ $t('更多') }} </a>
              </template>
            </template>
          </bk-table-column>
        </bk-table>
      </section>
    </div>
    <render-sideslider
      :is-show.sync="isShowSideslider"
      :title="sidesliderTitle"
      :engine-enable="curAppInfo.web_config.engine_enabled"
      :site-name="siteDisplayName"
    />
  </section>
</template>

<script>
    import moment from 'moment';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import 'echarts/lib/chart/line';
    import 'echarts/lib/component/tooltip';
    import RenderSideslider from './access-guide-sideslider';
    import chartOption from '@/json/analysis-chart-option';
    // eslint-disable-next-line
    import { export_json_to_excel } from '@/common/Export2Excel'
    import { formatDate } from '@/common/tools';

    export default {
        components: {
            chart: ECharts,
            RenderSideslider
        },
        mixins: [appBaseMixin],
        props: {
            type: {
                type: String,
                default: 'web'
            },
            backendType: {
                type: String,
                default: 'user_tracker'
            },
            tabName: {
                type: String,
                default: 'webAnalysis'
            },
            engineEnabled: {
                type: Boolean,
                default: true
            }
        },
        data () {
            return {
                isLoading: false,
                isPathDataLoading: false,
                isChartLoading: false,
                curEnv: 'stag',
                daterange: [new Date(), new Date()],
                page: '',
                pageList: [],
                pathData: [],
                fieldList: [],
                defaultRange: '1d',
                analysisConfig: null,
                startLimitDate: '',
                endLimitDate: '',
                dateRange: {
                    startTime: '',
                    endTime: ''
                },
                curTab: 'webAnalysis',
                initDateTimeRange: [],
                chartFilterType: {
                    pv: true,
                    uv: true
                },
                renderChartIndex: 0,
                dateOptions: {
                    // 大于今天的都不能选
                    disabledDate (date) {
                        return date && date.valueOf() > Date.now() - 86400;
                    }
                },
                summaryData: {
                    pv: '--',
                    uv: '--'
                },
                pageAnalysisData: [],
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10,
                    ordering: ''
                },
                currentBackup: 1,
                chartOption: chartOption.pv_uv,
                dimensionList: [],
                dimensionType: 'path',
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
                ],
                exportLoading: false,
                isLogEnabled: true,
                isEditLoading: false,
                isShowSideslider: false,
                tootipsText: this.$t('独立访客数目前是按天统计的，如果选择的时间范围跨天的话，同一个用户会被重复计算，故独立访客数会大于真实的用户数。'),
                requestQueue: ['status', 'config', 'pvuv', 'chart', 'path']
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
            chartData () {
                const data = this.$store.state.log.chartData;
                return data;
            },
            hasChartData () {
                if (this.chartData.series.length && this.chartData.series[0].data.length) {
                    return true;
                }
                return false;
            },
            allowRanges () {
                if (this.dateRange.startTime && this.dateRange.endTime) {
                    const start = this.dateRange.startTime;
                    const end = this.dateRange.endTime;
                    const now = moment().format('YYYY-MM-DD');

                    const startSeconds = moment(start).valueOf();
                    const endSeconds = moment(end).valueOf();
                    const oneEndSeconds = moment(start).add(1, 'days').valueOf(); // 一天后
                    const threeEndSeconds = moment(start).add(3, 'days').valueOf(); // 三天后
                    const sevenEndSeconds = moment(now).add(-7, 'days').valueOf(); // 七天后

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
                    } else {
                        if (oneEndSeconds <= startSeconds) {
                            // 大于1天小于3天
                            return ['1h', '1d'];
                        } else {
                            if (startSeconds <= sevenEndSeconds) {
                                return ['1h'];
                            }
                            // 小于1天
                            return ['5m', '1h'];
                        }
                    }
                } else {
                    return ['5m', '1h', '1d'];
                }
            },
            siteDisplayName () {
                return this.analysisConfig ? this.analysisConfig.site.name : '';
            },
            sidesliderTitle () {
                const curEnvText = this.curEnv === 'stag' ? this.$t('预发布环境') : this.$t('生产环境');
                return this.engineEnabled ? `${this.$t('网站访问统计')}-${curEnvText}` : '';
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
            defaultRange () {
                this.showInstanceChart();
            },
            curEnv () {
                this.refresh();
            },
            allowRanges () {
                this.defaultRange = this.allowRanges[this.allowRanges.length - 1];
            },
            '$route' () {
                this.refresh();
            },
            'pagination.current' (value) {
                this.currentBackup = value;
            }
        },
        created () {
            moment.locale(this.localLanguage);
            window.moment = moment;
            this.siteName = 'default';
        },
        mounted () {
            this.isLoading = true;
            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
            this.initDateTimeRange = [start, end];

            this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
            this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
        },
        methods: {
            async getAnalysisStatus () {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;

                    const res = await this.$store.dispatch('analysis/getAnalysisStatus', {
                        appCode,
                        moduleId
                    });
                    this.isLogEnabled = res.status;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                    this.isLogEnabled = false;
                }
            },

            // 手动修改基于日志统计功能状态
            async handleEnableLog () {
                if (this.isEditLoading) {
                    return false;
                }
                this.isEditLoading = true;

                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const params = {
                        status: true
                    };
                    await this.$store.dispatch('analysis/enableLog', {
                        appCode,
                        moduleId,
                        params
                    });

                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('已成功开启，请访问应用后刷新查看数据')
                    });
                    this.isLogEnabled = true;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isEditLoading = false;
                    }, 1000);
                }
            },

            async handleExportToExcel () {
                this.exportLoading = true;
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const env = this.curEnv;
                    const dimension = this.dimensionType;
                    const backendType = this.backendType;

                    const params = {
                        'limit': 10000,
                        'offset': 0,
                        'start_time': this.dateRange.startTime,
                        'end_time': this.dateRange.endTime
                    };

                    params.ordering = this.pagination.ordering || '-pv';
                    const res = await this.$store.dispatch('analysis/getDataByDimension', {
                        appCode,
                        moduleId,
                        env,
                        dimension,
                        params,
                        backendType,
                        siteName: this.siteName,
                        engineEnabled: this.engineEnabled
                    });
                    const results = [];
                    res.resources.forEach(item => {
                        let obj = {
                            name: item.name
                        };
                        for (const key in item.values) {
                            obj[key] = item.values[key];
                        }
                        if (item.display_options) {
                            obj = Object.assign(obj, { ...item.display_options });
                        }
                        results.push(obj);
                    });

                    const fields = this.fieldList.map(item => item.name);
                    const props = this.fieldList.map(item => item.prop);
                    const data = this.formatJson(props, results);

                    const getCurTabText = () => {
                        if (this.tabName === 'webAnalysis') {
                            return '_website_browsing_statistics_';
                        }
                        return '_access_log_statistics_';
                    };

                    const fileName = this.engineEnabled ? `${appCode}_${this.curModuleId}${getCurTabText()}${this.dimensionType}` : `${appCode}${getCurTabText()}${this.dimensionType}`;
                    export_json_to_excel(fields, data, fileName);
                } catch (e) {
                    if (e.detail && e.detail !== this.$t('未找到。')) {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail
                        });
                    }
                } finally {
                    this.exportLoading = false;
                }
            },

            formatJson (filterVal, jsonData) {
                return jsonData.map(v => filterVal.map(j => v[j]));
            },

            refresh () {
                // this.requestQueue = ['status', 'config', 'pvuv', 'chart', 'path']
                this.clearData();

                this.$nextTick(() => {
                    const promises = [];
                    if (this.engineEnabled) {
                        promises.push(this.getAnalysisStatus());
                    }
                    promises.push(this.getAnalysisConfig());
                    promises.push(this.getPvUv());
                    promises.push(this.showInstanceChart());
                    promises.push(this.getPathData());

                    Promise.all(promises).finally(() => {
                        this.$emit('data-ready');
                    });
                });
            },

            clearData () {
                this.summaryData = {
                    pv: '--',
                    uv: '--'
                };

                this.pagination = {
                    current: 1,
                    count: 0,
                    limit: 10,
                    ordering: ''
                };

                this.pathData = [];
                this.clearChart();
            },

            async getAnalysisConfig () {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const env = this.curEnv;
                    const backendType = this.backendType;

                    const res = await this.$store.dispatch('analysis/getAnalysisConfig', {
                        appCode,
                        moduleId,
                        env,
                        backendType,
                        siteName: this.siteName,
                        engineEnabled: this.engineEnabled
                    });

                    // tencent版访问日志统计-去掉用户选项
                    // if (this.curAppInfo && this.curAppInfo.application.region === 'tencent') {
                    //     res.supported_dimension_type = res.supported_dimension_type.filter(item => item.value !== 'user')
                    // }
                    this.startLimitDate = res.time_range.start_time;
                    this.endLimitDate = res.time_range.end_time;
                    this.dimensionList = res.supported_dimension_type;
                    this.analysisConfig = res;
                } catch (e) {
                    console.error(e);
                } finally {
                    this.isLoading = false;
                }
            },

            async getPvUv () {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const env = this.curEnv;
                    const backendType = this.backendType;

                    const params = {
                        'start_time': this.dateRange.startTime,
                        'end_time': this.dateRange.endTime,
                        'interval': this.defaultRange
                    };
                    const res = await this.$store.dispatch('analysis/getPvUv', {
                        appCode,
                        moduleId,
                        env,
                        params,
                        backendType,
                        siteName: this.siteName,
                        engineEnabled: this.engineEnabled
                    });
                    this.summaryData = res.result.results;
                } catch (e) {
                    if (e.detail && e.detail !== this.$t('未找到。')) {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail
                        });
                    }
                }
            },

            async getPathData (page) {
                this.isPathDataLoading = true;
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const env = this.curEnv;
                    const dimension = this.dimensionType;
                    const backendType = this.backendType;
                    const curPage = page || this.pagination.current;

                    const params = {
                        'limit': this.pagination.limit,
                        'offset': this.pagination.limit * (curPage - 1),
                        'start_time': this.dateRange.startTime,
                        'end_time': this.dateRange.endTime
                    };

                    params.ordering = this.pagination.ordering || '-pv';

                    const res = await this.$store.dispatch('analysis/getDataByDimension', {
                        appCode,
                        moduleId,
                        env,
                        dimension,
                        params,
                        backendType,
                        siteName: this.siteName,
                        engineEnabled: this.engineEnabled
                    });
                    const results = [];
                    const fieldList = [];

                    const schemas = res.meta.schemas;
                    fieldList.push({
                        name: schemas.resource_type.display_name,
                        prop: 'name',
                        sortable: false
                    });
                    schemas.values_type.forEach(item => {
                        fieldList.push({
                            name: item.display_name,
                            prop: item.name,
                            sortable: item.sortable ? 'custom' : false
                        });
                    });
                    res.resources.forEach(item => {
                        let obj = {
                            name: item.name
                        };
                        for (const key in item.values) {
                            obj[key] = item.values[key];
                        }

                        if (item.display_options) {
                            obj = Object.assign(obj, { ...item.display_options });
                        }

                        results.push(obj);
                    });

                    this.pathData = results;
                    this.fieldList = fieldList;
                    this.pagination.count = res.meta.pagination.total;
                } catch (e) {
                    if (e.detail && e.detail !== this.$t('未找到。')) {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail
                        });
                    }
                } finally {
                    this.isPathDataLoading = false;
                }
            },

            /**
             * 显示实例指标数据
             */
            showInstanceChart (instance, processes) {
                const chartRef = this.$refs.chart;

                chartRef && chartRef.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: []
                });

                chartRef && chartRef.showLoading({
                    text: this.$t('正在加载'),
                    color: '#30d878',
                    textColor: '#fff',
                    maskColor: 'rgba(255, 255, 255, 0.8)'
                });

                this.getChartData();
            },

            async getChartData () {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const env = this.curEnv;
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
                    this.chartDataCache = res.result.results;
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
                    xAxisData.push(moment(item.time).format(this.dateFormat));
                    uv.push(item.uv);
                    pv.push(item.pv);
                });

                // color: ['#699df4', '#ffb849']
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

                this.chartOption.xAxis[0].data = xAxisData;
                this.chartOption.series = series;
                setTimeout(() => {
                    const chartRef = this.$refs.chart;
                    chartRef && chartRef.mergeOptions(this.chartOption, true);
                    chartRef && chartRef.resize();
                    chartRef && chartRef.hideLoading();
                }, 1000);
            },

            handleChartFilte (type) {
                this.chartFilterType[type] = !this.chartFilterType[type];
                this.renderChart();
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

            sortPV (data1, data2) {
                const pv1 = data1.pv;
                const pv2 = data2.pv;
                return Number(pv1) > Number(pv2);
            },

            sortUV (data1, data2) {
                const uv1 = data1.uv;
                const uv2 = data2.uv;
                return Number(uv1) > Number(uv2);
            },

            handleDateChange (date, type) {
                this.dateRange = {
                    startTime: date[0],
                    endTime: date[1]
                };
            },

            handleRangeChange (type) {
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

            limitChange (limit) {
                this.pagination.limit = limit;
                this.pagination.current = 1;
                this.getPathData(this.pagination.current);
            },

            pageChange (newPage) {
                this.pagination.current = newPage;
                this.getPathData(newPage);
            },

            sortChange (params) {
                if (params.order === 'descending') {
                    this.pagination.ordering = `-${params.prop}`;
                } else if (params.order === 'ascending') {
                    this.pagination.ordering = `${params.prop}`;
                } else {
                    this.pagination.ordering = '';
                }
                this.getPathData();
            },

            handleDimensionChange (value, options) {
                this.pagination.current = 1;
                this.getPathData();
            }
        }
    };
</script>

<style lang="scss" scoped>
    .content-header {
        position: relative;
        height: 32px;
        .export-button {
            position: absolute;
            top: 0;
            right: 0;
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
                .uv-tips {
                    margin-left: -5px;
                    color: #63656e;
                }
            }
        }

        .chart-wrapper {
            flex: 1;
            overflow: hidden;
        }
    }

    .bk-table {
        .display-name {
            display: inline-block;
            padding-bottom: 1px;
            border-bottom: 1px dashed #979ba5;
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

    .icon-wrapper {
        width: 15px;
        margin-top: 2px;
        display: inline-block;
        vertical-align: middle;
        text-align: left;
        float: left;
    }

    .analysis-round-loading {
        position: relative;
        left: -3px;
    }

    .info-button {
        height: 30px;
        padding: 0 5px;
        line-height: 30px;
        font-size: 12px;
    }
</style>
