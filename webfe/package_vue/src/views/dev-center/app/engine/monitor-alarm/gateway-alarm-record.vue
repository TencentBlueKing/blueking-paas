<!--
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 -->
<template>
  <div class="gateway-alarm-record">
    <bk-alert
      class="mb-16"
      type="info"
      :title="$t('展示当前应用作为调用方，请求其他 API 网关时触发的告警。')"
    />
    <paas-content-loader
      :is-loading="isInitialLoading"
      placeholder="table-loading"
      :loader-props="{ operationCount: 1 }"
      :offset-top="10"
      class="alarm-list"
    >
      <div class="search-wrapper">
        <bk-date-picker
          class="date-picker"
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
        <bk-search-select
          class="alarm-search"
          :values="searchValues"
          :data="searchFields"
          :show-condition="false"
          clearable
          :placeholder="$t('搜索网关名称、资源名称、告警状态')"
          @change="handleSearchChange"
        />
      </div>
      <p
        v-if="dateError"
        class="date-error"
      >
        {{ dateError }}
      </p>
      <!-- bk-table 仅在挂载时读取 filtered-value。 -->
      <bk-table
        :key="filters.status"
        v-bkloading="{ isLoading: loading && !isInitialLoading, opacity: 1 }"
        :data="records"
        :pagination="pagination"
        row-key="id"
        size="small"
        @page-change="handlePageChange"
        @page-limit-change="handleLimitChange"
        @filter-change="handleFilterChange"
      >
        <div slot="empty">
          <bk-exception
            v-if="isForbidden"
            type="403"
            scene="part"
          >
            {{ $t('您没有访问当前应用该功能的权限') }}
          </bk-exception>
          <table-empty
            v-else
            :condition="{ filters, customTime: isCustomTime }"
            :show-clear="searchValues.length > 0"
            :is-error="isTableError"
            @clear-filter="clearSearchFilters"
            @reacquire="fetchRecords"
          />
        </div>
        <bk-table-column
          :label="$t('告警 ID')"
          min-width="100"
        >
          <template slot-scope="{ row }">
            {{ row.alarm_id || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('告警时间')"
          min-width="166"
        >
          <template slot-scope="{ row }">
            {{ formatCreatedTime(row.created_time) }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('网关')"
          min-width="130"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            {{ row.gateway_name || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('资源名称')"
          min-width="140"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            {{ row.resource_name || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('告警内容')"
          min-width="220"
        >
          <template slot-scope="{ row }">
            <bk-popover
              v-if="row.message"
              class="alarm-message"
              :max-width="560"
            >
              <span class="alarm-message-summary">{{ row.message }}</span>
              <ul
                slot="content"
                class="alarm-message-detail"
              >
                <li
                  v-for="(line, index) in row.message.split(/\r\n?|\n/)"
                  :key="index"
                  class="alarm-message-line"
                >
                  <span
                    v-if="line.trim()"
                    aria-hidden="true"
                  >•</span>
                  <span v-text="line" />
                </li>
              </ul>
            </bk-popover>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('状态')"
          prop="status"
          column-key="status"
          :filters="statusFilters"
          :filtered-value="filters.status ? [filters.status] : []"
          :filter-multiple="false"
          min-width="115"
        >
          <template slot-scope="{ row }">
            <span :class="['alarm-status', getStatusColor(row.status)]">
              {{ row.status_display || getStatusLabel(row.status) }}
            </span>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>
  </div>
</template>

<script>
import dayjs from '@/common/dayjs';
import { RECENT_DATE_KEYS, createDateShortcuts } from '@/common/date';

const STATUS_COLORS = new Map([
  ['received', 'blue'],
  ['skipped', 'gray'],
  ['success', 'green'],
  ['failure', 'red'],
]);

export default {
  name: 'GatewayAlarmRecord',
  props: {
    appCode: {
      type: String,
      required: true,
    },
  },
  data() {
    const now = dayjs();
    return {
      dateTimeRange: [now.subtract(24, 'hour').toDate(), now.toDate()],
      dateOptions: {
        disabledDate: date => dayjs(date).startOf('day')
          .isAfter(dayjs()),
      },
      isCustomTime: false,
      dateError: '',
      filters: { gateway_name: '', resource_name: '', status: '' },
      pagination: { current: 1, limit: 10, count: 0, limitList: [10, 20, 50, 100] },
      records: [],
      isInitialLoading: true,
      loading: false,
      isForbidden: false,
      isTableError: false,
      requestSequence: 0,
    };
  },
  computed: {
    dateShortcuts() {
      // 与云 API 申请记录保持一致：今天、最近7天、最近30天、最近半年
      return createDateShortcuts(this.$i18n, RECENT_DATE_KEYS);
    },
    statusOptions() {
      return [
        { id: 'received', name: this.$t('已接收') },
        { id: 'skipped', name: this.$t('已忽略') },
        { id: 'success', name: this.$t('告警成功') },
        { id: 'failure', name: this.$t('告警失败') },
      ];
    },
    statusFilters() {
      return this.statusOptions.map(({ id, name }) => ({ value: id, text: name }));
    },
    searchFields() {
      return [
        { id: 'gateway_name', name: this.$t('网关名称'), placeholder: this.$t('请输入网关名称'), children: [] },
        {
          id: 'resource_name',
          name: this.$t('资源名称'),
          placeholder: this.$t('请输入资源名称'),
          children: [],
          validate: () => !!this.filters.gateway_name || this.$t('请先输入网关名称'),
        },
        { id: 'status', name: this.$t('告警状态'), children: this.statusOptions },
      ];
    },
    searchValues() {
      return this.searchFields.filter(({ id }) => this.filters[id]).map(({ id, name }) => {
        const value = this.filters[id];
        return { id, name, values: [{ id: value, name: id === 'status' ? this.getStatusLabel(value) : value }] };
      });
    },
  },
  created() {
    this.fetchRecords();
  },
  beforeDestroy() {
    this.requestSequence += 1;
  },
  methods: {
    getStatusColor(status) {
      return STATUS_COLORS.get(status) || 'gray';
    },
    getStatusLabel(status) {
      return this.statusOptions.find(({ id }) => id === status)?.name || status || '--';
    },
    formatCreatedTime(value) {
      if (!value) return '--';
      const time = dayjs(value);
      return time.isValid() ? time.format('YYYY-MM-DD HH:mm:ss') : value;
    },
    handleDateChange(range) {
      this.dateTimeRange = range;
      this.isCustomTime = true;
      this.search();
    },
    handleSearchChange(values) {
      const next = { gateway_name: '', resource_name: '', status: '' };
      values.forEach(({ id, values: selected }) => {
        if (!Object.prototype.hasOwnProperty.call(next, id)
          || !Array.isArray(selected) || selected.length !== 1) return;
        next[id] = String(selected[0].id).trim();
      });
      if (!next.gateway_name || next.gateway_name !== this.filters.gateway_name) next.resource_name = '';
      this.applyFilters(next);
    },
    handleFilterChange({ status }) {
      if (status) this.applyFilters({ ...this.filters, status: status[0] || '' });
    },
    applyFilters(filters) {
      if (Object.keys(filters).every(key => filters[key] === this.filters[key])) return;
      this.filters = filters;
      this.search();
    },
    clearSearchFilters() {
      // table-empty 的刷新事件先触发 clear-filter，重试时保留原条件。
      if (this.isTableError) return;
      this.applyFilters({ gateway_name: '', resource_name: '', status: '' });
    },
    handlePageChange(page) {
      if (page === this.pagination.current || this.loading) return;
      this.pagination.current = page;
      this.fetchRecords();
    },
    handleLimitChange(limit) {
      if (limit === this.pagination.limit) return;
      this.pagination.limit = limit;
      this.search();
    },
    search() {
      this.pagination.current = 1;
      this.fetchRecords();
    },
    getRequestParams() {
      const [start, end] = this.dateTimeRange || [];
      if (!start || !end || !dayjs(start).isValid() || !dayjs(end).isValid()) {
        this.dateError = this.$t('请选择完整的告警时间范围');
        return null;
      }
      const timeStart = dayjs(start).unix();
      const timeEnd = Math.min(dayjs(end).unix(), dayjs().unix());
      if (timeEnd <= timeStart) {
        this.dateError = this.$t('结束时间必须大于起始时间');
        return null;
      }
      const { current, limit } = this.pagination;
      const params = {
        appCode: this.appCode,
        time_start: timeStart,
        time_end: timeEnd,
        offset: (current - 1) * limit,
        limit,
      };
      Object.entries(this.filters).forEach(([key, value]) => {
        if (value) params[key] = value;
      });
      return params;
    },
    async fetchRecords() {
      this.requestSequence += 1;
      const sequence = this.requestSequence;
      this.dateError = '';
      this.isForbidden = false;
      this.isTableError = false;
      const params = this.getRequestParams();
      if (!params) {
        this.records = [];
        this.pagination.count = 0;
        this.isInitialLoading = false;
        this.loading = false;
        return;
      }
      this.loading = true;
      try {
        const res = await this.$store.dispatch('cloudApi/getAppAlarmRecords', params);
        if (sequence !== this.requestSequence) return;
        if (!Array.isArray(res?.results) || !Number.isInteger(res.count) || res.count < 0) {
          throw new Error('Invalid gateway alarm records response');
        }
        this.records = res.results;
        this.pagination.count = res.count;
      } catch (error) {
        if (sequence !== this.requestSequence) return;
        this.records = [];
        this.pagination.count = 0;
        this.isForbidden = error?.status === 403;
        this.isTableError = !this.isForbidden;
      } finally {
        if (sequence === this.requestSequence) {
          this.isInitialLoading = false;
          this.loading = false;
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.alarm-list {
  padding: 16px 24px;
  background: #fff;
}
.search-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}
.date-picker {
  width: 350px;
  max-width: 100%;
}
.alarm-search {
  flex: 1;
  min-width: 260px;
}
.date-error {
  margin: -8px 0 16px;
  color: #ea3636;
  font-size: 12px;
}
.alarm-message {
  display: block;
  max-width: 100%;
  /deep/ .bk-tooltip-ref {
    display: block;
  }
}
.alarm-message-summary {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.alarm-message-detail {
  max-height: 50vh;
  margin: 0;
  padding: 0;
  overflow: auto;
  overflow-wrap: anywhere;
  list-style: none;
  line-height: 20px;
  white-space: pre-wrap;
}
.alarm-message-line {
  display: flex;
  gap: 4px;
  min-height: 20px;
}
.alarm-status {
  display: inline-block;
  padding: 0 8px;
  border-radius: 2px;
  line-height: 20px;
  &.blue {
    color: #3a84ff;
    background: #e1ecff;
  }
  &.gray {
    color: #63656e;
    background: #f0f1f5;
  }
  &.green {
    color: #14a568;
    background: #e4faf0;
  }
  &.red {
    color: #ea3636;
    background: #ffeded;
  }
}
</style>
