<template>
  <div class="paasng-api-panel">
    <div class="search-wrapper flex-row justify-content-between">
      <div class="operate-buttons flex-row">
        <bk-button
          theme="primary"
          :disabled="isApplyDisabled"
          @click="handleBatchApply"
        >
          {{ $t('批量申请') }}
        </bk-button>
        <bk-button
          :disabled="isRenewalDisabled"
          @click="handleBatchRenwal"
        >
          {{ $t('批量续期') }}
        </bk-button>
        <template v-if="!isComponentApi">
          <bk-button
            v-if="!judgeIsApplyByGateway.allow_apply_by_api"
            disabled
          >
            <span
              v-if="judgeIsApplyByGateway.reason !== ''"
              v-bk-tooltips.top="judgeIsApplyByGateway.reason"
            >
              {{ $t('按网关申请') }}
            </span>
            <span v-else>{{ $t('按网关申请') }}</span>
          </bk-button>
          <bk-button
            v-else
            @click="handleApplyByGateway"
          >
            {{ $t('按网关申请') }}
          </bk-button>
        </template>
      </div>
      <div class="keyword-search">
        <bk-input
          v-model="searchValue"
          :placeholder="$t('输入API名称或描述，多个API以逗号分割')"
          clearable
          right-icon="paasng-icon paasng-search"
          @input="handleSearch"
        />
        <div
          :class="['advanced-filter', { en: localLanguage === 'en' }]"
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
              {{ $t('仅显示可申请 API') }}
            </bk-checkbox>
          </div>
          <div class="overflow shaixuan">
            <bk-checkbox
              v-model="listFilter.isRenew"
              :true-value="true"
              :false-value="false"
            >
              {{ $t('仅显示可续期 API') }}
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
          :outer-border="false"
          :header-border="false"
          :show-overflow-tooltip="true"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @filter-change="handleFilterChange"
          @selection-change="handleSelectionChange"
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
            type="selection"
            :selectable="selectable"
            width="60"
          ></bk-table-column>
          <bk-table-column
            label="API"
            min-width="180"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="props">
              <template v-if="props.row.doc_link">
                <a
                  target="_blank"
                  :href="props.row.doc_link"
                  class="api-link"
                >
                  <span v-dompurify-html="highlight(props.row)" />
                  <i
                    class="fa fa-book"
                    aria-hidden="true"
                  />
                </a>
              </template>
              <template v-else>
                <span
                  v-bk-overflow-tips
                  v-dompurify-html="highlight(props.row)"
                />
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('描述')"
            min-width="120"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="props">
              <span v-dompurify-html="highlightDesc(props.row)" />
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限等级')"
            :render-header="$renderHeader"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="props">
              <span :class="['special', 'sensitive'].includes(props.row.permission_level) ? 'sensitive' : ''">
                {{ levelMap[props.row.permission_level] }}
              </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限期限')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ getComputedExpires(props.row) }}
            </template>
          </bk-table-column>
          <template v-if="allData.length > 0">
            <bk-table-column
              :label="$t('状态')"
              prop="permission_status"
              column-key="permission_status"
              :filters="statusFilters"
              :filter-multiple="true"
              :min-width="110"
              :show-overflow-tooltip="true"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <template v-if="props.row.permission_status === 'owned'">
                  <span class="paasng-icon paasng-pass" />
                  {{ $t('已申请') }}
                </template>
                <template v-else-if="props.row.permission_status === 'unlimited'">
                  <span class="paasng-icon paasng-pass" />
                  {{ $t('无限制') }}
                </template>
                <template v-else-if="props.row.permission_status === 'need_apply'">
                  <span
                    style="color: #c4c6cc; margin-top: 1px"
                    class="paasng-icon paasng-info-line"
                  />
                  {{ $t('未申请') }}
                </template>
                <template v-else-if="props.row.permission_status === 'expired'">
                  <span class="paasng-icon paasng-reject" />
                  {{ $t('已过期') }}
                </template>
                <template v-else-if="props.row.permission_status === 'rejected'">
                  <span class="paasng-icon paasng-reject" />
                  {{ $t('已拒绝') }}
                </template>
                <template v-else>
                  <round-loading ext-cls="applying" />
                  <bk-popover placement="top">
                    {{ $t('申请中') }}
                    <div slot="content">
                      <template v-if="isComponentApi && GLOBAL.HELPER.href">
                        {{ $t('请联系') }}
                        <a
                          :href="GLOBAL.HELPER.href"
                          style="margin: 0 5px; border-bottom: 1px solid #3a84ff; cursor: pointer"
                        >
                          {{ GLOBAL.HELPER.name }}
                        </a>
                        {{ $t('审批') }}
                      </template>
                      <template v-else>
                        {{ $t('请联系{n}负责人审批：', { n: $t('网关') }) }} {{ maintainers.join('，') }}
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
            :min-width="110"
            :show-overflow-tooltip="true"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <template v-if="props.row.permission_status === 'owned'">
                <span class="paasng-icon paasng-pass" />
                {{ $t('已申请') }}
              </template>
              <template v-else-if="props.row.permission_status === 'unlimited'">
                <span class="paasng-icon paasng-pass" />
                {{ $t('无限制') }}
              </template>
              <template v-else-if="props.row.permission_status === 'need_apply'">
                <span class="paasng-icon paasng-reject" />
                {{ $t('未申请') }}
              </template>
              <template v-else-if="props.row.permission_status === 'expired'">
                <span class="paasng-icon paasng-reject" />
                {{ $t('已过期') }}
              </template>
              <template v-else-if="props.row.permission_status === 'rejected'">
                <span class="paasng-icon paasng-reject" />
                {{ $t('已拒绝') }}
              </template>
              <template v-else>
                <round-loading ext-cls="applying" />
                <bk-popover placement="top">
                  {{ $t('申请中') }}
                  <div slot="content">
                    <template v-if="isComponentApi && GLOBAL.HELPER.href">
                      {{ $t('请联系') }}
                      <a
                        :href="GLOBAL.HELPER.href"
                        style="margin: 0 5px; border-bottom: 1px solid #3a84ff; cursor: pointer"
                      >
                        {{ GLOBAL.HELPER.name }}
                      </a>
                      {{ $t('审批') }}
                    </template>
                    <template v-else>
                      {{ $t('请联系{n}负责人审批：', { n: $t('网关') }) }} {{ maintainers.join('，') }}
                    </template>
                  </div>
                </bk-popover>
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            :width="localLanguage === 'en' ? 130 : 110"
          >
            <template slot-scope="{ row }">
              <div class="table-operate-buttons">
                <bk-button
                  style="padding: 0 0 0 10px"
                  theme="primary"
                  :disabled="row.applyDisabled"
                  size="small"
                  text
                  @click="handleApply(row)"
                >
                  <span
                    v-bk-tooltips="{
                      content: $t(row.applyTips),
                      disabled: !row.applyDisabled,
                    }"
                  >
                    {{ $t('申请') }}
                  </span>
                </bk-button>
                <bk-button
                  style="padding: 0 0 0 10px"
                  theme="primary"
                  :disabled="row.renewDisabled"
                  size="small"
                  text
                  @click="handleRenwal(row)"
                >
                  <span
                    v-bk-tooltips="{
                      content: $t(row.renewTips),
                      disabled: !row.renewDisabled,
                    }"
                  >
                    {{ $t('续期') }}
                  </span>
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
import { formatApplyFun, formatRenewFun } from '@/common/cloud-api';

export default {
  name: '',
  components: {
    BatchDialog,
    RenewalDialog,
    GatewayDialog,
  },
  props: {
    apiType: {
      type: String,
    },
    id: {
      type: [String, Number],
      default: '',
    },
    name: {
      type: String,
      default: '',
    },
    maintainers: {
      type: Array,
      default: () => [],
    },
    isRefresh: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      loading: false,
      apiList: [],
      allData: [],
      tableList: [],
      searchValue: '',
      isFilter: false,
      pagination: {
        current: 1,
        limit: 10,
        count: 0,
      },
      allChecked: false,
      indeterminate: false,
      applyDialog: {
        visiable: false,
        title: '',
        rows: [],
      },

      renewalDialog: {
        visiable: false,
        title: '',
        rows: [],
      },

      isShowBatchRenewalDialog: false,
      isShowGatewayDialog: false,
      levelMap: {
        normal: this.$t('普通'),
        special: this.$t('特殊'),
        sensitive: this.$t('敏感'),
        unlimited: this.$t('无限制'),
      },
      requestQueue: ['list'],
      judgeIsApplyByGateway: {
        allow_apply_by_api: false,
        reason: '',
      },
      statusFilters: [
        { text: this.$t('已申请'), value: 'owned' },
        { text: this.$t('无限制'), value: 'unlimited' },
        { text: this.$t('未申请'), value: 'need_apply' },
        { text: this.$t('已过期'), value: 'expired' },
        { text: this.$t('已拒绝'), value: 'rejected' },
        { text: this.$t('申请中'), value: 'pending' },
      ],
      tableKey: -1,
      ifopen: false,
      listFilter: {
        isApply: false,
        isRenew: false,
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      filterStatus: [],
      filterData: [],
      selectedList: [],
    };
  },
  computed: {
    isComponentApi() {
      return this.apiType === 'component';
    },
    appCode() {
      return this.$route.params.id;
    },
    curFetchDispatchMethod() {
      return this.isComponentApi ? 'getComponents' : 'getResources';
    },
    // 是否允许批量申请
    isApplyDisabled() {
      return !this.selectedList.some((item) => item.applyDisabled === false);
    },
    // 是否允许批量续期
    isRenewalDisabled() {
      return !this.selectedList.some((item) => item.renewDisabled === false);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    'listFilter.isApply'(value) {
      if (value) {
        if (this.listFilter.isRenew) {
          this.allData = this.apiList.filter((item) => ['apply', 'renew'].includes(item.permission_action));
        } else {
          this.allData = this.apiList.filter((item) => item.permission_action === 'apply');
        }
      } else {
        if (this.listFilter.isRenew) {
          this.allData = this.apiList.filter((item) => item.permission_action === 'renew');
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

    'listFilter.isRenew'(value) {
      if (value) {
        if (this.listFilter.isApply) {
          this.allData = this.apiList.filter((item) => ['apply', 'renew'].includes(item.permission_action));
        } else {
          this.allData = this.apiList.filter((item) => item.permission_action === 'renew');
        }
      } else {
        if (this.listFilter.isApply) {
          this.allData = this.apiList.filter((item) => item.permission_action === 'apply');
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

    searchValue(newVal, oldVal) {
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
      handler(value) {
        // 强制刷新表格，为了重置表格过滤条件
        this.tableKey = +new Date();
        this.searchValue = '';
        this.judgeIsApplyByGateway = Object.assign(
          {},
          {
            allow_apply_by_api: false,
            reason: '',
          }
        );
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
      immediate: true,
    },
    isRefresh(value) {
      if (value) {
        this.querySelect();
      }
    },
    requestQueue(value) {
      if (value.length < 1) {
        this.$emit('data-ready');
      }
    },
    allData() {
      this.tableKey = +new Date();
    },
  },
  created() {
    this.compare = (p) => (m, n) => {
      const a = m[p].slice(0, 1).charCodeAt();
      const b = n[p].slice(0, 1).charCodeAt();
      return a - b;
    };
  },
  methods: {
    getComputedExpires(payload) {
      if (!payload.expires_in) {
        if (payload.permission_status === 'owned') {
          return this.$t('永久');
        }
        return '--';
      }
      return `${Math.ceil(payload.expires_in / (24 * 3600))}天`;
    },

    // 状态筛选
    handleFilterChange(filter) {
      this.filterStatus = filter.permission_status || [];
      // 重置
      if (this.filterStatus.length === 0) {
        this.filterData = this.allData;
      } else {
        this.filterData = this.allData.filter((item) => this.filterStatus.includes(item.permission_status));
      }
      this.pagination.current = 1;
      this.pagination.count = this.filterData.length;
      this.tableList = this.filterData.slice(
        (this.pagination.current - 1) * this.pagination.limit,
        this.pagination.current * this.pagination.limit
      );
    },

    handleClickOutside() {
      if (
        arguments[0].target.className.indexOf('advanced-filter') !== -1 ||
        arguments[0].target.className.indexOf('paasng-angle-double-down') !== -1 ||
        arguments[0].target.className.indexOf('paasng-angle-double-up') !== -1
      ) {
        return;
      }
      this.ifopen = false;
    },

    handleSuccessApply() {
      this.applyDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    handleApiSuccessApply() {
      this.isShowGatewayDialog = false;
      this.judgeIsApplyByGateway.allow_apply_by_api = false;
      this.judgeIsApplyByGateway.reason = this.$t('权限申请中，请联系网关负责人审批');
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    handleSuccessRenewal() {
      this.renewalDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    handleAfterLeave() {
      this.applyDialog = Object.assign(
        {},
        {
          visiable: false,
          title: '',
          rows: [],
        }
      );
    },

    handleRenewalAfterLeave() {
      this.renewalDialog = Object.assign(
        {},
        {
          visiable: false,
          title: '',
          rows: [],
        }
      );
    },

    afterApplyDialogClose() {
      this.applyDialog.name = '';
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
          const val = [
            ...this.apiList.filter(
              (api) => api.name.indexOf(searchArr[i]) !== -1 || api.description.indexOf(searchArr[i]) !== -1
            ),
          ];
          filterArr.push(...val);
        }
        // 结果去重
        filterArr = _.uniq(filterArr);
        this.allData = filterArr;
      } else {
        this.allData = [
          ...this.apiList.filter(
            (api) => api.name.indexOf(this.searchValue) !== -1 || api.description.indexOf(this.searchValue) !== -1
          ),
        ];
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
    querySelect() {
      const { query } = this.$route;
      if (!Object.keys(query).length) {
        return;
      }
      this.searchValue = query.api;
      this.handleSearch();
    },

    /**
     * 初始化弹层翻页条
     */
    initPageConf() {
      this.pagination.current = 1;
      const total = this.allData.length;
      this.pagination.count = total;
    },

    /**
     * 翻页回调
     *
     * @param {number} page 当前页
     */
    pageChange(page = 1) {
      this.allChecked = false;
      this.indeterminate = false;
      this.tableList.forEach((api) => {
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
    getDataByPage(page) {
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
      // 当前状态数据
      if (this.filterStatus.length) {
        return this.filterData.slice(startIndex, endIndex);
      }
      return this.allData.slice(startIndex, endIndex);
    },

    limitChange(currentLimit) {
      this.allChecked = false;
      this.indeterminate = false;
      this.tableList.forEach((api) => {
        if (api.hasOwnProperty('checked')) {
          api.checked = false;
        }
      });
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.pageChange(this.pagination.current);
    },

    async fetchList(payload) {
      this.allChecked = false;
      this.indeterminate = false;
      this.loading = true;
      try {
        const params = {
          appCode: this.appCode,
        };
        if (this.isComponentApi) {
          params.systemId = payload;
        } else {
          params.apiId = payload;
        }
        const res = await this.$store.dispatch(`cloudApi/${this.curFetchDispatchMethod}`, params);
        // this.apiList = Object.freeze(res.data.sort(this.compare('name')))
        // 网关api，申请/续期处理
        if (res.data.length) {
          res.data = res.data.map((v) => {
            // 申请
            const apply = formatApplyFun(v.permission_status);
            // 续期
            const renew = formatRenewFun(v.permission_status, v);
            return {
              ...v,
              applyDisabled: apply.disabled,
              applyTips: apply.tips,
              renewDisabled: renew.disabled,
              renewTips: renew.tips,
            };
          });
        }
        this.apiList = Object.freeze(res.data);
        this.allData = this.apiList;
        this.filterStatus = [];
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

    async fetchIsApplyByGateway(payload) {
      try {
        const params = {
          appCode: this.appCode,
          apiId: payload,
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

    handleApply(item) {
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('申请权限');
      this.applyDialog.rows = [item];
    },

    handleRenwal(item) {
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('权限续期');
      this.renewalDialog.rows = [item];
    },

    handleApplyByGateway() {
      this.isShowGatewayDialog = true;
    },

    handleBatchRenwal() {
      if (!this.selectedList.length) {
        return;
      }
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('批量续期权限');
      this.renewalDialog.rows = [...this.selectedList];
    },

    handleBatchApply() {
      if (!this.selectedList.length) {
        return;
      }
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('批量申请权限');
      this.applyDialog.rows = [...this.selectedList];
    },

    highlight({ name }) {
      if (this.isFilter && this.searchValue.trim()) {
        // 分割、过滤空字符、去除两端空格，最后转义特殊字符
        const keywords = this.searchValue
          .split(',')
          .filter((keyword) => keyword.trim() !== '')
          .map((keyword) => keyword.trim().replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'));

        if (keywords.length === 0) return name; // 如果没有关键词，直接返回原名

        // 创建正则表达式，'gi'代表全局匹配且忽略大小写
        const regex = new RegExp(`(${keywords.join('|')})`, 'gi');

        // 进行匹配和替换
        return name.replace(regex, (matched) => `<marked>${matched}</marked>`);
      }
      return name;
    },

    highlightDesc({ description }) {
      if (description !== '' && this.isFilter) {
        const descriptionArr = this.searchValue.split(',');
        for (let i = 0; i < descriptionArr.length; i++) {
          if (descriptionArr[i] !== '') {
            description = description.replace(
              new RegExp(descriptionArr[i], 'g'),
              `<marked>${descriptionArr[i]}</marked>`
            );
          }
        }
      } else {
        return '--';
      }
      return description || '--';
    },

    showChoose() {
      this.ifopen = true;
    },

    toggleChoose() {
      this.ifopen = !this.ifopen;
    },

    clearFilterKey() {
      this.searchValue = '';
      this.$refs.gatewayRef.clearFilter();
      // 清空表头筛选条件
      if (this.$refs.gatewayRef && this.$refs.gatewayRef.$refs.tableHeader) {
        const { tableHeader } = this.$refs.gatewayRef.$refs;
        clearFilter(tableHeader);
      }
      this.fetchList(this.id);
    },

    updateTableEmptyConfig() {
      this.tableEmptyConf.keyword = this.searchValue;
    },

    // 勾选是否禁用
    selectable(row) {
      return !row.applyDisabled || !row.renewDisabled;
    },

    // 表格change事件
    handleSelectionChange(selected) {
      this.selectedList = selected;
    },
  },
};
</script>

<style lang="scss" scoped>
.paasng-api-panel {
  .ml12 {
    margin-left: 12px;
  }
}
.search-wrapper {
  min-height: 32px;
  .operate-buttons {
    gap: 12px;
  }
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
  &.en {
    width: 92px;
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
  transition: all 0.5s;
}

.shaixuan {
  line-height: 32px;
}

.empty-tips {
  margin-top: 5px;
  color: #979ba5;
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
