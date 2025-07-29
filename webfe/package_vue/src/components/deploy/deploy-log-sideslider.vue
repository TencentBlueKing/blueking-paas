<template>
  <bk-sideslider
    :width="920"
    :is-show.sync="historySideslider.isShow"
    :quick-close="true"
    ext-cls="deploy-history-sideslider"
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
          style="min-width: 250px"
        />
        <div class="paas-log-box">
          <div
            v-if="isMatchedSolutionsFound"
            class="wrapper danger"
          >
            <div class="fl">
              <span class="paasng-icon paasng-info-circle-shape" />
            </div>
            <section style="position: relative; margin-left: 50px">
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
            style="margin: -20px -20px 10px -20px; border-radius: 0"
            type="warning"
            :title="$t('仅展示准备阶段、构建阶段日志')"
          />
          <pre v-dompurify-html="curDeployLog" />
        </div>
      </template>
    </div>
  </bk-sideslider>
</template>

<script>import deployTimeline from './deploy-timeline';

export default {
  components: {
    deployTimeline,
  },
  props: {
    appCode: {
      type: String | Number,
      default: '',
    },
    moduleId: {
      type: String | Number,
      default: '',
    },
  },

  data() {
    return {
      isLogLoading: false,
      isTimelineLoading: false,
      ansiUp: null,
      curDeployLog: '',
      timeLineList: [],
      historySideslider: {
        title: '',
        isShow: false,
      },
      errorTips: {},
      logExportUrl: '',
    };
  },

  computed: {
    isMatchedSolutionsFound() {
      return this.errorTips.matched_solutions_found;
    },
  },

  mounted() {
    const AU = require('ansi_up');
    // eslint-disable-next-line
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
      this.logExportUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${params.moduleName || this.moduleId}/deployments/${params.deployment_id}/logs/export`;
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

    handleShowLog(row) {
      this.timeLineList = [];
      this.curDeployLog = '';
      if (this.isTimelineLoading || this.isLogLoading) {
        return false;
      }

      const operator = row.operator.username;
      const time = row.created;
      const moduleName = row.moduleName;
      if (row.operation_type === 'offline') {
        const title = `${moduleName}${this.$t(' 模块')}${row.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境')}${this.$t('下架日志')} (${operator}${this.$t('于')}${time}${this.$t('下架')}`;
        this.historySideslider.title = title;
        this.curDeployLog = row.logDetail;
      } else {
        this.historySideslider.title = `${moduleName}${this.$t(' 模块')}${
          row.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境')
        }${this.$t('部署日志')} ${operator}${this.$t('于')}${time}${this.$t('部署')}`;
        this.getDeployTimeline(row);
        this.getDeployLog(row);
      }
      this.historySideslider.isShow = true;
    },

    /** 构建详情 */
    handleShowBuildLog(row) {
      this.timeLineList = [];
      this.curDeployLog = '';
      if (this.isTimelineLoading || this.isLogLoading) {
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
      window.open(this.logExportUrl, '_blank')
    }
  },
};
</script>

<style lang="scss" scoped>
.deploy-header {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.deploy-history-sideslider :deep(.bk-sideslider-content) {
  overflow: unset;
}
.deploy-detail {
  display: flex;
  height: 100%;

  /deep/ .paas-deploy-log-wrapper {
    height: 100%;
  }

  .wrapper {
    margin: -20px -20px 10px;
    height: 64px;
    background: #f5f6fa;
    line-height: 64px;
    padding: 0 20px;

    &::after {
      display: block;
      clear: both;
      content: '';
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
      background: #e1ecff;
      color: #979ba5;
    }

    &.warning {
      background: #fff4e2;
      border-color: #ffdfac;

      .paasng-icon {
        color: #fe9f07;
      }
    }

    &.danger {
      background: #ffecec;
      color: #979ba5;

      .paasng-icon {
        color: #eb3635;
        position: relative;
        top: 4px;
        font-size: 32px;
      }
    }

    &.success {
      background: #e7fcfa;
      color: #979ba5;

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
        opacity: 0.9;
      }
      .branch-text,
      .version-text {
        margin-right: 30px;
      }
    }
  }
}
</style>
