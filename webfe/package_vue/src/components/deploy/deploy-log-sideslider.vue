<template>
  <bk-sideslider
    :width="920"
    :is-show.sync="historySideslider.isShow"
    :quick-close="true"
    ext-cls="deploy-history-sideslider"
    @hidden="handleSidesliderHidden"
  >
    <div
      slot="header"
      class="deploy-header"
    >
      <div
        class="text-ellipsis"
        v-bk-overflow-tips
      >
        <template v-if="isMultiTenantDisplayMode">
          <span>{{ historySideslider.titlePrefix }}</span>
          <UserDisplay :value="historySideslider.operator" />
          <span>{{ historySideslider.titleSuffix }}</span>
        </template>
        <span v-else>{{ historySideslider.title }}</span>
      </div>
      <bk-button
        class="flex-shrink-0"
        size="small"
        @click="handleExportLog"
      >
        {{ $t('下载日志') }}
      </bk-button>
    </div>
    <div
      slot="content"
      v-bkloading="{ isLoading: isLogLoading || isTimelineLoading || isDebugStatusLoading, opacity: 1 }"
      class="deploy-detail"
    >
      <template v-if="!(isLogLoading || isTimelineLoading || isDebugStatusLoading)">
        <!-- 部署状态栏 -->
        <deploy-status-bar
          v-if="isDeployOperation"
          :app-code="appCode"
          :module-id="moduleId"
          :deployment="currentDeployment"
          :possible-reason="errorTips.possible_reason"
          :show-debug-action="isBuildDebugEnabled"
          :debug-disabled="!currentDeployment.isLatestDeployment"
          @redeploy="handleRedeploy"
          @back="handleBack"
        />
        <div class="deploy-log-content">
          <deploy-timeline
            v-if="timeLineList.length"
            :list="timeLineList"
            :disabled="true"
            style="min-width: 250px; margin-right: 24px"
          />
          <div class="paas-log-box">
            <deploy-status-bar
              v-if="!isDeployOperation && isMatchedSolutionsFound"
              :deployment="{ status: 'failed' }"
              :show-actions="false"
              class="legacy-error-summary"
            >
              <template slot="description">
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
              </template>
            </deploy-status-bar>
            <bk-alert
              v-else-if="!isMatchedSolutionsFound"
              class="log-stage-alert"
              type="warning"
              :title="$t('仅展示准备阶段、构建阶段日志')"
            />
            <log-display :content="curDeployLog" />
          </div>
        </div>
      </template>
    </div>
  </bk-sideslider>
</template>

<script>
import deployTimeline from './deploy-timeline';
import DeployStatusBar from './deploy-status-bar.vue';
import LogDisplay from '@/components/log-display';
import UserDisplay from '@/components/user/user-display.vue';
import { mapGetters } from 'vuex';

export default {
  components: {
    deployTimeline,
    DeployStatusBar,
    LogDisplay,
    UserDisplay,
  },
  props: {
    appCode: {
      type: [String, Number],
      default: '',
    },
    moduleId: {
      type: [String, Number],
      default: '',
    },
  },

  data() {
    return {
      isLogLoading: false,
      isTimelineLoading: false,
      isDebugStatusLoading: false,
      isBuildDebugEnabled: false,
      ansiUp: null,
      curDeployLog: '',
      timeLineList: [],
      historySideslider: {
        title: '',
        titlePrefix: '',
        titleSuffix: '',
        operator: '',
        isShow: false,
      },
      errorTips: {},
      logExportUrl: '',
      currentDeployment: {},
    };
  },

  computed: {
    isMatchedSolutionsFound() {
      return this.errorTips.matched_solutions_found;
    },
    isDeployOperation() {
      return this.currentDeployment.operation_type === 'online';
    },
    ...mapGetters(['isMultiTenantDisplayMode']),
  },

  mounted() {
    // eslint-disable-next-line no-undef
    const AU = require('ansi_up');
    this.ansiUp = new AU.default();
  },

  methods: {
    /**
     * 获取部署阶段详情
     */
    async getDeployTimeline(params) {
      if (this.isTimelineLoading) {
        return false;
      }

      this.isTimelineLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/getDeployTimeline', {
          appCode: this.appCode,
          moduleId: this.moduleId || params.moduleName,
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

    /**
     * 获取部署日志
     */
    async getDeployLog(params) {
      if (this.isLogLoading) {
        return false;
      }
      this.isLogLoading = true;
      const moduleId = params.moduleName || this.moduleId;
      this.logExportUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${moduleId}/deployments/${params.deployment_id}/logs/export`;
      try {
        const res = await this.$store.dispatch('deploy/getDeployLog', {
          appCode: this.appCode,
          moduleId: params.moduleName || this.moduleId,
          deployId: params.deployment_id,
        });
        if (res.logs && res.logs === '\n') {
          res.logs = this.$t('暂无日志');
        }
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

    /**
     * 获取构建调试开启状态
     */
    async getBuildDebugEnabled(params) {
      this.isDebugStatusLoading = true;
      this.isBuildDebugEnabled = false;
      try {
        const res = await this.$store.dispatch('deploy/getBuildDebugStatus', {
          appCode: this.appCode,
          moduleId: params.moduleName || this.moduleId,
          deployId: params.deployment_id,
        });
        this.isBuildDebugEnabled = !!res.enabled;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isDebugStatusLoading = false;
      }
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
     * 构建环境显示文本
     * @param {string} environment - 环境类型 (prod/stag)
     * @returns {string} 环境显示文本
     */
    getEnvironmentText(environment) {
      return environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境');
    },

    /**
     * 构建日志标题信息
     * @param {Object} params - 参数对象
     * @param {string} params.moduleName - 模块名称
     * @param {string} params.environment - 环境类型
     * @param {string} params.operator - 操作者
     * @param {string} params.time - 操作时间
     * @param {string} params.logType - 日志类型 ('deploy' | 'offline')
     * @returns {Object} 包含标题信息的对象
     */
    buildLogTitleInfo({ moduleName, environment, operator, time, logType }) {
      const envText = this.getEnvironmentText(environment);

      if (logType === 'offline') {
        return {
          title: `${moduleName} ${this.$t('模块')}${envText}${this.$t('下架日志')} (${operator}${this.$t(
            '于'
          )}${time}${this.$t('下架')})`,
          titlePrefix: `${moduleName} ${this.$t('模块')}${envText}${this.$t('下架日志')} (`,
          titleSuffix: `${this.$t('于')}${time}${this.$t('下架')})`,
          operator,
        };
      } else {
        return {
          title: `${moduleName} ${this.$t('模块')}${envText}${this.$t('部署日志')} ${operator}${this.$t(
            '于'
          )}${time}${this.$t('部署')}`,
          titlePrefix: `${moduleName} ${this.$t('模块')}${envText}${this.$t('部署日志')} `,
          titleSuffix: `${this.$t('于')}${time}${this.$t('部署')}`,
          operator,
        };
      }
    },

    /**
     * 设置侧边栏标题
     * @param {Object} titleInfo - 标题信息对象
     */
    setSidesliderTitle(titleInfo) {
      this.historySideslider.title = titleInfo.title;
      this.historySideslider.titlePrefix = titleInfo.titlePrefix;
      this.historySideslider.titleSuffix = titleInfo.titleSuffix;
      this.historySideslider.operator = titleInfo.operator;
    },

    handleRedeploy(deployment) {
      this.historySideslider.isShow = false;
      this.$emit('redeploy', deployment);
    },

    handleBack() {
      this.historySideslider.isShow = false;
    },

    handleSidesliderHidden() {
      this.errorTips = {};
      this.currentDeployment = {};
      this.isBuildDebugEnabled = false;
    },

    handleShowLog(row) {
      this.timeLineList = [];
      this.curDeployLog = '';
      this.isBuildDebugEnabled = false;
      if (this.isTimelineLoading || this.isLogLoading || this.isDebugStatusLoading) {
        return false;
      }
      this.currentDeployment = row;

      const { operator, created: time, moduleName, environment, operation_type: operationType } = row;

      // 构建标题信息
      const titleInfo = this.buildLogTitleInfo({
        moduleName,
        environment,
        operator: operator.username,
        time,
        logType: operationType,
      });

      this.setSidesliderTitle(titleInfo);

      if (operationType === 'offline') {
        this.curDeployLog = row.logDetail;
      } else {
        this.getBuildDebugEnabled(row);
        this.getDeployTimeline(row);
        this.getDeployLog(row);
      }
      this.historySideslider.isShow = true;
    },

    /** 构建详情 */
    handleShowBuildLog(row) {
      this.timeLineList = [];
      this.curDeployLog = '';
      this.isBuildDebugEnabled = false;
      this.currentDeployment = {};
      if (this.isTimelineLoading || this.isLogLoading || this.isDebugStatusLoading) {
        return false;
      }

      this.historySideslider.title = this.$t('构建详情');
      if (row.operation_type === 'offline') {
        this.curDeployLog = row.logDetail;
      } else {
        this.getDeployTimeline(row);
        this.getDeployLog(row);
      }
      this.historySideslider.isShow = true;
    },

    handleExportLog() {
      window.open(this.logExportUrl, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.deploy-history-sideslider :deep(.bk-sideslider-content) {
  overflow: unset;
}
.deploy-detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  padding: 20px 24px;

  /deep/ .paas-deploy-log-wrapper {
    height: 100%;
  }

  .deploy-log-content {
    display: flex;
    flex: 1;
    min-height: 0;

    .paas-log-box {
      display: flex;
      flex-direction: column;
      min-width: 0;
      padding: 0;
      overflow: hidden;
      gap: 10px;
      background: #fff;
    }

    .log-stage-alert {
      flex-shrink: 0;
      border-radius: 0;
    }

    .legacy-error-summary {
      flex-shrink: 0;
    }
  }
}
</style>
