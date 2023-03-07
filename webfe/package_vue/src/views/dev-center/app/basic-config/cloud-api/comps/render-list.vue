<template>
  <div class="paasng-api-panel">
    <div class="search-wrapper">
      <div class="operate-buttons fl">
        <bk-button
          theme="primary"
          :disabled="isApplyDisabled"
          @click="handleBatchApply"
        >
          {{ $t('批量申请') }}
        </bk-button>
        <bk-button
          style="margin-left: 6px;"
          :disabled="isRenewalDisabled"
          @click="handleBatchRenwal"
        >
          {{ $t('批量续期') }}
        </bk-button>
        <template v-if="!isComponentApi">
          <bk-button
            v-if="!judgeIsApplyByGateway.allow_apply_by_api"
            style="margin-left: 6px;"
            disabled
          >
            <span
              v-if="judgeIsApplyByGateway.reason !== ''"
              v-bk-tooltips.top="judgeIsApplyByGateway.reason"
            > {{ $t('按网关申请') }} </span>
            <span v-else> {{ $t('按网关申请') }} </span>
          </bk-button>
          <bk-button
            v-else
            style="margin-left: 6px;"
            @click="handleApplyByGateway"
          >
            {{ $t('按网关申请') }}
          </bk-button>
        </template>
      </div>
      <div class="keyword-search fr">
        <bk-input
          v-model="searchValue"
          :placeholder="$t('输入API名称或描述，多个API以逗号分割')"
          clearable
          right-icon="paasng-icon paasng-search"
          @input="handleSearch"
        />
        <div
          class="advanced-filter"
          @click.stop="toggleChoose"
        >
          <p>
            {{ $t('高级筛选') }}
            <i
              class="paasng-icon"
              :class="ifopen ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
            />
          </p>
        </div>
        <div
          v-if="ifopen"
          v-bk-clickoutside="handleClickOutside"
          class="choose-panel"
          @click.stop="showChoose"
        >
          <div class="overflow shaixuan">
            <bk-checkbox
              v-model="listFilter.isApply"
              :true-value="true"
              :false-value="false"
            >
              {{ $t('显示可申请权限') }}
            </bk-checkbox>
          </div>
          <div class="overflow shaixuan">
            <bk-checkbox
              v-model="listFilter.isRenew"
              :true-value="true"
              :false-value="false"
            >
              {{ $t('显示可续期权限') }}
            </bk-checkbox>
          </div>
        </div>
      </div>
    </div>
    <paas-content-loader
      :is-loading="loading"
      placeholder="cloud-api-inner-loading"
      :height="300"
    >
      <div class="spacing-x2">
        <bk-table
          ref="gatewayRef"
          :key="tableKey"
          :data="tableList"
          :size="'small'"
          :empty-text="$t('暂无数据')"
          :pagination="pagination"
          :show-pagination-info="true"
          :header-border="false"
          :show-overflow-tooltip="true"
          @page-change="pageChange"
          @page-limit-change="limitChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="fetchList(id)"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            label="id"
            :render-header="renderHeader"
            width="60"
          >
            <template slot-scope="props">
              <bk-checkbox
                v-model="props.row.checked"
                :true-value="true"
                :false-value="false"
                :disabled="!props.row.permission_action"
                @change="columChage(...arguments, props.row)"
              />
            </template>
          </bk-table-column>
          <bk-table-column
            label="API"
            min-width="180"
          >
            <template slot-scope="props">
              <template v-if="props.row.doc_link">
                <a
                  target="_blank"
                  :href="props.row.doc_link"
                  class="api-link"
                >
                  <span
                    v-html="highlight(props.row)"
                  />
                  <i
                    class="fa fa-book"
                    aria-hidden="true"
                  />
                </a>
              </template>
              <template v-else>
                <span
                  v-bk-overflow-tips
                  v-html="highlight(props.row)"
                />
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('描述')"
            min-width="120"
          >
            <template slot-scope="props">
              <!-- <span v-html="highlightDesc(props.row)" v-bk-tooltips="props.row.description"></span> -->
              <span v-html="highlightDesc(props.row)" />
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('权限等级')">
            <template slot-scope="props">
              <span :class="['special', 'sensitive'].includes(props.row.permission_level) ? 'sensitive' : ''">{{ levelMap[props.row.permission_level] }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('权限期限')">
            <template slot-scope="props">
              {{ getComputedExpires(props.row) }}
            </template>
          </bk-table-column>
          <template v-if="allData.length > 0">
            <bk-table-column
              :label="$t('状态')"
              prop="permission_status"
              :filters="statusFilters"
              :filter-method="statusFilterMethod"
              :filter-multiple="true"
              :min-width="110"
            >
              <template slot-scope="props">
                <template v-if="props.row.permission_status === 'owned'">
                  <span class="paasng-icon paasng-pass" /> {{ $t('已拥有') }}
                </template>
                <template v-else-if="props.row.permission_status === 'need_apply'">
                  <span
                    style="color: #C4C6CC;margin-top:1px;"
                    class="paasng-icon paasng-info-line"
                  /> {{ $t('未申请') }}
                </template>
                <template v-else-if="props.row.permission_status === 'expired'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已过期') }}
                </template>
                <template v-else-if="props.row.permission_status === 'rejected'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已拒绝') }}
                </template>
                <template v-else>
                  <round-loading ext-cls="applying" />
                  <bk-popover placement="top">
                    {{ $t('申请中') }}
                    <div slot="content">
                      <template v-if="isComponentApi && GLOBAL.HELPER.href">
                        {{ $t('请联系') }} <a
                          :href="GLOBAL.HELPER.href"
                          style="margin: 0 5px; border-bottom: 1px solid #3a84ff; cursor: pointer;"
                        >{{ GLOBAL.HELPER.name }}</a> {{ $t('审批') }}
                      </template>
                      <template v-else>
                        {{ $t('请联系网关负责人审批：') }} {{ maintainers.join('，') }}
                      </template>
                    </div>
                  </bk-popover>
                </template>
              </template>
            </bk-table-column>
          </template>
          <bk-table-column
            v-else
            :label="$t('状态')"
          >
            <template slot-scope="props">
              <template v-if="props.row.permission_status === 'owned'">
                <span class="paasng-icon paasng-pass" /> {{ $t('已拥有') }}
              </template>
              <template v-else-if="props.row.permission_status === 'need_apply'">
                <span class="paasng-icon paasng-reject" /> {{ $t('未申请') }}
              </template>
              <template v-else-if="props.row.permission_status === 'expired'">
                <span class="paasng-icon paasng-reject" /> {{ $t('已过期') }}
              </template>
              <template v-else-if="props.row.permission_status === 'rejected'">
                <span class="paasng-icon paasng-reject" /> {{ $t('已拒绝') }}
              </template>
              <template v-else>
                <round-loading ext-cls="applying" />
                <bk-popover placement="top">
                  {{ $t('申请中') }}
                  <div slot="content">
                    <template v-if="isComponentApi && GLOBAL.HELPER.href">
                      {{ $t('请联系') }} <a
                        :href="GLOBAL.HELPER.href"
                        style="margin: 0 5px; border-bottom: 1px solid #3a84ff; cursor: pointer;"
                      >{{ GLOBAL.HELPER.name }}</a> {{ $t('审批') }}
                    </template>
                    <template v-else>
                      {{ $t('请联系网关负责人审批：') }} {{ maintainers.join('，') }}
                    </template>
                  </div>
                </bk-popover>
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="110"
          >
            <template slot-scope="props">
              <div class="table-operate-buttons">
                <bk-button
                  style="padding: 0 0 0 10px;"
                  theme="primary"
                  :disabled="props.row.permission_action !== 'apply'"
                  size="small"
                  text
                  @click="handleApply(props.row)"
                >
                  <template v-if="props.row.permission_action !== 'apply'">
                    <span v-bk-tooltips="props.row.permission_status === 'pending' ? $t('权限申请中') : $t('已拥有权限')"> {{ $t('申请') }} </span>
                  </template>
                  <span v-else> {{ $t('申请') }} </span>
                </bk-button>
                <bk-button
                  style="padding: 0 0 0 10px;"
                  theme="primary"
                  :disabled="props.row.permission_action !== 'renew'"
                  size="small"
                  text
                  @click="handleRenwal(props.row)"
                >
                  <template v-if="props.row.permission_action !== 'renew'">
                    <span v-bk-tooltips="$t('无权限，或权限有效期大于30天')"> {{ $t('续期') }} </span>
                  </template>
                  <span v-else> {{ $t('续期') }} </span>
                </bk-button>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <batch-dialog
      :show.sync="applyDialog.visiable"
      :title="applyDialog.title"
      :rows="applyDialog.rows"
      :api-id="id"
      :api-name="name"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-apply="handleSuccessApply"
      @after-leave="handleAfterLeave"
    />
    <renewal-dialog
      :show.sync="renewalDialog.visiable"
      :title="renewalDialog.title"
      :rows="renewalDialog.rows"
      :api-name="name"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-renewal="handleSuccessRenewal"
      @after-leave="handleRenewalAfterLeave"
    />
    <gateway-dialog
      :show.sync="isShowGatewayDialog"
      :api-id="id"
      :api-name="name"
      :app-code="appCode"
      @on-api-apply="handleApiSuccessApply"
    />
  </div>
</template>

<script>
    import _ from 'lodash';
    import BatchDialog from './batch-apply-dialog';
    import RenewalDialog from './batch-renewal-dialog';
    import GatewayDialog from './apply-by-gateway-dialog';
    import { clearFilter } from '@/common/utils';
    export default {
        name: '',
        components: {
            BatchDialog,
            RenewalDialog,
            GatewayDialog
        },
        props: {
            apiType: {
                type: String
            },
            id: {
                type: [String, Number],
                default: ''
            },
            name: {
                type: String,
                default: ''
            },
            maintainers: {
                type: Array,
                default: () => []
            },
            isRefresh: {
                type: Boolean,
                default: false
            }
        },
        data () {
            return {
                loading: false,
                apiList: [],
                allData: [],
                tableList: [],
                selectedAPIList: [],
                searchValue: '',
                isFilter: false,
                pagination: {
                    current: 1,
                    limit: 10,
                    count: 0
                },
                allChecked: false,
                indeterminate: false,
                applyDialog: {
                    visiable: false,
                    title: '',
                    rows: []
                },

                renewalDialog: {
                    visiable: false,
                    title: '',
                    rows: []
                },

                isShowBatchRenewalDialog: false,
                isShowGatewayDialog: false,
                levelMap: {
                    normal: this.$t('普通'),
                    special: this.$t('特殊'),
                    sensitive: this.$t('敏感'),
                    unlimited: this.$t('无限制')
                },
                requestQueue: ['list'],
                judgeIsApplyByGateway: {
                    allow_apply_by_api: false,
                    reason: ''
                },
                statusFilters: [
                    { text: this.$t('已拥有'), value: 'owned' },
                    { text: this.$t('未申请'), value: 'need_apply' },
                    { text: this.$t('已过期'), value: 'expired' },
                    { text: this.$t('已拒绝'), value: 'rejected' },
                    { text: this.$t('申请中'), value: 'pending' }
                ],
                tableKey: -1,
                ifopen: false,
                listFilter: {
                    isApply: false,
                    isRenew: false
                },
                tableEmptyConf: {
                    keyword: '',
                    isAbnormal: false
                }
            };
        },
        computed: {
            isComponentApi () {
                return this.apiType === 'component';
            },
            appCode () {
                return this.$route.params.id;
            },
            isPageDisabled () {
                return this.tableList.every(item => !item.permission_action) || !this.tableList.length;
            },
            curFetchDispatchMethod () {
                return this.isComponentApi ? 'getComponents' : 'getResources';
            },
            isApplyDisabled () {
                return !this.selectedAPIList.some(item => item.permission_action === 'apply');
            },
            isRenewalDisabled () {
                return !this.selectedAPIList.some(item => item.permission_action === 'renew');
            }
        },
        watch: {
            'listFilter.isApply' (value) {
                if (value) {
                    if (this.listFilter.isRenew) {
                        this.allData = this.apiList.filter(item => ['apply', 'renew'].includes(item.permission_action));
                    } else {
                        this.allData = this.apiList.filter(item => item.permission_action === 'apply');
                    }
                } else {
                    if (this.listFilter.isRenew) {
                        this.allData = this.apiList.filter(item => item.permission_action === 'renew');
                    } else {
                        this.allData = this.apiList;
                    }
                }
                this.pagination.count = this.allData.length;
                this.pagination.current = 1;
                const start = this.pagination.limit * (this.pagination.current - 1);
                const end = start + this.pagination.limit;
                this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
            },

            'listFilter.isRenew' (value) {
                if (value) {
                    if (this.listFilter.isApply) {
                        this.allData = this.apiList.filter(item => ['apply', 'renew'].includes(item.permission_action));
                    } else {
                        this.allData = this.apiList.filter(item => item.permission_action === 'renew');
                    }
                } else {
                    if (this.listFilter.isApply) {
                        this.allData = this.apiList.filter(item => item.permission_action === 'apply');
                    } else {
                        this.allData = this.apiList;
                    }
                }
                this.pagination.count = this.allData.length;
                this.pagination.current = 1;
                const start = this.pagination.limit * (this.pagination.current - 1);
                const end = start + this.pagination.limit;
                this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
            },

            searchValue (newVal, oldVal) {
                if (newVal === '' && oldVal !== '' && this.isFilter) {
                    this.allData = this.apiList;
                    this.pagination.count = this.apiList.length;
                    this.pagination.current = 1;
                    const start = this.pagination.limit * (this.pagination.current - 1);
                    const end = start + this.pagination.limit;
                    this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
                    this.isFilter = false;
                }
            },
            id: {
                handler (value) {
                    // 强制刷新表格，为了重置表格过滤条件
                    this.tableKey = +new Date();
                    this.searchValue = '';
                    this.judgeIsApplyByGateway = Object.assign({}, {
                        allow_apply_by_api: false,
                        reason: ''
                    });
                    if (!value) {
                        this.requestQueue = [];
                        this.$emit('data-ready');
                    } else {
                        if (this.isComponentApi) {
                            this.requestQueue = ['list'];
                        } else {
                            this.requestQueue = ['list', 'flag'];
                        }
                        this.fetchList(value);
                        if (!this.isComponentApi) {
                            this.fetchIsApplyByGateway(value);
                        }
                    }
                },
                immediate: true
            },
            isRefresh (value) {
                if (value) {
                    this.querySelect();
                }
            },
            requestQueue (value) {
                if (value.length < 1) {
                    this.$emit('data-ready');
                }
            },
            allData (value) {
                const list = [
                    { text: this.$t('已拥有'), value: 'owned' },
                    { text: this.$t('未申请'), value: 'need_apply' },
                    { text: this.$t('已过期'), value: 'expired' },
                    { text: this.$t('已拒绝'), value: 'rejected' },
                    { text: this.$t('申请中'), value: 'pending' }
                ];
                this.statusFilters = list.filter(item => {
                    return this.allData.map(_ => _.permission_status).includes(item.value);
                });
                this.tableKey = +new Date();
            }
        },
        created () {
            this.compare = p => {
                return (m, n) => {
                    const a = m[p].slice(0, 1).charCodeAt();
                    const b = n[p].slice(0, 1).charCodeAt();
                    return a - b;
                };
            };
        },
        methods: {
            getComputedExpires (payload) {
                if (!payload.expires_in) {
                    if (payload.permission_status === 'owned') {
                        return this.$t('永久');
                    }
                    return '--';
                }
                return `${Math.ceil(payload.expires_in / (24 * 3600))}天`;
            },

            statusFilterMethod (value, row, column) {
                const property = column.property;
                return row[property] === value;
            },

            handleClickOutside () {
                if (arguments[0]['target']['className'].indexOf('advanced-filter') !== -1 ||
                    arguments[0]['target']['className'].indexOf('paasng-angle-double-down') !== -1 ||
                    arguments[0]['target']['className'].indexOf('paasng-angle-double-up') !== -1) {
                    return;
                }
                this.ifopen = false;
            },

            handleSuccessApply () {
                this.applyDialog.visiable = false;
                this.allChecked = false;
                this.indeterminate = false;
                this.fetchList(this.id);
            },

            handleApiSuccessApply () {
                this.isShowGatewayDialog = false;
                this.judgeIsApplyByGateway.allow_apply_by_api = false;
                this.judgeIsApplyByGateway.reason = this.$t('权限申请中，请联系网关负责人审批');
                this.allChecked = false;
                this.indeterminate = false;
                this.fetchList(this.id);
            },

            handleSuccessRenewal () {
                this.renewalDialog.visiable = false;
                this.allChecked = false;
                this.indeterminate = false;
                this.fetchList(this.id);
            },

            handleAfterLeave () {
                this.applyDialog = Object.assign({}, {
                    visiable: false,
                    title: '',
                    rows: []
                });
            },

            handleRenewalAfterLeave () {
                this.renewalDialog = Object.assign({}, {
                    visiable: false,
                    title: '',
                    rows: []
                });
            },

            afterApplyDialogClose () {
                this.applyDialog.name = '';
            },

            columChage (newVal, modelVal, trueVal, item) {
                if (newVal) {
                    this.selectedAPIList.push(item);
                } else {
                    const len = this.selectedAPIList.length;
                    for (let i = 0; i < len; i++) {
                        if (item.id === this.selectedAPIList[i].id) {
                            this.selectedAPIList.splice(i, 1);
                            break;
                        }
                    }
                }
                this.indeterminate = !!this.selectedAPIList.length && this.selectedAPIList.length < this.tableList.filter(api => api.status !== 'pending' && api.status !== 'owned').length;
                this.allChecked = this.selectedAPIList.length === this.tableList.filter(api => api.status !== 'pending' && api.status !== 'owned').length && !!this.tableList.length;
            },

            tableAllClick () {
                if (this.isPageDisabled) {
                    return;
                }

                this.allChecked = !this.allChecked;
                if (this.allChecked) {
                    this.indeterminate = false;
                    this.selectedAPIList.splice(0, this.selectedAPIList.length, ...this.tableList.filter(api => api.status !== 'pending' && api.status !== 'owned' && !!api.permission_action));
                } else {
                    this.selectedAPIList.splice(0, this.selectedAPIList.length, ...[]);
                }
                this.tableList.forEach(api => {
                    if (api.permission_action) {
                        this.$set(api, 'checked', this.allChecked);
                    }
                });
            },

            renderHeader (h, { column }) {
                return h(
                    'div',
                    [
                        h('bk-checkbox', {
                            style: 'margin-right: 10px;',
                            props: {
                                disabled: this.isPageDisabled,
                                indeterminate: this.indeterminate,
                                checked: this.allChecked
                            },
                            nativeOn: {
                                click: () => this.tableAllClick()
                            }
                        })
                    ]
                );
            },

            handleSearch: _.debounce(function () {
                if (this.searchValue === '') {
                    return;
                }
                this.isFilter = true;
                // 多个API过滤
                if (this.searchValue.indexOf(',') !== -1) {
                    let searchArr = this.searchValue.split(',');
                    searchArr = _.uniq(searchArr);
                    let filterArr = [];
                    for (let i = 0; i < searchArr.length; i++) {
                        if (searchArr[i] === '') {
                            continue;
                        }
                        const val = [...this.apiList.filter(api => {
                            return api.name.indexOf(searchArr[i]) !== -1 || api.description.indexOf(searchArr[i]) !== -1;
                        })];
                        filterArr.push(...val);
                    }
                    // 结果去重
                    filterArr = _.uniq(filterArr);
                    this.allData = filterArr;
                } else {
                    this.allData = [...this.apiList.filter(api => {
                        return api.name.indexOf(this.searchValue) !== -1 || api.description.indexOf(this.searchValue) !== -1;
                    })];
                }
                this.pagination.count = this.allData.length;

                this.pagination.current = 1;

                const start = this.pagination.limit * (this.pagination.current - 1);
                const end = start + this.pagination.limit;
                this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
                this.updateTableEmptyConfig();
            }, 350),

            /**
             * 根据query参数选择对应网关
             */
            querySelect () {
                const query = this.$route.query;
                if (!Object.keys(query).length) {
                    return;
                }
                this.searchValue = query.api;
                this.handleSearch();
            },

            /**
             * 初始化弹层翻页条
             */
            initPageConf () {
                this.pagination.current = 1;
                const total = this.allData.length;
                this.pagination.count = total;
            },

            /**
             * 翻页回调
             *
             * @param {number} page 当前页
             */
            pageChange (page = 1) {
                this.allChecked = false;
                this.indeterminate = false;
                this.selectedAPIList = [];
                this.tableList.forEach(api => {
                    if (api.hasOwnProperty('checked')) {
                        api.checked = false;
                    }
                });
                this.pagination.current = page;
                const data = this.getDataByPage(page);
                this.tableList.splice(0, this.tableList.length, ...data);
            },

            /**
             * 获取当前这一页的数据
             *
             * @param {number} page 当前页
             *
             * @return {Array} 当前页数据
             */
            getDataByPage (page) {
                if (!page) {
                    this.pagination.current = page = 1;
                }
                let startIndex = (page - 1) * this.pagination.limit;
                let endIndex = page * this.pagination.limit;
                if (startIndex < 0) {
                    startIndex = 0;
                }
                if (endIndex > this.allData.length) {
                    endIndex = this.allData.length;
                }
                return this.allData.slice(startIndex, endIndex);
            },

            limitChange (currentLimit, prevLimit) {
                this.allChecked = false;
                this.indeterminate = false;
                this.selectedAPIList = [];
                this.tableList.forEach(api => {
                    if (api.hasOwnProperty('checked')) {
                        api.checked = false;
                    }
                });
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;
                this.pageChange(this.pagination.current);
            },

            async fetchList (payload) {
                this.allChecked = false;
                this.indeterminate = false;
                this.selectedAPIList = [];
                this.loading = true;
                try {
                    const params = {
                        appCode: this.appCode
                    };
                    if (this.isComponentApi) {
                        params.systemId = payload;
                    } else {
                        params.apiId = payload;
                    }
                    const res = await this.$store.dispatch(`cloudApi/${this.curFetchDispatchMethod}`, params);
                    // this.apiList = Object.freeze(res.data.sort(this.compare('name')))
                    this.apiList = Object.freeze(res.data);
                    this.allData = this.apiList;
                    this.initPageConf();
                    this.tableList = this.getDataByPage();
                    this.updateTableEmptyConfig();
                    this.tableEmptyConf.isAbnormal = false;
                } catch (e) {
                    this.tableEmptyConf.isAbnormal = true;
                    this.catchErrorHandler(e);
                } finally {
                    this.loading = false;
                    if (this.requestQueue.length > 0) {
                        this.requestQueue.shift();
                    }
                    this.handleSearch();
                }
            },

            async fetchIsApplyByGateway (payload) {
                try {
                    const params = {
                        appCode: this.appCode,
                        apiId: payload
                    };
                    const res = await this.$store.dispatch('cloudApi/getAllowApplyByApi', params);
                    this.judgeIsApplyByGateway = res.data;
                } catch (e) {
                    console.warn(e);
                } finally {
                    if (this.requestQueue.length > 0) {
                        this.requestQueue.shift();
                    }
                }
            },

            handleApply (item) {
                this.applyDialog.visiable = true;
                this.applyDialog.title = this.$t('申请权限');
                this.applyDialog.rows = [item];
            },

            handleRenwal (item) {
                this.renewalDialog.visiable = true;
                this.renewalDialog.title = this.$t('权限续期');
                this.renewalDialog.rows = [item];
            },

            handleApplyByGateway () {
                this.isShowGatewayDialog = true;
            },

            handleBatchRenwal () {
                if (!this.selectedAPIList.length) {
                    return;
                }
                this.renewalDialog.visiable = true;
                this.renewalDialog.title = this.$t('批量续期权限');
                const applyRows = this.selectedAPIList.filter(item => item.permission_action === 'apply');
                const renewalRows = this.selectedAPIList.filter(item => item.permission_action === 'renew');
                this.renewalDialog.rows = renewalRows.concat(applyRows);
            },

            handleBatchApply () {
                if (!this.selectedAPIList.length) {
                    return;
                }
                this.applyDialog.visiable = true;
                this.applyDialog.title = this.$t('批量申请权限');
                const applyRows = this.selectedAPIList.filter(item => item.permission_action === 'apply');
                const renewalRows = this.selectedAPIList.filter(item => item.permission_action === 'renew');
                this.applyDialog.rows = applyRows.concat(renewalRows);
            },

            highlight ({ name }) {
                if (this.isFilter) {
                    const searchValueArr = this.searchValue.split(',');
                    for (let i = 0; i < searchValueArr.length; i++) {
                        if (searchValueArr[i] !== '') {
                            name = name.replace(new RegExp(searchValueArr[i], 'g'), `<marked>${searchValueArr[i]}</marked>`);
                        }
                    }
                }
                return name;
            },

            highlightDesc ({ description }) {
                if (description !== '' && this.isFilter) {
                    const descriptionArr = this.searchValue.split(',');
                    for (let i = 0; i < descriptionArr.length; i++) {
                        if (descriptionArr[i] !== '') {
                            description = description.replace(new RegExp(descriptionArr[i], 'g'), `<marked>${descriptionArr[i]}</marked>`);
                        }
                    }
                } else {
                    return '--';
                }
                return description || '--';
            },

            showChoose () {
                this.ifopen = true;
            },

            toggleChoose () {
                this.ifopen = !this.ifopen;
            },

            clearFilterKey () {
                this.searchValue = '';
                this.$refs.gatewayRef.clearFilter();
                // 清空表头筛选条件
                if (this.$refs.gatewayRef && this.$refs.gatewayRef.$refs.tableHeader) {
                    const tableHeader = this.$refs.gatewayRef.$refs.tableHeader;
                    clearFilter(tableHeader);
                }
                this.fetchList(this.id);
            },

            updateTableEmptyConfig () {
                this.tableEmptyConf.keyword = this.searchValue;
            }
        }
    };
</script>

<style lang="scss" scoped>
    .search-wrapper {
        min-height: 32px;
        .keyword-search {
            display: flex;
            width: 385px;
        }
        .apply-tips {
            font-size: 12px;
            i {
                margin-right: 3px;
            }
        }
    }

    .table-operate-buttons {
        position: relative;
        left: -12px;
    }

    span.sensitive {
        color: #ff0000;
    }

    span.paasng-pass {
        position: relative;
        top: 1px;
        color: #2dcb56;
        font-size: 14px;
    }

    span.paasng-reject {
        position: relative;
        top: 1px;
        color: #ea3636;
        font-size: 14px;
    }

    .applying {
        position: relative;
        top: -1px;
    }

    .advanced-filter {
        width: 160px;
        height: 32px;
        line-height: 30px;
        margin-left: -1px;
        border: 1px solid #c4c6cc;
        border-radius: 0 2px 2px 0;
        background: #fff;
        cursor: pointer;
        z-index: 1;
        &:hover {
            color: #3a84ff;
        }
        p {
            padding-left: 14px;
            .paasng-icon {
                font-size: 12px;
            }
        }
    }

    div.choose-panel {
        input {
            appearance: none;
        }
    }

    .choose-panel {
        padding-left: 10px;
        position: absolute;
        right: 0;
        top: 35px;
        width: 228px;
        border-top: solid 1px #e9edee;
        box-shadow: 0 2px 5px #e5e5e5;
        background: #fff;
        height: auto;
        overflow: hidden;
        z-index: 99;
        transition: all .5s;
    }

    .shaixuan {
        line-height: 32px;
    }

    .empty-tips {
        margin-top: 5px;
        color: #979BA5;
        .clear-search {
            cursor: pointer;
            color: #3a84ff;
        }
    }
    .api-link {
        display: inline-block;
        width: 100%;
        & span {
            display: inline-block;
            width: 100%;
            display: inline-block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }
</style>

<style>
    marked {
        background: yellow;
        color: black;
    }
    .bk-plugin-wrapper .exception-wrap-item .bk-exception-img.part-img {
        height: 130px;
    }
    .bk-plugin-wrapper .bk-table th .bk-table-column-filter-trigger.is-filtered {
        color: #3a84ff !important;
    }
</style>
