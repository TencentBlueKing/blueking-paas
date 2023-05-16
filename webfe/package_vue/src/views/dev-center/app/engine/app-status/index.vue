le<template lang="html">
  <div class="right-main">
    <section class="app-container middle">
      <paas-content-loader
        placeholder="process-loading"
        :offset-top="10"
      >
        <div class="title mb15">
          {{ $t('部署状态') }}
        </div>
        <bk-tab
          :key="routeName"
          :active.sync="environment"
          type="unborder-card"
          ext-cls="status-tab-wrapper"
          @tab-change="changeEnv"
        >
          <bk-tab-panel
            v-for="(panelItem, index) in panels"
            :key="index"
            :name="panelItem.env"
            :label="panelItem.env === 'stag' ? $t('预发布环境') : $t('生产环境')"
          >
            <div class="environment environment-instance">
              <div
                v-if="Object.keys(statusData.deployment).length"
                class="ps-deploy-container mb20"
              >
                <bk-alert
                  v-if="statusData.deployment.status === 'error'"
                  type="error"
                  :show-icon="false"
                >
                  <div slot="title">
                    <i
                      style="color: #EA3636;"
                      :class="['icon paasng-icon', 'paasng-close-circle-shape']"
                    />
                    {{ $t('由') }} {{ statusData.deployment.operator }} {{ $t('于') }} {{ deploymentCreatedTime }} {{ $t('部署失败') }}
                    <!-- <bk-button class="pl20" theme="primary" text style="font-size: 12px;"> {{ $t('查看日志') }} </bk-button> -->
                    <div
                      v-for="(item, i) in deployFailData"
                      :key="i"
                      class="pl15 message-container"
                    >
                      {{ item.type }}: {{ item.reason }}, {{ item.message || $t('无') }}
                      <i
                        v-if="item.status === 'True'"
                        class="paasng-icon paasng-correct success-icon"
                      />
                      <i
                        v-if="item.status === 'False'"
                        class="paasng-icon paasng-icon-close error-icon"
                      />
                      <i
                        v-if="item.status === 'Unknown'"
                        class="pl10 paasng-icon paasng-exclamation-circle warning-icon"
                      />
                    </div>
                  </div>
                </bk-alert>
                <bk-alert
                  v-else-if="statusData.deployment.status === 'ready'"
                  type="success"
                  :show-icon="false"
                >
                  <div slot="title">
                    <i
                      style="color: #2DCB56;"
                      :class="['icon paasng-icon', 'paasng-check-circle-shape']"
                    />
                    {{ $t('由') }} {{ statusData.deployment.operator }} {{ $t('于') }} {{ deploymentCreatedTime }} {{ $t('部署成功') }}
                    <!-- <bk-button class="pl20" theme="primary" text style="font-size: 12px;"> {{ $t('查看日志') }} </bk-button> -->
                    <div
                      v-for="(item, i) in deployFailData"
                      :key="i"
                      class="pl15 message-container"
                    >
                      {{ item.type }}: {{ item.reason }}, {{ item.message || $t('无') }}
                      <i
                        v-if="item.status === 'True'"
                        class="paasng-icon paasng-correct success-icon"
                      />
                      <i
                        v-if="item.status === 'False'"
                        class="paasng-icon paasng-icon-close error-icon"
                      />
                      <i
                        v-if="item.status === 'Unknown'"
                        class="pl10 paasng-icon paasng-exclamation-circle warning-icon"
                      />
                    </div>
                  </div>
                </bk-alert>
                <bk-alert
                  v-else
                  type="info"
                  :show-icon="false"
                >
                  <div slot="title">
                    <round-loading
                      style="margin-bottom: 3px"
                      size="mini"
                      ext-cls="deploy-round-load"
                    />
                    {{ $t('发布中，请等待更新完成') }}
                    <!-- <bk-button class="pl20" theme="primary" text style="font-size: 12px;"> {{ $t('查看日志') }} </bk-button> -->
                    <div
                      v-for="(item, i) in deployFailData"
                      :key="i"
                      class="pl15 message-container"
                    >
                      {{ item.type }}: {{ item.reason }}, {{ item.message || $t('无') }}
                      <i
                        v-if="item.status === 'True'"
                        class="paasng-icon paasng-correct success-icon"
                      />
                      <i
                        v-if="item.status === 'False'"
                        class="paasng-icon paasng-icon-close error-icon"
                      />
                      <i
                        v-if="item.status === 'Unknown'"
                        class="pl10 paasng-icon paasng-exclamation-circle warning-icon"
                      />
                    </div>
                  </div>
                </bk-alert>
              </div>
              <div class="ps-tip-record mb20">
                <div class="left-contanier">
                  {{ statusData.deployment.tag }}
                </div>
                <div
                  v-if="Object.keys(statusData.deployment).length"
                  class="right-contanier"
                >
                  {{ $t('操作记录') }}：{{ $t('由') }} {{ statusData.deployment.operator }} {{ $t('于') }} {{ deploymentCreatedTime }} {{ $t('发布') }}
                  <a
                    class="ml20"
                    target="_blank"
                    :href="statusData.ingress.url"
                  > {{ $t('点击访问') }} </a>
                </div>
                <div
                  v-else
                  class="right-contanier"
                >
                  {{ $t('操作记录：暂无') }}
                </div>
              </div>
              <bk-tab
                v-if="activeIndex === index"
                :key="active"
                :active.sync="active"
                ext-cls="status-tab-cls"
              >
                <bk-tab-panel
                  key="status"
                  name="status"
                  v-bind="tabData[0]"
                >
                  <process-operation
                    v-if="active === 'status'"
                    :ref="panelItem.env + 'Component'"
                    style="padding: 0 20px;"
                    :app-code="appCode"
                    :environment="panelItem.env"
                    @data-ready="handlerDataReady"
                  />
                </bk-tab-panel>
                <bk-tab-panel
                  key="event"
                  name="event"
                  v-bind="tabData[1]"
                >
                  <process-event
                    v-if="active === 'event'"
                    :app-code="appCode"
                    :environment="panelItem.env"
                    :events="eventList"
                  />
                </bk-tab-panel>
                <bk-tab-panel
                  ref="yamlRef"
                  key="yaml"
                  name="yaml"
                  v-bind="tabData[2]"
                >
                  <process-yaml
                    v-if="active === 'yaml'"
                    :key="yamlKey"
                    :deploy-id="deployId"
                    :env="environment"
                    @getCloudAppInfo="getCloudAppInfo"
                  />
                </bk-tab-panel>
                <bk-tab-panel
                  key="version"
                  name="version"
                  v-bind="tabData[3]"
                >
                  <process-version
                    v-if="active === 'version'"
                    :key="versionKey"
                    :env="environment"
                  />
                </bk-tab-panel>
              </bk-tab>
            </div>
          </bk-tab-panel>
        </bk-tab>
      </paas-content-loader>
    </section>
  </div>
</template>

<script>
    import processOperation from './comps/process-operation';
    import processYaml from './comps/process-yaml';
    import processVersion from './comps/process-version';
    import processEvent from './comps/process-event.vue';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import moment from 'moment';
    import i18n from '@/language/i18n.js';

    export default {
        components: {
            processOperation,
            processYaml,
            processVersion,
            processEvent
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isStagLoading: true,
                isProdLoading: true,
                environment: 'stag',
                panels: [{ env: 'stag', label: '预发布环境' }, { env: 'prod', label: '生产环境' }],
                tabData: [
                    { name: 'status', label: i18n.t('进程状态'), count: 10 },
                    { name: 'event', label: i18n.t('事件'), count: 10 },
                    { name: 'yaml', label: 'YAML', count: 20 },
                    { name: 'version', label: i18n.t('版本'), count: 30 }
                ],
                active: 'status',
                statusData: {
                    deployment: {},
                    ingress: {}
                },
                deploymentCreatedTime: '',
                deployId: 0,
                deployFailData: [],
                intervalTimer: null,
                yamlKey: 0,
                versionKey: 0,
                activeIndex: 0,
                eventList: []
            };
        },
        computed: {
            routeName () {
                return this.$route.name;
            }
        },
        watch: {
            '$route' (to, from) {
                this.isStagLoading = true;
                this.isProdLoading = true;
            }
        },
        created () {
            this.environment = this.$route.query.env || 'stag';
            if (this.environment === 'prod') {
                this.activeIndex = 1;
            }
            this.$store.commit('updataEnvEventData', []);
            this.init();
        },
        beforeDestroy () {
            this.$store.commit('updataEnvEventData', ['stag', 'prod']);
            clearInterval(this.intervalTimer);
        },
        methods: {
            async getCloudAppInfo () {
                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppStatus', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.environment

                    });
                    this.eventList = res.events;
                    this.statusData = res;
                    this.deployId = this.statusData.deployment.deploy_id;
                    this.deploymentCreatedTime = moment(res.deployment.created).format('YYYY-MM-DD HH:mm:ss');
                    this.deployFailData = res.conditions && res.conditions;
                    this.intervalTimer = setTimeout(() => {
                        this.getCloudAppInfo();
                    }, 3000);
                    if (this.statusData.deployment.status === 'ready' || this.statusData.deployment.status === 'error') {
                        clearInterval(this.intervalTimer);
                    }
                    this.heavyLoad();
                } catch (e) {
                    this.heavyLoad();
                    if (e.code !== 'GET_DEPLOYMENT_FAILED') {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail || e.message || this.$t('接口异常')
                        });
                    }
                    this.resetData();
                    clearInterval(this.intervalTimer);
                }
            },
            resetData () {
                this.deployId = 0;
                this.statusData = {
                    deployment: {},
                    ingress: {}
                };
                this.deploymentCreatedTime = '';
                this.eventList = [];
            },
            async init () {
                this.getCloudAppInfo();
            },
            changeEnv (val) {
                this.activeIndex = this.panels.findIndex(item => item.env === val);
                this.getCloudAppInfo();
            },
            handlerDataReady (env) {
                setTimeout(() => {
                    if (env === 'stag') {
                        this.isStagLoading = false;
                    } else {
                        this.isProdLoading = false;
                    }
                }, 200);
            },
            heavyLoad () {
                this.$nextTick(() => {
                    if (this.active === 'yaml') {
                        this.yamlKey++;
                    }
                    if (this.active === 'version') {
                        this.versionKey++;
                    }
                });
            }
        }
    };
</script>

<style lang="scss">
    .status-tab-cls .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item {
        padding: 0 20px;
        margin-right: 0;
    }
    .bk-tab.status-tab-cls .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item {
        border-right: 1px solid #ccc !important;
    }
    .success-icon{
        color: #2DCB56;
        font-size: 24px;
    }
    .error-icon{
        color: #EA3636;
        font-size: 24px;
    }

    .warning-icon{
        color: #FF9C01;
        font-size: 12px;
        padding-top: 2px;
        height: 24px;
        line-height: 24px;
    }
    .message-container{
        display: flex;
        align-items: center;
    }

    .status-tab-cls.bk-tab-border-card>.bk-tab-header {
        border-right: none;
        border-left: none;
    }
</style>

<style lang="scss" scoped>
    .title{
        font-size: 16px;
        color: #313238;
    }
    .ps-tip-record{
        background: #F5F7FA;
        box-shadow: 0 2px 4px 0 rgba(25,25,41,0.05);
        border-radius: 2px;
        display: flex;
        padding: 10px;
    }

    a {
        cursor: pointer;
    }
    .textarea {
        height: 300px;
    }

    .textarea .inner p {
        height: 25px;
        word-break: break-all;
        white-space: nowrap;
    }

    .environment-instance {
        overflow: visible;
        padding-bottom: 0;
    }

    .doc-links-container {
        margin-top: 5px;

        h2 {
            font-size: 14px;
            color: #55545a;
            font-weight: bold;
            line-height: 22px;
            padding: 5px 0;
            margin-bottom: 6px;

            span.tip {
                font-weight: normal;
                color: #666;
            }
        }

        ul.doc-links-list li {
            border: none;
            padding: 4px 0;
            margin: 0;
            font-size: 14px;
            line-height: 28px;
        }
    }
    .status-tab-wrapper{
        padding: 0 20px;
    }
    .status-tab-cls{
        border: 1px solid #e6e9ea;
        border-top: none;
        margin-bottom: 20px;
    }
</style>
