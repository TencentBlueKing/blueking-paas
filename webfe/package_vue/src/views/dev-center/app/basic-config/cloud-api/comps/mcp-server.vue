<template>
  <div class="mcp-server-container">
    <div class="flex-row justify-content-between mb-16">
      <bk-button
        theme="primary"
        :disabled="!selectionList.length"
        @click="handleShowApplyDialog('batch')"
      >
        {{ $t('批量申请') }}
      </bk-button>
      <bk-input
        v-model="searchQuery"
        style="width: 400px"
        :placeholder="$t('请输入 MCP Server 名称或描述')"
        :clearable="true"
        :right-icon="'bk-icon icon-search'"
        @clear="handleSearch"
        @right-icon-click="handleSearch"
      ></bk-input>
    </div>
    <bk-table
      ref="mcpServerTable"
      :data="mcpServerList"
      :size="'small'"
      :pagination="pagination"
      :shift-multi-checked="true"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
      @page-change="handlePageChange"
      @page-limit-change="handlePageLimitChange"
      @selection-change="handleSelectionChange"
      @filter-change="handleFilterChange"
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
        type="selection"
        width="60"
        :selectable="selectable"
      ></bk-table-column>
      <bk-table-column
        v-for="column in columns"
        v-bind="column"
        :label="$t(column.label)"
        :key="column.prop"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <!-- 状态 -->
          <span v-if="column.prop === 'permission.status'">
            <round-loading
              v-if="row.permission?.status === 'pending'"
              ext-cls="applying"
            />
            <span
              v-else
              :class="['dot-icon', 'paasng-icon', row.permission?.status]"
            />
            <span
              v-bk-tooltips="{
                content: `${$t('请联系{n}负责人审批：', { n: ' MCP Server ' })} ${row.permission?.handled_by?.join(
                  '，'
                )}`,
                disabled: !row.permission?.handled_by?.length || row.permission?.status !== 'pending',
              }"
            >
              {{ $t(MCP_SERVER_STATUS[row.permission?.status]) || '--' }}
            </span>
          </span>
          <span v-else-if="['name', 'description'].includes(column.prop)">
            <a
              v-if="row.mcp_server?.doc_link && column.prop === 'name'"
              :href="row.mcp_server?.doc_link"
              target="_blank"
              v-dompurify-html="highlight(row.mcp_server?.name || '--')"
            ></a>
            <span
              v-else
              v-dompurify-html="highlight(row.mcp_server?.[column.prop] || '--')"
            ></span>
          </span>
          <template v-else>
            {{ row.mcp_server?.[column.prop] || '--' }}
          </template>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        width="120"
      >
        <template slot-scope="{ row }">
          <bk-button
            theme="primary"
            text
            :disabled="row.applyDisabled"
            @click="handleShowApplyDialog('single', row)"
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
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 申请权限弹窗 -->
    <BatchDialog
      :show.sync="applyDialog.visiable"
      :title="applyDialog.title"
      :rows="applyDialog.rows"
      :app-code="appCode"
      :api-type="'mcp-service'"
      :is-apply-time="false"
      @on-apply="handleSuccessApply"
      @after-leave="handleAfterLeave"
    />
  </div>
</template>

<script>
import BatchDialog from './batch-apply-dialog';
import { paginationFun } from '@/common/utils';
import { MCP_SERVER_STATUS } from '@/common/constants';
import { debounce } from 'lodash';

export default {
  name: 'McpServer',
  components: {
    BatchDialog,
  },
  props: {
    appCode: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      isLoading: false,
      // 全量数据
      allMcpServerList: [],
      mcpServerList: [],
      selectionList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      searchQuery: '',
      // 表头筛选字段
      headerFilterField: '',
      applyDialog: {
        visiable: false,
        title: '',
        rows: [],
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      MCP_SERVER_STATUS,
      statusFilters: Object.keys(MCP_SERVER_STATUS).map((key) => ({
        text: this.$t(MCP_SERVER_STATUS[key]),
        value: key,
      })),
    };
  },
  computed: {
    columns() {
      return [
        {
          label: '名称',
          prop: 'name',
        },
        {
          label: '描述',
          prop: 'description',
        },
        {
          label: '工具数',
          prop: 'tools_count',
        },
        {
          label: '状态',
          prop: 'permission.status',
          filters: this.statusFilters,
          'filter-multiple': false,
          'column-key': 'status',
        },
      ];
    },
  },
  watch: {
    searchQuery(newVal) {
      if (newVal.trim() === '') {
        this.pagination.current = 1;
        this.setTableData(this.allMcpServerList, this.pagination.current, this.pagination.limit);
      } else {
        this.debouncedHandleSearch();
      }
    },
    headerFilterField() {
      this.pagination.current = 1;
      const filteredData = this.getFilteredData();
      this.setTableData(filteredData, this.pagination.current, this.pagination.limit);
    },
  },
  created() {
    this.debouncedHandleSearch = debounce(this.handleSearch, 300);
    this.getMcpServerList();
  },
  beforeDestroy() {
    // 清理防抖函数
    if (this.debouncedHandleSearch) {
      this.debouncedHandleSearch.cancel();
    }
  },
  methods: {
    // 设置表格数据
    setTableData(data, page, limit) {
      const { pageData = [] } = paginationFun(data, page, limit);
      this.mcpServerList = pageData;
      this.pagination.count = data?.length || 0;
      this.updateTableEmptyConfig();
    },

    // 获取 MCP Server 列表（前端分页）
    async getMcpServerList() {
      this.isLoading = true;
      try {
        const results = await this.$store.dispatch('cloudApi/getMcpServerList', {
          appCode: this.appCode,
        });
        const disabledTips = {
          pending: this.$t('权限申请中'),
          approved: this.$t('已有权限，无需申请'),
        };
        const mcpServers = results.map((item) => {
          return {
            ...item,
            // 判断当前权限是否可以申请
            applyDisabled: ['pending', 'approved'].includes(item?.permission?.status),
            applyTips: disabledTips[item?.permission?.status] || '',
          };
        });
        this.setTableData(mcpServers, this.pagination.current, this.pagination.limit);
        // 全量数据
        this.allMcpServerList = mcpServers;
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },

    selectable(row) {
      // 申请中、已申请不可选禁用
      return !['pending', 'approved'].includes(row.permission?.status);
    },

    updateTableEmptyConfig() {
      if (this.searchQuery || this.headerFilterField) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },

    clearFilterKey() {
      this.searchQuery = '';
      this.pagination.current = 1;
      this.setTableData(this.allMcpServerList, this.pagination.current, this.pagination.limit);
    },

    // 获取过滤后的数据（根据搜索条件）
    getFilteredData() {
      console.log('this.headerFilterField', this.headerFilterField);
      if (!this.searchQuery && !this.headerFilterField) {
        return this.allMcpServerList;
      }
      const keyword = this.searchQuery.toLowerCase();
      return this.allMcpServerList.filter((item) => {
        console.log('item', item);
        const name = item.mcp_server?.name?.toLowerCase() || '';
        const description = item.mcp_server?.description?.toLowerCase() || '';
        const status = item.permission?.status || '';
        // 关键字搜索条件
        const keywordMatch = !this.searchQuery || name.includes(keyword) || description.includes(keyword);
        // 状态筛选条件
        const statusMatch = !this.headerFilterField || status === this.headerFilterField;
        // 同时满足关键字搜索和状态筛选条件
        return keywordMatch && statusMatch;
      });
    },

    // 分页处理
    handlePageChange(page) {
      this.pagination.current = page;
      const filteredData = this.getFilteredData();
      this.setTableData(filteredData, page, this.pagination.limit);
    },

    // 页容量变化
    handlePageLimitChange(limit) {
      this.pagination.current = 1;
      this.pagination.limit = limit;
      const filteredData = this.getFilteredData();
      this.setTableData(filteredData, this.pagination.current, limit);
    },

    // 选择变化
    handleSelectionChange(selection) {
      this.selectionList = selection;
    },

    // 表头筛选
    handleFilterChange(filds) {
      if (filds.status) {
        this.headerFilterField = filds.status.length ? filds.status[0] : '';
      }
    },

    // 搜索处理
    handleSearch() {
      this.pagination.current = 1;
      const filteredData = this.getFilteredData();
      this.setTableData(filteredData, this.pagination.current, this.pagination.limit);
    },

    // 格式化申请选择数据
    formatData(type, row) {
      const formatRow = (row) => {
        return {
          id: row.mcp_server?.id,
          name: row.mcp_server?.name,
          description: row.mcp_server?.description,
          status: row.permission?.status,
          expires_in: row.permission?.expires_in,
        };
      };
      if (type === 'single') {
        return [formatRow(row)];
      } else if (type === 'batch') {
        return this.selectionList.map((item) => formatRow(item));
      }
    },

    // 显示申请权限弹窗
    handleShowApplyDialog(type, row = {}) {
      this.applyDialog.rows = this.formatData(type, row);
      this.applyDialog.visiable = true;
      this.applyDialog.title = '申请权限';
    },

    // 申请成功
    handleSuccessApply() {
      this.applyDialog.visiable = false;
      // 取消table勾选
      this.$refs.mcpServerTable.clearSelection();
      this.selectionList = [];
      this.getMcpServerList();
    },

    handleAfterLeave() {
      this.applyDialog.visiable = false;
    },

    // 搜索关键词高亮
    highlight(text) {
      const keyword = this.searchQuery;
      if (!keyword || !text) return text;
      const escapeRegExp = (str) => {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      };
      const escapedKeyword = escapeRegExp(keyword);
      const regex = new RegExp(`(${escapedKeyword})`, 'gi');
      return text.replace(regex, '<marked>$1</marked>');
    },
  },
};
</script>

<style lang="scss" scoped>
.mcp-server-container {
  .dot-icon {
    display: inline-block;
    margin-right: 4px;
    width: 8px;
    height: 8px;
    background: #f0f1f5;
    border: 1px solid #c3c5ca;
    border-radius: 50%;
    &.rejected {
      background: #ffdddd;
      border-color: #ea3636;
    }
    &.approved {
      background: #cbf0da;
      border-color: #2caf5e;
    }
  }
}
</style>
