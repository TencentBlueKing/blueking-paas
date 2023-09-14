<template>
  <div class="deploy-history">
    <paas-content-loader
      :is-loading="isLoading"
      :is-transition="false"
      placeholder="event-list-loading"
      :class="{ 'deploy-history-loader': isLoading }"
    >
      <section class="search-wrapper">
        <!-- 模块列表 -->
        <bk-select
          v-model="moduleValue"
          style="width: 154px;"
          :clearable="false"
          searchable>
          <bk-option v-for="option in curAppModuleList"
              :key="option.name"
              :id="option.name"
              :name="option.name">
          </bk-option>
        </bk-select>
        <!-- 只支持从操作人搜索 -->
        <user
          v-model="personnelSelectorList"
          style="width: 320px;"
          :placeholder="$t('请输入')"
          :max-data="1"
        />
      </section>
      <bk-table
        v-bkloading="{ isLoading: isPageLoading }"
        ref="historyRef"
        class="mt15 ps-history-list"
        :data="historyList"
        :outer-border="false"
        :size="'small'"
        :pagination="pagination"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
        @sort-change="handleSortChange"
        @filter-change="handleFilterChange"
      >
        <div slot="empty">
          <table-empty
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            @reacquire="getDeployHistory"
            @clear-filter="handleClearFilter"
          />
        </div>
        <bk-table-column
          :label="$t('部署环境')"
          prop="environment"
          column-key="env"
          :filters="sourceFilters"
          :filter-multiple="false"
          :render-header="$renderHeader"
        >
          <template slot-scope="{ row }">
            <span v-if="row.environment === 'stag'"> {{ $t('预发布环境') }} </span>
            <span v-else> {{ $t('生产环境') }} </span>
          </template>
        </bk-table-column>
        <bk-table-column
          width="150"
          :label="$t('分支')"
          :show-overflow-tooltip="false"
        >
          <template slot-scope="{ row }">
            <bk-popover>
              <span class="branch-name">{{ row.name }}</span>
              <div slot="content">
                <p class="flex">
                  <span class="label"> {{ $t('部署分支：') }} </span><span class="value">{{ row.name }}</span>
                </p>
                <p class="flex">
                  <span class="label"> {{ $t('仓库地址：') }} </span><span class="value">{{ row.url }}</span>
                </p>
              </div>
            </bk-popover>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('版本')"
          prop="revision"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('类型')"
          prop="operation_act"
          :render-header="$renderHeader"
        />
        <bk-table-column :label="$t('结果')">
          <template slot-scope="{ row }">
            <div class="flex-row align-items-center" v-if="row.status !== 'pending'">
              <span :class="['dot', row.status]" /> {{ $t(deployStatus[row.status]) }}
            </div>
            <template v-else>
              <div class="flex-row align-items-center" v-if="row.status === 'pending' && row.operation_type === 'online'">
                <span class="dot warning" /> {{ $t('部署中') }}
              </div>
              <div
                class="flex-row align-items-center" v-if="row.status === 'pending'
                  && row.operation_type === 'offline'">
                <span class="dot warning" /> {{ $t('下架中') }}
              </div>
            </template>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('耗时')"
          sortable
          :render-header="$renderHeader"
        >
          <template slot-scope="{ row }">
            {{ computedDeployTime(row) }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作人')"
          prop="operator.username"
          :render-header="$renderHeader"
        />
        <bk-table-column
          width="180"
          :label="$t('操作时间')"
          prop="created"
        />
        <bk-table-column
          width="115"
          :label="$t('操作')"
        >
          <template slot-scope="{ row }">
            <bk-button :text="true" @click="handleShowLogSideslider(row)">
              {{$t('部署日志')}}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <!-- 部署日志 -->
    <deploy-log-sideslider
      ref="logSidesliderRef"
      :app-code="'appid1'"
      :module-id="curModuleId"
    />
  </div>
</template>

<script>
import user from '@/components/user';
import deployLogSideslider from '@/components/deploy/deploy-log-sideslider.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import { DEPLOY_STATUS } from '@/common/constants';
import { clearFilter } from '@/common/utils';
import { cloneDeep } from 'lodash';

export default {
  components: {
    user,
    deployLogSideslider,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      isPageLoading: false,
      historyList: [],
      oldHistoryList: [],
      deployStatus: DEPLOY_STATUS,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      personnelSelectorList: [],
      // 部署日志
      logSidesliderData: {},
      moduleValue: 'default',
      filterEnv: []
    };
  },

  computed: {
    sourceFilters() {
      return [
        { text: this.$t('生产环境'), value: 'prod' },
        { text: this.$t('预发布环境'), value: 'stag' },
      ];
    },
  },

  watch: {
    personnelSelectorList() {
      this.getDeployHistory();
    },
    moduleValue (value) {
      // 重新发起请求并附带参数
      this.getDeployHistory();
    },
    filterEnv () {
      this.getDeployHistory();
    }
  },

  created() {
    this.init();
  },

  methods: {
    init() {
      this.getDeployHistory();
    },

    /**
     * 计算耗时时间
     */
    computedDeployTime(payload) {
      if (!payload.deployment) {
        return '--';
      }

      if (!payload.deployment.complete_time || !payload.deployment.start_time) {
        return '--';
      }

      const start = new Date(payload.deployment.start_time).getTime();
      const end = new Date(payload.deployment.complete_time).getTime();
      const interval = (end - start) / 1000;

      if (!interval) {
        return `< 1${this.$t('秒')}`;
      }

      return this.getDisplayTime(interval);
    },

    getDisplayTime(payload) {
      let theTime = payload;
      if (theTime < 1) {
        return `< 1${this.$t('秒')}`;
      }
      let middle = 0;
      let hour = 0;

      if (theTime > 60) {
        middle = parseInt(theTime / 60, 10);
        theTime = parseInt(theTime % 60, 10);
        if (middle > 60) {
          hour = parseInt(middle / 60, 10);
          middle = parseInt(middle % 60, 10);
        }
      }

      let result = '';

      if (theTime > 0) {
        result = `${theTime}${this.$t('秒')}`;
      }
      if (middle > 0) {
        result = `${middle}${this.$t('分')}${result}`;
      }
      if (hour > 0) {
        result = `${hour}${this.$t('时')}${result}`;
      }

      return result;
    },

    /**
     * 获取部署历史记录
     */
    async getDeployHistory(page = 1) {
      this.isPageLoading = true;

      const curPage = page || this.pagination.current;
      const pageParams = {
        limit: this.pagination.limit,
        offset: this.pagination.limit * (curPage - 1),
      };

      // 部署环境
      if (this.filterEnv.length) {
        pageParams.environment = this.filterEnv[0];
      }

      // 操作人
      if (this.personnelSelectorList.length) {
        pageParams.operator = this.personnelSelectorList[0];
      }

      try {
        const res = await this.$store.dispatch('deploy/getDeployHistory', {
          appCode: this.appCode,
          moduleId: this.moduleValue,
          pageParams,
        });

        const reg = RegExp('^[a-z0-9]{40}$');
        res.results.forEach((operation) => {
          const key = operation.operation_type === 'offline' ? 'offline_operation' : 'deployment';
          operation.environment = operation[key].environment;
          operation.name = operation[key].repo.name;
          operation.revision = operation[key].repo.revision;
          operation.url = operation[key].repo.url;

          if (reg.test(operation[key].repo.revision)) {
            operation.revision = operation[key].repo.revision.substring(0, 8);
          }

          if (operation.operation_type === 'offline') {
            operation.logDetail = operation.offline_operation.log;
            operation.operation_act = this.$t('下架');
          } else {
            operation.deployment_id = operation.deployment.deployment_id;
            operation.logDetail = '';
            operation.operation_act = this.$t('部署');
          }
        });

        this.historyList = res.results;
        this.pagination.count = res.count;

        this.oldHistoryList = cloneDeep(res.results);
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isPageLoading = false;
        this.isLoading = false
      }
    },

    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getDeployHistory(this.pagination.current);
    },

    /** 页容量改变 */
    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.getDeployHistory(newPage);
    },

    /** 排序 */
    handleSortChange({ order }) {
      this.historyList.forEach((item) => {
        item.interval = this.getTimeConsuming(item);
      });
      switch (order) {
        case 'ascending':
          this.historyList.sort((a, b) => a.interval - b.interval);
          break;
        case 'descending':
          this.historyList.sort((a, b) => b.interval - a.interval);
          break;
        default:
          this.historyList = cloneDeep(this.oldHistoryList);
          break;
      }
    },

    handleFilterChange (filter) {
      this.filterEnv = filter.env || [];
    },

    getTimeConsuming(payload) {
      if (!payload.deployment) {
        return 0;
      }

      if (!payload.deployment.complete_time || !payload.deployment.start_time) {
        return 0;
      }

      const start = new Date(payload.deployment.start_time).getTime();
      const end = new Date(payload.deployment.complete_time).getTime();
      const interval = (end - start) / 1000;

      return interval;
    },

    computedDeployTimelineTime(startTime, endTime) {
      if (!startTime || !endTime) {
        return '--';
      }

      const start = (new Date(startTime).getTime()) / 1000;
      const end = (new Date(endTime).getTime()) / 1000;
      const interval = Math.ceil(end - start);

      if (!interval) {
        return `< 1${this.$t('秒')}`;
      }

      return this.getDisplayTime(interval);
    },

    /**
     * 部署日志侧栏
     */
    handleShowLogSideslider(row) {
      this.$refs.logSidesliderRef?.handleShowLog(row);
    },

    handleClearFilter() {
      this.personnelSelectorList = [];
      // 手动清空表头筛选
      if (this.$refs.historyRef.$refs?.tableHeader) {
        const { tableHeader } = this.$refs.historyRef.$refs;
        clearFilter(tableHeader);
      }
      this.getDeployHistory();
    },

    updateTableEmptyConfig() {
      if (this.personnelSelectorList.length || this.filterEnv.length) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-history {
  background: #fff;
  padding: 24px;
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;

  .deploy-history-loader {
    height: 520px;
  }

  .search-wrapper {
    display: flex;
    justify-content: space-between;
  }

  .deploy-detail {
      display: flex;
      height: 100%;

      /deep/ .paas-deploy-log-wrapper {
          height: 100%;
      }
  }

  .dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.failed {
      background: #EA3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.warning {
      background: #FF9C01;
      border: 3px solid #ffefd6;
    }
    &.successful {
      background: #3FC06D;
      border: 3px solid #daefe4;
    }
  }
}
</style>
