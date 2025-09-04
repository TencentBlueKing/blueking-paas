<template>
  <div class="operation-record-container">
    <div class="top-box">
      <div class="search-select-cls">
        <bk-search-select
          clearable
          v-model="searchValues"
          :show-popover-tag-change="true"
          :data="filteredSearchData"
          :show-condition="false"
          :remote-method="handleRemoteMethod"
          :remote-empty-text="Object.keys(searchValues).length ? $t('无匹配人员') : $t('请输入操作人')"
          @change="resetPaginationAndRefresh"
          @clear="resetPaginationAndRefresh"
        ></bk-search-select>
      </div>
      <bk-date-picker
        ref="datePickerRef"
        :placeholder="$t('选择日期时间范围')"
        :format="'yyyy-MM-dd HH:mm:ss'"
        :shortcuts="dateShortcuts"
        :options="datePickerOption"
        :type="'datetimerange'"
        :clearable="true"
        :shortcut-close="true"
        placement="bottom-end"
        @change="handleDateChange"
        @pick-success="getRecords"
        @clear="handleDateClear"
        ext-cls="date-picker-wrapper"
      ></bk-date-picker>
    </div>
    <div class="table-wrapper">
      <bk-table
        ref="tableRef"
        :data="records"
        :pagination="pagination"
        size="small"
        class="plan-table-cls"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        @page-change="pgHandlePageChange"
        @page-limit-change="pgHandlePageLimitChange"
      >
        <div slot="empty">
          <table-empty
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            :empty-title="$t('暂无应用')"
            @reacquire="resetPaginationAndRefresh"
            @clear-filter="clearFilterKey"
          />
        </div>
        <bk-table-column
          v-for="column in columns"
          v-bind="column"
          :label="$t(column.label)"
          :prop="column.prop"
          :key="column.user"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span v-if="column.prop === 'status'">
              {{ $t(APP_RESULT_CODE[row[column.prop]]) || '--' }}
            </span>
            <span v-else-if="column.prop === 'target'">
              {{ $t(targetMap[row[column.prop]]) || '--' }}
            </span>
            <span v-else-if="column.prop === 'operation'">
              {{ (isEnglish ? row.operation : APP_OPERATION[row.operation]) || '--' }}
            </span>
            <span v-else-if="column.prop === 'environment'">
              {{ envMap[row[column.prop]] || '--' }}
            </span>
            <bk-user-display-name
              v-else-if="column.prop === 'operator' && isMultiTenantDisplayMode"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <span v-else>{{ row[column.prop] || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="100"
        >
          <template slot-scope="{ row }">
            <bk-button
              theme="primary"
              text
              @click="handleView(row)"
            >
              {{ $t('查看') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>

    <!-- diff 详情 -->
    <bk-sideslider
      :is-show.sync="diffConfig.isShow"
      :width="960"
      :quick-close="true"
      :title="$t('操作详情')"
      ext-cls="diff-sideslider-cls"
    >
      <diff
        slot="content"
        v-bkloading="{ isLoading: diffConfig.isLoading, color: 'rgba(255, 255, 255, 0.1)', zIndex: 10 }"
        :old-code="diffConfig.beforeYaml"
        :new-code="diffConfig.afterYaml"
      />
    </bk-sideslider>
  </div>
</template>

<script>
import { APP_OPERATION, APP_RESULT_CODE } from '@/common/constants';
import { platformColumns, appColumns } from './column';
import { mapState, mapGetters } from 'vuex';
import diff from '@/views/dev-center/app/operation-record/comps/diff.vue';
import yamljs from 'js-yaml';
import { createLongTermDatePresets } from '@/common/date';

export default {
  name: 'OperationRecord',
  components: {
    diff,
  },
  props: {
    type: {
      type: String,
      default: 'platform',
    },
  },
  data() {
    return {
      isTableLoading: true,
      // 操作记录
      records: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 20,
      },
      APP_OPERATION,
      APP_RESULT_CODE,
      envMap: {
        stag: this.$t('预发布环境'),
        prod: this.$t('生产环境'),
      },
      diffConfig: {
        isShow: false,
        beforeYaml: '',
        afterYaml: '',
        isLoading: false,
      },
      datePickerOption: {
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      dateParams: {},
      searchValues: [],
      filterOptions: {},
      // 操作对象映射
      targetMap: {},
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    ...mapState(['localLanguage']),
    ...mapGetters(['tenantId', 'isMultiTenantDisplayMode']),
    isPlatform() {
      return this.type === 'platform';
    },
    isEnglish() {
      return this.$store.state.localLanguage === 'en';
    },
    columns() {
      return this.isPlatform ? platformColumns : appColumns;
    },
    dateShortcuts() {
      return createLongTermDatePresets(this.$i18n);
    },
    searchData() {
      return [
        {
          name: this.$t('操作对象'),
          id: 'target',
          children: this.filterOptions.target ?? [],
        },
        {
          name: this.$t('操作类型'),
          id: 'operation',
          children: this.filterOptions.operation ?? [],
        },
        {
          name: this.$t('状态'),
          id: 'status',
          children: this.filterOptions.status ?? [],
        },
        {
          name: this.$t('操作人'),
          id: 'operator',
          placeholder: this.$t('请输入操作人'),
          remote: true,
          async: true,
        },
      ];
    },
    filteredSearchData() {
      const existingIds = this.searchValues.map((item) => item.id);
      return this.searchData.filter((item) => !existingIds.includes(item.id));
    },
  },
  created() {
    this.getRecords();
    this.getFilterOptions();
  },
  methods: {
    // 页容量改变
    pgHandlePageLimitChange(limit) {
      this.pagination.current = 1;
      this.pagination.limit = limit;
      this.getRecords();
    },
    // 页码改变
    pgHandlePageChange(page) {
      this.pagination.current = page;
      this.getRecords();
    },
    filterEmptyParams(obj) {
      const filtered = {};
      for (const [key, value] of Object.entries(obj)) {
        if (value !== '' && value !== null && value !== undefined) {
          filtered[key] = value;
        }
      }
      return filtered;
    },
    // 处理列表请求参数
    constructQueryParams() {
      const { limit, current } = this.pagination;
      const search = this.searchValues.map((v) => {
        return {
          [v.id]: v.values[0]?.id,
        };
      });
      const searchParams = Object.assign({}, ...search);
      const queryParams = {
        limit,
        offset: limit * (current - 1),
        ...this.filterEmptyParams(this.dateParams),
        ...searchParams,
      };
      return queryParams;
    },
    // 获取操作记录
    async getRecords() {
      this.isTableLoading = true;
      const queryParams = this.constructQueryParams();
      const dispatchName = this.isPlatform ? 'getPlatformRecords' : 'getAppRecords';
      try {
        const ret = await this.$store.dispatch(`tenantOperations/${dispatchName}`, { queryParams });
        this.records = ret.results || [];
        this.pagination.count = ret.count;
        this.setTableAbnormal(false);
        this.updateTableEmptyConfig();
      } catch (e) {
        this.setTableAbnormal(true);
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    resetPaginationAndRefresh() {
      this.pagination.current = 1;
      this.getRecords();
    },
    // 查看操作详情
    handleView(row) {
      this.diffConfig.isShow = true;
      this.getPlatformRecordDetail(row.uuid);
    },
    setDiffData(before, after) {
      this.diffConfig.beforeYaml = yamljs.dump(before, { indent: 2 });
      this.diffConfig.afterYaml = yamljs.dump(after, { indent: 2 });
    },
    clearDiffData() {
      this.diffConfig.beforeYaml = '';
      this.diffConfig.afterYaml = '';
    },
    // 获取操作详情
    async getPlatformRecordDetail(recordId) {
      this.clearDiffData();
      this.diffConfig.isLoading = true;
      const dispatchName = this.isPlatform ? 'getPlatformRecordDetail' : 'getAppRecordDetail';
      try {
        const ret = await this.$store.dispatch(`tenantOperations/${dispatchName}`, {
          recordId,
        });
        const { data_before = '', data_after = '' } = ret;
        this.setDiffData(data_before, data_after);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.diffConfig.isLoading = false;
      }
    },
    // 获取操作记录过滤项
    async getFilterOptions() {
      try {
        const ret = await this.$store.dispatch('tenantOperations/getFilterOptions');
        // 格式化数据，适配 search
        const transformedData = {};
        Object.entries(ret ?? {}).forEach(([key, items]) => {
          transformedData[key] = items.map((item) => ({
            id: item.value,
            name: item.label,
          }));
        });
        this.filterOptions = transformedData;
        // 操作对象映射
        this.targetMap = (ret.target || []).reduce((acc, { value, label }) => {
          acc[value] = label;
          return acc;
        }, {});
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleDateChange(date) {
      this.dateParams = {
        start_time: date[0],
        end_time: date[1],
      };
      this.pagination.current = 1;
    },
    handleDateClear() {
      this.dateParams = {};
      this.resetPaginationAndRefresh();
    },
    // 异步获取列表数据
    handleRemoteMethod(val) {
      return new Promise(async (resolve) => {
        if (val.includes(this.$t('操作人'))) {
          resolve([]);
          return;
        }
        const users = await this.getTenantUsers(val);
        resolve(users);
      });
    },
    // 获取多租户人员列表数据
    async getTenantUsers(keyword) {
      if (!this.tenantId) return [];
      try {
        const { data = [] } = await this.$store.dispatch('tenant/searchTenantUsers', {
          keyword,
          tenantId: this.tenantId,
        });
        return data.map(({ login_name, bk_username, ...rest }) => ({
          ...rest,
          name: login_name,
          id: bk_username,
        }));
      } catch {
        return [];
      }
    },
    // 设置表格异常状态
    setTableAbnormal(isAbnormal = true) {
      this.tableEmptyConf.isAbnormal = isAbnormal;
    },
    // 清空搜索筛选条件
    clearFilterKey() {
      this.searchValues = [];
      this.dateParams = {};
      this.$refs?.datePickerRef?.handleClear();
      this.$refs.tableRef?.clearFilter();
    },
    updateTableEmptyConfig() {
      if (this.searchValues?.length || Object.keys(this.dateParams)?.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.operation-record-container {
  .top-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 16px;
    .search-select-cls {
      background: #fff;
      flex: 1;
    }
    /deep/ .date-picker-wrapper {
      flex-shrink: 0;
      &:hover .clear-action {
        display: block;
      }
      .bk-date-picker-rel {
        .icon-wrapper {
          left: 0 !important;
        }
      }
    }
  }
  .table-wrapper {
    background-color: #fff;
  }
}
.diff-sideslider-cls {
  display: flex;
  flex-direction: column;
  height: 100%;
  /deep/ .bk-sideslider-wrapper {
    background: #1d1d1d;
    .bk-sideslider-content {
      overflow-x: hidden;
      overflow: hidden;
    }
  }
}
</style>
