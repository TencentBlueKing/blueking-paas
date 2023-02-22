<template lang="html">
  <div
    v-if="domainConfig.enabled"
    class="paas-domain-part-wrapper"
  >
    <div class="ps-top-card">
      <p class="main-title">
        {{ $t('独立域名配置') }}
      </p>
      <p class="desc">
        {{ $t('独立域名允许你通过默认地址以外的其他自定义域名来访问蓝鲸应用。使用前请先阅读') }}
        <a
          :href="GLOBAL.DOC.APP_ENTRY_INTRO"
          target="blank"
        > {{ $t('详细使用说明') }} </a>
      </p>
    </div>
    <div class="content">
      <bk-tab
        :active.sync="active"
        ext-cls="domain-tab-cls"
        type="unborder-card"
      >
        <bk-tab-panel
          v-for="(panel, index) in panels"
          :key="index"
          v-bind="panel"
        />
      </bk-tab>
      <div class="controller">
        <div
          v-if="isInitLoading"
          class="result-table-content"
        >
          <div
            v-bkloading="{ isLoading: isInitLoading }"
            class="ps-loading-placeholder"
          />
        </div>
        <div
          v-else
          v-bkloading="{ isLoading: isDomainLoading }"
        >
          <template v-if="active === 'domain'">
            <bk-button
              theme="primary"
              class="mb20"
              @click="handleShowAddUrlDialog"
            >
              {{ $t('添加域名') }}
            </bk-button>
            <bk-table
              v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
              :data="domainConfigList"
              size="small"
              :class="{ 'set-border': tableLoading }"
              :ext-cls="'ps-permission-table'"
            >
              <div slot="empty">
                <table-empty empty />
              </div>
              <bk-table-column :label="$t('环境')">
                <template slot-scope="props">
                  <span>{{ props.row.environment_name || '--' }}</span>
                </template>
              </bk-table-column>
              <bk-table-column :label="$t('域名')">
                <template slot-scope="{ row }">
                  <span v-bk-tooltips="row.domain_name">{{ row.domain_name }}</span>
                </template>
              </bk-table-column>
              <bk-table-column :label="$t('路径')">
                <template slot-scope="props">
                  <span>{{ props.row.path_prefix || '--' }}</span>
                </template>
              </bk-table-column>
              <bk-table-column :label="$t('绑定模块')">
                <template slot-scope="props">
                  <span>{{ props.row.module_name || '--' }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('操作')"
                width="150"
              >
                <template slot-scope="{ row, $index }">
                  <bk-button
                    theme="primary"
                    text
                    style="margin-left: 6px;"
                    @click="handleEdit(row, $index)"
                  >
                    {{ $t('编辑') }}
                  </bk-button>
                  <bk-button
                    theme="primary"
                    text
                    style="margin-left: 6px;"
                    @click="showRemoveModal(row, $index)"
                  >
                    {{ $t('删除') }}
                  </bk-button>
                </template>
              </bk-table-column>
            </bk-table>
          </template>
          <template v-else>
            <!-- 如果所有模块 & 环境出口 IP 一致，则展示一行即可 -->
            <table
              v-if="allIngressIpEqual(curIngressIpConfigs)"
              class="ps-table ps-table-border"
              style="width: 100%;"
            >
              <tr>
                <td
                  style="width: 148px;"
                  class="has-right-border"
                >
                  {{ $t('域名解析目标IP') }}
                </td>
                <td v-if="(curIngressIpConfigs.length !== 0)">
                  {{ curIngressIpConfigs[0].frontend_ingress_ip }}
                </td>
                <td v-else>
                  {{ $t('暂无信息') }}
                  <span v-if="GLOBAL.HELPER.href"> {{ $t('请联系') }} <a :href="GLOBAL.HELPER.href">{{ GLOBAL.HELPER.name }}</a>）
                  </span>
                </td>
              </tr>
            </table>
            <!-- 如果任一模块或环境出口 IP 不同，则每项都展示 -->
            <bk-table
              v-else
              :data="curIngressIpConfigs"
              size="small"
              :ext-cls="'ps-permission-table'"
            >
              <div slot="empty">
                <table-empty empty />
              </div>
              <bk-table-column
                :label="$t('模块')"
              >
                <template slot-scope="props">
                  <span>{{ props.row.module }}</span>
                </template>
              </bk-table-column>
              <bk-table-column :label="$t('环境')">
                <template slot-scope="props">
                  <span v-if="props.row.environment === 'prod'">{{ $t('生产环境') }}</span>
                  <span v-if="props.row.environment === 'stag'">{{ $t('预发布环境') }}</span>
                </template>
              </bk-table-column>
              <bk-table-column :label="$t('域名解析目标 IP')">
                <template slot-scope="props">
                  <span>{{ props.row.frontend_ingress_ip || '--' }}</span>
                </template>
              </bk-table-column>
            </bk-table>
          </template>
          <div
            v-if="active === 'ipInfo'"
            class="info-wrapper"
          >
            <p class="title">
              {{ $t('推荐操作流程：') }}
            </p>
            <p>1. {{ $t('首先，在“域名管理”添加域名') }}</p>
            <p>2. {{ $t('修改本机 Hosts 文件，将域名解析到表格中的 IP') }}</p>
            <p>3. {{ $t('打开浏览器，测试访问是否正常') }}</p>
            <p>4. {{ $t('修改域名解析记录，将其永久解析到目标 IP') }}</p>
          </div>
          <bk-dialog
            v-model="addUrlDialog.visiable"
            width="600"
            :title="addUrlDialog.title"
            header-position="left"
            :theme="'primary'"
            :mask-close="false"
            :close-icon="!addUrlDialog.isLoading"
            :loading="addUrlDialog.isLoading"
            @confirm="addDomainUrl"
            @cancel="cancelAddUrl"
          >
            <template style="min-height: 140px;">
              <bk-form
                v-if="addUrlDialog.showForm"
                ref="addUrlForm"
                :label-width="100"
                :model="curUrlParams"
              >
                <bk-form-item
                  :label="$t('环境')"
                  :rules="urlParamRules.environment_name"
                  :required="true"
                  :property="'environment_name'"
                >
                  <bk-select
                    v-model="curUrlParams.environment_name"
                    :clearable="false"
                    :disabled="addUrlDialog.isEdit"
                  >
                    <bk-option
                      v-for="(option, index) in envSelectList"
                      :id="option.id"
                      :key="index"
                      :name="option.text"
                    />
                  </bk-select>
                </bk-form-item>
                <bk-form-item
                  :label="$t('域名')"
                  :rules="urlParamRules.domain_name"
                  :required="true"
                  :property="'domain_name'"
                >
                  <bk-input
                    v-model="curUrlParams.domain_name"
                    :placeholder="domainInputPlaceholderText"
                  />
                </bk-form-item>
                <bk-form-item
                  :label="$t('路径')"
                  :rules="urlParamRules.path_prefix"
                  :required="true"
                  :property="'path_prefix'"
                >
                  <bk-input v-model="curUrlParams.path_prefix" />
                  <p class="paas-tip">
                    {{ $t('子路径仅支持配置一段') }}('/sub/'), {{ $t('不支持配置多段') }}('/sub/path/')
                  </p>
                </bk-form-item>
                <bk-form-item
                  :label="$t('绑定模块')"
                  :rules="urlParamRules.module_name"
                  :required="true"
                  :property="'module_name'"
                >
                  <bk-select
                    v-model="curUrlParams.module_name"
                    :clearable="false"
                    :disabled="addUrlDialog.isEdit"
                  >
                    <bk-option
                      v-for="option in curAppModuleList"
                      :id="option.name"
                      :key="option.name"
                      :name="option.name"
                    />
                  </bk-select>
                </bk-form-item>
              </bk-form>
            </template>
          </bk-dialog>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    let domainInputPlaceholderText = '';

    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                isInitLoading: true,
                isDomainLoading: false,
                domainConfig: {
                    enabled: false,
                    valid_domain_suffixes: [],
                    allow_user_modifications: true
                },
                domainList: [],
                envSelectList: [
                    { id: 'stag', text: this.$t('预发布环境') },
                    { id: 'prod', text: this.$t('生产环境') }
                ],
                curIngressIpConfigs: [],
                panels: [
                    { name: 'domain', label: this.$t('域名管理') },
                    { name: 'ipInfo', label: this.$t('IP 信息') }
                ],
                active: 'domain',
                requestQueue: ['domain', 'config'],
                domainConfigList: [],
                tableLoading: false,
                addUrlDialog: {
                    visiable: false,
                    isLoading: false,
                    showForm: false,
                    isEdit: false,
                    title: this.$t('添加域名')
                },
                urlParamRules: {
                    environment_name: [
                        {
                            required: true,
                            message: this.$t('请选择'),
                            trigger: 'blur'
                        }
                    ],
                    domain_name: [
                        {
                            required: true,
                            message: this.$t('域名不能为空'),
                            trigger: 'blur'
                        },
                        {
                            validator: value => {
                                const validDomainsPart = this.domainConfig.valid_domain_suffixes.join('|').replace('.', '\\.');
                                const domainReg = new RegExp('^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})*?(' + validDomainsPart + ')$');
                                return domainReg.test(value);
                            },
                            message: () => {
                                return `${this.$t('请输入有效域名，并以这些后缀结尾：')}${domainInputPlaceholderText}`;
                            },
                            trigger: 'blur'
                        }
                    ],
                    path_prefix: [
                        {
                            regex: /^\/[a-z-z0-9_-]*\/?$/,
                            message: `${this.$t('路径必须以')}"/"${this.$t('开头、且路径只能包含小写字母、数字、下划线(_)和连接符(-)')}`,
                            trigger: 'blur'
                        }
                    ],
                    module_name: [
                        {
                            required: true,
                            message: this.$t('请选择'),
                            trigger: 'blur'
                        }
                    ]
                },
                curUrlParams: {
                    environment_name: '',
                    domain_name: '',
                    path_prefix: '/',
                    module_name: '',
                    id: ''
                }
            };
        },
        computed: {
            // Valid domain suffix or not
            shouldValidateDomainSuffix () {
                return this.domainConfig.valid_domain_suffixes.length > 0;
            },
            // The place holder text for domain input element
            // eslint-disable-next-line vue/return-in-computed-property
            domainInputPlaceholderText () {
                if (this.domainConfig.valid_domain_suffixes.length) {
                    domainInputPlaceholderText = this.domainConfig.valid_domain_suffixes.join(',');
                    return this.$t('请输入有效域名，并以这些后缀结尾：') + domainInputPlaceholderText;
                }
                return this.$t('请输入有效域名');
            }
        },
        watch: {
            '$route' () {
                this.init();
            },
            domainList (list) {
                if (!list.length) {
                    this.addDomain();
                }
            },
            requestQueue (value) {
                const flag = value.length < 1;
                if (flag) {
                    this.isDomainLoading = false;
                    this.isInitLoading = false;
                    this.$emit('data-ready', 'domain-config');
                }
            }
        },
        created () {
            console.log('curAppModuleList', this.curAppModuleList);
            this.init();
        },
        methods: {
            init () {
                this.active = 'domain';
                this.curIngressIpConfigs = [];
                this.requestQueue = ['domain', 'config'];
                this.isDomainLoading = true;
                this.checkAppRegion();
                this.loadDomain();
                this.loadDomainConfig();
            },
            async checkAppRegion () {
                // Set domainConfig to default values
                this.domainConfig = {
                    enabled: false,
                    valid_domain_suffixes: [],
                    allow_user_modifications: true
                };
                try {
                    const region = this.curAppInfo.application.region;
                    const res = await this.$store.dispatch('getAppRegion', region);
                    // Update domain config
                    this.domainConfig = res.module_custom_domain;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },
            addDomain () {
                this.domainList.push({
                    id: -1,
                    isEdited: true,
                    domain_name: '',
                    environment_name: 'prod'
                });
            },
            loadDomainConfig () {
                this.$http.get(BACKEND_URL + '/api/bkapps/applications/' + this.appCode + '/custom_domains/config/').then(
                    res => {
                        this.curIngressIpConfigs = res;
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: `${this.$t('无法获取域名解析目标IP，错误：')}${res.detail}`
                        });
                    }
                ).finally(res => {
                    this.requestQueue.shift();
                });
            },
            loadDomain () {
                this.$http.get(BACKEND_URL + '/svc_workloads/api/services/applications/' + this.appCode + '/domains/').then(
                    res => {
                        this.domainConfigList = res;
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: `${this.$t('无法获取当前独立域名配置，错误：')}${res.detail}`
                        });
                    }
                ).finally(res => {
                    this.requestQueue.shift();
                });
            },
            editDomain (domain) {
                const input = this.getTargetInput(event.target);
                domain.isEdited = true;
                // 保存原来值，用到取消操作时返现
                domain.originDomain = domain.domain_name;
                this.$nextTick(() => {
                    input && input.focus();
                });
            },
            cancelDomain (domain, index) {
                if (domain.id === -1) {
                    this.domainList.splice(index, 1);
                } else {
                    domain.domain_name = domain.originDomain;
                    domain.isEdited = false;
                    delete domain.originDomain;
                }
            },
            getTargetInput (target) {
                let bkFormItem = null;
                while (target.offsetParent) {
                    target = target.offsetParent;
                    if (target.className === 'bk-form-item') {
                        bkFormItem = target;
                        break;
                    }
                }
                if (bkFormItem) {
                    return bkFormItem.querySelector('.bk-form-input');
                }
                return undefined;
            },
            submitDomain (domain, event) {
                const input = this.getTargetInput(event.target);
                if (!domain.domain_name) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请输入域名')
                    });
                    input && input.focus();
                    return false;
                }

                const domainRegString = '^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})*?(';
                let domainReg;
                if (this.shouldValidateDomainSuffix) {
                    // Construct domain regex
                    const validDomainsPart = this.domainConfig.valid_domain_suffixes.join('|').replace('.', '\\.');
                    domainReg = new RegExp(domainRegString + validDomainsPart + ')$');
                } else {
                    domainReg = new RegExp(domainRegString + ')$');
                }

                if (!domainReg.test(domain.domain_name)) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.domainInputPlaceholderText
                    });
                    input && input.focus();
                    return false;
                }

                if (domain.id === -1) {
                    this.createDomain(domain);
                } else {
                    this.updateDomain(domain);
                }
            },
            createDomain (domain) {
                const domainInfo = {
                    environment_name: domain.environment_name,
                    domain_name: domain.domain_name
                };
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/domain/`;
                this.$http.post(url, domainInfo).then(
                    res => {
                        domain.id = res.id;
                        domain.isEdited = false;

                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('添加成功')
                        });

                        this.loadDomain();
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: res.message
                        });
                    }
                );
            },
            updateDomain (domain) {
                const domainInfo = {
                    environment_name: domain.environment_name,
                    domain_name: domain.domain_name
                };
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/domain/${domain.id}/`;
                this.$http.put(url, domainInfo).then(
                    res => {
                        domain.id = res.id;
                        domain.isEdited = false;

                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('更新成功')
                        });

                        this.loadDomain();
                    },
                    res => {
                        const errorMsg = res.message;
                        this.$paasMessage({
                            theme: 'error',
                            message: `${this.$t('更新失败，错误：')}${errorMsg}`
                        });
                    }
                );
            },
            handleShowAddUrlDialog () {
                // this.$refs.addUrlForm.clear()
                this.addUrlDialog.visiable = true;
                this.addUrlDialog.showForm = true;
                this.curUrlParams = {
                    environment_name: '',
                    domain_name: '',
                    path_prefix: '/',
                    module_name: '',
                    id: ''
                };
            },
            cancelAddUrl () {
                this.addUrlDialog.showForm = false;
                this.addUrlDialog.visiable = false;
                this.addUrlDialog.isLoading = false;
                this.addUrlDialog.isEdit = false;
                this.addUrlDialog.title = '添加域名';
            },
            async addDomainUrl () {
                this.addUrlDialog.isLoading = true;
                this.$refs.addUrlForm.validate().then(async () => {
                    try {
                        const params = {
                            data: this.curUrlParams,
                            appCode: this.appCode
                        };
                        let fetchUrl = 'entryConfig/addDomainInfo';
                        if (this.curUrlParams.id) {
                            fetchUrl = 'entryConfig/updateDomainInfo';
                        }
                        await this.$store.dispatch(fetchUrl, params);
                        this.$paasMessage({
                            theme: 'success',
                            message: `${this.curUrlParams.id ? this.$t('更新') : this.$t('添加')}${this.$t('成功')}`
                        });
                        this.cancelAddUrl();
                        this.loadDomain();
                    } catch (e) {
                        this.addUrlDialog.isLoading = false;
                        this.$paasMessage({
                            theme: 'error',
                            message: e.message || e.detail || this.$t('接口异常')
                        });
                    }
                }).catch(() => {
                    this.addUrlDialog.isLoading = false;
                });
            },
            handleEdit (data) {
                this.curUrlParams = data;
                this.addUrlDialog.title = this.$t('编辑域名');
                this.addUrlDialog.visiable = true;
                this.addUrlDialog.showForm = true;
                this.addUrlDialog.isEdit = true;
            },
            handleDelete (domain, index) {
                const url = `${BACKEND_URL}/svc_workloads/api/services/applications/${this.appCode}/domains/${domain.id}/`;
                this.$http.delete(url).then(
                    res => {
                        this.$paasMessage({
                            theme: 'success',
                            message: this.$t('删除成功')
                        });
                        this.loadDomain();
                    },
                    res => {
                        const errorMsg = res.message;
                        this.$paasMessage({
                            theme: 'error',
                            message: `${this.$t('删除失败')},${errorMsg}`
                        });
                    }
                );
            },
            showRemoveModal (data, index) {
                this.$bkInfo({
                    title: this.$t('确定要删除该域名') + '?',
                    maskClose: true,
                    confirmFn: () => {
                        this.handleDelete(data);
                    }
                });
            },
            allIngressIpEqual (ipConfigs) {
              if (ipConfigs.length === 0) {
                return true;
              }
              let firstIngIp = ipConfigs[0].frontend_ingress_ip;
              for (let config of ipConfigs) {
                if (config.frontend_ingress_ip !== firstIngIp) {
                  return false;
                }
              }
              return true;
            }
        }
    };
</script>

<style lang="scss">
    .paas-domain-part-wrapper {
        h3 {
            line-height: 1;
            padding: 10px 0;
        }

        .domain-tab-cls {
            .bk-tab-section {
                padding: 0 !important;
            }
        }

        .content {
            // display: flex;

            .description {
                padding: 15px 5px;
                width: 35%;
                font-size: 13px;
                line-height: 20px;
            }

            .controller {
                width: 100%;
                padding: 20px 0px 0px 0;

                .bk-form {
                    margin-bottom: 10px;
                }
            }
        }

        .info-wrapper {
            margin-top: 20px;
            p {
                font-size: 12px;
                color: #979ba5;
            }
            p.title {
                margin-bottom: 5px;
                font-size: 14px;
                color: #313238;
                font-weight: bold;
            }
        }

    }
    .paas-tip{
        font-size: 12px;
        color: #979BA5;
    }
</style>
