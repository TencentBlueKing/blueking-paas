<template>
  <div class="operation-records">
    <paas-plugin-title />
    <paas-content-loader
      class="app-container"
      :is-loading="isLoading"
      placeholder="deploy-inner-history-loading"
      :is-transform="false"
    >
      <div class="record-main card-style">
        <div class="tools">
          <!-- 时间筛选 -->
          <bk-date-picker
            :placeholder="$t('选择日期时间范围')"
            :clearable="true"
            :shortcuts="dateShortcuts"
            :format="'yyyy-MM-dd HH:mm:ss'"
            :shortcut-close="true"
            :options="datePickerOption"
            type="datetimerange"
            ext-cls="record-date-picker-cls"
            @change="handleDateChange"
            @pick-success="getPluginOperations(1)"
          ></bk-date-picker>
          <div class="user-filter">
            <span class="mr15">{{ $t('操作人') }}</span>
            <user
              v-model="operatorList"
              style="width: 350px"
              :placeholder="$t('请输入')"
              :multiple="false"
              @change="getPluginOperations(1)"
            />
          </div>
        </div>
        <div class="table-wrapper">
          <bk-table
            :data="operationRecords"
            size="small"
            ref="records"
            v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
            :pagination="pagination"
            @page-change="handlePageChange"
            @page-limit-change="handlePageLimitChange"
            @filter-change="handleFilterChange"
          >
            <div slot="empty">
              <table-empty
                :keyword="tableEmptyConf.keyword"
                :abnormal="tableEmptyConf.isAbnormal"
                @reacquire="getPluginOperations"
                @clear-filter="clearFilterKey"
              />
            </div>
            <bk-table-column
              :label="$t('操作对象')"
              prop="subject"
              column-key="subject"
              :filters="subjectFilters"
              :filter-multiple="false"
            >
              <span slot-scope="{ row }">
                {{ (isEnglish ? row.subject : PLUGIN_SUBJECT[row.subject]) ?? '--' }}
              </span>
            </bk-table-column>
            <bk-table-column
              :label="$t('操作类型')"
              prop="action"
              column-key="action"
              :filters="actionFilters"
              :filter-multiple="false"
            >
              <template slot-scope="{ row }">
                {{ (isEnglish ? row.action : PLUGIN_ACTION[row.action]) || '--' }}
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('对象属性')"
              prop="specific"
            >
              <span slot-scope="{ row }">
                {{ row?.specific || '--' }}
              </span>
            </bk-table-column>
            <bk-table-column
              :label="$t('操作人')"
              prop="operator"
            ></bk-table-column>
            <bk-table-column
              :label="$t('操作时间')"
              prop="updated"
            ></bk-table-column>
          </bk-table>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import user from '@/components/user';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import { PLUGIN_SUBJECT, PLUGIN_ACTION } from '@/common/constants';
import { createTimeShortcuts } from '@/common/date';
export default {
  name: 'PluginOperationRecords',
  components: {
    paasPluginTitle,
    user,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isLoading: true,
      operationRecords: [],
      isTableLoading: false,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [5, 10, 20, 50],
      },
      filterParams: {},
      dateParams: {},
      PLUGIN_SUBJECT,
      PLUGIN_ACTION,
      operatorList: [],
      datePickerOption: {
        // 小于今天的日期不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    isEnglish() {
      return this.$store.state.localLanguage === 'en';
    },
    subjectFilters() {
      return this.formatTableFilters(PLUGIN_SUBJECT);
    },
    actionFilters() {
      return this.formatTableFilters(PLUGIN_ACTION);
    },
    dateShortcuts() {
      return createTimeShortcuts(this.$i18n);
    },
  },
  created() {
    this.getPluginOperations();
  },
  methods: {
    formatTableFilters(obj, type = null) {
      return Object.entries(obj).map(([key, value]) => {
        const text = this.isEnglish && !type ? key : type ? this.$t(value) : value;
        return { value: key, text };
      });
    },
    // 获取动态
    async getPluginOperations(page = 1) {
      this.isTableLoading = true;
      try {
        const curPage = page || this.pagination.current;
        if (page === 1) {
          // 重置页码
          this.pagination.current = 1;
        }
        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
          ...this.filterParams,
          ...this.dateParams,
          ...(this.operatorList.length && { operator: this.operatorList.join(',') }),
        };
        const res = await this.$store.dispatch('plugin/getPluginOperations', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          params,
        });
        this.operationRecords = res.results;
        this.pagination.count = res.count;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.isTableLoading = false;
      }
    },
    handlePageChange(page) {
      this.pagination.current = page;
      this.getPluginOperations(page);
    },
    handlePageLimitChange(newLimit) {
      this.pagination.limit = newLimit;
      this.getPluginOperations();
    },
    // 表格筛选
    handleFilterChange(filter) {
      Object.keys(filter).forEach((key) => {
        if (filter[key].length > 0) {
          this.filterParams[key] = filter[key][0];
        } else {
          delete this.filterParams[key];
        }
      });
      this.pagination.current = 1;
      this.getPluginOperations();
    },
    // 时间筛选
    handleDateChange(date) {
      // 清空
      if (date?.every((t) => t === '')) {
        this.dateParams = {};
        this.getPluginOperations(1);
        return;
      }
      this.dateParams = {
        start_time: date[0],
        end_time: date[1],
      };
    },
    // 清空当前表格筛选项
    clearFilterKey() {
      this.dateParams = {};
      this.operatorList = [];
      this.$refs.records?.clearFilter();
    },
    updateTableEmptyConfig() {
      if (this.operatorList.length || Object.keys(this.filterParams).length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.operation-records {
  .record-main {
    padding: 24px;
    .tools {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      /deep/ .record-date-picker-cls {
        width: 300px;
        .icon-wrapper {
          left: 0 !important;
        }
        .bk-date-picker-rel .clear-action {
          display: block;
        }
      }
    }
    .user-filter {
      display: flex;
      align-items: center;
      margin-left: 16px;
    }
  }
}
</style>
