<template>
  <div
    class="index-main"
    @click="closeOpen"
  >
    <div
      v-if="!userHasApp"
      class="paas-banner"
    >
      <div class="wrap">
        <div class="paas-text">
          <img
            src="/static/images/yahei-5.png"
            class="appear"
          >
        </div>
        <router-link
          :to="{ name: 'createApp' }"
          class="paas-banner-button appear"
        >
          {{ homePageStaticInfo.data.banner_btn.text }}
        </router-link>
        <router-link
          v-if="userFeature.MGRLEGACY"
          :to="{ name: 'appLegacyMigration' }"
          class="btn-link spacing-h-x2"
        >
          {{ $t('迁移旧版应用') }}
        </router-link>
        <router-link
          v-if="isShowOffAppAction"
          :to="{ name: 'myApplications', query: { include_inactive: true } }"
          style="margin-left: 0;"
          class="btn-link spacing-h-x2"
        >
          {{ $t('查看已下架应用') }}
        </router-link>
      </div>
    </div>
    <!-- 最近操作 start -->
    <div
      v-if="userHasApp"
      class="paas-content white"
    >
      <div class="wrap">
        <paas-content-loader
          :is-loading="isLoading"
          placeholder="index-loading"
          :offset-top="0"
          :height="378"
          data-test-id="developer_header_content"
        >
          <div
            class="paas-operation-tit"
            data-test-id="developer_header_operationTit"
          >
            <h2> {{ $t('最近操作') }} </h2>
            <div class="fright">
              <router-link
                :to="{ name: 'createApp' }"
                class="paas-operation-icon"
              >
                <i class="paasng-icon paasng-plus" /> {{ $t('创建应用') }}
              </router-link>
            </div>

            <div
              v-if="userFeature.MGRLEGACY"
              class="fright legacy-links"
            >
              <a
                :href="GLOBAL.LINK.V2_APP_SUMMARY"
                target="_blank"
              >
                <i class="paasng-icon paasng-chain" /> {{ $t('管理旧版应用') }} </a>
              <router-link
                :to="{ name: 'appLegacyMigration' }"
                class="btn-link spacing-h-x2"
              >
                {{ $t('一键迁移') }}
              </router-link>
            </div>
          </div>
          <div data-test-id="developer_list_sectionApp">
            <ul
              v-if="records.length && !isLoading"
              class="paas-operation"
            >
              <li
                v-for="(recordItem, index) in records"
                :key="index"
                class="clearfix"
              >
                <div class="paas-operation-section section1">
                  <template v-if="recordItem.engine_enabled">
                    <router-link :to="{ name: 'appSummary', params: { id: recordItem.appcode, moduleId: recordItem.defaultModuleId } }">
                      <img
                        :src="recordItem.applogo"
                        width="38px"
                        height="38px"
                        class="fleft"
                        style="border-radius: 4px"
                      ><span
                        v-bk-tooltips="recordItem.appname"
                        class="spantext"
                      >{{ recordItem.appname }}</span>
                    </router-link>
                  </template>
                  <template v-else>
                    <router-link :to="{ name: 'appSummary', params: { id: recordItem.appcode, moduleId: recordItem.defaultModuleId } }">
                      <img
                        :src="recordItem.applogo"
                        width="38px"
                        height="38px"
                        class="fleft"
                        style="border-radius: 4px"
                      ><span
                        v-bk-tooltips="recordItem.appname"
                        class="spantext"
                      >{{ recordItem.appname }}</span>
                    </router-link>
                  </template>
                </div>
                <div class="paas-operation-section time-section">
                  <em v-bk-tooltips="recordItem.time">{{ smartTime(recordItem.time,'fromNow') }}</em>
                </div>
                <div class="paas-operation-section section2 section-wrapper">
                  <span
                    v-if="recordItem.represent_info.props.display_module && recordItem.represent_info.props.provide_links"
                    class="module-name"
                  >{{ recordItem.represent_info.module_name + $t('模块') }}</span>
                  <span
                    v-bk-tooltips.bottom="recordItem.type"
                    class="bottom-middle text-style"
                    :title="recordItem.type"
                  >{{ recordItem.type }}</span>
                </div>

                <div
                  v-if="!recordItem.stag.deployed && !recordItem.prod.deployed"
                  class="paas-operation-section section3"
                >
                  <button
                    v-if="recordItem.represent_info.props.provide_links"
                    v-bk-tooltips="$t('无可用地址')"
                    class="ps-btn ps-btn-disabled-new"
                  >
                    {{ $t('访问模块') }} <i class="paasng-icon paasng-angle-down" />
                  </button>
                </div>

                <div
                  v-if="recordItem.represent_info.props.provide_links && (recordItem.stag.deployed || recordItem.prod.deployed)"
                  :class="['paas-operation-section','section3',{ 'open': activeVisit === index }]"
                >
                  <div
                    :class="['section-box']"
                  >
                    <a
                      class="section-button-new"
                      href="javascript:"
                      @click.stop.prevent="visitOpen($event,index)"
                    > {{ $t('访问模块') }} <i class="paasng-icon paasng-angle-down" /></a>
                    <div class="section-button-down">
                      <a
                        v-if="recordItem.stag.deployed"
                        target="_blank"
                        :href="recordItem.stag.url"
                      >
                        {{ $t('预发布环境') }}
                      </a>
                      <a
                        v-if="recordItem.prod.deployed"
                        target="_blank"
                        :href="recordItem.prod.url"
                      >
                        {{ $t('生产环境') }}
                      </a>
                    </div>
                  </div>
                </div>

                <div class="paas-operation-section fright">
                  <template v-if="recordItem.represent_info.props.provide_actions">
                    <bk-button
                      theme="primary"
                      text
                      style="margin-right: 6px; height:38px"
                      @click="toDeploy(recordItem)"
                    >
                      {{ $t('部署') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      style="margin-right: 10px;height: 38px"
                      @click="toViewLog(recordItem)"
                    >
                      {{ $t('查看日志') }}
                    </bk-button>
                  </template>
                  <template v-else>
                    <bk-button
                      theme="primary"
                      text
                      style="margin-right: 10px;"
                      @click="toCloudAPI(recordItem)"
                    >
                      {{ $t('申请云API权限') }}
                    </bk-button>
                  </template>
                  <!-- <a href="javascript:" target="_blank">权限管理</a> -->
                </div>
              </li>
              <li
                v-if="appCount < 4"
                class="clearfix lessthan"
              >
                <router-link :to="{ name: 'createApp' }">
                  {{ $t('点击创建应用，探索蓝鲸 PaaS 平台的更多内容！') }}
                </router-link>
              </li>
            </ul>
            <div
              v-else
              class="paas-operation"
              data-test-id="developer_list_empty"
            >
              <div class="ps-no-result">
                <table-empty
                  :empty-title="$t('暂无应用')"
                  empty
                />
              </div>
            </div>
            <router-link
              v-if="appCount >= 4"
              :to="{ name: 'myApplications' }"
              class="read-more"
            >
              {{ $t('查看更多应用') }}
            </router-link>
          </div>
        </paas-content-loader>
      </div>
    </div>
    <!-- 最近操作 end -->

    <!-- 中间部分 start -->
    <div
      class="paas-content"
      data-test-id="developer_content_wrap"
    >
      <div class="wrap">
        <div
          v-if="userHasApp"
          class="appuser"
        >
          <!-- 图表 start -->
          <div
            class="paas-content-boxpanel"
            data-test-id="developer_content_highCharts"
          >
            <div class="paas-highcharts fleft">
              <paas-content-loader
                :is-loading="loading1"
                background-color="#f5f6f9"
                data-test-id="developer_highCharts_left"
              >
                <div style="width: 100%; height: 275px;">
                  <chart
                    id="viewchart"
                    style="width: 100%; height: 275px;"
                  />
                  <div
                    v-if="chartList1.length === 0"
                    class="ps-no-result"
                    style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"
                  >
                    <table-empty empty />
                  </div>
                </div>
              </paas-content-loader>
            </div>
            <div class="paas-highcharts fright">
              <paas-content-loader
                :is-loading="loading2"
                background-color="#f5f6f9"
                data-test-id="developer_highCharts_right"
              >
                <div style="width: 100%; height: 275px;">
                  <chart
                    id="visitedchart"
                    style="width: 100%; height: 275px;"
                  />
                  <div
                    v-if="chartList2.length === 0"
                    class="ps-no-result"
                    style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"
                  >
                    <table-empty empty />
                  </div>
                </div>
              </paas-content-loader>
            </div>
          </div>
          <!-- 图表 end -->

          <!-- 资源使用情况 start -->
          <div
            class="paas-content-boxpanel bk-fade-animate hide"
            data-test-id="developer_list_resource"
          >
            <ul class="paas-resource">
              <li>
                <div class="paas-resource-title">
                  Mysql
                </div>
                <div class="paas-resource-text">
                  <p class="resource-text">
                    <span>1024</span>/MB
                  </p>
                  <p> {{ $t('资源使用量') }} </p>
                </div>
              </li>
              <li>
                <div class="paas-resource-title">
                  Redis
                </div>
                <div class="paas-resource-text">
                  <p class="resource-text">
                    <span>215</span>/MB
                  </p>
                  <p> {{ $t('资源使用量') }} </p>
                </div>
              </li>
              <li>
                <div class="paas-resource-title">
                  {{ $t('对象储存') }}
                </div>
                <div class="paas-resource-text">
                  <p class="resource-text">
                    <span>852</span>/MB
                  </p>
                  <p> {{ $t('资源使用量') }} </p>
                </div>
              </li>
            </ul>
          </div>
          <!-- 资源使用情况 end -->
        </div>
        <!-- 新手入门&使用指南 start -->
        <div
          class="paas-content-boxpanel"
          data-test-id="developer_list_info"
        >
          <div class="paas-modular fleft">
            <h2 class="paas-modular-title">
              {{ $t('新手入门') }}
            </h2>
            <div
              v-for="(item, index) in homePageStaticInfo.data.new_user.list"
              :key="index"
              class="paas-question"
            >
              <a
                :href="item.url"
                target="_blank"
                class="paas-ask"
              >{{ item.title }}</a>
              <p>{{ item.info }}</p>
            </div>
          </div>
          <div class="paas-modular fright">
            <h2 class="paas-modular-title">
              {{ $t('使用指南') }}
            </h2>
            <div
              v-for="(item, index) in homePageStaticInfo.data.guide_info.list"
              :key="index"
              class="paas-question"
            >
              <a
                :href="item.url"
                target="_blank"
                class="paas-ask"
              >
                {{ item.title }}
                <i
                  v-if="item.icon"
                  class="paasng-icon paasng-play"
                />
              </a>
              <p>{{ item.info }}</p>
            </div>
          </div>
        </div>
        <!-- 新手入门&使用指南 end -->
        <!-- 了解我们的服务 start -->
        <div
          class="paas-content-boxpanel bk-fade-animate"
          data-test-id="developer_list_service"
        >
          <h2 class="paas-modular-title center">
            {{ $t('了解我们的服务') }}
          </h2>
          <div class="paas-service">
            <ul class="paas-service-list">
              <li
                v-for="(item, index) in serviceInfo"
                :key="index"
                :class="{ 'active': index === curServiceIndex }"
                @click="changeService(index)"
              >
                <i :class="['paas-service-icon', 'icon' + (index + 1)]" />
                <span class="paas-service-text">{{ item.title }}</span>
              </li>
            </ul>
            <div
              class="paas-service-main"
              data-test-id="developer_list_main"
            >
              <div :class="['paas-service-content', 'showCon' + curServiceIndex]">
                <!-- 开发 -->
                <div
                  v-for="(service, index) in serviceInfo"
                  :key="index"
                  class="content-panel"
                >
                  <dl
                    v-for="(item, serviceIndex) in service.items"
                    :key="serviceIndex"
                  >
                    <dt>
                      <a
                        v-if="item.url === 'javascript:;'"
                        target="_blank"
                        :href="GLOBAL.DOC.API_HELP"
                      >
                        {{ item.text }}
                      </a>
                      <router-link
                        v-else
                        target="_blank"
                        :to="'/developer-center/service/' + item.url"
                      >
                        {{ item.text }}
                      </router-link>
                    </dt>
                    <dd>{{ item.explain }}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 了解我们的服务 end -->
      </div>
    </div>
  </div>
</template>

<script>
    import auth from '@/auth';
    import { bus } from '@/common/bus';
    import ECharts from 'vue-echarts/components/ECharts.vue';
    import echarts from 'echarts';
    import 'echarts/lib/chart/bar';
    import 'echarts/lib/component/tooltip';
    import { psIndexInfo, psHeaderInfo } from '@/mixins/ps-static-mixin';

    export default {
        components: {
            'chart': ECharts
        },
        mixins: [psIndexInfo, psHeaderInfo],
        data () {
            return {
                userHasApp: false,
                isNewUser: global.isUser,
                serviceInfo: [], // 服务列表
                curServiceIndex: 0,
                flag: false,
                activeVisit: -1,
                appCount: 0,
                records: [], // 操作记录
                isLoading: true,
                loading1: true,
                loading2: true,
                colorList1: ['#3a84ff', '#89c1fa', '#a8d3ff', '#c9e4ff', '#e2f1ff'],
                colorList2: ['#ccdff3', '#cfeedc', '#f7eedb', '#fae5d5', '#fcc8c8'],
                isnull: false,
                chartList1: [],
                chartList2: [],
                defaultImg: '/static/images/default_logo.png',
                isShowOffAppAction: false,
                type: 'default'
            };
        },
        computed: {
            userFeature () {
                return this.$store.state.userFeature;
            }
        },
        // Get userHasApp before render
        beforeRouteEnter (to, from, next) {
            const promise = auth.requestHasApp();
            promise.then((userHasApp) => {
                next(vm => {
                    vm.setUserHasApp(userHasApp);
                    if (!userHasApp) {
                        auth.requestOffApp()
                            .then(flag => {
                                vm.isShowOffAppAction = flag;
                            });
                    }
                });
            });
        },
        beforeRouteUpdate (to, from, next) {
            const promise = auth.requestHasApp();
            promise.then((userHasApp) => {
                this.setUserHasApp(userHasApp);
                next(() => {
                    if (!userHasApp) {
                        auth.requestOffApp()
                            .then(flag => {
                                this.isShowOffAppAction = flag;
                            });
                    }
                });
            });
        },
        created () {
            // 了解我们的服务和头部导航同步
            const results = [];
            this.headerStaticInfo.list.subnav_service.forEach(item => {
                if (!item.title) {
                    results.push(...item.items);
                } else {
                    results.push(item);
                }
            });
            this.serviceInfo = results;

            // 获取最近四次操作记录
            this.$http.get(BACKEND_URL + '/api/bkapps/applications/lists/latest/').then((response) => {
                const resData = response;

                this.appCount = resData.results.length;

                resData.results.forEach((item) => {
                    const appinfo = item.application;

                    this.records.push({
                        'applogo': appinfo.logo_url || '/static/images/default_logo.png',
                        'appname': appinfo.name,
                        'appcode': appinfo.code,
                        'time': item.at,
                        'type': item.operate,
                        'stag': item.represent_info.props.provide_links ? item.represent_info.links.stag : {},
                        'prod': item.represent_info.props.provide_links ? item.represent_info.links.prod : {},
                        'engine_enabled': appinfo.config_info.engine_enabled,
                        'defaultModuleId': item.represent_info.module_name,
                        'represent_info': item.represent_info
                    });
                });
                this.isLoading = false;
            });
            this.chartSet({
                type: 'app_groups',
                url: BACKEND_URL + '/api/bkapps/applications/statistics/group_by_state/',
                id: 'viewchart',
                title: this.$t('我的应用(模块)分布'),
                yAxisName: this.$t('单位（个）'),
                colorList: this.colorList1
            });
            this.chartSet({
                type: 'pv',
                url: BACKEND_URL + '/api/bkapps/applications/statistics/pv/top5/?limit=5&days_before=30',
                id: 'visitedchart',
                title: this.$t('访问量 Top 5 (最近 30 天)'),
                yAxisName: this.$t('单位（次）'),
                colorList: this.colorList2
            });
        },
        methods: {
            async toDeploy (recordItem) {
                const url = `${BACKEND_URL}/api/bkapps/applications/${recordItem.appcode}/`;
                try {
                    const res = await this.$http.get(url);
                    this.type = res.application.type;
                    this.$router.push({
                        name: this.type === 'cloud_native' ? 'cloudAppDeploy' : 'appDeploy',
                        params: {
                            id: recordItem.appcode
                        }
                    });
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                }
            },

            toViewLog (recordItem) {
                this.$router.push({
                    name: 'appLog',
                    params: {
                        id: recordItem.appcode,
                        moduleId: recordItem.represent_info.module_name || 'default'
                    },
                    query: {
                        tab: 'structured'
                    }
                });
            },

            toCloudAPI (recordItem) {
                this.$router.push({
                    name: 'appCloudAPI',
                    params: {
                        id: recordItem.appcode
                    }
                });
            },

            chartSet ({ type, url, id, title, colorList, yAxisName }) {
                this.$http.get(url).then((response) => {
                    const resData = response;

                    const chatData = {
                        countList: [],
                        nameList: []
                    };

                    if (type === 'app_groups') {
                        this.loading1 = false;
                        for (let i = 0; i < resData.data.length; i++) {
                            chatData.countList.push(resData.data[i].count);
                            chatData.nameList.push(resData.data[i].name);
                        }
                        this.chartList1 = resData.data;
                    } else if (type === 'pv') {
                        this.loading2 = false;
                        for (let i = 0; i < resData.data.length; i++) {
                            chatData.countList.push(resData.data[i].pv);
                            chatData.nameList.push(resData.data[i].application_name);
                        }
                        this.chartList2 = resData.data;
                    }

                    this.$nextTick(() => {
                        const chart = echarts.init(document.getElementById(id));
                        let yAxisNameBackup = '';
                        if (id === 'viewchart') {
                            yAxisNameBackup = this.chartList1.length ? yAxisName : '';
                        } else {
                            yAxisNameBackup = this.chartList2.length ? yAxisName : '';
                        }
                        chart.setOption({
                            color: '#666666',
                            title: {
                                text: title,
                                x: 'center',
                                y: 'top',
                                textStyle: {
                                    color: '#333333',
                                    fontStyle: 'normal',
                                    fontWeight: 'normal',
                                    fontFamily: 'Helvetica Neue, Helvetica, Tahoma, Arial, Microsoft Yahei, 微软雅黑, Hiragino Sans GB, PingFang SC, STHeiTi, sans-serif',
                                    fontSize: 16
                                }
                            },
                            tooltip: {
                                trigger: 'item',
                                axisPointer: { // 坐标轴指示器，坐标轴触发有效
                                    type: 'shadow' // 默认为直线，可选为：'line' | 'shadow'
                                }
                            },
                            xAxis: [
                                {
                                    axisTick: { show: false },
                                    type: 'category',
                                    data: chatData.nameList,
                                    splitArea: { show: false }, // 保留网格区域
                                    splitLine: { // 分隔线
                                        show: false // 默认显示，属性show控制显示与否
                                    },
                                    axisLine: {
                                        show: false

                                    },
                                    axisLabel: {
                                        show: true,
                                        rotate: 0,
                                        interval: 'auto',
                                        textStyle: {
                                            color: '#666666',
                                            fontFamily: 'Helvetica Neue, Helvetica, Tahoma, Arial, Microsoft Yahei, 微软雅黑, Hiragino Sans GB, PingFang SC, STHeiTi, sans-serif'
                                        },
                                        formatter: params => {
                                            let newParamsName = '';
                                            const paramsNameNumber = params.length; // 字符总长度
                                            const provideNumber = 5; // 每行显示的字符数量
                                            const maxLenNumber = 9; // 最多两行显示的字符最大数量
                                            if (paramsNameNumber > provideNumber) {
                                                if (paramsNameNumber > maxLenNumber) {
                                                    newParamsName = params.substring(0, provideNumber) + '\n' + params.substring(provideNumber, maxLenNumber) + '...';
                                                } else {
                                                    newParamsName = params.substring(0, provideNumber) + '\n' + params.substring(provideNumber, paramsNameNumber);
                                                }
                                            } else {
                                                newParamsName = params;
                                            }
                                            return newParamsName;
                                        }
                                    }
                                }
                            ],
                            yAxis: [
                                {
                                    name: yAxisNameBackup,
                                    allowDecimals: false,
                                    axisTick: { show: false },
                                    type: 'value',
                                    splitArea: { show: false },
                                    splitLine: { // 分隔线
                                        show: true, // 默认显示，属性show控制显示与否
                                        lineStyle: { // 属性lineStyle（详见lineStyle）控制线条样式
                                            color: ['#e9edee'],
                                            width: 1,
                                            type: 'solid'
                                        }
                                    },
                                    axisLine: {
                                        show: false,
                                        lineStyle: {
                                            color: '#999999',
                                            type: 'solid',
                                            width: '0'
                                        }
                                    },
                                    axisLabel: {
                                        show: true,
                                        textStyle: {
                                            color: '#999999',
                                            fontFamily: 'Helvetica Neue, Helvetica, Tahoma, Arial, Microsoft Yahei, 微软雅黑, Hiragino Sans GB, PingFang SC, STHeiTi, sans-serif'
                                        }
                                    }
                                }
                            ],
                            series: [
                                {

                                    type: 'bar',
                                    data: chatData.countList,
                                    barWidth: 40,
                                    itemStyle: {
                                        normal: {
                                            color: (params) => {
                                                return colorList[params.dataIndex];
                                            },
                                            type: 'line',
                                            barBorderRadius: [8, 8, 0, 0],
                                            lineStyle: {
                                                color: '#3a84ff',
                                                type: 'dashed'
                                            }

                                        },
                                        emphasis: {
                                            barBorderRadius: [8, 8, 0, 0]
                                        }
                                    }
                                }
                            ]
                        });
                    });
                });
            },
            setUserHasApp (value) {
                this.userHasApp = value;
                if (!value) {
                    bus.$emit('page-header-be-transparent');
                }
            },
            // 服务列表切换
            changeService (index) {
                this.curServiceIndex = index;
            },
            // 访问按钮展开
            visitOpen (event, index) {
                if (event.currentTarget.parentNode.classList.contains('disabledBox')) return;
                const isopen = event.currentTarget.parentNode.parentNode.classList.contains('open');
                if (isopen) {
                    this.activeVisit = -1;
                } else {
                    this.activeVisit = index;
                }
            },
            closeOpen () {
                this.activeVisit = -1;
            }

        }
    };
</script>
<style lang="scss" scoped>
    @import '~@/assets/css/mixins/ellipsis.scss';
    .paas-highcharts {
        width: 50%;
        position: relative;

        h3 {
            text-align: center;
            position: absolute;
            width: 100%;
            font-size: 16px;
            font-weight: normal;
        }
    }

    .paas-banner {
        width: 100%;
        height: 420px;
        background: url(/static/images/banner.jpg) top center no-repeat;
        text-align: center;
        background-color: #191828;

        .paas-text {
            text-align: center;
            font-size: 24px;
            line-height: 40px;
            color: #fff;
            padding-top: 172px;
        }

        .paas-banner-button {
            display: inline-block;
            color: #fff;
            font-size: 18px;
            line-height: 54px;
            text-align: center;
            width: 220px;
            border-radius: 27px;
            background: #3976e4;
            margin: 47px auto;
            transition: all .5s;

            &:hover {
                background: #3369cc;
                transtion: all .5s;
            }
        }
    }

    .paas-operation-section {
        &.time-section {
            padding: 0;
            width: 100px;
            @include ellipsis;
        }
        &.section1 {
            width: 210px;

            a {
                padding-left: 11px;
                color: #63656e;
                display: inline-block;
                overflow: hidden;
                line-height: 38px;
                vertical-align: middle;
                text-overflow: ellipsis;

                .spantext {
                    padding-left: 10px;
                    max-width: 138px;
                    font-weight: bold;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    display: inline-block;
                }

                &:hover {
                    color: #3a84ff
                }
            }
        }

        &.section2 {
            width: 350px;
            text-align: left;

            span {
                color: #63656e;
                &.module-name {
                    margin-right: 3px;
                    font-weight: bold;
                }
            }

            // 对齐显示操作
            em {
                display: inline-block;
            }
        }

        &.fright {
            float: right;

            a {
                padding: 0 20px;
                font-size: 14px;
            }
        }
    }

    .paas-operation-tit {
        padding: 10px 0 0 0;
        color: #333;
        line-height: 36px;
        font-size: 16px;

        h2 {
            font-size: 18px;
            font-weight: normal;
            display: inline-block;
            color: #313238;
            line-height: 24px;
        }

        .paas-operation-icon {
            color: #fff;
            font-size: 14px;
            height: 36px;
            line-height: 36px;
            width: 120px;
            text-align: center;
            margin-left: 19px;
            border-radius: 2px;
            background: #3a84ff;
            transition: all .5s;

            &:hover {
                background: #4b9cf2;
            }

            .paasng-icon {
                margin-right: 5px;
            }
        }
    }

    .paas-operation {
        padding: 2px 0 0 0;

        li {
            margin: 10px 0 0 0;
            padding: 12px 0;
            height: 62px;
            border: solid 1px #dcdee5;
            line-height: 38px;
            color: #63656e;
            border-radius: 2px;

            &:hover {
                box-shadow: 0 4px 5px -3px #dcdee5;
            }

            &.lessthan {
                border: dashed 1px #e9edee;
                text-align: center;
                color: #ccc;
                font-size: 14px;
                transition: all .5s;

                &:hover {
                    border: dashed 1px #999;
                }

                a {
                    color: #ccc;
                    font-size: 14px;
                    transition: all .5s;

                    &:hover {
                        color: #999;
                    }
                }
            }
        }
    }

    .ps-btn-disabled-new {
        color: #dcdee5 !important;
        background: #fafbfd;
        cursor: not-allowed;
        .paasng-icon {
            color: #dcdee5 !important;
        }
    }

    .section-button-new {
        padding: 0 12px;
        width: 100px;
        height: 30px;
        line-height: 30px;
        border-radius: 2px;
        font-size: 14px;
        color: #2dcb56;
        background: #dcffe2;
        -moz-transition: all .5s;
        -ms-transition: all .5s;
        -webkit-transition: all .5s;
        transition: all .5s;
        .paasng-icon {
            position: relative;
        }
    }

    .section-button-new:hover {
        color: #fff;
        background: #2dcb56;
        .paasng-icon {
            color: #fff;
        }
    }

    .disabledBox .section-button-new:hover {
        color: #4fb377;
        background: #eefaf3;
    }

    .open .section-button-new {
        .paasng-icon {
            left: 30px;
            transition: left .5s ease-in .1s;
            color: #2dcb56;
        }
    }

    .section-button-new img {
        padding-left: 6px;
        vertical-align: middle;
        position: relative;
        top: -1px;
    }

    .open .section-button-new {
        background: #fff;
        color: #666666;
        text-align: left;
        padding: 0 12px;
        display: block;
    }

    .open .section-button-new img {
        position: absolute;
        top: 14px;
        right: 12px;
    }

    .section-box {
        position: absolute;
        top: 4px;
        padding: 0;
        width: 100px;
        height: 30px;
        line-height: 30px;
        border-radius: 2px;
        border: solid 1px #eefaf3;
        transition: all .5s;
        background-color: white;
        overflow: hidden;
    }

    .open .section-box {
        height: auto;
        border: solid 1px #e9edee;
        border-radius: 2px;
        z-index: 99;
        border-color: #3a84ff;
        box-shadow: 0 4px 8px -4px rgba(0, 0, 0, 0.1), 0 -4px 8px -4px rgba(0, 0, 0, 0.1);
    }

    .section-button-down {
        min-width: 110px;
        width: auto;

        a {
            line-height: 34px;
            padding: 0 10px;
            display: block;
            height: 34px;
            color: #63656e;
            cursor: pointer;

            &:hover {
                background: #dcffe2;
                color: #2dcb56;
            }
        }
    }

    .read-more {
        display: block;
        position: relative;
        margin-top: 10px;
        width: 100%;
        height: 32px;
        line-height: 32px;
        border-radius: 2px;
        background: #fafbfd;
        font-size: 12px;
        color: #63656e;
        text-align: center;
        &:hover {
            color: #3a84ff
        }

        img {
            padding-left: 5px;
            position: relative;
            top: -2px;
        }
    }

    .paasng-angle-up,
    .paasng-angle-down {
        padding-left: 3px;
        transition: all .5s;
        font-size: 12px;
        font-weight: bold;
        color: #5bd18b;
    }

    .open .section-button .paasng-angle-down {
        position: absolute;
        top: 8px;
        right: 12px;

    }

    .paas-highcharts {
        width: 560px;
        height: 275px;
    }

    .paas-modular {
        width: 540px;

        .paas-question {
            line-height: 24px;
            color: #63656e;
            min-height: 100px;
            .paas-ask {
                display: block;
                padding: 14px 0;
                color: #3a84ff;
                font-size: 16px;

                &:hover {
                    color: #3a84ff
                }

                img {
                    vertical-align: top;
                    line-height: 24px;
                    padding: 4px 0 0 4px;
                }
            }
        }
    }

    .paas-modular-title {
        font-size: 30px;
        color: #4f515e;
        line-height: 40px;
        font-weight: normal;
        padding: 10px 0;
    }

    .paas-help {
        width: 100%;
        overflow: hidden;
        padding: 25px 0 13px 0;

        .advantage-detail {
            padding: 40px 50px;
            border: 1px solid #ccc;
            margin-right: -1px;
            width: 50%;
            float: left;
            cursor: default;
            box-sizing: border-box;
            height: 214px;

            .advantage-detail-title {
                font-size: 20px;
                color: #333;
                line-height: 1;

                img {
                    vertical-align: top;
                    margin-right: 19px;
                }

                .advantage-detail-title-line {
                    transition: all .35s;
                    width: 35px;
                    border: 1px solid #3a84ff;
                    top: 0;
                    left: 0;
                    margin-top: 30px;
                    margin-left: 50px;
                }

                &:hover {
                    .advantage-detail-title-line {
                        width: 78px;
                    }
                }
            }

            .describe-text {
                margin-top: 12px;
                margin-left: 50px;

                a {
                    display: block;
                    color: #63656e;
                    line-height: 30px;
                    transition: all .35s;

                    &:hover {
                        color: #3a84ff
                    }
                }
            }
        }
    }

    .paas-resource {
        display: flex;
        margin-left: -16px;
        margin-right: -16px;
        color: #999;
        text-align: center;

        li {
            width: 370px;
            height: 198px;
            margin: 0 16px;
            border: solid 1px #e9edee;
            box-shadow: 0 2px 4px #eee;
            overflow: hidden;
            transition: all .5s;
            float: left;
            border-radius: 2px;

            &:hover {
                border: solid 1px #3a84ff;
            }

            .paas-resource-title {
                line-height: 50px;
                height: 50px;
                overflow: hidden;
                padding: 0 10px;
                border-bottom: solid 1px #e9edee;
                color: #63656e;
                font-size: 16px;
            }

            .resource-text {
                padding: 28px 0 0 0;
                line-height: 60px;

                span {
                    font-size: 60px;
                    color: #3a84ff;
                    line-height: 60px;
                    font-family: 'PingFang';
                }
            }
        }
    }

    .paas-service {
        padding-top: 30px;
        overflow: hidden;

        .paas-service-list {
            width: 100%;
            overflow: hidden;
            display: flex;

            li {
                width: 20%;
                float: left;
                height: 117px;
                border-top: solid 3px #fafafa;
                text-align: center;
                cursor: pointer;
                transition: all .35s;

                &.active {
                    border-top: solid 3px #3a84ff;
                    background: #e9edee;
                }

                &:hover {
                    background: #e9edee;
                }

                .paas-service-text {
                    display: block;
                    font-size: 20px;
                    color: #333;
                    line-height: 28px;
                    padding: 10px 0 0 0;
                }

                .paas-service-icon {
                    height: 45px;
                    display: inline-block;
                    margin: 16px auto 0;
                    background: url(/static/images/service-icon3.png) no-repeat;

                    &.icon1 {
                        width: 67px;
                        background-position: 0 0;
                    }

                    &.icon2 {
                        width: 68px;
                        background-position: -194px 0;
                    }

                    &.icon3 {
                        width: 68px;
                        background-position: -391px 0;
                    }

                    &.icon4 {
                        width: 67px;
                        background-position: -592px 0;
                    }

                    &.icon5 {
                        width: 67px;
                        background-position: -785px 0;
                    }

                    &.icon6 {
                        width: 67px;
                        background-position: -985px 0;
                    }
                }
            }
        }

        .paas-service-main {
            width: 100%;
            overflow: hidden;

            .paas-service-content {
                width: 7080px;
                display: flex;
                overflow: hidden;
                margin-left: 0;
                transition: all .5s;

                &.showCon {
                    margin-left: 0;
                }

                &.showCon1 {
                    margin-left: -100%;
                }

                &.showCon2 {
                    margin-left: -200%;
                }

                &.showCon3 {
                    margin-left: -300%;
                }

                &.showCon4 {
                    margin-left: -400%;
                }

                &.showCon5 {
                    margin-left: -500%;
                }

                .content-panel {
                    background: #e9edee;
                    overflow: hidden;
                    padding: 9px 0 17px 0;
                    width: 1180px;

                    dl {
                        display: inline-block;
                        width: 219px;
                        padding: 10px 38px;
                        vertical-align: text-top;
                    }

                    dt {
                        font-size: 18px;
                        color: #4f515e;
                        line-height: 38px;

                        a {
                            color: #333;
                            transition: all .5s;

                            &:hover {
                                color: #3a84ff
                            }
                        }
                    }

                    dd {
                        color: #999;
                        line-height: 18px;
                    }
                }
            }
        }
    }

    .appear {
        animation: opacity_show 0.85s 1 cubic-bezier(0.445, 0.05, 0.55, 0.95) forwards;
        opacity: 1 !important;
    }

    @keyframes opacity_show {
        0% {
            transform: translateY(50px);
            opacity: .1;
        }

        100% {
            transform: translateY(0);
            opacity: 1;
        }
    }

    .migration-legacy {
        padding-right: 20px;
    }

    .migration-legacy-at-applist {
        position: absolute;
        right: 450px;
    }

    .ps-table-app {
        color: #63656e;

        &:hover {
            color: #3a84ff;
        }
    }

    .legacy-links {
        font-size: 14px;
    }

    .ps-btn-visit-disabled .paasng-angle-down,
    .ps-btn-visit:disabled .paasng-angle-down,
    .ps-btn-visit[disabled] .paasng-angle-down {
        color: #d7eadf !important;
    }

    .wrap {
        width: 1180px;
        margin: 50px auto auto auto;
    }
    .section-wrapper {
        display: flex;
        white-space: nowrap;
    }
    .text-style {
        display: inline-block;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
</style>
