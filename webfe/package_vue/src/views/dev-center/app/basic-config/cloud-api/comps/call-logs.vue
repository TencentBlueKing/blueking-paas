<template>
  <div class="call-logs">
    <div class="search-wrapper">
      <div class="time-filter">
        <span>{{ $t('请求时间') }}</span>
        <bk-date-picker
          ext-cls="application-time"
          :value="dateTimeRange"
          type="datetimerange"
          format="yyyy-MM-dd HH:mm:ss"
          :clearable="false"
          :shortcuts="dateShortcuts"
          :shortcut-close="true"
          :options="dateOptions"
          :placeholder="$t('选择日期时间范围')"
          @change="handleDateChange"
        />
      </div>
      <bk-search-select
        :key="searchInputKey"
        class="log-search"
        :values="searchSelectValue"
        :data="searchFields"
        :show-condition="false"
        :clearable="true"
        :validate-message="searchValidationMessage"
        :placeholder="$t('搜索请求 ID、资源名称、响应状态码')"
        @change="handleSearchChange"
        @input-change="searchValidationMessage = ''"
      />
    </div>
    <p
      v-if="dateError"
      class="date-error"
    >
      {{ dateError }}
    </p>
    <bk-table
      ref="logsTable"
      :key="tableKey"
      :data="records"
      :size="tableSize"
      :pagination="pagination"
      :header-border="false"
      :outer-border="false"
      v-bkloading="{ isLoading: loading, zIndex: 10 }"
      @page-change="handlePageChange"
      @page-limit-change="handleLimitChange"
      @filter-change="handleFilterChange"
      @row-click="handleRowClick"
    >
      <div slot="empty">
        <table-empty
          :condition="{ filters, customTime: isCustomTime }"
          :show-clear="hasSearchFilters"
          :is-error="isTableError"
          @clear-filter="clearSearchFilters"
          @reacquire="fetchLogs"
        />
      </div>
      <bk-table-column
        type="expand"
        width="30"
      >
        <template slot-scope="{ row }">
          <dl class="log-detail">
            <div
              v-for="field in detailFields"
              :key="field.id"
              class="detail-item"
            >
              <dt>{{ field.label }} ({{ field.id }})：</dt>
              <dd>{{ formatField(row, field.id, true) }}</dd>
            </div>
          </dl>
        </template>
      </bk-table-column>
      <bk-table-column
        v-for="column in visibleColumns"
        :key="column.id"
        :prop="column.id"
        :label="column.label"
        :min-width="column.width"
        :column-key="column.id"
        :filters="getColumnFilters(column.id)"
        :filtered-value="getFilteredValue(column.id)"
        :filter-multiple="false"
        :filter-searchable="['gateway_name', 'status'].includes(column.id)"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span
            v-if="column.id === 'status'"
            :class="['status-code', getStatusClass(row.status)]"
          >
            {{ formatField(row, column.id) }}
          </span>
          <template v-else>{{ formatField(row, column.id) }}</template>
        </template>
      </bk-table-column>
      <bk-table-column
        type="setting"
        width="42"
      >
        <bk-table-setting-content
          :fields="columns"
          :selected="visibleColumns"
          :size="tableSize"
          @setting-change="handleSettingChange"
        />
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import dayjs from '@/common/dayjs';
import { createTimeShortcuts, createLongTermDatePresets } from '@/common/date';

const MAX_LOOKBACK_SECONDS = 180 * 24 * 60 * 60;
const COMMON_STATUSES = [200, 201, 204, 400, 401, 403, 404, 429, 499, 500, 502, 504];

export default {
  props: {
    appCode: {
      type: String,
      required: true,
    },
  },
  data() {
    const end = new Date();
    return {
      dateTimeRange: [new Date(end.getTime() - 60 * 60 * 1000), end],
      dateError: '',
      isCustomTime: false,
      filters: { gateway_name: '', request_id: '', resource_name: '', status: null },
      searchInputKey: 0,
      searchValidationMessage: '',
      gateways: [],
      records: [],
      loading: false,
      isTableError: false,
      requestSequence: 0,
      pagination: { current: 1, limit: 10, count: 0, limitList: [10, 20, 50, 100] },
      tableSize: 'small',
      selectedColumnIds: [
        'timestamp', 'gateway_name', 'stage', 'resource_name', 'method', 'http_path', 'status', 'request_duration',
      ],
      dateOptions: {
        disabledDate(date) {
          const now = Date.now();
          const earliest = dayjs(date).endOf('day');
          const latest = dayjs(date).startOf('day');
          return earliest.valueOf() < now - MAX_LOOKBACK_SECONDS * 1000 || latest.valueOf() > now;
        },
      },
    };
  },
  computed: {
    tableKey() {
      // 表格组件未监听 filteredValue，仅在表头筛选值变化时重建以同步选中态。
      return JSON.stringify([this.filters.gateway_name, this.filters.status]);
    },
    dateShortcuts() {
      const longTerm = createLongTermDatePresets(this.$i18n)
        .filter(item => [this.$t('最近7天'), this.$t('最近30天')].includes(item.text));
      return [...createTimeShortcuts(this.$i18n), ...longTerm];
    },
    searchFields() {
      return [
        { id: 'request_id', name: this.$t('请求 ID'), placeholder: this.$t('请输入请求 ID'), children: [] },
        { id: 'resource_name', name: this.$t('资源名称'), placeholder: this.$t('请输入资源名称'), children: [] },
        {
          id: 'status',
          name: this.$t('响应状态码'),
          placeholder: this.$t('请输入响应状态码'),
          children: [],
          validate: values => this.validateStatus(values[0]?.id),
        },
      ];
    },
    searchSelectValue() {
      return this.searchFields.filter(field => this.filters[field.id] !== '' && this.filters[field.id] !== null)
        .map(field => ({
          ...field,
          values: [{ id: String(this.filters[field.id]), name: String(this.filters[field.id]) }],
        }));
    },
    hasSearchFilters() {
      return !!(this.filters.gateway_name || this.searchSelectValue.length);
    },
    columns() {
      return [
        { id: 'timestamp', label: this.$t('请求时间'), width: 160, disabled: true },
        { id: 'request_id', label: this.$t('请求 ID'), width: 220 },
        { id: 'gateway_name', label: this.$t('网关'), width: 160 },
        { id: 'stage', label: this.$t('环境'), width: 80 },
        { id: 'resource_name', label: this.$t('资源名称'), width: 120 },
        { id: 'method', label: this.$t('请求方法'), width: 90 },
        { id: 'http_path', label: this.$t('路径'), width: 220 },
        { id: 'status', label: this.$t('响应状态码'), width: 90 },
        { id: 'request_duration', label: this.$t('耗时'), width: 80 },
      ];
    },
    visibleColumns() {
      return this.columns.filter(column => this.selectedColumnIds.includes(column.id));
    },
    detailFields() {
      return [
        { id: 'request_id', label: this.$t('请求 ID') },
        { id: 'timestamp', label: this.$t('请求时间') },
        { id: 'gateway_name', label: this.$t('网关名称') },
        { id: 'stage', label: this.$t('环境') },
        { id: 'resource_name', label: this.$t('资源名称') },
        { id: 'method', label: this.$t('请求方法') },
        { id: 'http_host', label: this.$t('请求域名') },
        { id: 'http_path', label: this.$t('请求路径') },
        { id: 'status', label: this.$t('状态码') },
        { id: 'request_duration', label: this.$t('请求总耗时') },
        { id: 'code_name', label: this.$t('错误编码名称') },
        { id: 'error', label: this.$t('错误信息') },
        { id: 'response_desc', label: this.$t('响应说明') },
      ];
    },
  },
  created() {
    this.fetchLogs();
    this.fetchGateways();
  },
  methods: {
    validateStatus(value) {
      return /^[1-5]\d{2}$/.test(String(value).trim()) || this.$t('请输入 100–599 的整数状态码');
    },
    getColumnFilters(id) {
      if (id === 'gateway_name') {
        return this.gateways.map(gateway => ({ text: gateway.name, value: gateway.name }));
      }
      if (id === 'status') {
        const statuses = [...new Set([...COMMON_STATUSES, this.filters.status].filter(value => value !== null))];
        return statuses.sort((a, b) => a - b).map(value => ({ text: String(value), value }));
      }
      return undefined;
    },
    getFilteredValue(id) {
      if (id === 'status' && this.filters.status !== null) return [this.filters.status];
      if (id === 'gateway_name' && this.filters.gateway_name) return [this.filters.gateway_name];
      return [];
    },
    handleSearchChange(values) {
      const hasInvalidField = values.some(item => !this.searchFields.some(field => field.id === item.id)
        || !Array.isArray(item.values) || item.values.length !== 1);
      if (hasInvalidField) {
        this.searchValidationMessage = this.$t('请先选择搜索字段，再输入关键词');
        // 输入组件自行维护标签，重建以撤回未被接受的无字段标签。
        this.searchInputKey += 1;
        return;
      }
      this.searchValidationMessage = '';
      const next = { request_id: '', resource_name: '', status: null };
      values.forEach((item) => {
        if (Object.prototype.hasOwnProperty.call(next, item.id)) {
          next[item.id] = String(item.values?.[0]?.id ?? '').trim();
        }
      });
      if (next.status !== null) {
        next.status = Number(next.status);
      }
      if (Object.keys(next).every(key => next[key] === this.filters[key])) return;
      this.filters = { ...this.filters, ...next };
      this.search();
    },
    handleFilterChange(fields) {
      const next = { ...this.filters };
      if (fields.gateway_name) next.gateway_name = fields.gateway_name[0] || '';
      if (fields.status) next.status = fields.status.length ? Number(fields.status[0]) : null;
      if (Object.keys(next).every(key => next[key] === this.filters[key])) return;
      this.filters = next;
      this.search();
    },
    handleDateChange(range) {
      this.dateTimeRange = range;
      this.isCustomTime = true;
      this.search();
    },
    search() {
      this.pagination.current = 1;
      this.fetchLogs();
    },
    clearSearchFilters() {
      // table-empty 的错误重试会先触发 clear-filter，此时应保留查询条件。
      if (this.isTableError) return;
      this.searchValidationMessage = '';
      this.filters = { gateway_name: '', request_id: '', resource_name: '', status: null };
      this.search();
    },
    handlePageChange(page) {
      if (page === this.pagination.current || this.loading) return;
      this.pagination.current = page;
      this.fetchLogs();
    },
    handleLimitChange(limit) {
      this.pagination.limit = limit;
      this.search();
    },
    // 点击整行展开/收起详情；左侧展开按钮的点击已阻止冒泡，不会重复触发
    handleRowClick(row) {
      // 拖选文本时不切换展开状态
      if (String(window.getSelection())) return;
      this.$refs.logsTable.toggleRowExpansion(row);
    },
    handleSettingChange({ fields, size }) {
      this.selectedColumnIds = fields.map(field => field.id);
      this.tableSize = size;
    },
    getRequestParams() {
      this.dateError = '';
      const [start, end] = this.dateTimeRange || [];
      if (!start || !end || !dayjs(start).isValid() || !dayjs(end).isValid()) {
        this.dateError = this.$t('请选择完整的请求时间范围');
        return null;
      }
      const now = Math.floor(Date.now() / 1000);
      const timeStart = dayjs(start).unix();
      const timeEnd = Math.min(dayjs(end).unix(), now);
      if (timeEnd <= timeStart) {
        this.dateError = this.$t('结束时间必须大于起始时间');
        return null;
      }
      if (timeStart < now - MAX_LOOKBACK_SECONDS) {
        this.dateError = this.$t('起始时间不得早于当前时间前 180 天');
        return null;
      }
      const params = {
        appCode: this.appCode,
        time_start: timeStart,
        time_end: timeEnd,
        offset: (this.pagination.current - 1) * this.pagination.limit,
        limit: this.pagination.limit,
      };
      Object.entries(this.filters).forEach(([key, value]) => {
        if (value !== '' && value !== null) params[key] = value;
      });
      return params;
    },
    async fetchLogs() {
      this.requestSequence += 1;
      const sequence = this.requestSequence;
      const params = this.getRequestParams();
      this.records = [];
      this.isTableError = false;
      if (!params) {
        this.loading = false;
        this.pagination.count = 0;
        this.$emit('data-ready');
        return;
      }
      this.loading = true;
      try {
        const res = await this.$store.dispatch('cloudApi/getAppRequestLogs', params);
        if (sequence !== this.requestSequence) return;
        if (!Array.isArray(res?.results) || !Number.isInteger(res.count) || res.count < 0) {
          throw new Error(this.$t('服务暂不可用，请稍后再试'));
        }
        this.records = res.results;
        this.pagination.count = res.count;
      } catch (error) {
        if (sequence !== this.requestSequence) return;
        this.pagination.count = 0;
        this.isTableError = true;
        this.catchErrorHandler(error);
      } finally {
        if (sequence === this.requestSequence) {
          this.loading = false;
          this.$emit('data-ready');
        }
      }
    },
    async fetchGateways() {
      try {
        const gateways = await this.$store.dispatch('cloudApi/getApis', { appCode: this.appCode });
        if (!Array.isArray(gateways)) {
          throw new Error(this.$t('服务暂不可用，请稍后再试'));
        }
        this.gateways = gateways;
      } catch (error) {
        this.gateways = [];
        this.catchErrorHandler(error);
      }
    },
    formatField(row, id, detail = false) {
      const value = row[id];
      if (value === undefined || value === null || value === '') return '--';
      if (id === 'timestamp') {
        return dayjs.unix(value).format(detail ? 'YYYY-MM-DD HH:mm:ss ZZ' : 'YYYY-MM-DD HH:mm:ss');
      }
      if (id === 'request_duration' && !detail) return `${value} ms`;
      return value;
    },
    getStatusClass(status) {
      if (status >= 200 && status < 300) return 'success';
      if (status >= 400 && status < 500) return 'warning';
      if (status >= 500 && status < 600) return 'danger';
      return '';
    },
  },
};
</script>

<style lang="scss" scoped>
/deep/ .application-time .bk-date-picker-rel .bk-date-picker-editor {
  padding: 0 40px 0 10px;
}
.search-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  .time-filter {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    .bk-date-picker {
      width: 360px;
    }
  }
  .log-search {
    flex: 1;
    min-width: 260px;
  }
}
.date-error {
  margin: -8px 0 16px;
  color: #ea3636;
  font-size: 12px;
}
/deep/ .bk-table-body > tbody > tr.bk-table-row {
  cursor: pointer;
}
// 固定右侧列补丁块的默认背景色（#f5f7fa）与表头背景色（#fafbfd）不一致，会产生色差
/deep/ .bk-table-fixed-right-patch {
  background-color: #fafbfd;
  border-bottom: none;
}
.log-detail {
  padding: 12px 24px;
  font-size: 12px;
  line-height: 28px;
  .detail-item {
    display: flex;
  }
  dt {
    flex: 0 0 260px;
    text-align: right;
    color: #979ba5;
  }
  dd {
    flex: 1;
    min-width: 0;
    margin-left: 12px;
    color: #63656e;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
}
.status-code {
  display: inline-block;
  padding: 0 8px;
  line-height: 20px;
  &.success {
    color: #14a568;
    background: #e4faf0;
  }
  &.warning {
    color: #ff9c01;
    background: #fff3e1;
  }
  &.danger {
    color: #ea3636;
    background: #ffeded;
  }
}
</style>
