<template>
  <div class="clund-build-history">
    <paas-content-loader
      :is-loading="isLoading"
      :is-transition="false"
      placeholder="event-list-loading"
    >
      <section class="module-select">
        <bk-select
          v-model="moduleName"
          style="width: 150px"
          :clearable="false"
          ext-cls="module-select-custom"
          prefix-icon="paasng-icon paasng-project"
          @change="handleModuleChange"
        >
          <bk-option
            v-for="option in curAppModuleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
        </bk-select>
      </section>
      <bk-table
        v-bkloading="{ isLoading: isPageLoading }"
        ref="historyRef"
        class="mt15 ps-history-list"
        :data="historyList"
        :outer-border="false"
        :size="'small'"
        :height="historyList.length ? '' : '520px'"
        :pagination="pagination"
        @page-limit-change="handlePageLimitChange"
        @page-change="handlePageChange"
      >
        <div slot="empty">
          <table-empty empty />
        </div>
        <bk-table-column
          :label="$t('执行 ID')"
          prop="generation"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('镜像 tag')"
          prop="image_tag"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row }">
            {{ row.image_tag || '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('状态')"
          min-width="100"
        >
          <template slot-scope="{ row }">
            <div class="flex-row align-items-center">
              <span :class="['dot', row.status]" />
              {{ $t(buildStatus[row.status]) }}
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('触发信息')"
          prop="invoke_message"
          :render-header="$renderHeader"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('开始时间')"
          prop="start_at"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('持续时间')"
          prop="duration"
          sortable
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row }">
            <!-- completed_at 存在 null 的情况 -->
            <!-- completed_at 完成时间 持续时间=开始时间-完成时间 -->
            {{ row.durationText }}
          </template>
        </bk-table-column>
        <bk-table-column
          width="115"
          :label="$t('操作')"
        >
          <template slot-scope="{ row }">
            <bk-button
              :text="true"
              @click="handleHistoryDetail(row)"
            >
              {{ $t('查看详情') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <!-- 构建详情 -->
    <deploy-log-sideslider
      ref="logSidesliderRef"
      :app-code="appCode"
      :module-id="curModuleId"
    />
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import deployLogSideslider from '@/components/deploy/deploy-log-sideslider.vue';
import { cloneDeep } from 'lodash';
import dayjs from 'dayjs';
export default {
  name: 'ClundBuildHistory',
  components: {
    deployLogSideslider,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      isPageLoading: false,
      moduleName: '',
      historyList: [],
      oldHistoryList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      // successful(成功), failed(失败), pending(等待), interrupted(已中断)
      buildStatus: {
        successful: this.$t('成功'),
        failed: this.$t('失败'),
        pending: this.$t('等待'),
        interrupted: this.$t('已中断'),
      },
      sidesliderConfig: {
        isShow: false,
      },
      buildDetails: {},
      curLogs: '',
      errorTips: {},
      isLogLoading: false,
      isTimelineLoading: false,
    };
  },
  computed: {
    isMatchedSolutionsFound() {
      return this.errorTips.matched_solutions_found;
    },
  },
  watch: {
    $route() {
      this.getBuildhistoryList();
    },
  },
  created() {
    if (this.$route.meta.history) {
      this.$emit('top-change');
    }
    this.moduleName = this.curModuleId;
    this.getBuildhistoryList();
  },
  methods: {
    /** 模块切换 */
    handleModuleChange() {
      this.getBuildhistoryList();
    },

    /** 获取构建历史列表 */
    async getBuildhistoryList(page = 1) {
      const curPage = page || this.pagination.current;
      this.isPageLoading = true;
      try {
        const res = await this.$store.dispatch('imageManage/getBuildhistoryList', {
          appCode: this.appCode,
          moduleName: this.moduleName,
          pageParams: {
            limit: this.pagination.limit,
            offset: this.pagination.limit * (curPage - 1),
          },
        });
        res.results.forEach((log) => {
          log.duration = this.calculateTimeDifference(log.start_at, log.completed_at);
          log.durationText = this.calculateAndFormatTimeDifference(log.start_at, log.completed_at);
        });

        this.historyList = res.results;
        this.oldHistoryList = cloneDeep(res.results);
        this.pagination.count = res.count;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isPageLoading = false;
        this.$emit('hide-loading');
      }
    },

    /** 页码改变 */
    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getBuildhistoryList(this.pagination.current);
    },

    /** 页容量改变 */
    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.getBuildhistoryList(newPage);
    },

    /** 历史详情 */
    handleHistoryDetail(row) {
      // 当前模块
      row.moduleName = this.moduleName;
      this.$refs.logSidesliderRef?.handleShowBuildLog(row);
    },

    /**  计算时间差 */
    calculateTimeDifference(startDateTime, endDateTime) {
      const startDate = dayjs(startDateTime);
      const endDate = dayjs(endDateTime);

      return endDate.diff(startDate, 'second'); // 时间差以秒为单位
    },

    /** 获取时间差字符串 */
    calculateAndFormatTimeDifference(startDateTime, endDateTime) {
      if (!startDateTime || !endDateTime) {
        return '--';
      }
      const duration = this.calculateTimeDifference(startDateTime, endDateTime);

      const days = Math.floor(duration / (24 * 3600));
      const hours = Math.floor((duration % (24 * 3600)) / 3600);
      const minutes = Math.floor((duration % 3600) / 60);
      const seconds = duration % 60;

      let result = '';

      if (days > 0) {
        result += `${days}${this.$t('天')} `;
      }
      if (hours > 0 || days > 0) {
        result += `${hours}${this.$t('时')} `;
      }
      if (minutes > 0 || hours > 0 || days > 0) {
        result += `${minutes}${this.$t('分')} `;
      }
      result += `${seconds}${this.$t('秒')}`;

      return result;
    },
  },
};
</script>

<style lang="scss" scoped>
.clund-build-history {
  padding: 24px;

  .dot {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    margin-right: 8px;

    &.failed {
      background: #ea3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.pending {
      background: #ff9c01;
      border: 3px solid #ffefd6;
    }
    &.successful {
      background: #3fc06d;
      border: 3px solid #daefe4;
    }
  }

  .build-detail {
      display: flex;
      height: 100%;

      /deep/ .paas-deploy-log-wrapper {
          height: 100%;
      }
  }
}
.module-select-custom {
  /deep/ i.paasng-project {
    color: #a3c5fd;
  }
}
</style>
