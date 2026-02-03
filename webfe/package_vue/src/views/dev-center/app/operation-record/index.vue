<template>
  <div class="operation-record-container">
    <section class="ps-top-bar">
      <h2>
        {{ $t('操作记录') }}
      </h2>
    </section>
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="deploy-inner-history-loading"
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
            @pick-success="getRecords(1)"
          ></bk-date-picker>
          <div class="right-filter">
            <span class="mr15">{{ $t('操作人') }}</span>
            <user
              v-model="operatorList"
              style="width: 350px"
              :placeholder="$t('请输入')"
              :multiple="false"
              @change="getRecords(1)"
            />
          </div>
        </div>
        <bk-table
          :data="records"
          :pagination="pagination"
          ref="recordTable"
          v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
          @page-change="handlePageChange"
          @page-limit-change="handlePageLimitChange"
          @filter-change="handleFilterChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="getRecords"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            :label="$t('操作对象')"
            prop="target"
            column-key="target"
            show-overflow-tooltip
            :filters="targetFilters"
            :filter-multiple="false"
            :render-header="$renderHeader"
          >
            <span slot-scope="{ row }">
              {{ (isEnglish ? row.target : APP_OPERATION_TARGET[row.target]) || '--' }}
            </span>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作类型')"
            prop="operation"
            column-key="operation"
            show-overflow-tooltip
            :filters="operationFilters"
            :filter-multiple="false"
            :render-header="$renderHeader"
          >
            <span slot-scope="{ row }">
              {{ (isEnglish ? row.operation : APP_OPERATION[row.operation]) || '--' }}
            </span>
          </bk-table-column>
          <bk-table-column
            :label="$t('对象属性')"
            prop="attribute"
            show-overflow-tooltip
            :render-header="$renderHeader"
          >
            <span slot-scope="{ row }">{{ row.attribute || '--' }}</span>
          </bk-table-column>
          <bk-table-column
            :label="$t('模块')"
            prop="module_name"
            column-key="module_name"
            show-overflow-tooltip
            :filters="moduleFilters"
            :filter-multiple="false"
          >
            <span slot-scope="{ row }">{{ row.module_name || '--' }}</span>
          </bk-table-column>
          <bk-table-column
            :label="$t('环境')"
            prop="environment"
            column-key="environment"
            show-overflow-tooltip
            :filters="envFilters"
            :filter-multiple="false"
          >
            <span slot-scope="{ row }">{{ envFilters.find((v) => v.value === row.environment)?.text || '--' }}</span>
          </bk-table-column>
          <bk-table-column
            :label="$t('状态')"
            prop="result_code"
            column-key="result_code"
            show-overflow-tooltip
            :filters="resultCodeFilters"
            :filter-multiple="false"
          >
            <span slot-scope="{ row }">
              {{ $t(APP_RESULT_CODE[row.result_code]) || '--' }}
            </span>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作人')"
            show-overflow-tooltip
            prop="operator"
          >
            <template slot-scope="{ row }">
              <bk-user-display-name
                :user-id="row.operator"
                v-if="isMultiTenantDisplayMode"
              ></bk-user-display-name>
              <span v-else>{{ row.operator }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作时间')"
            prop="at"
            show-overflow-tooltip
            :render-header="$renderHeader"
          ></bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="120"
          >
            <template slot-scope="{ row }">
              <bk-button
                v-if="row.detail_type"
                style="margin-right: 12px"
                theme="primary"
                text
                @click="viewDetails(row)"
              >
                {{ $t('查看详情') }}
              </bk-button>
              <span v-else>-</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <!-- diff 详情 -->
    <bk-sideslider
      :is-show.sync="diffConfig.isShow"
      :width="960"
      :quick-close="true"
      ext-cls="diff-sideslider-cls"
    >
      <div
        slot="header"
        class="detail-header-wrapper"
      >
        {{ $t('操作详情') }}
        <span class="tips">
          {{ sidesliderTitleTips }}
        </span>
      </div>
      <diff
        slot="content"
        v-bkloading="{ isLoading: diffConfig.isLoading, zIndex: 10, color: '#313238' }"
        :old-code="diffConfig.beforeYaml"
        :new-code="diffConfig.afterYaml"
      />
    </bk-sideslider>
    <!-- 申请记录详情 -->
    <bk-sideslider
      :is-show.sync="detailConfig.isShow"
      :width="640"
      :quick-close="true"
    >
      <div
        slot="header"
        class="detail-header-wrapper"
      >
        {{ $t('操作详情') }}
        <span class="tips">
          {{ sidesliderTitleTips }}
        </span>
      </div>
      <div
        class="m20"
        v-bkloading="{ isLoading: detailLoading, zIndex: 10 }"
        slot="content"
      >
        <cloud-api-detail
          v-if="!detailLoading"
          type="gateway"
          :cur-record="curCloudApiRecord"
        />
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import { APP_OPERATION_TARGET, APP_OPERATION, APP_RESULT_CODE } from '@/common/constants';
import { createTimeShortcuts } from '@/common/date';
import user from '@/components/user';
import diff from './comps/diff.vue';
import cloudApiDetail from './comps/cloud-api-detail.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import yamljs from 'js-yaml';
import { mapGetters } from 'vuex';

export default {
  name: 'OperationRecord',
  components: {
    user,
    diff,
    cloudApiDetail,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      isTableLoading: false,
      operatorList: [],
      records: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [5, 10, 20, 50],
      },
      diffConfig: {
        isShow: false,
        beforeYaml: '',
        afterYaml: '',
        isLoading: false,
      },
      detailConfig: {
        isShow: false,
      },
      detailLoading: false,
      curCloudApiRecord: {},
      APP_OPERATION_TARGET,
      APP_OPERATION,
      APP_RESULT_CODE,
      envFilters: [
        { value: 'stag', text: this.$t('预发布环境') },
        { value: 'prod', text: this.$t('生产环境') },
      ],
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      filterParams: {},
      dateParams: {},
      sidesliderTitleTips: '',
      datePickerOption: {
        // 小于今天的日期不能选
        disabledDate(date) {
          return date && date.valueOf() > Date.now() - 86400;
        },
      },
    };
  },
  computed: {
    ...mapGetters(['isMultiTenantDisplayMode']),
    appCode() {
      return this.$route.params.id;
    },
    moduleFilters() {
      return this.curAppModuleList.map((m) => ({ value: m.name, text: m.name }));
    },
    dateShortcuts() {
      return createTimeShortcuts(this.$i18n);
    },
    isEnglish() {
      return this.$store.state.localLanguage === 'en';
    },
    targetFilters() {
      return this.formatTableFilters(APP_OPERATION_TARGET);
    },
    operationFilters() {
      return this.formatTableFilters(APP_OPERATION);
    },
    resultCodeFilters() {
      return this.formatTableFilters(APP_RESULT_CODE, 'translation');
    },
  },
  watch: {
    $route() {
      this.isLoading = true;
      this.pagination.current = 1;
      this.getRecords();
    },
  },
  created() {
    this.getRecords();
  },
  methods: {
    formatTableFilters(obj, type = null) {
      return Object.entries(obj).map(([key, value]) => {
        const text = this.isEnglish && !type ? key : type ? this.$t(value) : value;
        return { value: key, text };
      });
    },
    // 获取操作记录
    async getRecords(page = 1) {
      this.isTableLoading = true;
      try {
        const curPage = page || this.pagination.current;
        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
          ...this.dateParams,
          ...this.filterParams,
        };
        // 操作人
        if (this.operatorList.length) {
          params.operator = this.operatorList.join();
        }
        const res = await this.$store.dispatch('baseInfo/getRecords', {
          appCode: this.appCode,
          params,
        });
        this.records = res.results;
        this.pagination.count = res.count;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
        this.isLoading = false;
      }
    },
    handlePageChange(page) {
      this.pagination.current = page;
      this.getRecords(page);
    },
    handlePageLimitChange(newLimit) {
      this.pagination.limit = newLimit;
      this.getRecords(1);
    },
    // 查看详情
    viewDetails(row) {
      this.sidesliderTitleTips = row.operate;
      if (['bkapp_revision', 'raw_data'].includes(row.detail_type)) {
        // diff raw_data-直接使用接口数据，bkapp_revision-拿取id通过接口获取）
        this.handleOpenDiff(row);
      } else {
        // 云api-申请记录-详情（cloud_api_record）
        this.detailConfig.isShow = true;
        this.getApiRecord(row);
      }
    },
    setDiffData(before, after) {
      this.diffConfig.beforeYaml = yamljs.dump(before, { indent: 2 });
      this.diffConfig.afterYaml = yamljs.dump(after, { indent: 2 });
    },
    handleOpenDiff(row) {
      this.diffConfig.isLoading = true;
      if (row.detail_type === 'raw_data') {
        // raw_data 类型直接使用接口返回数据
        this.setDiffData(row.data_before?.data ?? '', row.data_after?.data ?? '');
        this.diffConfig.isLoading = false;
      } else {
        // 通过id查询
        this.getDiffData(row);
      }
      this.diffConfig.isShow = true;
    },
    // bkapp_revision 类型通过 id 获取数据
    getDiffData(row) {
      const { module_name, environment, data_before, data_after } = row;

      const getDataPromise = (data) => {
        return data ? this.getDeployVersionDetails(module_name, environment, data) : Promise.resolve(null);
      };

      const promises = [getDataPromise(data_before?.data), getDataPromise(data_after?.data)];

      Promise.all(promises)
        .then(([before, after]) => {
          const beforeJsonValue = before?.json_value || '';
          const afterJsonValue = after?.json_value || '';
          this.setDiffData(beforeJsonValue, afterJsonValue);
        })
        .catch((e) => {
          this.catchErrorHandler(e);
        })
        .finally(() => {
          this.diffConfig.isLoading = false;
        });
    },
    // 获取云api申请详情
    async getApiRecord(row) {
      const dispatchMethod = row.detail_type === 'esb_api_record' ? 'getSysApplyRecordDetail' : 'getApplyRecordDetail';
      this.detailLoading = true;
      try {
        const res = await this.$store.dispatch(`cloudApi/${dispatchMethod}`, {
          appCode: this.appCode,
          recordId: row.data_after.data,
        });
        this.curCloudApiRecord = Object.assign(this.curCloudApiRecord, res.data);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.detailLoading = false;
      }
    },
    // 获取某个部署版本的详细信息
    async getDeployVersionDetails(module, env, id) {
      return this.$store.dispatch('deploy/getDeployVersionDetails', {
        appCode: this.appCode,
        moduleId: module,
        environment: env,
        revisionId: id,
      });
    },
    handleEditorErr(err) {
      // 捕获编辑器错误提示
      this.editorErr.type = 'content'; // 编辑内容错误
      this.editorErr.message = err;
    },
    // 时间筛选
    handleDateChange(date) {
      // 清空
      if (date?.every((t) => t === '')) {
        this.dateParams = {};
        this.getRecords(1);
        return;
      }
      this.dateParams = {
        start_time: date[0],
        end_time: date[1],
      };
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
      this.getRecords(1);
    },
    // 清空当前表格筛选项
    clearFilterKey() {
      this.dateParams = {};
      this.operatorList = [];
      this.$refs.recordTable?.clearFilter();
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
.operation-record-container {
  .record-main {
    padding: 24px;
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
  .tools {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    .right-filter {
      display: flex;
      align-items: center;
      margin-left: 16px;
    }
  }
  .diff-sideslider-cls {
    display: flex;
    flex-direction: column;
    height: 100%;
    /deep/ .bk-sideslider-wrapper {
      background: #1d1d1d;
      .bk-sideslider-content {
        height: calc(100vh - 52px) !important;
        max-height: calc(100vh - 52px) !important;
        overflow-x: hidden;
        overflow: hidden;
      }
    }
  }
  .detail-header-wrapper .tips {
    color: #63656e;
    font-size: 14px;
  }
}
</style>
