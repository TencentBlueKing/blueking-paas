<template>
  <bk-sideslider
    :is-show.sync="isShow"
    :title="$t('进程 {n1} 实例 {n2} 事件详情', { n1: config?.processName, n2: config?.name })"
    :quick-close="true"
    :width="width"
    @hidden="handleHidden">
    <div class="p20" slot="content">
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
          :show-overflow-tooltip="column.prop !== 'first_timestamp'"
          :key="column.prop"
          :render-header="$renderHeader"
        >
          <template slot-scope="{ row }">
            <span
              v-bk-tooltips="{
                html: getTooltipsHtml(row),
                disabled: column.prop !== 'first_timestamp',
              }"
            >{{ row[column.prop] || '--' }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </bk-sideslider>
</template>

<script>
import { paginationFun } from '@/common/utils';
import dayjs from 'dayjs';
export default {
  name: 'EventDetail',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => {},
    },
    env: {
      type: String,
      default: '',
    },
    moduleId: {
      type: String,
      default: '',
    },
    width: {
      type: Number,
      default: 980,
    },
  },
  data() {
    return {
      isShow: false,
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
  watch: {
    value(newVal) {
      this.isShow = newVal;
      if (newVal) {
        this.getInstanceEvents();
      }
    },
  },
  methods: {
    getTooltipsHtml(row) {
      return `<div><p>${this.$t('首次发生时间')}：${row.first_timestamp}</p><p>${this.$t('最新发生时间')}：${row.last_timestamp}</p></div>`;
    },
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
          name: this.config.instanceName,
        });
        instanceEventList.forEach((item) => {
          item.first_timestamp = item.first_timestamp === null ? item.first_timestamp : dayjs(item.first_timestamp).format('YYYY-MM-DD HH:mm:ss');
          item.last_timestamp = item.last_timestamp === null ? item.last_timestamp : dayjs(item.last_timestamp).format('YYYY-MM-DD HH:mm:ss');
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
    handleHidden() {
      this.pagination = {
        current: 1,
        count: 0,
        limit: 10,
      },
      this.allEvents = [];
      this.instanceEvents = [];
      this.$emit('change', false);
    },
  },
};
</script>
