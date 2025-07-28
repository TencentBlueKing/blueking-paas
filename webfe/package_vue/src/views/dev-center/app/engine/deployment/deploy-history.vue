<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-inner-history-loading"
    :offset-top="0"
    :offset-left="-8"
    class="deploy-history m20"
  >
    <bk-form form-type="inline">
      <bk-form-item
        :label="$t('环境')"
        style="vertical-align: top;"
      >
        <bk-select
          v-model="choosedEnv"
          style="width: 150px;"
          :clearable="false"
          @change="getDeployHistory(1)"
        >
          <bk-option
            v-for="(option, index) in envList"
            :id="option.id"
            :key="index"
            :name="option.text"
          />
        </bk-select>
      </bk-form-item>
      <bk-form-item
        :label="$t('操作人')"
        style="vertical-align: top;"
      >
        <user
          v-model="personnelSelectorList"
          style="width: 350px;"
          :placeholder="$t('请选择')"
          :multiple="false"
          @change="getDeployHistory(1)"
        />
      </bk-form-item>
    </bk-form>
    <bk-table
      v-bkloading="{ isLoading: isPageLoading }"
      class="mt15 ps-history-list"
      :data="historyList"
      :outer-border="false"
      :size="'small'"
      :pagination="pagination"
      @row-click="handleShowLog"
      @page-limit-change="handlePageLimitChange"
      @page-change="handlePageChange"
    >
      <div slot="empty">
        <table-empty
          :keyword="tableEmptyConf.keyword"
          :abnormal="tableEmptyConf.isAbnormal"
          @reacquire="getDeployHistory"
          @clear-filter="clearFilter"
        />
      </div>
      <bk-table-column
        :label="$t('部署环境')"
        prop="name"
        :render-header="$renderHeader"
      >
        <template slot-scope="props">
          <span v-if="props.row.environment === 'stag'"> {{ $t('预发布环境') }} </span>
          <span v-else> {{ $t('生产环境') }} </span>
        </template>
      </bk-table-column>
      <bk-table-column
        width="150"
        :label="$t('分支')"
        prop="name"
        :show-overflow-tooltip="false"
      >
        <template slot-scope="props">
          <bk-popover>
            <span class="branch-name">{{ props.row.name }}</span>
            <div slot="content">
              <p class="flex">
                <span class="label"> {{ $t('部署分支：') }} </span><span class="value">{{ props.row.name }}</span>
              </p>
              <p class="flex">
                <span class="label"> {{ $t('仓库地址：') }} </span><span class="value">{{ props.row.url }}</span>
              </p>
            </div>
          </bk-popover>
        </template>
      </bk-table-column>
      <!-- <bk-table-column label="部署目录">
                <template slot-scope="{ row }">
                    {{ row.source_dir || '--' }}
                </template>
            </bk-table-column> -->
      <bk-table-column
        :label="$t('版本')"
        prop="revision"
        :show-overflow-tooltip="true"
      />
      <bk-table-column
        :label="$t('操作人')"
        prop="operator.username"
        :render-header="$renderHeader"
      />
      <bk-table-column
        :label="$t('类型')"
        prop="operation_act"
        :render-header="$renderHeader"
      />
      <bk-table-column
        :label="$t('耗时')"
        :render-header="$renderHeader"
      >
        <template slot-scope="{ row }">
          {{ computedDeployTime(row) }}
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('结果')">
        <template slot-scope="props">
          <div v-if="props.row.status === 'successful'">
            <span class="dot success" /> {{ $t('成功') }}
          </div>
          <div v-if="props.row.status === 'failed'">
            <span class="dot danger" /> {{ $t('失败') }}
          </div>
          <div v-if="props.row.status === 'interrupted'">
            <span class="dot warning" /> {{ $t('中断') }}
          </div>
          <div v-if="props.row.status === 'pending' && props.row.operation_type === 'online'">
            <span class="dot warning" /> {{ $t('部署中') }}
          </div>
          <div v-if="props.row.status === 'pending' && props.row.operation_type === 'offline'">
            <span class="dot warning" /> {{ $t('下架中') }}
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        width="180"
        :label="$t('操作时间')"
        prop="created"
      />
    </bk-table>

    <bk-sideslider
      :width="920"
      :is-show.sync="historySideslider.isShow"
      :quick-close="true"
      @hidden="errorTips = {}"
    >
      <div
        slot="header"
        class="deploy-header"
      >
        <div style="float: left;">
          {{ historySideslider.title }}
        </div>
        <div style="float: right;">
          <bk-button class="mr10" size="small" @click="handleExportLog">{{ $t('下载日志') }}</bk-button>
        </div>
      </div>
      <div
        slot="content"
        v-bkloading="{ isLoading: isLogLoading || isTimelineLoading, opacity: 1 }"
        class="deploy-detail"
      >
        <template v-if="!(isLogLoading || isTimelineLoading)">
          <deploy-timeline
            v-if="timeLineList.length"
            :list="timeLineList"
            :disabled="true"
            class="mt20 ml15 mr15"
            style="min-width: 250px;"
          />
          <div class="paas-log-box">
            <div
              v-if="isMatchedSolutionsFound"
              class="wrapper danger"
            >
              <div class="fl">
                <span class="paasng-icon paasng-info-circle-shape" />
              </div>
              <section style="position: relative; margin-left: 50px;">
                <p class="deploy-pending-text">
                  {{ $t('部署失败') }}
                </p>
                <p class="deploy-text-wrapper">
                  <span class="reason mr5">{{ errorTips.possible_reason }}</span>
                  <span
                    v-for="(help, index) in errorTips.helpers"
                    :key="index"
                  >
                    <a
                      :href="help.link"
                      target="_blank"
                      class="mr10"
                    >
                      {{ help.text }}
                    </a>
                  </span>
                </p>
              </section>
            </div>
            <bk-alert
              v-else
              style="margin: -20px -20px 10px -20px; border-radius: 0;"
              type="warning"
              :title="$t('仅展示准备阶段、构建阶段日志')"
            />
            <pre v-dompurify-html="curDeployLog" />
          </div>
        </template>
      </div>
    </bk-sideslider>
  </paas-content-loader>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import deployTimeline from './comps/deploy-timeline';
import user from '@/components/user';

export default {
  components: {
    user,
    deployTimeline,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      choosedEnv: 'all',
      historyList: [],
      curDeployLog: '',
      logDetail: '',
      isLoading: true,
      isPageLoading: true,
      isLogLoading: false,
      isTimelineLoading: false,
      ansiUp: null,
      personnelSelectorList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      envList: [
        {
          id: 'all',
          text: this.$t('全部'),
        },
        {
          id: 'prod',
          text: this.$t('生产环境'),
        },
        {
          id: 'stag',
          text: this.$t('预发布环境'),
        },
      ],
      timeLineList: [],
      historySideslider: {
        title: '',
        isShow: false,
      },
      errorTips: {},
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      logExportUrl: '',
    };
  },
  computed: {
    isMatchedSolutionsFound() {
      return this.errorTips.matched_solutions_found;
    },
  },
  watch: {
    $route() {
      this.isLoading = true;
      this.getDeployHistory();
    },
  },
  created() {
    this.isLoading = true;
    this.getDeployHistory();
  },
  mounted() {
    const AU = require('ansi_up');
    // eslint-disable-next-line
    this.ansiUp = new AU.default
  },
  methods: {
    updateValue(curVal) {
      curVal ? this.personnelSelectorList = curVal : this.personnelSelectorList = '';
    },

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

    getDisplayTime(payload) {
      let theTime = payload;
      if (theTime < 1) {
        return `<script 1${this.$t('秒')}`;
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
     * 获取部署记录
     */
    async getDeployHistory(page = 1) {
      this.isPageLoading = true;
      const curPage = page || this.pagination.current;
      const pageParams = {
        limit: this.pagination.limit,
        offset: this.pagination.limit * (curPage - 1),
      };
      if (this.choosedEnv !== 'all') {
        pageParams.environment = this.choosedEnv;
      }

      if (this.personnelSelectorList.length) {
        pageParams.operator = this.personnelSelectorList[0];
      }

      try {
        const res = await this.$store.dispatch('deploy/getDeployHistory', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          pageParams,
        });

        const reg = RegExp('^[a-z0-9]{40}$');
        res.results.forEach((operation) => {
          if (operation.operation_type === 'offline') {
            operation.logDetail = operation.offline_operation.log;
            operation.operation_act = this.$t('下架');
            operation.environment = operation.offline_operation.environment;

            operation.name = operation.offline_operation.repo.name;
            operation.revision = operation.offline_operation.repo.revision;
            operation.url = operation.offline_operation.repo.url;

            if (reg.test(operation.offline_operation.repo.revision)) {
              operation.revision = operation.offline_operation.repo.revision.substring(0, 8);
            }
          } else {
            operation.deployment_id = operation.deployment.deployment_id;
            operation.environment = operation.deployment.environment;
            operation.logDetail = '';
            operation.operation_act = this.$t('部署');

            operation.name = operation.deployment.repo.name;
            operation.revision = operation.deployment.repo.revision;
            operation.url = operation.deployment.repo.url;

            if (reg.test(operation.deployment.repo.revision)) {
              operation.revision = operation.deployment.repo.revision.substring(0, 8);
            }
          }
        });
        this.historyList = res.results;
        this.pagination.count = res.count;

        // 如果有deployid，默认显示
        if (this.$route.query.deployId) {
          const recordItem = this.historyList.find(item => item.deployment_id === this.$route.query.deployId);
          if (recordItem) {
            this.handleShowLog(recordItem);
          }
        }
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
        this.isPageLoading = false;
      }
    },

    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getDeployHistory(this.pagination.current);
    },

    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.getDeployHistory(newPage);
    },

    handleShowLog(row) {
      this.timeLineList = [];
      this.curDeployLog = '';
      if (this.isTimelineLoading || this.isLogLoading) {
        return false;
      }

      const operator = row.operator.username;
      const time = row.created;
      if (row.operation_type === 'offline') {
        const title = `${row.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境')}${this.$t('下架日志')} (${operator}${this.$t('于')}${time}${this.$t('下架')}`;
        this.historySideslider.title = title;
        this.curDeployLog = row.logDetail;
      } else {
        const branch = row.name;
        this.historySideslider.title = `${row.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境')}${this.$t('部署日志')} (${operator}${this.$t('于')}${time}${this.$t('部署')}${branch}${this.$t('分支')})`;
        this.getDeployTimeline(row);
        this.getDeployLog(row);
      }
      this.historySideslider.isShow = true;
    },

    async getDeployTimeline(params) {
      if (this.isTimelineLoading) {
        return false;
      }

      this.isTimelineLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/getDeployTimeline', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: params.environment,
          deployId: params.deployment_id,
        });
        const timeLineList = [];
        res.forEach((stageItem) => {
          timeLineList.push({
            tag: stageItem.display_name,
            content: this.computedDeployTimelineTime(stageItem.start_time, stageItem.complete_time),
            status: stageItem.status || 'default',
            stage: stageItem.type,
          });

          stageItem.steps.forEach((stepItem) => {
            timeLineList.push({
              tag: stepItem.display_name,
              content: this.computedDeployTimelineTime(stepItem.start_time, stepItem.complete_time),
              status: stepItem.status || 'default',
              parentStage: stageItem.type,
            });
          });
        });
        this.timeLineList = timeLineList;
      } catch (e) {
        this.timeLineList = [];
      } finally {
        this.isTimelineLoading = false;
      }
    },

    async getDeployLog(params) {
      if (this.isLogLoading) {
        return false;
      }
      this.isLogLoading = true;
      this.logExportUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${params.module_name || params.moduleName}/deployments/${params.deployment_id}/logs/export`;
      try {
        const res = await this.$store.dispatch('deploy/getDeployLog', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: params.environment,
          deployId: params.deployment_id,
        });
        this.curDeployLog = this.ansiUp ? this.ansiUp.ansi_to_html(res.logs) : res.logs;
        this.errorTips = Object.assign({}, res.error_tips);
      } catch (e) {
        this.curDeployLog = '';
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLogLoading = false;
      }
    },

    clearFilter() {
      this.choosedEnv = 'all';
      this.personnelSelectorList = [];
      this.getDeployHistory();
    },

    updateTableEmptyConfig() {
      if (this.personnelSelectorList.length || this.choosedEnv !== 'all') {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },
    handleExportLog() {
      window.open(this.logExportUrl, '_blank')
    },
  },
};
</script>

<style lang="scss" scoped>
    .deploy-history {
        min-height: 500px !important;
    }
    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;

        &.success {
            background: #a0f5e3;
            border: 1px solid #18c0a1;
        }

        &.danger {
            background: #fd9c9c;
            border: 1px solid #ea3636;
        }

        &.warning {
            background: #FFE8C3;
            border: 1px solid #FF9C01;
        }
    }

    .wrapper {
        margin: -20px -20px 10px;
        height: 64px;
        background: #F5F6FA;
        line-height: 64px;
        padding: 0 20px;

        &::after {
            display: block;
            clear: both;
            content: "";
            font-size: 0;
            height: 0;
            visibility: hidden;
        }

        &.default-box {
            padding: 11px 12px 11px 20px;
            height: auto;
            line-height: 16px;
            .span {
                height: 16px;
            }
        }

        &.not-deploy {
            height: 42px;
            line-height: 42px;
        }

        &.primary {
            background: #E1ECFF;
            color: #979BA5;
        }

        &.warning {
            background: #FFF4E2;
            border-color: #FFDFAC;

            .paasng-icon {
                color: #fe9f07;
            }
        }

        &.danger {
            background: #FFECEC;
            color: #979BA5;

            .paasng-icon {
                color: #eb3635;
                position: relative;
                top: 4px;
                font-size: 32px;
            }
        }

        &.success {
            background: #E7FCFA;
            color: #979BA5;

            .paasng-icon {
                position: relative;
                top: 4px;
                color: #3fc06d;
                font-size: 32px;
            }
        }
        .deploy-pending-text {
            position: relative;
            top: 5px;
            font-size: 14px;
            color: #313238;
            font-weight: 500;
            line-height: 32px;
        }
        .deploy-text-wrapper {
            position: relative;
            top: -5px;
            line-height: 32px;
            font-size: 12px;
            .branch-text,
            .version-text,
            .time-text {
                font-size: 12px;
                color: #63656e;
                opacity: .9;
            }
            .branch-text,
            .version-text {
                margin-right: 30px;
            }
        }
    }

    .deploy-detail {
        display: flex;
        height: 100%;

        /deep/ .paas-deploy-log-wrapper {
            height: 100%;
        }
    }

    .flex {
        display: flex;
        line-height: 16px;
        margin-bottom: 3px;

        .label {
            display: inline-block;
            width: 60px;
        }

        .value {
            text-align: left;
            display: inline-block;
            flex: 1;
        }
    }

    .branch-name {
        width: 130px;
        display: block;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
