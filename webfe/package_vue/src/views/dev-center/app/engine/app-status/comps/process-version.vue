<template>
  <div class="version-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="event-list-loading"
      :offset-top="0"
      :offset-left="-8"
      class="deploy-history"
    >
      <!-- <bk-form form-type="inline">
              <bk-form-item :label="$t('环境')" style="vertical-align: top;">
                  <bk-select
                      v-model="choosedEnv"
                      style="width: 150px;"
                      :clearable="false">
                      <bk-option
                          v-for="(option, index) in envList"
                          :key="index"
                          :id="option.id"
                          :name="option.text">
                      </bk-option>
                  </bk-select>
              </bk-form-item>
              <bk-form-item :label="$t('操作人')" style="vertical-align: top;">
                  <user
                      style="width: 350px;"
                      :placeholder="$t('请选择')"
                      :max-data="1"
                      v-model="personnelSelectorList">
                  </user>
              </bk-form-item>
              <bk-form-item label="" style="vertical-align: top;">
                  <bk-button theme="primary" type="button" @click.stop.prevent="getDeployHistory(1)"> {{ $t('查询') }} </bk-button>
              </bk-form-item>
          </bk-form> -->
      <bk-table
        v-bkloading="{ isLoading: isPageLoading }"
        class="mt15 ps-history-list"
        :data="historyList"
        :outer-border="false"
        :size="'small'"
        :pagination="pagination"
        :height="historyList.length ? '' : '520px'"
        @row-click="handleShowLog"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
      >
        <div slot="empty">
          <table-empty empty />
        </div>
        <bk-table-column
          :label="$t('版本')"
          prop="name"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('部署环境')"
          prop="environment_name"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span v-if="props.row.environment_name === 'stag'"> {{ $t('预发布环境') }} </span>
            <span v-else> {{ $t('生产环境') }} </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作人')"
          prop="operator"
          :render-header="$renderHeader"
        />
        <bk-table-column
          :label="$t('耗时')"
          :render-header="$renderHeader"
        >
          <template slot-scope="{ row }">
            {{ computedDeployTime(row) }}
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('结果')">
          <template slot-scope="props">
            <div v-if="props.row.status === 'ready'">
              <span class="dot success" /> {{ $t('成功') }}
            </div>
            <div v-if="props.row.status === 'error'">
              <span class="dot danger" /> {{ $t('失败') }}
            </div>
            <div v-if="props.row.status === 'progressing' || props.row.status === 'pending'">
              <span class="dot warning" /> {{ $t('部署中') }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          width="180"
          :label="$t('操作时间')"
        >
          <template slot-scope="{ row }">
            {{ formatDeployCreateTime(row) }}
          </template>
        </bk-table-column>
      </bk-table>

      <bk-sideslider
        :title="historySideslider.title"
        :width="820"
        :is-show.sync="historySideslider.isShow"
        :quick-close="true"
        @hidden="errorTips = {}"
      >
        <div
          slot="content"
          v-bkloading="{ isLoading: isLogLoading || isTimelineLoading, opacity: 1 }"
          class="deploy-detail"
        >
          <bk-tab
            type="unborder-card"
            :active.sync="active"
            ext-cls="version-tab-cls"
          >
            <bk-tab-panel
              key="processes"
              name="processes"
              v-bind="tabData[0]"
            >
              <div class="process-container">
                <div
                  v-for="(item, index) in processData"
                  :key="index"
                  class="process-item"
                >
                  <div class="process-url">
                    {{ $t('容器镜像地址') }}: <span>{{ item.image }}</span>
                  </div>
                  <div class="pt20 pl20">
                    {{ $t('镜像凭证') }}: {{ bkappAnnotations[`bkapp.paas.bk.tencent.com/image-credentials.${item.name}`] || '无' }}
                  </div>
                  <div class="pt20 pl20">
                    {{ $t('启动命令') }}: {{ item.command && item.command.length ? item.command.join(',') : '无' }}
                  </div>
                  <div class="pt20 pl20">
                    {{ $t('命令参数') }}: {{ item.args && item.args.length ? item.args.join(',') : '无' }}
                  </div>
                  <div class="pt20 pl20">
                    {{ $t('副本数量') }}: {{ item.replicas }}
                  </div>
                  <div class="pt20 pl20 pb20">
                    {{ $t('资源') }}: {{ item.memory }} / {{ item.cpu }}
                  </div>
                </div>
              </div>
            </bk-tab-panel>
            <bk-tab-panel
              key="env"
              name="env"
              v-bind="tabData[1]"
            >
              <div
                v-if="envData.length"
                class="env-container"
              >
                <div
                  v-for="(item, index) in envData"
                  :key="index"
                  class="env-item pb20"
                >
                  NAME: {{ item.name }}
                  <span class="pl20">VALUE: {{ item.value }}</span>
                </div>
              </div>
              <div
                v-else
                class="exception-wrapper"
              >
                <table-empty empty />
              </div>
            </bk-tab-panel>
            <bk-tab-panel
              key="resource"
              name="resource"
              v-bind="tabData[2]"
            >
              <div class="resource-contanier">
                <div class="resource-item mb20">
                  <div class="pb10">
                    <span class="item-title">{{ $t('增强服务') }}</span>
                    <router-link
                      :to="{ path: `/developer-center/apps/${appCode}/default/service/1` }"
                      class="link pl20"
                    >
                      {{ $t('管理增强服务') }}
                    </router-link>
                  </div>
                  <div class="item-data">
                    {{ $t('启用未创建') }}: {{ notCreated || $t('无') }}
                  </div>
                  <div class="item-data">
                    {{ $t('已创建实例') }}: {{ created || $t('无') }}
                  </div>
                </div>
                <div class="resource-item no-border">
                  <div class="item-title-content">
                    <span class="item-title pb10">
                      {{ $t('服务发现') }}
                    </span>
                    <span>{{ $t('（其他 SaaS）') }}</span>
                  </div>
                  <div class="item-data">
                    {{ $t('通过环境变量获取其他Saas应用的访问地址') }}
                    <a
                      target="_blank"
                      :href="GLOBAL.DOC.SERVE_DISCOVERY"
                      style="color: #3a84ff"
                    >{{ $t('查看使用帮助') }}</a>
                  </div>
                </div>
              </div>
            </bk-tab-panel>
            <bk-tab-panel
              key="yaml"
              name="yaml"
              v-bind="tabData[3]"
            >
              <div class="process-container">
                <resource-editor
                  ref="versionEditorRef"
                  key="editor"
                  v-model="yamlData"
                  v-bkloading="{ isLoading, opacity: 1, color: '#1a1a1a' }"
                  :height="600"
                  @error="handleEditorErr"
                />
                <EditorStatus
                  v-show="!!editorErr.message"
                  class="status-wrapper"
                  :message="editorErr.message"
                />
              </div>
            </bk-tab-panel>
          </bk-tab>
        </div>
      </bk-sideslider>
    </paas-content-loader>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import ResourceEditor from './deploy-resource-editor';
    import EditorStatus from './deploy-resource-editor/editor-status';
    import moment from 'moment';
    import { uniqBy } from 'lodash';
    // import user from '@/components/user';

    export default {
        components: {
            ResourceEditor,
            EditorStatus
            // user,
        },
        mixins: [appBaseMixin],
        props: {
            env: {
                type: String,
                default: ''
            }
        },
        data () {
            return {
                choosedEnv: 'all',
                historyList: [],
                curDeployLog: '',
                logDetail: '',
                isLoading: true,
                isPageLoading: true,
                isLogLoading: false,
                isTimelineLoading: false,
                ansiUp: null,
                personnelSelectorList: [],
                formDatas: {},
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                historySideslider: {
                    title: '',
                    isShow: false
                },
                tabData: [
                    { name: 'processes', label: '进程配置' },
                    { name: 'env', label: '环境变量' },
                    { name: 'resource', label: '增强服务' },
                    { name: 'yaml', label: 'YAML' },
                    { name: 'hook', label: '钩子命令' }
                ],
                active: 'processes',
                processData: [],
                bkappAnnotations: {},
                envData: [],
                resourceData: {
                    notCreated: [],
                    created: []
                },
                notCreated: [],
                created: [],
                yamlData: {},
                errorTips: {},
                editorErr: {
                    type: '',
                    message: ''
                }
            };
        },
        computed: {
            isMatchedSolutionsFound () {
                return this.errorTips.matched_solutions_found;
            }
        },
        watch: {
            '$route': function () {
                this.isLoading = true;
                this.getDeployHistory();
            },
            resourceData: {
                handler (value) {
                    this.notCreated = value.notCreated && value.notCreated.map(e => e.display_name).join('，');
                    this.created = value.created && value.created.map(e => e.display_name).join('，');
                },
                immediate: true,
                deep: true
            }
        },
        created () {
            this.isLoading = true;
            this.getDeployHistory();
        },
        mounted () {
            const AU = require('ansi_up');
            // eslint-disable-next-line
            this.ansiUp = new AU.default
        },
        methods: {
            updateValue (curVal) {
                curVal ? this.personnelSelectorList = curVal : this.personnelSelectorList = '';
            },

            computedDeployTime (payload) {
                if (payload.status !== 'ready') {
                    return '--';
                }

                const start = new Date(payload.created).getTime();
                const end = new Date(payload.last_transition_time).getTime();
                const interval = (end - start) / 1000;

                if (!interval) {
                    return `< 1${this.$t('秒')}`;
                }

                return this.getDisplayTime(interval);
            },

            formatDeployCreateTime (payload) {
                return moment(payload.created).format('YYYY-MM-DD HH:mm:ss');
            },

            computedDeployTimelineTime (startTime, endTime) {
                if (!startTime || !endTime) {
                    return '--';
                }

                const start = (new Date(startTime).getTime()) / 1000;
                const end = (new Date(endTime).getTime()) / 1000;
                const interval = Math.ceil(end - start);

                if (!interval) {
                    return `< 1${this.$t('秒')}`;
                }

                return this.getDisplayTime(interval);
            },

            getDisplayTime (payload) {
                let theTime = payload;
                if (theTime < 1) {
                    return `< 1${this.$t('秒')}`;
                }
                let middle = 0;
                let hour = 0;

                if (theTime > 60) {
                    middle = parseInt(theTime / 60, 10);
                    theTime = parseInt(theTime % 60, 10);
                    if (middle > 60) {
                        hour = parseInt(middle / 60, 10);
                        middle = parseInt(middle % 60, 10);
                    }
                }

                let result = '';

                if (theTime > 0) {
                    result = `${theTime}${this.$t('秒')}`;
                }
                if (middle > 0) {
                    result = `${middle}${this.$t('分')}${result}`;
                }
                if (hour > 0) {
                    result = `${hour}${this.$t('时')}${result}`;
                }

                return result;
            },

            /**
             * 获取部署记录
             */
            async getDeployHistory (page = 1) {
                this.isPageLoading = true;
                const curPage = page || this.pagination.current;
                const pageParams = {
                    limit: this.pagination.limit,
                    offset: this.pagination.limit * (curPage - 1)
                };
                if (this.choosedEnv !== 'all') {
                    pageParams.environment = this.choosedEnv;
                }

                if (this.personnelSelectorList.length) {
                    pageParams.operator = this.personnelSelectorList[0];
                }

                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppDeployHistory', {
                        env: this.env,
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        pageParams
                    });

                    this.historyList = res.results;
                    this.pagination.count = res.count;

                    // 如果有deployid，默认显示
                    if (this.$route.query.deployId) {
                        const recordItem = this.historyList.find(item => {
                            return item.deployment_id === this.$route.query.deployId;
                        });
                        if (recordItem) {
                            this.handleShowLog(recordItem);
                        }
                    }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message
                    });
                } finally {
                    this.isLoading = false;
                    this.isPageLoading = false;
                }
            },

            handlePageLimitChange (limit) {
                this.pagination.limit = limit;
                this.pagination.current = 1;
                this.getDeployHistory(this.pagination.current);
            },

            handlePageChange (newPage) {
                this.pagination.current = newPage;
                this.getDeployHistory(newPage);
            },

            handleShowLog (row) {
                this.deployId = row.id;
                this.getProcessVersionDetail();
                this.getCloudAppServicesInfo();
                this.historySideslider.title = `${row.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境')}${this.$t('版本详情')}`;
                this.historySideslider.isShow = true;
            },

            // 所有信息
            async getProcessVersionDetail () {
                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppDeployYaml', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env,
                        deployId: this.deployId
                    });
                    this.$nextTick(() => {
                        this.yamlData = res.manifest;
                        this.processData = this.yamlData.spec.processes; // 进程配置
                        this.bkappAnnotations = this.yamlData.metadata.annotations; // 凭证
                        this.envData = this.yamlData.spec.configuration.env; // 环境变量
                        this.$nextTick(() => {
                            this.$refs.versionEditorRef.setValue(this.yamlData);
                        });
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.screenIsLoading = false;
                }
            },

            // 增强服务数据
            async getCloudAppServicesInfo () {
                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppResource', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });

                    // 启用未创建数据
                    this.resourceData = Object.keys(res).reduce((p, e) => {
                        const notCreatedData = res[e].filter(item => !item.is_provisioned);
                        const createdData = res[e].filter(item => item.is_provisioned);
                        p.notCreated.push(...notCreatedData);
                        p.created.push(...createdData);
                        return p;
                    }, { notCreated: [], created: [] });

                    // 已创建实例

                    this.resourceData.notCreated = uniqBy(this.resourceData.notCreated, 'name'); // 根据name去重
                    this.resourceData.created = uniqBy(this.resourceData.created, 'name'); // 根据name去重
                    // 若 prod 对应分类不存在该服务，则展示（带上测试的备注）
                    this.resourceData.created.map(e => {
                        if (!res['prod'].find(item => item.name === e.name)) {
                            e.display_name = e.display_name + '(测试)';
                        } else {
                            res['prod'].forEach(element => {
                                if ((e.name === element.name && !element.is_provisioned)) {
                                    e.display_name = e.display_name + '(测试)';
                                }
                            });
                        }
                        return e;
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                }
            },
            handleEditorErr (err) { // 捕获编辑器错误提示
                this.editorErr.type = 'content'; // 编辑内容错误
                this.editorErr.message = err;
            }

        }
    };
</script>

<style lang="scss" scoped>
    .version-container {
        padding: 0 20px 20px;
    }
    .deploy-history {
        min-height: 500px !important;
    }
    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;

        &.success {
            background: #a0f5e3;
            border: 1px solid #18c0a1;
        }

        &.danger {
            background: #fd9c9c;
            border: 1px solid #ea3636;
        }

        &.warning {
            background: #FFE8C3;
            border: 1px solid #FF9C01;
        }
    }

    .wrapper {
        margin: -20px -20px 10px;
        height: 64px;
        background: #F5F6FA;
        line-height: 64px;
        padding: 0 20px;

        &::after {
            display: block;
            clear: both;
            content: "";
            font-size: 0;
            height: 0;
            visibility: hidden;
        }

        &.default-box {
            padding: 11px 12px 11px 20px;
            height: auto;
            line-height: 16px;
            .span {
                height: 16px;
            }
        }

        &.not-deploy {
            height: 42px;
            line-height: 42px;
        }

        &.primary {
            background: #E1ECFF;
            color: #979BA5;
        }

        &.warning {
            background: #FFF4E2;
            border-color: #FFDFAC;

            .paasng-icon {
                color: #fe9f07;
            }
        }

        &.danger {
            background: #FFECEC;
            color: #979BA5;

            .paasng-icon {
                color: #eb3635;
                position: relative;
                top: 4px;
                font-size: 32px;
            }
        }

        &.success {
            background: #E7FCFA;
            color: #979BA5;

            .paasng-icon {
                position: relative;
                top: 4px;
                color: #3fc06d;
                font-size: 32px;
            }
        }
        .deploy-pending-text {
            position: relative;
            top: 5px;
            font-size: 14px;
            color: #313238;
            font-weight: 500;
            line-height: 32px;
        }
        .deploy-text-wrapper {
            position: relative;
            top: -5px;
            line-height: 32px;
            font-size: 12px;
            .branch-text,
            .version-text,
            .time-text {
                font-size: 12px;
                color: #63656e;
                opacity: .9;
            }
            .branch-text,
            .version-text {
                margin-right: 30px;
            }
        }
    }

    .deploy-detail {
        display: flex;
        height: 100%;

        /deep/ .paas-deploy-log-wrapper {
            height: 100%;
        }
    }

    .flex {
        display: flex;
        line-height: 16px;
        margin-bottom: 3px;

        .label {
            display: inline-block;
            width: 60px;
        }

        .value {
            text-align: left;
            display: inline-block;
            flex: 1;
        }
    }

    .branch-name {
        width: 130px;
        display: block;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .process-container{
        padding: 0 20px;
        font-size: 14px;
        color: #63656E;
        .process-item{
            .process-url{
                height: 42px;
                line-height: 42px;
                padding: 0 20px;
                font-size: 12px;
                background: #F0F1F5;
                border-radius: 2px;
            }
        }
    }
    .env-container{
        padding: 0 20px 20px 20px;
        font-size: 14px;
        color: #63656E;
    }

    .resource-contanier{
        padding: 0 20px 20px 20px;
        .resource-item{
            padding-bottom: 20px;
            border-bottom: 1px solid #DCDEE5;
            .item-title{
                font-weight: Bold;
                font-size: 14px;
                color: #313238;
            }
            .item-data{
                padding: 10px 30px;
            }
        }
        .no-border{
            border-bottom: none;
        }
    }
    .exception-wrapper {
        margin-top: 120px;
        text-align: center;
        .img-exception {
            width: 300px;
        }

        .text-exception {
            color: #979ba5;
            font-size: 14px;
            text-align: center;
            margin-top: 14px;
        }
    }

</style>
<style>
    .bk-tab.version-tab-cls .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item {
        border: none !important;
    }
    .version-tab-cls{
        width: 100% !important;
    }
</style>
