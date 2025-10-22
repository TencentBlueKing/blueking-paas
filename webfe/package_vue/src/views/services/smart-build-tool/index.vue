<template>
  <div class="smart-build-tool-container">
    <div class="ps-top-bar">
      <h2>{{ $t('S-mart 打包工具') }}</h2>
    </div>
    <div class="tool-main">
      <bk-alert
        class="mb-16"
        type="info"
      >
        <div slot="title">
          {{
            $t(
              'S-mart 应用包是一种便捷的应用打包与交付方式，每个 S-mart 应用包可以直接部署到其他环境中。本工具支持将源代码打包为 S-mart 应用包。'
            )
          }}
          <a
            class="ml5"
            :href="GLOBAL.DOC.SMART_APP_FEATURES"
            target="_blank"
          >
            {{ $t('S-mart 应用特性说明') }}
          </a>
        </div>
      </bk-alert>
      <bk-button
        :theme="'primary'"
        @click="handleShowSidebar"
      >
        {{ $t('生成 S-mart 包') }}
      </bk-button>
      <div class="tool-table-container card-style mt-16">
        <div class="top-bar mb-8 flex-row justify-content-between align-items-center">
          <div class="g-sub-title">{{ $t('打包历史') }}</div>
          <bk-input
            v-model="searchValue"
            :placeholder="$t('请输入分支 / 包名 / 操作人')"
            :right-icon="'bk-icon icon-search'"
            style="width: 480px"
            clearable
            @clear="handleSearch"
            @enter="handleSearch"
            @right-icon-click="handleSearch"
          ></bk-input>
        </div>
        <bk-table
          :data="tableList"
          :outer-border="false"
          :pagination="pagination"
          size="small"
          class="plan-table-cls"
          v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
          @page-change="handlePageChange"
          @page-limit-change="handlePageLimitChange"
          @filter-change="handleFilterChange"
          @sort-change="handleSortChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              :empty-title="$t('暂无打包历史')"
              @reacquire="getBuildRecords"
              @clear-filter="clearFilterKey"
            />
            <bk-button
              v-if="!tableEmptyConf.keyword"
              text
              theme="primary"
              @click="handleShowSidebar"
            >
              {{ $t('去生成 S-mart 包') }}
            </bk-button>
          </div>
          <bk-table-column
            v-for="column in columns"
            v-bind="column"
            :label="column.label"
            :prop="column.prop"
            :key="column.label"
            show-overflow-tooltip
          >
            <template slot-scope="{ row }">
              <template v-if="column.prop === 'status'">
                <round-loading
                  v-if="row[column.prop] === 'pending'"
                  class="mr-8"
                />
                <span
                  v-else
                  :class="['g-dot-default mr-8', row[column.prop]]"
                ></span>
                {{ statusMap[row[column.prop]] || row[column.prop] || '--' }}
              </template>
              <bk-user-display-name
                v-else-if="column.prop === 'operator' && isMultiTenantDisplayMode"
                :user-id="row[column.prop]"
              ></bk-user-display-name>
              <template v-else-if="column.prop === 'source_origin'">
                <span>{{ sourceTypeMap[row[column.prop]] || '--' }}</span>
              </template>
              <span v-else>{{ row[column.prop] ?? '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            :width="140"
          >
            <template slot-scope="{ row }">
              <bk-button
                theme="primary"
                text
                class="mr10"
                :disabled="!row.artifact_url"
                @click="downloadBuildLog(row)"
              >
                {{ $t('下载') }}
              </bk-button>
              <bk-button
                theme="primary"
                text
                @click="viewExecutionDetails(row)"
              >
                {{ $t('执行详情') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </div>

    <!-- 生成 S-mart 包侧边栏 -->
    <SmartSideslider
      :show.sync="smartSideConfig.visible"
      :isDetail="smartSideConfig.isDetail"
      :row-data="smartSideConfig.row"
      @refresh-list="getBuildRecords"
    />
  </div>
</template>

<script>
import SmartSideslider from './smart-sideslider.vue';
import { filterUndefinedProperties } from '@/common/tools';
import { fileDownload } from '@/common/utils';
import { mapGetters } from 'vuex';

export default {
  name: 'SmartBuildTool',
  components: { SmartSideslider },
  data() {
    return {
      searchValue: '',
      tableList: [],
      isTableLoading: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [10, 20, 50, 100],
      },
      // 表头过滤
      tableFilterMap: {},
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      sourceTypeMap: {
        repo: this.$t('代码仓库'),
        package: this.$t('源码包'),
      },
      // 侧边栏配置
      smartSideConfig: {
        visible: false,
        // 是否查看执行详情
        isDetail: false,
        row: {},
      },
    };
  },
  computed: {
    ...mapGetters(['isMultiTenantDisplayMode']),
    // 状态映射配置
    statusMap() {
      return {
        successful: this.$t('成功'),
        failed: this.$t('失败'),
        pending: this.$t('等待'),
        interrupted: this.$t('已中断'),
      };
    },
    // 状态过滤器配置
    statusFilters() {
      return Object.entries(this.statusMap).map(([value, text]) => ({
        text,
        value,
      }));
    },
    columns() {
      return [
        {
          label: `${this.$t('构建')} ID`,
          prop: 'uuid',
          'min-width': 140,
        },
        {
          label: this.$t('源码来源'),
          prop: 'source_origin',
        },
        {
          label: this.$t('源码包 / 代码分支'),
          prop: 'package_name',
        },
        {
          label: this.$t('状态'),
          prop: 'status',
          filters: this.statusFilters,
          'filter-multiple': false,
          'column-key': 'status',
        },
        {
          label: this.$t('操作人'),
          prop: 'operator',
        },
        {
          label: this.$t('执行时间'),
          prop: 'created',
          sortable: 'created',
          'column-key': 'created',
          tooltipsProp: 'created',
        },
      ];
    },
  },
  watch: {
    searchValue(newVal) {
      if (!newVal) {
        this.handleSearch();
      }
    },
  },
  created() {
    this.getBuildRecords();
  },
  methods: {
    // 下载构建日志
    downloadBuildLog(row) {
      try {
        fileDownload(row.artifact_url, `smart-build-${row.uuid}`);
      } catch (error) {
        this.$bkMessage({
          message: this.$t('下载文件失败'),
          theme: 'error',
        });
      }
    },
    // 处理列表请求参数
    constructQueryParams() {
      const { limit, current } = this.pagination;
      const filteredData = filterUndefinedProperties(this.tableFilterMap);

      const queryParams = {
        limit,
        offset: limit * (current - 1),
        ...filteredData,
      };
      if (this.searchValue) {
        queryParams.search = this.searchValue;
      }
      return queryParams;
    },
    // 获取打包历史
    async getBuildRecords() {
      this.isTableLoading = true;
      try {
        const params = this.constructQueryParams();
        const res = await this.$store.dispatch('tool/getSmartBuildRecords', { params });
        this.tableList = res.results || [];
        this.pagination.count = res.count;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    handleSearch() {
      this.resetPage();
      this.getBuildRecords();
    },
    resetPage() {
      this.pagination.current = 1;
    },
    // 页容量改变
    handlePageLimitChange(limit) {
      this.resetPage();
      this.pagination.limit = limit;
      this.getBuildRecords();
    },
    // 页码改变
    handlePageChange(page) {
      this.pagination.current = page;
      this.getBuildRecords();
    },
    transformData(data) {
      const key = Object.keys(data)[0];
      return { [key]: data[key][0] };
    },
    // 表头筛选
    handleFilterChange(filter) {
      this.tableFilterMap = Object.assign(this.tableFilterMap, { ...this.transformData(filter) });
      this.getBuildRecords();
    },
    // 表头排序-时间
    handleSortChange(sort) {
      const propMap = {
        created: 'created',
      };

      const orderBy = sort.order
        ? sort.order === 'ascending'
          ? `-${propMap[sort.prop]}`
          : propMap[sort.prop]
        : undefined;
      this.$set(this.tableFilterMap, 'order_by', orderBy);
      this.getBuildRecords();
    },
    // 清空搜索筛选条件
    clearFilterKey() {
      this.searchValue = '';
      this.tableFilterMap = {};
      this.$refs.tableRef?.clearFilter();
      this.getBuildRecords();
    },
    // 显示侧栏
    handleShowSidebar() {
      this.smartSideConfig = {
        visible: true,
        isDetail: false,
        row: {},
      };
    },
    // 查看执行详情
    async viewExecutionDetails(row) {
      this.smartSideConfig = {
        visible: true,
        isDetail: true,
        row,
      };
    },
    updateTableEmptyConfig() {
      const filteredData = filterUndefinedProperties(this.tableFilterMap);
      if (this.searchValue || Object.keys(filteredData)?.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.smart-build-tool-container {
  .tool-main {
    padding: 16px 24px 24px;
  }
  .tool-table-container {
    background-color: #fff;
    padding: 12px 16px;
  }
}
</style>
