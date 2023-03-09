<template lang="html">
  <div
    id="summary"
    class="right-main"
  >
    <paas-content-loader
      :is-loading="loading"
      placeholder="summary-loading"
      :offset-top="20"
      class="overview-middle"
    >
      <template v-if="!loading">
        <div class="summary-content">
          <div class="overview-warp mb20">
            <div class="info flex_1">
              <div class="type">
                应用类型：普通应用
              </div>
              <div class="type-desc pt5">
                平台为该类应用提供应用引擎、增强服务、云API 权限、应用市场等功能
              </div>
            </div>
            <div class="process flex_1 flex align-center pl20">
              <div class="img-warp">
                <img
                  src="/static/images/process.png"
                >
              </div>
              <div class="desc pl10">
                <div class="over-fs">
                  6
                </div>
                <div>进程</div>
              </div>
              <div class="desc pl20">
                <div>cpu: <span>111</span></div>
                <div class="desc-text">
                  内存: <span>111</span>
                </div>
              </div>
            </div>

            <div class="alarm flex_1 flex align-center pl20">
              <div class="img-warp">
                <img
                  src="/static/images/alarm.png"
                >
              </div>
              <div class="desc pl10">
                <div class="over-fs">
                  6
                </div>
                <div class="desc">
                  告警数量
                </div>
              </div>
            </div>
          </div>
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
                <div class="mr20">
                  <i
                    class="paasng-icon paasng-bold"
                    :class="activeName.includes(key) ? 'paasng-down-shape':'paasng-right-shape'"
                  />
                  <span
                    class="
                    header-title"
                  >{{ key }} {{ item.is_default ? '(主)' : '' }}</span>
                </div>
                <div
                  v-for="(data, k) in item.envs"
                  v-if="!activeName.includes(key)"
                  :key="k"
                  class="header-info"
                >
                  <span class="header-env">{{ k === 'stag' ? '预发布环境' : '正式环境' }}</span>
                  <span class="header-env pl10">{{ data.is_deployed ? '已部署' : '未部署' }}</span>
                  <bk-button
                    v-if="data.is_deployed"
                    class="pl10"
                    theme="primary"
                    text
                    @click="handleItemClick(k, 'access')"
                  >
                    访问
                  </bk-button>
                  <bk-button
                    class="pl10"
                    theme="primary"
                    text
                    @click="handleItemClick(k, 'deploy')"
                  >
                    部署
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
                    <div class="info-env">
                      <div class="env-name">
                        {{ k === 'stag' ? '预发布环境' : '正式环境' }}
                      </div>
                      <div class="env-status pl10 pr320">
                        {{ data.is_deployed ? releaseInfoText(k) : '未部署' }}
                      </div>
                      <bk-button
                        v-if="data.is_deployed"
                        class="pl10"
                        theme="primary"
                        text
                        @click="handleItemClick(k, 'access')"
                      >
                        访问
                      </bk-button>
                      <bk-button
                        class="pl10"
                        theme="primary"
                        text
                        @click="handleItemClick(k, 'deploy')"
                      >
                        部署
                      </bk-button>
                    </div>

                    <!-- 折线图内容 部署了才展示内容-->
                    <div
                      v-if="data.is_deployed"
                      class="chart-warp"
                    >
                      <chart
                        :key="renderChartIndex"
                        ref="chart"
                        :options="envChartOption"
                        auto-resize
                        style="width: 100%; height: 220px; background: #1e1e21;"
                      />
                    </div>

                    <div
                      v-else
                      class="empty-warp"
                    >
                      <img
                        class="empty-img"
                        src="/static/images/empty-content.png"
                      >
                      <p class="empty-tips">
                        暂无数据
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </bk-collapse-item>
          </bk-collapse>
          <!-- <div
            class="middle over-new"
            data-test-id="summary_list_overNew"
          >
            <ul class="middle-list">
              <li style="margin-top: -5px;">
                <release-info
                  :key="appCode"
                  :app-code="appCode"
                  :environment="'stag'"
                  :app-deploy-info="releaseStatusStag"
                />
              </li>
              <li>
                <release-info
                  :key="appCode"
                  :app-code="appCode"
                  :environment="'prod'"
                  :app-deploy-info="releaseStatusProd"
                />
              </li>
            </ul>
          </div> -->

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
                style="width: 150px; font-weight: normal;"
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
                style="width: 150px; font-weight: normal;"
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
                style="width: 150px; font-weight: normal;"
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
                  <span class="header-title">{{ curEnvName === 'prod' ? $t('生产环境') : $t('预发布环境') }}{{ $t('资源用量') }}</span>
                  <span
                    v-if="curEnvName"
                    class="text"
                  >
                    <a
                      href="javascript: void(0);"
                      @click="goProcessView"
                    > {{ $t('查看详情') }} </a>
                  </span>
                </div>
                <!-- <div
                  v-if="isProcessDataReady && !isChartLoading"
                  class="search-chart-wrap"
                >
                  <bk-select
                    v-model="curProcessName"
                    style="width: 150px; background: #fff; font-weight: normal;"
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
                    style="width: 150px; background: #fff; font-weight: normal;"
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
                    style="width: 150px; background: #fff; font-weight: normal;"
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
                </div> -->
              </div>
              <div
                slot="content"
                class="middle bgc pl10 pr10"
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
                        <bk-dropdown-menu
                          ref="dropdownCpu"
                          trigger="click"
                          @show="dropdownShow"
                          @hide="dropdownHide"
                        >
                          <div
                            slot="dropdown-trigger"
                            class="dropdown-trigger-btn"
                          >
                            <span>{{ timeMap[curCpuActive] }}</span>
                            <div class="trigger-icon">
                              <i :class="['bk-icon icon-angle-down',{ 'icon-angle-up': isCpuDropdownShow }]" />
                            </div>
                          </div>
                          <div
                            slot="dropdown-content"
                            class="bk-dropdown-list"
                          >
                            <li>
                              <a
                                href="javascript:;"
                                :class="curCpuActive === '1h' ? 'active' : ''"
                                @click="triggerHandler('1h', 'cpu')"
                              > {{ $t('1小时') }} </a>
                            </li>
                            <li>
                              <a
                                href="javascript:;"
                                :class="curCpuActive === '24h' ? 'active' : ''"
                                @click="triggerHandler('24h', 'cpu')"
                              > {{ $t('24小时') }} </a>
                            </li>
                            <li>
                              <a
                                href="javascript:;"
                                :class="curCpuActive === '168h' ? 'active' : ''"
                                @click="triggerHandler('168h', 'cpu')"
                              >7天</a>
                            </li>
                          </div>
                        </bk-dropdown-menu>
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
                        <bk-dropdown-menu
                          ref="dropdownMem"
                          trigger="click"
                          @show="dropdownShowMem"
                          @hide="dropdownHideMem"
                        >
                          <div
                            slot="dropdown-trigger"
                            class="dropdown-trigger-btn"
                          >
                            <span>{{ timeMap[curMemActive] }}</span>
                            <div class="trigger-icon">
                              <i :class="['bk-icon icon-angle-down',{ 'icon-angle-up': isMemDropdownShow }]" />
                            </div>
                          </div>
                          <div
                            slot="dropdown-content"
                            class="bk-dropdown-list"
                          >
                            <li>
                              <a
                                href="javascript:;"
                                :class="curMemActive === '1h' ? 'active' : ''"
                                @click="triggerHandler('1h', 'mem')"
                              > {{ $t('1小时') }} </a>
                            </li>
                            <li>
                              <a
                                href="javascript:;"
                                :class="curMemActive === '24h' ? 'active' : ''"
                                @click="triggerHandler('24h', 'mem')"
                              > {{ $t('24小时') }} </a>
                            </li>
                            <li>
                              <a
                                href="javascript:;"
                                :class="curMemActive === '168h' ? 'active' : ''"
                                @click="triggerHandler('168h', 'mem')"
                              >7天</a>
                            </li>
                          </div>
                        </bk-dropdown-menu>
                      </div>
                      <strong class="title"> {{ $t('单位：MB') }} </strong>
                      <chart
                        ref="memLine"
                        :options="memLine"
                        auto-resize
                        style="width: 100%; height: 235px;"
                      />
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

        <!-- <div
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
        </div> -->
        <div
          class="overview-sub-fright"
          data-test-id="summary_content_detail"
        >
          <!-- <div
            v-if="curAppModule.web_config.runtime_type === 'custom_image'"
            class="fright-middle"
            data-test-id="summary_content_source"
          >
            <h3> {{ $t('镜像信息') }} </h3>
            <div>{{ $t('类型') }}: <span class="summary_text">{{ curAppModule.repo && curAppModule.repo.display_name }}</span></div>
            <div style="display: flex;">
              <p :class="[localLanguage === 'en' ? 'address-en' : 'address-zh-cn']">
                {{ $t('地址') }}:
              </p>
              <bk-popover
                :content="curAppModule.repo.repo_url"
                placement="bottom"
                class="urlText"
              >
                <p>{{ curAppModule.repo && curAppModule.repo.repo_url }}</p>
              </bk-popover>
            </div>
          </div> -->
          <!-- <div
            v-else
            class="fright-middle"
            data-test-id="summary_content_source"
          >
            <h3>
              {{ $t('应用源码') }}
              <dropdown
                v-if="sourceType === 'bk_svn'"
                :options="{ position: 'bottom right' }"
              >
                <button
                  slot="trigger"
                  class="btn-source-more ps-btn ps-btn-default ps-btn-xs"
                >
                  <i class="paasng-icon paasng-down-shape when-drop-hide" />
                  <i class="paasng-icon paasng-up-shape when-drop-show" />
                  <i class="paasng-icon paasng-cog" />
                </button>
                <div slot="content">
                  <ul class="ps-list-group-link spacing-x0">
                    <li>
                      <router-link
                        :to="{ name: 'serviceCode' }"
                        class="blue"
                      >
                        {{ $t('管理 SVN 账号') }}
                      </router-link>
                    </li>
                  </ul>
                </div>
              </dropdown>
            </h3>
            <p>
              {{ $t('开发语言：') }} <label class="ps-label primary"><span>{{ appDevLang }}</span></label>
            </p>
            <p v-if="curAppModule.source_origin === 1">
              {{ $t('已托管至：') }} <a
                target="_blank"
                :href="trunkUrl"
                class="blue svn-a"
              >{{ sourceTypeDisplayName }}</a>
            </p>
            <p v-else>
              {{ $t('源码包：') }} <router-link
                :to="{ name: 'appPackages' }"
                class="blue svn-a"
              >
                {{ $t('查看包版本') }}
              </router-link>
            </p>
            <div
              v-if="!isSmartApp"
              class="checkout-code"
            >
              <a
                v-if="curAppModule.web_config.templated_source_enabled && !curAppModule.repo.linked_to_internal_svn"
                class="ps-btn ps-btn-primary ps-btn-checkout-code"
                @click="downloadTemplate"
              > {{ $t('下载初始化模板代码') }} </a>
              <dropdown
                v-if="curAppModule.repo && curAppModule.repo.linked_to_internal_svn"
                :options="{ position: 'bottom right' }"
              >
                <bk-button
                  slot="trigger"
                  theme="primary"
                  style="width: 100%;"
                >
                  {{ $t('签出应用代码') }}
                  <i class="paasng-icon paasng-angle-down when-drop-hide" />
                  <i class="paasng-icon paasng-angle-up when-drop-show" />
                </bk-button>
                <div
                  slot="content"
                  class="code-checkout ps-dropdown"
                >
                  <template>
                    <h2> {{ $t('使用 SVN 签出代码') }} </h2>
                    <div class="checkout-content">
                      <p> {{ $t('使用 SVN 客户端签出该地址来获取应用代码：') }} </p>
                      <div class="spacing-x1 svn-input-container">
                        <input
                          id="urlInput"
                          v-model="trunkUrl"
                          readonly
                          class="svn-input ps-form-control"
                          type="text"
                          onfocus="this.select()"
                        >
                        <div class="svn-input-button-group">
                          <bk-popover
                            :content="$t('复制地址')"
                            style="float: left;"
                          >
                            <a
                              href="javascript:"
                              :class="['btn-c','btn-clipboard']"
                              @click.stop.prevent="copyUrl"
                            >
                              <i class="paasng-icon paasng-clipboard" />
                            </a>
                          </bk-popover>
                          <bk-popover :content="$t('签出代码')">
                            <a
                              :href="trunkUrl"
                              :class="['btn-c', 'btn-clipboard']"
                            >
                              <i class="paasng-icon paasng-download" />
                            </a>
                          </bk-popover>
                        </div>
                      </div>
                    </div>
                  </template>
                </div>
              </dropdown>
            </div>
          </div> -->

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
                      v-bk-tooltips="item.at"
                      class="tooltip-time"
                    >{{ item.at_friendly }}</span>
                  </p>
                  <p
                    v-bk-overflow-tips
                    class="dynamic-content"
                    style="-webkit-line-clamp: 2;-webkit-box-orient: vertical"
                  >
                    {{ $t('由') }}<span class="gruy">{{ item.operator ? item.operator : '—' }}</span>{{ item.operate }}
                  </p>
                </li>
                <li />
              </template>
              <template v-else>
                <table-empty empty />
              </template>
            </ul>
          </div>
        </div>
      </template>
    </paas-content-loader>
  </div>
</template>

<script>
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import 'echarts/lib/chart/line';
    import 'echarts/lib/component/tooltip';
    // import dropdown from '@/components/ui/Dropdown';
    // import releaseInfo from './comps/release-info';
    import moment from 'moment';
    import chartOption from '@/json/process-chart-option';
    import envChartOption from '@/json/analysis-chart-option';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import i18n from '@/language/i18n.js';
    import { formatDate } from '@/common/tools';

    const colorList = ['#3A84FF', '#89c1fa', '#a8d3ff', '#c9e4ff', '#e2f1ff'];

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

    const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
    const initStartDate = moment().subtract(6, 'days').format('YYYY-MM-DD HH:mm:ss');
    let timeRangeCache = '';

    export default {
        components: {
            'chart': ECharts
            // dropdown,
            // releaseInfo
            // appTopBar
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
                isLoading: true,
                trunkUrl: '',
                noLogs: true,
                releaseStatusStag: { ...DEFAULT_RELEASE_STATUS },
                releaseStatusProd: { ...DEFAULT_RELEASE_STATUS },
                resLength: 0,
                logsFiveHundred: [],
                operationsList: [],
                total: 0,
                userCount: 0,
                interval: 3600,
                current: -1,
                rangePickerInitialized: false,
                // 开发语言
                appDevLang: '',
                // 已托管至
                sourceType: '',
                cpuLine: chartOption.cpu,
                memLine: chartOption.memory,
                envChartOption: envChartOption.pv_uv,
                isChartLoading: true,
                dateTimeRange: [initStartDate, initEndDate],
                dateTimes: [initStartDate, initEndDate],
                curProcessName: '',
                processes: [],
                isProcessDataReady: true,
                dateShortCut: [
                    {
                        text: this.$t('最近 1 天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 60 * 1000 * 60 * 24);
                            return [start, end];
                        },
                        onClick () {
                            timeRangeCache = '1d';
                        }
                    },
                    {
                        text: this.$t('最近 3 天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 60 * 1000 * 60 * 24 * 3);
                            return [start, end];
                        },
                        onClick () {
                            timeRangeCache = '3d';
                        }
                    },
                    {
                        text: this.$t('最近 7 天'),
                        value () {
                            const end = new Date();
                            const start = new Date();
                            start.setTime(start.getTime() - 60 * 1000 * 60 * 24 * 7);
                            return [start, end];
                        },
                        onClick () {
                            timeRangeCache = '7d';
                        }
                    }
                ],
                timeMap: {
                    '1h': this.$t('1小时'),
                    '24h': this.$t('24小时'),
                    '168h': this.$t('7天')
                },
                curCpuActive: '1h',
                curMemActive: '1h',
                isCpuDropdownShow: false,
                isMemDropdownShow: false,

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
                envData: [{name: 'prod', label: '生产环境'}, {name: 'stag', label: '预发布环境'}],
                activeResource: '1',
                curModuleName: '',
                curEnvName: 'prod'
            };
        },
        computed: {
            sourceTypeDisplayName () {
                return this.curAppModule.repo && this.curAppModule.repo.display_name || '';
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
            }
        },
        created () {
            moment.locale(this.localLanguage);
        },
        mounted () {
            this.init();

            const end = new Date();
            const start = new Date();
            start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);

            this.dateRange.startTime = moment(start).format('YYYY-MM-DD');
            this.dateRange.endTime = moment(end).format('YYYY-MM-DD');
        },
        methods: {
            init () {
                this.loading = true;
                this.isChartLoading = true;
                this.isProcessDataReady = false;
                this.rangePickerInitialized = false;

                this.resLength = '';
                this.curProcessName = '';
                this.releaseStatusStag = { ...DEFAULT_RELEASE_STATUS };
                this.releaseStatusProd = { ...DEFAULT_RELEASE_STATUS };
                this.appDevLang = this.curAppModule.language;
                this.fetchAllDeployedInfos();
                this.getModuleOperations();
                if (this.curAppModule && this.curAppModule.repo) {
                    this.trunkUrl = this.curAppModule.repo.trunk_url || '';
                    this.sourceType = this.curAppModule.repo.source_type || '';
                }
                this.getOverViewData(); // 获取概览数据
            },
            dropdownShow () {
                this.isCpuDropdownShow = true;
            },
            dropdownHide () {
                this.isCpuDropdownShow = false;
            },
            dropdownShowMem () {
                this.isMemDropdownShow = true;
            },
            dropdownHideMem () {
                this.isMemDropdownShow = false;
            },
            triggerHandler (payload, type) {
                if (type === 'cpu') {
                    this.curCpuActive = payload;
                    this.showCurProcessResource(this.curEnv, 'cpu');
                    this.$refs.dropdownCpu.hide();
                } else {
                    this.curMemActive = payload;
                    this.showCurProcessResource(this.curEnv, 'mem');
                    this.$refs.dropdownMem.hide();
                }
                // this.showProcessResource(this.curEnv)
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
            getModuleOperations () {
                // 最新动态
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
                    this.loading = false;
                }

                // 资源视图优先展示生产环境
                this.$nextTick(() => {
                    this.showProcessLoading();
                    const prodProcess = this.releaseStatusProd.proc.find(item => item.status === this.$t('正在运行'));
                    const stagProcess = this.releaseStatusStag.proc.find(item => item.status === this.$t('正在运行'));
                    if (!this.releaseStatusProd.isEnvOfflined && prodProcess) {
                        this.curProcessName = prodProcess.name;
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
                console.log('type', type);
                // console.log('curAppModuleList', value, this.curEnv, this.curProcessName);
                // const process = this.curEnvProcesses.find(item => {
                //     return item.name === value;
                // });
                // if (process) {
                //     this.curMemActive = '1h';
                //     this.curCpuActive = '1h';
                //     this.curProcessName = process.name;
                    this.showProcessResource(this.curEnvName);
                // }
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

            showCurProcessResource (env, type) {
                const process = this.curEnvProcesses.find(item => {
                    return item.name === this.curProcessName;
                });

                if (process) {
                    if (type === 'cpu') {
                        const chart = this.$refs.cpuLine;
                        chart && chart.mergeOptions({
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
                    } else {
                        const memChart = this.$refs.memLine;
                        memChart && memChart.mergeOptions({
                            xAxis: [
                                {
                                    data: []
                                }
                            ],
                            series: []
                        });
                        if (memChart) {
                            memChart.resize();
                            memChart.showLoading({
                                text: this.$t('正在加载'),
                                color: '#30d878',
                                textColor: '#fff',
                                maskColor: '#FCFCFD'
                            });
                        }
                    }
                    this.getProcessMetric({
                        cpuChart: this.$refs.cpuLine,
                        memChart: this.$refs.memLine,
                        process: process,
                        env: env
                    }, type);
                }
            },

            /**
             * 从接口获取Metric 数据
             * @param {Object} conf 配置参数
             * @param {String} type
             */
            async getProcessMetric (conf, type = 'all') {
                console.log('this.curProcessName', this.curProcessName);
                // 请求数据
                const fetchData = (metricType) => {
                    const params = {
                        appCode: this.appCode,
                        moduleId: this.curModuleName,
                        env: conf.env,
                        process_type: this.curProcessName,
                        time_range_str: metricType === 'cpu' ? this.curCpuActive : this.curMemActive,
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
             * 图表初始化
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

                cpuRef && cpuRef.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: []
                });

                memRef && memRef.mergeOptions({
                    xAxis: [
                        {
                            data: []
                        }
                    ],
                    series: []
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

            /**
             * 选择自定义时间
             */
            handlerChange (dates) {
                this.dateTimes = dates;
            },

            /**
             * 选择自定义时间，并确定
             */
            handlerPickSuccess () {
                setTimeout(() => {
                    const startAsStr = this.dateTimes[0];
                    const endAsStr = this.dateTimes[1];
                    const timeShort = 'customized';
                    const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/statistics/pv/?start=${startAsStr}&end=${endAsStr}&interval=${this.interval}&pv_time_short=${timeShort}`;
                    this.chartSet(url, 'pieVisitChart', this.$t('应用视图'), colorList);
                }, 100);
            },

            /**
             * 通过快捷相对时间搜索
             */
            handlerShortcutClick () {
                setTimeout(() => {
                    const startAsStr = this.dateTimes[0];
                    const endAsStr = this.dateTimes[1];
                    const timeShort = timeRangeCache;
                    const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/statistics/pv/?start=${startAsStr}&end=${endAsStr}&interval=${this.interval}&pv_time_short=${timeShort}`;
                    this.chartSet(url, 'pieVisitChart', this.$t('应用视图'), colorList);
                }, 100);
            },
            copyUrl () {
                // 之前的复制插件绑定的点击事件和阻止隐藏事件冒泡冲突，现有方法原生js改写，方法执行时阻止默认事件及冒泡
                document.getElementById('urlInput').onfocus();
                if (document.execCommand('copy', false, null)) {
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('地址复制成功！')
                    });
                } else {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('地址复制失败！')
                    });
                }
            },
            downloadTemplate () {
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/sourcectl/init_template/`;
                this.$http.post(url).then(resp => {
                    const s3Address = resp.downloadable_address;
                    const a = document.createElement('a');
                    a.href = s3Address;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                }, resp => {
                    this.$paasMessage({
                        theme: 'error',
                        message: resp.detail
                    });
                });
            },

            // 新版本概览

            // 概览数据接口
            async getOverViewData () {
                try {
                    this.overViewData = await this.$store.dispatch('overview/getOverViewInfo', {appCode: this.appCode});
                    // 默认展开第一个
                    if (this.overViewData) {
                        this.activeName = Object.keys(this.overViewData)[0];
                        this.curModuleName = Object.keys(this.overViewData)[0]; // 模块下拉默认选中第一个
                        setTimeout(() => {
                            this.$nextTick(() => {
                                this.handleCollapseClick(Object.keys(this.overViewData));
                            });
                        }, 1500);
                    }
                } catch (error) {
                    console.log(error);
                }
            },

            handleCollapseClick (data) {
                if (data.length) {
                    this.$nextTick(() => {
                        this.showInstanceChart();
                    });
                }
            },

            /**
             * 显示实例指标数据
             */
             showInstanceChart (instance, processes) {
                 const chartRef = this.$refs.chart;
                 console.log('chartRef', chartRef);

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

                    this.getChartData(this.envData[index].name);
                });
            },

            async getChartData (env) {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    console.log('this.curEnv', this.curEnv);
                    console.log('this.dateRange', this.dateRange);
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

                    console.log('params', params);

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
                    console.log('this.chartDataCache', this.chartDataCache);
                    this.renderEnvChart();
                } catch (e) {
                    console.log('e', e);
                    const chartRef = this.$refs.chart;
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
             renderEnvChart () {
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

                this.envChartOption.xAxis[0].data = xAxisData;
                this.envChartOption.series = series;
                setTimeout(() => {
                    const chartRef = this.$refs.chart;
                    chartRef && chartRef.forEach((refItem) => {
                        refItem && refItem.mergeOptions(this.envChartOption, true);
                        refItem && refItem.resize();
                        refItem && refItem.hideLoading();
                    });
                }, 1000);
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
            }

        }
    };
</script>

<style scoped lang="scss">
    #summary {
        .visited-span span input {
            width: 180px;
        }

        .visited-span span input,
        .visited-span span input:focus {
            border: none;
            outline: none;
            box-shadow: none;
            background: #fcfcfc;
        }

        .visited-span span.on input[type="text"],
        .visited-span span:hover input {
            background: #fcfcfc;
            cursor: pointer
        }

        .middle.http {
            border-bottom: none;
        }
    }

    .search-chart-wrap {
        background: #F5F7FA !important;
        float: right;
    }

    .bk-dropdown-menu {
        float: right;
        margin: 10px 10px 0 0;
    }
    .dropdown-trigger-btn {
        height: 32px;
        width: 80px;
        line-height: 32px;
        border-radius: 2px;
        color: #63656e;
        font-weight: normal;
        text-align: center;
        cursor: pointer;
        .trigger-icon {
            display: inline-block;
            background: #f0f1f5;
            text-align: center;
            width: 28px;
            height: 20px;
            line-height: 18px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
        }
    }
    .bk-dropdown-list {
        li {
            display: block;
            color: #63656e;
            a {
                font-weight: normal;
                &.active {
                    background-color: #eaf3ff;
                    color: #3a84ff;
                }
            }
        }
    }

    .summary-chart-box {
        flex: 1 1 50%;
        .type-title {
            line-height: 48px;
            color: #333;
        }
    }

    .over-new {
        min-height: 390px;
    }

    .over-new .middle-list li {
        border-bottom: 0;
    }

    .over-new .middle-list li:first-child {
        border-bottom: 1px solid #e6e9ea;
    }

    .over-new .middle-list dd {
        padding-left: 15px;
    }

    .over-new .middle-list dd p {
        padding-left: 0;
    }

    .over-new .middle-list dd:first-child p {
        padding-left: 25px;
    }

    .over-new .middle-list dd:first-child {
        width: 340px;
        padding-left: 25px;
    }

    .over-new .middle-list dl:after {
        left: 365px;
        margin-left: 0;
    }

    .t-center {
        text-align: center;
    }

    .noDeploy .grayPanel p {
        color: #ccc;
    }

    .disabledButton,
    .disabledButton:hover {
        background: #e5e5e5;
        color: #fff;
        border: 1px solid #e5e5e5;
        cursor: default;
    }

    .disabledButton:hover {
        cursor: not-allowed
    }

    .middle h3 span.text {
        font-size: 12px;
        color: #999;
        padding: 0 5px;
        font-weight: normal
    }

    .overview-middle {
        display: flex;
        padding: 16px 24px;
        .summary-wrapper,
        .coding {
            flex: 1;
        }

        .header-warp{
            display: flex;
            .paasng-down-shape{
                float: left !important;
                line-height: 45px !important;
                color: #63656e !important;
            }
            .header-title{
                font-weight: 700;
                font-size: 14px;
                color: #313238;
            }
            .header-env{
                font-size: 12px;
                color: #979BA5;
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
        .content-warp{
            display: flex;
            align-items: center;
            .content-info{
                padding: 12px 0px;
                flex: 1;
                .info-env {
                    display: flex;
                    align-items: center;
                    .env-name{
                        color: #313238;
                    }
                    .env-status{
                        font-size: 12px;
                        color: #979BA5;
                    }
                }
            }
            .content-info:nth-of-type(1) {
                padding-right: 10px;
                border-right: solid 1px #F5F7FA;
            }
            .content-info:nth-of-type(2) {
                padding-left: 10px;
            }
            .empty-warp{
                text-align: center;
                height: 220px;
                .empty-img{
                    margin-top: 20px;
                }
                .empty-tips{
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

    .checkout-content {
        padding: 10px 20px;
        line-height: 20px;
        font-size: 13px;
        color: #7b7d8a;
    }

    .input-container {
        padding: 14px 0 23px 0;
    }

    input.input-form-control {
        color: #7b7d8a;
        font-size: 12px;
        cursor: initial;
        line-height: 30px;
        padding: 0 10px;
        width: 234px;
        border: solid 1px #ccc;
    }

    input.input-form-control:focus {
        outline: none;
        border-color: #3a84ff;
    }

    .btn-clipboard {
        width: 30px;
        height: 30px;
        border: solid 1px #ccc;
        border-left: none;
        text-align: center;
        line-height: 30px;
        cursor: pointer;
        color: #6c6c6c;
        margin: 0;
        padding: 0;
    }

    .btn-clipboard.on {
        background: #f6f6f6
    }

    .btn-clipboard i {
        font-size: 14px;
        position: relative;
        padding: 8px;
    }

    .paasng-icon.paasng-download:hover,
    .paasng-icon.paasng-clipboard:hover {
        color: #3A84FF
    }

    .paasng-angle-up,
    .paasng-angle-down {
        padding-left: 6px;
        transition: all .5s;
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
        margin: 16px 10px 16px 0
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
        margin: 16px 10px 16px 0
    }

    .dateSelector {
        input {
            color: #666;
        }
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
        text-overflow: ellipsis;
        white-space: normal;
        word-break: break-all;
        display: -webkit-box;
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

    .amount-number {
        position: absolute;
        left: 50%;
        margin-left: -180px;
        z-index: 99;
        top: 0;
    }

    .amount {
        width: 150px;
        display: inline-block;
        margin: 0 20px;
    }

    .amount span {
        display: block;
        text-align: center;
    }

    .amount span.number1 {
        font-size: 36px;
        font-family: "PingFang";
        line-height: 40px;
    }

    .amount span.number2 {
        font-size: 12px;
        line-height: 24px;
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
        .overview-warp{
            display: flex;
            padding: 25px 16px;
            border: 1px solid #DCDEE5;
            border-radius: 2px;
            font-size: 12px;
            .over-fs{
                font-weight: 700;
                font-size: 24px;
                color: #313238;
            }
            .desc-text{
                padding-top: 13px;
            }
            .info {
                padding-right: 90px;
                border-right: 1px solid #F5F7FA;
                .type-desc{
                    line-height: 20px;
                }
            }
            .process{
                padding-right: 48px;
                border-right: 1px solid #F5F7FA;
            }
            .img-warp {
                width: 48px;
                height: 48px;
                background: #F0F5FF;
                border-radius: 4px;
                text-align: center;
                img{
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
        content: "";
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
        background: #FAFBFD;
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
    .flex{
        display: flex;
    }
    .flex_1 {
        flex: 1;
    }
    .align-center{
        align-items: center;
    }
    .justify-center{
        justify-content: center;
    }
    .justify-between{
        justify-content: space-between;
    }
</style>

<!-- 折叠板内部样式 -->
<style lang="scss">
    .paas-module-warp{
        .paas-module-item {
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
