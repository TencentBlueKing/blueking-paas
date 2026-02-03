<template>
  <div class="paasng-api-panel">
    <div class="search-wrapper flex-row justify-content-between">
      <div class="left-btns flex-row flex-shrink-0">
        <!-- 续期：支持跨网关/组件续期、MCP Server 默认为永久权限无需续期  -->
        <bk-button
          v-if="!isMcpService"
          class="flex-shrink-0"
          theme="primary"
          :disabled="isRenewalDisabled"
          @click="handleBatchRenewal"
        >
          {{ $t('批量续期') }}
        </bk-button>
      </div>
      <section class="right-wrapper flex-row align-items-center">
        <div class="flex-row align-items-center">
          <div class="label mr15">{{ $t('类型') }}</div>
          <bk-select
            v-model="typeValue"
            style="width: 180px"
            :clearable="false"
            @change="handleSelect"
          >
            <bk-option
              v-for="option in typeList"
              :key="option.id"
              :id="option.id"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </div>
        <div class="input-wrapper">
          <bk-input
            v-model="searchValue"
            :placeholder="$t('输入API名称或描述，按Enter搜索')"
            clearable
            right-icon="paasng-icon paasng-search"
            @input="handleSearch"
          />
        </div>
      </section>
    </div>
    <paas-content-loader
      :is-loading="loading"
      :offset-top="0"
      placeholder="cloud-api-inner-loading"
      :height="300"
    >
      <div>
        <paasng-alert
          v-if="!isMcpService"
          :title="$t('若有效期限不足180天，但应用仍在访问 API，有效期限将自动延长至 180 天（不限次数）。')"
          style="margin-bottom: 16px; width: 100%"
        />
        <bk-table
          ref="permRef"
          :key="tableKey"
          :data="tableList"
          :size="'small'"
          :empty-text="$t('暂无数据')"
          :pagination="pagination"
          :show-pagination-info="true"
          :header-border="false"
          :outer-border="false"
          @filter-change="filterChange"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @selection-change="handleSelectionChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="fetchList"
              @clear-filter="clearFilterKey"
            />
          </div>
          <!-- 无续期操作 -->
          <bk-table-column
            v-if="!isMcpService"
            label="id"
            type="selection"
            :selectable="selectable"
            width="60"
          ></bk-table-column>
          <bk-table-column
            label="API"
            min-width="120"
          >
            <template slot-scope="props">
              <template v-if="props.row.doc_link">
                <a
                  target="_blank"
                  :href="props.row.doc_link"
                >
                  <span v-dompurify-html="highlight(props.row)" />
                  <i
                    class="fa fa-book"
                    aria-hidden="true"
                  />
                </a>
              </template>
              <template v-else>
                <span v-dompurify-html="highlight(props.row)" />
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            v-if="!isMcpService"
            :label="isComponentApi ? $t('系统') : $t('网关')"
            min-width="100"
            :prop="isComponentApi ? 'system_name' : 'api_name'"
            :column-key="isComponentApi ? 'system_name' : 'api_name'"
            :filters="isTableEmpty ? null : nameFilters"
            :filter-multiple="true"
          >
            <template slot-scope="{ row }">
              {{ row[isComponentApi ? 'system_name' : 'api_name'] || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('描述')"
            min-width="120"
          >
            <template slot-scope="props">
              <span
                v-bk-tooltips="{ content: props.row.description, disabled: props.row.description === '' }"
                v-dompurify-html="highlightDesc(props.row)"
              />
            </template>
          </bk-table-column>
          <bk-table-column
            v-if="!isMcpService"
            :label="$t('权限等级')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <span :class="['special', 'sensitive'].includes(props.row.permission_level)">
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
            prop="permission_status"
            column-key="status"
            :filters="isTableEmpty ? null : statusFilters"
            :filter-multiple="true"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <template v-if="statusConfig[row.permission_status]">
                <span :class="['paasng-icon', statusConfig[row.permission_status].icon]" />
                {{ statusConfig[row.permission_status].text }}
              </template>
              <template v-else>
                <round-loading ext-cls="applying" />
                {{ $t('申请中') }}
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            :width="localLanguage === 'en' ? 130 : 110"
            v-if="!isMcpService"
          >
            <template slot-scope="{ row }">
              <div class="table-operate-buttons">
                <bk-button
                  style="padding: 0 0 0 10px"
                  theme="primary"
                  :disabled="row.renewDisabled"
                  size="small"
                  text
                  @click="handleRenewal(row)"
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

    <!-- 申请权限 -->
    <batch-dialog
      :show.sync="applyDialog.visiable"
      :title="applyDialog.title"
      :rows="applyDialog.rows"
      :api-id="applyDialog.superiorId"
      :api-name="applyDialog.superiorName"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-apply="handleSuccessApply"
      @after-leave="handleAfterLeave"
    />

    <renewal-dialog
      :show.sync="renewalDialog.visiable"
      :title="renewalDialog.title"
      :rows="renewalDialog.rows"
      :api-name="renewalDialog.name"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-renewal="handleSuccessRenewal"
      @after-leave="handleRenewalAfterLeave"
    />
  </div>
</template>

<script>
import RenewalDialog from './batch-renewal-dialog';
import BatchDialog from './batch-apply-dialog';
import PaasngAlert from './paasng-alert';
import { formatRenewFun, formatApplyFun } from '@/common/cloud-api';

export default {
  name: '',
  components: {
    RenewalDialog,
    PaasngAlert,
    BatchDialog,
  },
  props: {
    typeList: {
      type: Array,
      default: () => [],
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
      renewalDialog: {
        visiable: false,
        title: '',
        rows: [],
        name: '',
      },
      typeValue: 'gateway',
      levelMap: {
        normal: this.$t('普通'),
        special: this.$t('特殊'),
        sensitive: this.$t('敏感'),
        unlimited: this.$t('无限制'),
      },
      is_up: true,
      nameFilters: [],
      tableKey: -1,
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      allFilterData: {},
      selectedList: [],
      // 申请权限弹窗数据
      applyDialog: {
        visiable: false,
        title: '',
        rows: [],
        superiorId: '',
        superiorName: '',
      },
      statusFilterValues: [],
      nameFilterValues: [],
      filterAllList: [],
      statusConfig: {
        owned: { icon: 'paasng-pass', text: this.$t('已拥有') },
        unlimited: { icon: 'paasng-pass', text: this.$t('无限制') },
        need_apply: { icon: 'paasng-reject', text: this.$t('未申请') },
        expired: { icon: 'paasng-reject', text: this.$t('已过期') },
        rejected: { icon: 'paasng-reject', text: this.$t('已拒绝') },
      },
    };
  },
  computed: {
    isComponentApi() {
      return this.typeValue === 'component';
    },
    appCode() {
      return this.$route.params.id;
    },
    curDispatchMethod() {
      const methodMap = {
        component: 'getSysAppPermissions',
        gateway: 'getAppPermissions',
        mcp: 'getMcpAppliedPermissions',
      };
      return methodMap[this.typeValue] || 'getSysAppPermissions';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    // 是否允许批量续期
    isRenewalDisabled() {
      return !this.selectedList.some((item) => item.renewDisabled === false);
    },
    isSesetTableList() {
      return !this.nameFilterValues.length && !this.statusFilterValues.length;
    },
    isTableEmpty() {
      return this.tableList.length === 0;
    },
    // 是否为 MCP 服务类型
    isMcpService() {
      return this.typeValue === 'mcp';
    },
    statusFilters() {
      if (this.isMcpService) {
        return [
          { text: this.$t('已拥有'), value: 'owned' },
          { text: this.$t('已拒绝'), value: 'rejected' },
          { text: this.$t('申请中'), value: 'pending' },
        ];
      }
      return [
        { text: this.$t('已拥有'), value: 'owned' },
        { text: this.$t('无限制'), value: 'unlimited' },
        { text: this.$t('未申请'), value: 'need_apply' },
        { text: this.$t('已过期'), value: 'expired' },
        { text: this.$t('已拒绝'), value: 'rejected' },
        { text: this.$t('申请中'), value: 'pending' },
      ];
    },
  },
  watch: {
    $route() {
      this.init();
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
      if (newVal === '') {
        this.updateTableEmptyConfig();
      }
    },
    allData() {
      this.tableKey = +new Date();
    },
    nameFilterValues() {
      this.filterApiList(this.isComponentApi ? 'system_name' : 'api_name');
    },
    statusFilterValues() {
      this.filterApiList('permission_status');
    },
  },
  created() {
    this.init();
    this.compare = (p) => (m, n) => {
      const a = m[p] ? m[p] : 0;
      const b = n[p] ? n[p] : 0;
      return this.is_up ? a - b : b - a;
    };
    this.compareName = (p) => (m, n) => {
      const a = m[p].slice(0, 1).charCodeAt();
      const b = n[p].slice(0, 1).charCodeAt();
      return a - b;
    };
  },
  methods: {
    handleBatchRenewal() {
      if (!this.selectedList.length) {
        return;
      }
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('批量续期权限');
      this.renewalDialog.rows = [...this.selectedList];
    },

    nameFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },

    statusFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    // 设置对应筛选条件值
    setFilterValues(filters) {
      let target;
      const fieldName = Object.keys(filters)[0];
      switch (fieldName) {
        case 'api_name':
        case 'system_name':
          target = 'nameFilterValues';
          break;
        case 'status':
          target = 'statusFilterValues';
          break;
        default:
          return;
      }
      // 设置目标变量的值
      this[target] = filters[fieldName]?.length ? filters[fieldName] : [];
    },

    // 表格多选无数据时筛选项丢失处理
    handleTableFilterOptionMissing() {
      if (!this.$refs.permRef?.$refs?.tableHeader) return;
      const filterPanelsRef = this.$refs.permRef?.$refs?.tableHeader?.filterPanels || {};
      const filterKeys = ['api_name', 'system_name'];

      Object.keys(filterPanelsRef).forEach((key) => {
        const { selected, column } = filterPanelsRef[key] || {};
        // 根据组件中的数据更新本地数据
        if (filterKeys.includes(column?.key)) {
          this.nameFilterValues = selected || [];
        } else {
          this.statusFilterValues = selected || [];
        }
      });
    },

    filterChange(filters) {
      if (!this.isSesetTableList && !Object.keys(filters).length) {
        this.handleTableFilterOptionMissing();
        return;
      }
      this.setFilterValues(filters);
      Object.entries(filters).forEach((item) => {
        const [name, value] = item;
        this.allFilterData[name] = value;
      });
      this.updateTableEmptyConfig();
    },

    handleSelect(value, option) {
      this.pagination = Object.assign(
        {},
        {
          current: 1,
          limit: 10,
          count: 0,
        }
      );
      this.nameFilters = [];
      this.selectedList = [];
      this.fetchList();
      this.$nextTick(() => {
        this.$refs.permRef?.doLayout();
      });
    },

    sortTable() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
    },

    handleSuccessRenewal() {
      this.renewalDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.selectedList = [];
      this.fetchList(this.id);
    },

    handleRenewalAfterLeave() {
      this.renewalDialog = Object.assign(
        {},
        {
          visiable: false,
          title: '',
          rows: [],
          name: '',
        }
      );
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
      let dataSource = this.allData;
      // 存在筛选条件更改数据源为已筛选后的列表
      if (this.nameFilterValues.length || this.statusFilterValues.length) {
        dataSource = this.filterAllList;
      }
      if (!page) {
        this.pagination.current = page = 1;
      }
      let startIndex = (page - 1) * this.pagination.limit;
      let endIndex = page * this.pagination.limit;
      if (startIndex < 0) {
        startIndex = 0;
      }
      if (endIndex > dataSource.length) {
        endIndex = dataSource.length;
      }
      return dataSource.slice(startIndex, endIndex);
    },

    limitChange(currentLimit, prevLimit) {
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

    getComputedExpires(payload) {
      if (!payload.expires_in) {
        if (payload.permission_status === 'owned') {
          return this.$t('永久');
        }
        return '--';
      }
      return `${Math.ceil(payload.expires_in / (24 * 3600))}${this.$t('天')}`;
    },

    async handlePageSearch() {
      this.selectedList = [];
      try {
        await this.fetchList();
        this.handleSearch();
        this.allData = this.apiList;
        this.initPageConf();
        this.tableList = this.getDataByPage();
        this.handleSearch();
      } catch (e) {
        console.error(e);
      }
    },

    handleSearch() {
      if (this.searchValue === '') {
        return;
      }
      this.isFilter = true;
      this.allData = [
        ...this.apiList.filter(
          (api) => api.name.indexOf(this.searchValue) !== -1 || api.description.indexOf(this.searchValue) !== -1
        ),
      ];
      this.pagination.count = this.allData.length;

      this.pagination.current = 1;

      const start = this.pagination.limit * (this.pagination.current - 1);
      const end = start + this.pagination.limit;
      this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
      this.updateTableEmptyConfig();
    },

    init() {
      this.fetchList();
    },

    // mcp service 数据格式化
    formatMcpServiceData(data) {
      return data.map((item) => ({
        ...item.permission,
        ...item.mcp_server,
        ...item,
        permission_status: item.permission.status,
      }));
    },

    // 获取已申请的权限列表
    async fetchList() {
      this.loading = true;
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDispatchMethod}`, { appCode: this.appCode });
        // 网关、组件使用 res.data / MCP使用 res
        let apiData = this.isMcpService ? this.formatMcpServiceData(res) : res.data || [];
        apiData.forEach((item) => {
          item.type = this.typeValue;
        });
        // 权限续期处理
        if (apiData.length) {
          apiData = apiData.map((v) => {
            // 申请
            const apply = formatApplyFun(v.permission_status);
            // 续期
            const renew = formatRenewFun(v.permission_status, v);
            // Mcp Service 为永久权限，直接禁用
            return {
              ...v,
              applyDisabled: apply.disabled,
              applyTips: apply.tips,
              renewDisabled: renew.disabled,
              renewTips: renew.tips,
            };
          });
        }
        this.apiList = Object.freeze(apiData);
        const nameSet = new Set(this.nameFilters.map((item) => item.value));
        this.apiList.forEach((item) => {
          const name = item[this.isComponentApi ? 'system_name' : 'api_name'];
          if (!nameSet.has(name)) {
            nameSet.add(name);
            this.nameFilters.push({
              text: name,
              value: name,
            });
          }
        });
        this.allData = apiData;
        this.initPageConf();
        this.tableList = this.getDataByPage();
        this.indeterminate = false;
        this.allChecked = false;
        this.tableKey = +new Date();
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
        this.$emit('data-ready');
      }
    },

    handleRenewal(item) {
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('权限续期');
      this.renewalDialog.rows = [item];
      this.renewalDialog.name = this.isComponentApi ? item.system_name : item.api_name;
    },

    resetSelectedAPIList() {
      this.tableList.forEach((item) => {
        this.$set(item, 'checked', false);
      });
      this.allChecked = false;
      this.indeterminate = false;
    },

    highlight({ name }) {
      if (this.isFilter) {
        return name.replace(this.searchValue, `<marked>${this.searchValue}</marked>`);
      }
      return name;
    },

    highlightDesc({ description }) {
      if (this.isFilter) {
        if (description !== '') {
          return description.replace(this.searchValue, `<marked>${this.searchValue}</marked>`);
        }
        return '--';
      }
      return description || '--';
    },
    clearFilterKey() {
      this.nameFilterValues = [];
      this.statusFilterValues = [];
      this.searchValue = '';
      this.allFilterData = {};
      this.$refs.permRef?.clearFilter();
      this.fetchList();
    },

    updateTableEmptyConfig() {
      const isTableFilter = this.isFilterCriteria();

      if (this.searchValue || isTableFilter) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '$CONSTANT';
    },

    // 表头是否存在筛选条件
    isFilterCriteria() {
      let isFilter = false;
      for (const key in this.allFilterData) {
        if (this.allFilterData[key].length) {
          isFilter = true;
        }
      }
      return isFilter;
    },

    // 勾选是否禁用
    selectable(row) {
      return !row.applyDisabled || !row.renewDisabled;
    },

    // 表格change事件
    handleSelectionChange(selected) {
      this.selectedList = selected;
    },

    // 申请
    handleSuccessApply() {
      this.applyDialog.visiable = false;
      this.allChecked = false;
      this.selectedList = [];
      // 获取列表
      this.fetchList(this.id);
    },

    // 取消
    handleAfterLeave() {
      this.applyDialog = Object.assign(
        {},
        {
          visiable: false,
          title: '',
          rows: [],
          superiorId: '',
          superiorName: '',
        }
      );
    },

    // 通用筛选逻辑
    getFilterAllList(data, fields, key) {
      return data.filter((v) => fields.includes(v[key]));
    },

    // 重置TableList
    updateTableList(isReset) {
      this.tableList = this.getDataByPage(1);
      this.pagination.current = 1;
      this.pagination.count = isReset ? this.allData.length : this.filterAllList.length;
    },

    // 根据条件筛选已申请权限
    filterApiList(key) {
      // 无筛选条件数据重置处理
      if (this.isSesetTableList) {
        this.updateTableList(true);
        return;
      }
      const filterFields = key === 'permission_status' ? this.statusFilterValues : this.nameFilterValues;
      // 多筛选条件处理
      if (this.statusFilterValues.length && this.nameFilterValues.length) {
        const curFilterList = this.getFilterAllList(
          this.allData,
          this.nameFilterValues,
          this.isComponentApi ? 'system_name' : 'api_name'
        );
        this.filterAllList = this.getFilterAllList(curFilterList, this.statusFilterValues, 'permission_status');
      } else {
        // 当前筛选条件重置，但存在另外一组筛选条件
        if (!filterFields.length) {
          if (key === 'permission_status' && this.nameFilterValues.length) {
            const fieldKey = this.isComponentApi ? 'system_name' : 'api_name';
            this.filterAllList = this.getFilterAllList(this.allData, this.nameFilterValues, fieldKey);
          } else if (key !== 'permission_status' && this.statusFilterValues.length) {
            this.filterAllList = this.getFilterAllList(this.allData, this.statusFilterValues, 'permission_status');
          }
        } else {
          this.filterAllList = this.getFilterAllList(this.allData, filterFields, key);
        }
      }
      this.updateTableList();
    },
  },
};
</script>

<style lang="scss" scoped>
.search-wrapper {
  margin-bottom: 16px;
  .left-btns,
  .right-wrapper {
    gap: 12px;
  }
  .label {
    line-height: 32px;
  }
  .input-wrapper {
    width: 420px;
  }
}

.table-operate-buttons {
  position: relative;
  left: -12px;
}

span.sensitive {
  color: #ff0000;
}

span.inner {
  color: rgb(58, 171, 255);
  opacity: 0.7;
}

span.clound {
  color: #45e35f;
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
</style>

<style>
marked {
  background: yellow;
  color: black;
}
</style>
