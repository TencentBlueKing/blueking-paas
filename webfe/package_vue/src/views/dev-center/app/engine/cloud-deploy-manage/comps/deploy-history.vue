<template>
  <div class="deploy-history">
    <paas-content-loader
      :is-loading="isLoading"
      :is-transition="false"
      placeholder="event-list-loading"
      :class="{ 'deploy-history-loader': isLoading }"
    >
      <section class="search-wrapper">
        <bk-form form-type="inline">
          <bk-form-item
            :label="$t('模块')"
            style="vertical-align: top"
          >
            <bk-select
              v-model="moduleValue"
              style="width: 150px"
              :clearable="false"
              placeholder=" "
              @change="getDeployHistory(1)"
            >
              <bk-option
                v-for="option in moduleList"
                :key="option.key"
                :id="option.key"
                :name="option.name"
              ></bk-option>
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('操作人')"
            class="ml20"
            style="vertical-align: top"
          >
            <user
              v-model="personnelSelectorList"
              style="width: 350px"
              :placeholder="$t('请输入')"
              :multiple="false"
              @change="getDeployHistory(1)"
            />
          </bk-form-item>
        </bk-form>
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
        @row-click="handleShowLogSideslider"
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
          width="150"
          :label="$t('模块')"
          prop="moduleName"
          column-key="moduleName"
          :render-header="$renderHeader"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          :label="$t('部署环境')"
          prop="environment"
          column-key="env"
          :filters="sourceFilters"
          :filter-multiple="false"
          :render-header="$renderHeader"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span v-if="row.environment === 'stag'">{{ $t('预发布环境') }}</span>
            <span v-else>{{ $t('生产环境') }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          width="150"
          :label="$t('分支')"
          :show-overflow-tooltip="false"
        >
          <template slot-scope="{ row }">
            <bk-popover class="branch-popover-cls">
              <span class="branch-name">{{ row.name }}</span>
              <div slot="content">
                <p class="flex">
                  <span class="label">{{ $t('部署分支：') }}</span>
                  <span class="value">{{ row.name }}</span>
                </p>
                <p class="flex">
                  <span class="label">{{ $t('仓库地址：') }}</span>
                  <span class="value">{{ row.url }}</span>
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
        <bk-table-column
          :label="$t('结果')"
          min-width="100"
        >
          <template slot-scope="{ row }">
            <div
              class="flex-row align-items-center"
              v-if="row.status !== 'pending'"
            >
              <span :class="['dot', row.status]" />
              {{ $t(deployStatus[row.status]) }}
            </div>
            <template v-else>
              <div
                class="flex-row align-items-center"
                v-if="row.status === 'pending' && row.operation_type === 'online'"
              >
                <span class="dot warning" />
                {{ $t('部署中') }}
              </div>
              <div
                class="flex-row align-items-center"
                v-if="row.status === 'pending' && row.operation_type === 'offline'"
              >
                <span class="dot warning" />
                {{ $t('下架中') }}
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
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <bk-user-display-name
              :user-id="row.operator.username"
              v-if="isMultiTenantDisplayMode"
            ></bk-user-display-name>
            <span v-else>{{ row.operator.username }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          width="180"
          :label="$t('操作时间')"
          prop="created"
          show-overflow-tooltip
        />
        <bk-table-column
          :width="localLanguage === 'en' ? 200 : 180"
          :label="$t('操作')"
        >
          <template slot-scope="{ row }">
            <bk-button
              text
              class="mr15"
              @click.stop="handleShowLogSideslider(row)"
            >
              {{ $t('部署日志') }}
            </bk-button>
            <bk-button
              text
              :disabled="row.operation_type === 'offline'"
              @click.stop="handleShowYamlSideslider(row)"
            >
              {{ $t('查看 YAML') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <!-- 部署日志 -->
    <deploy-log-sideslider
      ref="logSidesliderRef"
      :app-code="appCode"
      :module-id="moduleValue"
    />

    <!-- 查看YAML -->
    <bk-sideslider
      :is-show.sync="yamlSidesliderConfig.isShow"
      :width="900"
      :quick-close="true"
    >
      <div slot="header">{{ $t('查看 YAML') }}</div>
      <div
        class="yaml-wrapper"
        slot="content"
      >
        <resource-editor
          ref="editorRef"
          key="editor"
          v-model="yamlData"
          :readonly="true"
          v-bkloading="{ isLoading: isYamlLoading, opacity: 1, color: '#1a1a1a' }"
          :height="height"
          :width="900"
          @error="handleEditorErr"
        />
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import user from '@/components/user';
import deployLogSideslider from '@/components/deploy/deploy-log-sideslider.vue';
import ResourceEditor from '@/components/deploy-resource-editor';
import appBaseMixin from '@/mixins/app-base-mixin';
import { DEPLOY_STATUS } from '@/common/constants';
import { clearFilter } from '@/common/utils';
import { cloneDeep } from 'lodash';
import { mapState, mapGetters } from 'vuex';

export default {
  components: {
    user,
    deployLogSideslider,
    ResourceEditor,
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
      moduleValue: '',
      filterEnv: [],
      yamlSidesliderConfig: {
        isShow: false,
      },
      height: window.innerHeight - 60,
      yamlData: {},
      isYamlLoading: false,
      moduleList: [],
    };
  },

  computed: {
    ...mapState(['localLanguage']),
    ...mapGetters(['isMultiTenantDisplayMode']),
    sourceFilters() {
      return [
        { text: this.$t('生产环境'), value: 'prod' },
        { text: this.$t('预发布环境'), value: 'stag' },
      ];
    },
    logId() {
      return this.$route.query.logId;
    },
  },

  watch: {
    filterEnv() {
      this.getDeployHistory();
    },
  },

  created() {
    this.init();
  },

  methods: {
    init() {
      this.moduleValue = '';
      this.getDeployHistory();
      this.moduleList = this.curAppModuleList.map((item) => ({ key: item.name, name: item.name }));
      // 在列表头新增一项
      this.moduleList.unshift({ key: '', name: `${this.$t('全部')}` });
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
          operation.moduleName = operation.module_name;

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
        this.isLoading = false;
        this.$nextTick(() => {
          if (!this.logId) return;
          // query参数获取默认打开项
          const curLog = this.historyList.find((v) => v.deployment?.id === this.logId);
          curLog && this.handleShowLogSideslider(curLog);
        });
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

    handleFilterChange(filter) {
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

      const start = new Date(startTime).getTime() / 1000;
      const end = new Date(endTime).getTime() / 1000;
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

    /**
     * 查看侧栏
     */
    handleShowYamlSideslider(row) {
      this.yamlSidesliderConfig.isShow = true;
      this.getDeployVersionDetails(row);
    },

    // 获取某个部署版本的详细信息
    async getDeployVersionDetails(data) {
      this.isYamlLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/getDeployVersionDetails', {
          appCode: this.appCode,
          moduleId: this.moduleValue || data.moduleName,
          environment: data.environment,
          revisionId: data.deployment.bkapp_revision_id,
        });
        this.yamlData = res.json_value || {};
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isYamlLoading = false;
      }
    },

    handleEditorErr(err) {
      // 捕获编辑器错误提示
      this.editorErr.type = 'content'; // 编辑内容错误
      this.editorErr.message = err;
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

  .branch-popover-cls {
    max-width: 100%;
    /deep/ .bk-tooltip-ref {
      max-width: 100%;
      .branch-name {
        display: inline-block;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
      }
    }
  }

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
      background: #ea3636;
      border: 3px solid #fce0e0;
    }
    &.interrupted,
    &.warning {
      background: #ff9c01;
      border: 3px solid #ffefd6;
    }
    &.successful {
      background: #3fc06d;
      border: 3px solid #daefe4;
    }
  }
}
.yaml-wrapper {
  /deep/ .resource-editor {
    border-radius: 0;
  }
}
</style>
