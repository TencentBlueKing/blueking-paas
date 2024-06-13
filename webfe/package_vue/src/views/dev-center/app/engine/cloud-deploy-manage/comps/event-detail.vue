<template>
  <bk-table
    :data="instanceEvents"
    size="small"
    :pagination="pagination"
    :border="false"
    :outer-border="false"
    v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    @page-change="handlePageChange"
    @page-limit-change="handlePageLimitChange">
    <bk-table-column
      v-for="column in tableColumns"
      :label="column.label"
      :prop="column.prop"
      show-overflow-tooltip
      :key="column.prop"
      :render-header="$renderHeader"
    >
    </bk-table-column>
  </bk-table>
</template>

<script>
import { paginationFun } from '@/common/utils';
export default {
  name: 'EventDetail',
  props: {
    env: {
      type: String,
      default: '',
    },
    moduleId: {
      type: String,
      default: '',
    },
    instanceName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      allEvents: [],
      instanceEvents: [],
      isTableLoading: false,
      tableColumns: [
        {
          label: this.$t('首次发生时间'),
          prop: 'first_timestamp',
        },
        {
          label: this.$t('最新发生时间'),
          prop: 'last_timestamp',
        },
        {
          label: this.$t('事件类型'),
          prop: 'type',
        },
        {
          label: this.$t('事件原因'),
          prop: 'reason',
        },
        {
          label: this.$t('事件次数'),
          prop: 'count',
        },
        {
          label: this.$t('事件内容'),
          prop: 'message',
        },
      ],
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
  },
  created() {
    this.getInstanceEvents();
  },
  methods: {
    // 前端分页
    handlePagination(data, current, limit) {
      const { pageData } = paginationFun(data, current, limit);
      this.instanceEvents = pageData;
    },
    handlePageLimitChange(limit) {
      this.handlePagination(this.allEvents, this.pagination.current, limit);
      this.pagination.limit = limit;
    },
    handlePageChange(page) {
      this.handlePagination(this.allEvents, page, this.pagination.limit);
      this.pagination.current = page;
    },
    // 获取事件详情
    async getInstanceEvents() {
      this.isTableLoading = true;
      try {
        const instanceEventList = await this.$store.dispatch('deploy/getInstanceEvents', {
          appCode: this.appCode,
          moduleId: this.moduleId,
          env: this.env,
          name: this.instanceName,
        });
        this.allEvents = instanceEventList;
        this.pagination.count = this.allEvents.length;
        this.handlePagination(this.allEvents, this.pagination.current, this.pagination.limit);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
      }
    },
  },
};
</script>
