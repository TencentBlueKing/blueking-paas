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
            v-if="!judgeIsApplyByGateway.allow_apply_by_gateway"
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
      placeholder="table-loading"
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
              :condition="searchValue"
              :is-error="isTableError"
              @reacquire="fetchList(id)"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            label="id"
            type="selection"
            :selectable="selectable"
            :reserve-selection="true"
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
          <bk-table-column
            :label="$t('状态')"
            v-bind="statusColumnBindings"
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
                  :class="needApplyStatusIconClass"
                  :style="needApplyStatusIconStyle"
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
      :api-name="name"
      :app-code="appCode"
      @on-api-apply="handleApiSuccessApply"
    />
  </div>
</template>

<script>
import { mapState } from 'vuex';
import { debounce, uniq } from 'lodash';
import BatchDialog from './batch-apply-dialog';
import RenewalDialog from './batch-renewal-dialog';
import GatewayDialog from './apply-by-gateway-dialog';
import { clearFilter } from '@/common/utils';
import { formatApplyFun, formatRenewFun } from '@/common/cloud-api';
import { updateHeaderCheckboxState } from './table-utils';

export default {
  name: 'CloudApiRenderList',
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

      isShowGatewayDialog: false,
      levelMap: {
        normal: this.$t('普通'),
        special: this.$t('特殊'),
        sensitive: this.$t('敏感'),
        unlimited: this.$t('无限制'),
      },
      requestQueue: ['list'],
      judgeIsApplyByGateway: {
        // v2 字段更名: allow_apply_by_api -> allow_apply_by_gateway
        allow_apply_by_gateway: false,
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
      isTableError: false,
      filterStatus: [],
      filterData: [],
      selectedList: [],
      listRequestId: 0,
      applyByGatewayRequestId: 0,
    };
  },
  computed: {
    ...mapState(['localLanguage']),
    // 是否为组件 API 类型（非网关 API）
    isComponentApi() {
      return this.apiType === 'component';
    },
    appCode() {
      return this.$route.params.id;
    },
    curFetchDispatchMethod() {
      return this.isComponentApi ? 'getComponents' : 'getResources';
    },
    // 是否禁用批量申请按钮
    isApplyDisabled() {
      return !this.selectedList.some((item) => item.applyDisabled === false);
    },
    // 是否禁用批量续期按钮
    isRenewalDisabled() {
      return !this.selectedList.some((item) => item.renewDisabled === false);
    },
    statusColumnBindings() {
      if (this.allData.length > 0) {
        return {
          prop: 'permission_status',
          'column-key': 'permission_status',
          filters: this.statusFilters,
          'filter-multiple': true,
        };
      }
      return {};
    },
    // 未申请状态图标的 CSS 类名
    needApplyStatusIconClass() {
      if (this.allData.length > 0) {
        return 'paasng-icon paasng-info-line';
      }
      return 'paasng-icon paasng-reject';
    },
    needApplyStatusIconStyle() {
      if (this.allData.length > 0) {
        return { color: '#c4c6cc', marginTop: '1px' };
      }
      return {};
    },
  },
  watch: {
    // 「仅显示可申请」勾选变化
    'listFilter.isApply'() {
      this.updatePermissionActionFilter();
    },

    // 「仅显示可续期」勾选变化
    'listFilter.isRenew'() {
      this.updatePermissionActionFilter();
    },

    searchValue(newVal, oldVal) {
      if (newVal === '' && oldVal !== '' && this.isFilter) {
        this.allData = this.apiList;
        this.resetPaginationByData();
        this.updateTableListByPage();
        this.isFilter = false;
      }
    },
    // 监听网关/系统 ID 变化，刷新表格数据并重置状态
    id: {
      handler(value) {
        // 强制刷新表格，为了重置表格过滤条件
        this.tableKey = +new Date();
        this.searchValue = '';
        this.resetTableState();
        this.judgeIsApplyByGateway = Object.assign(
          {},
          {
            allow_apply_by_gateway: false,
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
    /**
     * 计算权限到期剩余天数
     * @param {Object} payload - API 数据对象
     * @param {number|undefined} payload.expires_in - 到期剩余秒数
     * @param {string} payload.permission_status - 权限状态
     * @returns {string} 剩余天数文本，「永久」或「--」
     */
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
      this.resetPaginationByData(this.filterData);
      this.updateTableListByPage();
    },

    /**
     * 点击高级筛选区域外部时关闭筛选面板
     * @param {Event} event - 点击事件对象
     */
    handleClickOutside(event) {
      if (
        event.target.className.indexOf('advanced-filter') !== -1 ||
        event.target.className.indexOf('paasng-angle-double-down') !== -1 ||
        event.target.className.indexOf('paasng-angle-double-up') !== -1
      ) {
        return;
      }
      this.ifopen = false;
    },

    /**
     * 申请权限成功后的回调：关闭弹窗，重置勾选状态，刷新列表
     */
    handleSuccessApply() {
      this.applyDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    /**
     * 按网关申请成功后的回调：关闭弹窗，更新网关申请状态，刷新列表
     */
    handleApiSuccessApply() {
      this.isShowGatewayDialog = false;
      this.judgeIsApplyByGateway.allow_apply_by_gateway = false;
      this.judgeIsApplyByGateway.reason = this.$t('权限申请中，请联系网关负责人审批');
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    /**
     * 续期成功后的回调：关闭弹窗，重置勾选状态，刷新列表
     */
    handleSuccessRenewal() {
      this.renewalDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    /**
     * 申请弹窗关闭后的回调：重置申请弹窗数据
     */
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

    /**
     * 续期弹窗关闭后的回调：重置续期弹窗数据
     */
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

    /**
     * 根据高级筛选选项（仅显示可申请/可续期）过滤 API 列表
     */
    updatePermissionActionFilter() {
      const { isApply, isRenew } = this.listFilter;
      const actions = [];

      if (isApply) {
        actions.push('apply');
      }
      if (isRenew) {
        actions.push('renew');
      }

      this.allData = actions.length
        ? this.apiList.filter((item) => actions.includes(item.permission_action))
        : this.apiList;
      this.resetPaginationByData();
      this.updateTableListByPage();
    },

    /**
     * 关键字搜索 API（防抖 350ms）
     * 支持逗号分隔多个关键词搜索，匹配 API 名称和描述
     */
    handleSearch: debounce(function () {
      if (this.searchValue === '') {
        return;
      }
      this.isFilter = true;
      // 多个API过滤
      if (this.searchValue.indexOf(',') !== -1) {
        let searchArr = this.searchValue.split(',');
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
        filterArr = uniq(filterArr);
        this.allData = filterArr;
      } else {
        this.allData = [
          ...this.apiList.filter(
            (api) => api.name.indexOf(this.searchValue) !== -1 || api.description.indexOf(this.searchValue) !== -1
          ),
        ];
      }
      this.resetPaginationByData();
      this.updateTableListByPage();
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
      this.resetPaginationByData();
    },

    /**
     * 根据数据重置分页器（回到第一页）
     * @param {Array} data - 数据源，默认为 allData
     */
    resetPaginationByData(data = this.allData) {
      this.pagination.current = 1;
      this.pagination.count = data.length;
    },

    /**
     * 根据页码更新当前页的表格数据
     * @param {number} page - 页码，默认为当前页
     */
    updateTableListByPage(page = this.pagination.current) {
      this.tableList.splice(0, this.tableList.length, ...this.getDataByPage(page));
    },

    /**
     * 重置表格所有状态
     */
    resetTableState() {
      this.apiList = [];
      this.allData = [];
      this.tableList = [];
      this.filterData = [];
      this.filterStatus = [];
      this.selectedList = [];
      this.pagination.current = 1;
      this.pagination.count = 0;
      this.allChecked = false;
      this.indeterminate = false;
      this.isFilter = false;
      this.isTableError = false;
    },

    /**
     * 生成当前网关/系统的唯一选择标识 key
     * 组件 API：直接使用 id
     * 网关 API：使用 id:name 组合
     * @param {string|number} id - 网关/系统 ID
     * @param {string} name - 网关名称
     * @returns {string} 唯一标识 key
     */
    getSelectionKey(id = this.id, name = this.name) {
      return this.isComponentApi ? String(id) : `${String(id)}:${name}`;
    },

    /**
     * 创建请求上下文，用于避免慢请求覆盖快请求的结果
     * @param {string} requestIdKey - 请求 ID 对应的 data 属性名
     * @param {string|number} id - 网关/系统 ID
     * @returns {{id: number, gatewayName: string, selectionKey: string}} 请求上下文
     */
    createRequestContext(requestIdKey, id = this.id) {
      this[requestIdKey] += 1;
      const gatewayName = this.name;
      return {
        id: this[requestIdKey],
        gatewayName,
        selectionKey: this.getSelectionKey(id, gatewayName),
      };
    },

    /**
     * 判断是否为最新一次请求，防止慢网络下旧请求返回覆盖新数据
     * @param {string} requestIdKey - 请求 ID 对应的 data 属性名
     * @param {{id: number, selectionKey: string}} requestContext - 请求上下文
     * @returns {boolean} 是否为最新请求
     */
    isLatestRequest(requestIdKey, requestContext) {
      return requestContext.id === this[requestIdKey] && requestContext.selectionKey === this.getSelectionKey();
    },

    /**
     * 翻页回调
     *
     * @param {number} page 当前页
     */
    pageChange(page = 1) {
      this.pagination.current = page;
      this.updateTableListByPage(page);
      // 翻页后更新表头勾选框状态
      this.syncHeaderCheckbox();
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
        this.pagination.current = 1;
      }
      const currentPage = page || 1;
      const data = this.filterStatus.length ? this.filterData : this.allData;
      const startIndex = Math.max((currentPage - 1) * this.pagination.limit, 0);
      const endIndex = Math.min(currentPage * this.pagination.limit, data.length);
      return data.slice(startIndex, endIndex);
    },

    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.pageChange(this.pagination.current);
    },

    /**
     * 获取 API 列表数据
     * @param {string|number} payload - 网关/系统 ID
     */
    async fetchList(payload) {
      const requestContext = this.createRequestContext('listRequestId', payload);
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
          params.gatewayName = requestContext.gatewayName;
        }
        const res = await this.$store.dispatch(`cloudApi/${this.curFetchDispatchMethod}`, params);
        if (!this.isLatestRequest('listRequestId', requestContext)) {
          return;
        }
        // 新 API 响应格式：直接返回数据，无 result 层级
        // this.apiList = Object.freeze(res.sort(this.compare('name')))
        // 网关 api, 申请/续期处理
        if (res.length) {
          const apiData = res.map((v) => {
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
          this.apiList = Object.freeze(apiData);
        } else {
          this.apiList = Object.freeze(res);
        }
        this.allData = this.apiList;
        this.filterStatus = [];
        this.initPageConf();
        this.tableList = this.getDataByPage();
        this.isTableError = false;
      } catch (e) {
        if (!this.isLatestRequest('listRequestId', requestContext)) {
          return;
        }
        this.isTableError = true;
        this.catchErrorHandler(e);
      } finally {
        if (!this.isLatestRequest('listRequestId', requestContext)) {
          return;
        }
        this.loading = false;
        if (this.requestQueue.length > 0) {
          this.requestQueue.shift();
        }
        this.handleSearch();
      }
    },

    /**
     * 获取当前网关是否允许按网关申请的标志位
     */
    async fetchIsApplyByGateway() {
      const requestContext = this.createRequestContext('applyByGatewayRequestId');
      try {
        const params = {
          appCode: this.appCode,
          gatewayName: requestContext.gatewayName,
        };
        // 新 API 响应格式: 直接返回数据, 无 result 层级
        const res = await this.$store.dispatch('cloudApi/getAllowApplyByApi', params);
        if (!this.isLatestRequest('applyByGatewayRequestId', requestContext)) {
          return;
        }
        this.judgeIsApplyByGateway = res;
      } catch (e) {
        if (!this.isLatestRequest('applyByGatewayRequestId', requestContext)) {
          return;
        }
        console.warn(e);
      } finally {
        if (!this.isLatestRequest('applyByGatewayRequestId', requestContext)) {
          return;
        }
        if (this.requestQueue.length > 0) {
          this.requestQueue.shift();
        }
      }
    },

    /**
     * 单个 API 申请权限
     * @param {Object} item - API 数据行
     */
    handleApply(item) {
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('申请权限');
      this.applyDialog.rows = [item];
    },

    /**
     * 单个 API 权限续期
     * @param {Object} item - API 数据行
     */
    handleRenwal(item) {
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('权限续期');
      this.renewalDialog.rows = [item];
    },

    handleApplyByGateway() {
      this.isShowGatewayDialog = true;
    },

    /**
     * 批量权限续期
     */
    handleBatchRenwal() {
      if (!this.selectedList.length) {
        return;
      }
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('批量续期权限');
      this.renewalDialog.rows = [...this.selectedList];
    },

    /**
     * 批量申请权限
     */
    handleBatchApply() {
      if (!this.selectedList.length) {
        return;
      }
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('批量申请权限');
      this.applyDialog.rows = [...this.selectedList];
    },

    /**
     * 搜索关键字高亮匹配，用 <marked> 标签包裹匹配文本
     * @param {{name: string}} row - API 数据行
     * @returns {string} 高亮后的 HTML 字符串
     */
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

    /**
     * 搜索时对描述字段进行关键字高亮匹配
     * @param {{description: string}} row - API 数据行
     * @returns {string} 高亮后的 HTML 字符串，空描述返回 '--'
     */
    highlightDesc({ description }) {
      if (description !== '' && this.isFilter) {
        const keywords = this.searchValue
          .split(',')
          .filter((keyword) => keyword.trim() !== '')
          .map((keyword) => keyword.trim().replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'));
        if (keywords.length) {
          const regex = new RegExp(`(${keywords.join('|')})`, 'gi');
          description = description.replace(regex, (matched) => `<marked>${matched}</marked>`);
        }
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

    /**
     * 判断当前行是否可勾选（申请和续期均不可用则禁用勾选）
     */
    selectable(row) {
      return !row.applyDisabled || !row.renewDisabled;
    },

    /**
     * 表格勾选状态变更回调
     * @param {Array} selected - 当前勾选的行数据
     */
    handleSelectionChange(selected) {
      this.selectedList = selected;
      this.syncHeaderCheckbox();
    },

    /**
     * 同步表头全选/半选复选框状态
     */
    syncHeaderCheckbox() {
      this.$nextTick(() => {
        updateHeaderCheckboxState({
          tableRef: this.$refs.gatewayRef,
          tableData: this.tableList,
          selectedList: this.selectedList,
          selectable: this.selectable,
        });
      });
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
