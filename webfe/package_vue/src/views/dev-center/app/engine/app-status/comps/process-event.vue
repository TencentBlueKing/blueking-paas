<template>
  <div class="event-container">
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="event-list-loading"
    >
      <bk-table
        v-bkloading="{ isLoading: isPageLoading }"
        :data="currentPageData"
        :outer-border="false"
        :size="'small'"
        :pagination="pagination"
        :height="currentPageData.length ? '' : '520px'"
        :show-overflow-tooltip="true"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange"
      >
        <div slot="empty">
          <table-empty empty />
        </div>
        <bk-table-column
          :label="$t('最近出现时间')"
          prop="last_seen"
          :render-header="$renderHeader"
        />
        <bk-table-column
          :label="$t('组件')"
          prop="source_component"
        />
        <bk-table-column
          :label="$t('级别')"
          prop="type"
        />
        <bk-table-column
          :label="$t('事件内容')"
          prop="message"
          :render-header="$renderHeader"
        />
        <bk-table-column
          :label="$t('累计出现次数')"
          prop="count"
          :render-header="$renderHeader"
        />
      </bk-table>
    </paas-content-loader>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
    mixins: [appBaseMixin],
    props: {
        environment: {
            type: String,
            default: ''
        },
        events: {
            type: Array,
            default: () => []
        }
    },
    data () {
        return {
            isLoading: true,
            pagination: {
                current: 1,
                count: 0,
                limit: 10
            },
            isPageLoading: false,
            currentPageData: [],
            allEvents: []
        };
    },
    watch: {
        events: {
            handler (newEvents) {
                this.allEvents = newEvents;
                this.pagination.count = newEvents.length;
                this.getCurrentPageList();
            },
            deep: true
        }
    },
    created () {
        this.init();
    },
    methods: {
        init () {
            this.allEvents = this.events;
            this.getCurrentPageList();
            this.pagination.count = this.allEvents.length;
            setTimeout(() => {
                this.isLoading = false;
            }, 500);
        },
        handlePageLimitChange (limit) {
            this.pagination.limit = limit;
            this.pagination.current = 1;
            this.getCurrentPageList();
        },
        handlePageChange (newPage) {
            this.pagination.current = newPage;
            this.getCurrentPageList();
        },
        // 分页
        getCurrentPageList () {
            this.isPageLoading = true;
            this.currentPageData = this.allEvents.slice((this.pagination.current - 1) * this.pagination.limit, this.pagination.current * this.pagination.limit);
            setTimeout(() => {
                this.isPageLoading = false;
            }, 300);
        }
    }
};
</script>

<style lang="scss" scoped>
.event-container {
    padding: 0 20px 20px;
}
</style>
