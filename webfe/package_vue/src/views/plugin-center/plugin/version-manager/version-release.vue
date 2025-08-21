<template>
  <div class="visible-range-release right-main-release">
    <!-- 测试阶段宽度占满 -->
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-inner-loading"
      :offset-top="20"
      :offset-left="20"
      :is-min-height="false"
      :custom-style="customStyle"
      :class="['loader-phase-container', { 'test-phase-container': curStageComponmentType === 'test' }]"
    >
      <!-- 部署信息概览 -->
      <div
        class="plugin-release-top"
      >
        <div class="bg-top">
          <paas-plugin-title
            :name="isOfficialVersion ? $t('发布') : $t('测试')"
            :no-shadow="true"
            :version-data="curRelease"
            :status-map="PLUGIN_TEST_VERSION_STATUS"
          />
          <!-- 结束发布流程禁用终止发布 -->
          <span
            v-bk-tooltips="{
              content: $t('当前版本{s}，无需终止操作', { s: releaseDisablePrompt }),
              disabled: !disableTerminationRelease,
              placements: ['bottom']
            }"
          >
            <bk-button
              v-if="pluginFeatureFlags.CANCEL_RELEASE"
              class="discontinued"
              :disabled="disableTerminationRelease"
              @click="showInfoCancelRelease"
            >
              <i class="paasng-icon paasng-minus-circle" />
              {{ isOfficialVersion ? $t('终止发布') : $t('终止测试') }}
            </bk-button>
          </span>
        </div>
      </div>
      <section class="content-container" :class="{ 'with-footer': isShowButtonGroup && !isPostedSuccessfully }">
        <!-- 只有一个阶段的发布, 不展示发布步骤 -->
        <version-steps
          v-if="!isSingleStage"
          class="steps-warp-cls"
          :steps="stepAllStages"
          :cur-step.sync="curStep"
          :controllable="true"
          @change="changeStep"
        />
        <!-- 内容 - 默认步骤根据 curStageComponmentType -->
        <component
          :style="{ marginBottom: isShowButtonGroup && !isPostedSuccessfully ? '48px' : '24px' }"
          :class="{ 'component-card-cls': !excludeCardStyleList.includes(curStageComponmentType) }"
          :is="curStageComponmentType"
          v-if="stageData"
          ref="curStageComponment"
          :stage-data="stageData"
          :plugin-data="pluginDetailedData"
          :is-next="isAllowNext"
          :manual-preview="isManualPreview"
          :is-manual-switch="isShowButtonGroup"
          @rerunStage="rerunStage"
        />
        <template v-else-if="!finalStageIsOnline">
          <online
            :stage-data="stageData"
            @rerunStage="rerunStage"
          />
        </template>
      </section>

      <!-- 手动预览与发布完成不展示底部操作按钮组 -->
      <div class="footer-btn-warp" v-if="isShowButtonGroup && !isPostedSuccessfully">
        <!-- 构建完成可以进入下一步 -->
        <bk-popover placement="top" :disabled="nextTips.disabled">
          <bk-button
            v-if="!isFinalStage"
            theme="primary"
            class="ml5"
            style="width: 120px"
            :disabled="!isAllowNext"
            @click="handlerNext()"
          >
            <!-- 是否可以进行下一步 -->
            <template v-if="stageId !== 'market'">
              {{ $t('下一步') }}
            </template>
            <template v-else>
              {{ $t('保存') }}
            </template>
          </bk-button>
          <div slot="content" style="white-space: normal;">
            {{ $t(nextTips.content) }}
          </div>
        </bk-popover>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import { bus } from '@/common/bus';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import deployStage from './release-stages/deploy';
import marketStage from './release-stages/market';
import onlineStage from './release-stages/online';
// eslint-disable-next-line import/no-duplicates
import itsmStage from './release-stages/itsm';
// eslint-disable-next-line import/no-duplicates
import approvalStage from './release-stages/itsm';
import buildStage from './release-stages/build';
import testStage from './release-stages/test';
import { PLUGIN_VERSION_MAP, PLUGIN_VERSION_STATUS, PLUGIN_TEST_VERSION_STATUS } from '@/common/constants';
import versionSteps from './version-steps/index.vue';

export default {
  components: {
    paasPluginTitle,
    deploy: deployStage,
    market: marketStage,
    online: onlineStage,
    itsm: itsmStage,
    // 上线审批
    approval1: approvalStage,
    build: buildStage,
    test: testStage,
    versionSteps,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      stagesIndex: 0,
      curStep: 1,
      isLoading: true,
      stageData: {},
      pluginDetailedData: {},
      failedMessage: '',
      stepsStatus: '',
      isFirstStage: false,
      isFinalStage: false,
      // 停止轮询状态
      stopPollingStatus: ['successful', 'failed', 'interrupted'],
      isPrevious: false,
      timeId: null,
      clickStageId: null,
      isShowButtonGroup: true,
      curStepIndex: null,
      // 点击，切换后的步骤状态
      stepAllStages: [],
      // 当前获取详情id
      currentStepId: null,
      customStyle: {
        height: '100%',
      },
      excludeCardStyleList: ['deploy', 'itsm', 'test'],
      isWebPolling: true,
      PLUGIN_TEST_VERSION_STATUS,
    };
  },
  computed: {
    curRelease() {
      return this.$store.state.plugin.curRelease;
    },
    releaseId() {
      return this.$route.query.release_id;
    },
    stageId() {
      return this.curRelease?.current_stage?.stage_id;
    },
    curVersion() {
      return this.$route.query.version || this.titleVersion;
    },
    titleVersion() {
      return `${this.curRelease.version} (${this.curRelease.source_version_name})`;
    },
    status() {
      return this.curRelease.status;
    },
    releaseTopHeight() {
      const topHeight = this.stageId === 'deploy' ? 117 : 117 - 56;
      // 是否展示steps
      return !this.isSingleStage ? topHeight : topHeight - 44;
    },
    curFirstStep() {
      return this.curAllStages.length > 0 ? this.curAllStages[0] : {};
    },
    curStageComponmentType() {
      // 根据 invoke_method 字段判断当前步骤
      const invokeMethod = this.stageData?.invoke_method;
      if (invokeMethod === 'builtin') {
        return this.stageData?.stage_id;
      }
      return PLUGIN_VERSION_MAP[invokeMethod];
    },
    finalStageIsOnline() {
      return this.curAllStages.length > 0 && this.curAllStages[this.curAllStages.length - 1].name === 'online';
    },
    isSingleStage() {
      return this.curAllStages.length === 1;
    },
    isAllowNext() {
      // 测试阶段下一步按钮禁用由接口返回值决定
      if (this.curStageComponmentType === 'test') {
        return this.stageData.detail.can_proceed;
      }
      return this.stageData.status === 'successful' || this.stageData.stage_id === 'market';
    },
    // 是否为审批阶段
    isItsmStage() {
      return this.curStageComponmentType === 'itsm';
    },
    // 下一步 tips
    nextTips() {
      const config = {
        content: '',
        disabled: true,
      };
      if (this.stageData?.detail?.next_step_disabled_tips) {
        config.content = this.stageData.detail?.next_step_disabled_tips || '';
        config.disabled = this.isAllowNext;
      }
      // 审批阶段-禁用状态tips
      if (this.isItsmStage && !this.isAllowNext) {
        config.content = this.$t('只有在当前步骤成功完成后，才可进行下一步操作。');
        config.disabled = false;
      }
      // 消除无tips内容展示
      if (!config.content) config.disabled = true;
      return config;
    },
    // 是否发布成功
    isPostedSuccessfully() {
      const curStageData = this.pluginDetailedData.current_stage || {};
      return curStageData.stage_id === 'online' && curStageData.status === 'successful';
    },
    // 是否为手动切换预览步骤
    isManualPreview() {
      return this.currentStepId !== this.stageId;
    },
    versionType() {
      return this.$route.query.type || 'prod';
    },
    // 正式版
    isOfficialVersion() {
      return this.versionType === 'prod';
    },
    disableTerminationRelease() {
      return !['initial', 'pending'].includes(this.pluginDetailedData.status);
    },
    releaseDisablePrompt() {
      if (this.pluginDetailedData.status === 'interrupted') {
        return this.$t(PLUGIN_VERSION_STATUS[this.pluginDetailedData.status]);
      }
      return this.$t(`已${PLUGIN_VERSION_STATUS[this.pluginDetailedData.status]}`);
    },
  },
  watch: {
    stageData: {
      handler() {
        // 获取 stage 对应的序号
        const curStepIndex = this.calStageOrder(this.stageData);
        // 是否展示下一步、保存
        this.isFinalStage = this.curAllStages.length === curStepIndex;
        this.curStep = curStepIndex;
      },
      deep: true,
      immediate: true,
    },
    'stageData.stage_id'(value) {
      if (!Object.keys(this.pluginDetailedData).length) {
        this.getReleaseDetail();
        bus.$emit('release-stage-changes', value);
      }
    },
    clickStageId(value) {
      if (value) {
        bus.$emit('release-stage-changes', value);
      }
    },
  },
  async created() {
    this.stepAllStages = this.curAllStages;
    await this.getReleaseDetail();
    this.getReleaseStageDetail();
    bus.$emit('release-stage-changes', this.stageId);

    // 组件销毁前
    this.$once('hook:beforeDestroy', () => {
      // 关闭基本信息编辑态
      bus.$emit('release-stage-changes', 'leave');
    });
    // 在接收消息的页面中设置监听器
    window.addEventListener('message', this.messageEvent);
  },
  beforeDestroy() {
    clearTimeout(this.timeId);
  },
  methods: {
    messageEvent(event) {
      if (!event.data || event.data?.type !== 'design-test') return;
      const status = event.data.data;
      if (status === 'success') {
        this.isShowButtonGroup && this.updateStepStatus('successful');
      } else if (status === 'fail') {
        this.isShowButtonGroup && this.updateStepStatus('failed');
      }
    },
    async pollingReleaseStageDetail() {
      if (this.clickStageId) {
        clearTimeout(this.timeId);
        return;
      }
      await new Promise((resolve) => {
        this.timeId = setTimeout(resolve, 2000);
      });

      // 对应状态，停止轮询 / 上一步停止轮询
      if (this.stopPollingStatus.includes(this.stageData.status) || this.isPrevious) {
        return;
      }
      // 轮询获取发布步骤详情
      this.getReleaseStageDetail();
    },

    // 获取版本详情（获取当前步骤详情数据）
    async getReleaseDetail() {
      const data = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: this.releaseId,
      };
      try {
        const releaseData = await this.$store.dispatch('plugin/getReleaseDetail', data);
        this.pluginDetailedData = releaseData;
        this.$store.commit('plugin/updateCurRelease', releaseData);
        // 设置执行步骤状态
        this.setStepsDataStatus();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取发布步骤详情
    async getReleaseStageDetail(curStepStageId) {
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.releaseId,
          stageId: curStepStageId || this.stageId,
        };
        this.currentStepId = params.stageId;
        if (Object.values(params).some(value => value === undefined)) {
          return;
        }
        const res = await this.$store.dispatch('plugin/getPluginReleaseStage', params);
        this.stageData = res;
        // status_polling_method === 'frontend' 前端IFrame通信，其他状态都需要进行轮询 && 手动切换不用轮询
        this.isWebPolling = res.status_polling_method !== 'frontend';
        if (this.isWebPolling && this.stageData.status === 'pending' && !curStepStageId) {
          this.pollingReleaseStageDetail();
        }
        switch (this.stageData.stage_id) {
          case 'market':
            break;
          case 'deploy':
            if (this.stageData.status === 'failed') {
              // 改变状态
              this.stepsStatus = 'error';
              this.failedMessage = res.fail_message;
            } else {
              this.stepsStatus = '';
            }
            break;
        }

        // this.setStepDataFunction(curStepStageId, stageData);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          // 关闭loading
          this.isLoading = false;
        }, 500);
      }
    },

    // 设置步骤状态
    setStepsDataStatus() {
      const id = this.pluginDetailedData?.current_stage?.stage_id || this.stageId;
      const curIndex = this.curAllStages.findIndex(v => v.stage_id === id) + 1;
      this.stepAllStages = this.curAllStages.map((v, index) => ({
        ...v,
        // 已完成步骤设置状态
        status: index < curIndex ? 'done' : '',
      }));
    },

    // 重新执行发布步骤
    async rerunStage() {
      this.isLoading = true;
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: this.releaseId,
        stageId: this.stageId,
      };
      this.stepsStatus = '';
      try {
        await this.$store.dispatch('plugin/rerunStage', params);
        await this.getReleaseStageDetail();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        this.isLoading = false;
      }
    },

    // 重新发布, 重置之前的发布状态
    async republish() {
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: this.$route.query.release_id,
      };
      try {
        const releaseData = await this.$store.dispatch('plugin/republishRelease', params);
        this.$store.commit('plugin/updateCurRelease', releaseData);
        await this.getReleaseStageDetail();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 200);
      }
    },
    // 下一步
    async handlerNext() {
      if (!this.isAllowNext) {
        return;
      }
      await this.$refs.curStageComponment.nextStage(async () => {
        this.isLoading = true;
        try {
          const params = {
            pdId: this.pdId,
            pluginId: this.pluginId,
            releaseId: this.$route.query.release_id,
          };
          const releaseData = await this.$store.dispatch('plugin/nextStage', params);
          this.$store.commit('plugin/updateCurRelease', releaseData);
          await this.getReleaseDetail();
          await this.getReleaseStageDetail();
        } catch (e) {
          this.$bkMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
          this.isLoading = false;
        }
      });
    },

    showInfoCancelRelease() {
      this.$bkInfo({
        title: `${this.$t(`确认终止${this.isOfficialVersion ? '发布' : '测试'}版本`)}${this.curVersion} ？`,
        width: 540,
        maskClose: true,
        confirmFn: () => {
          this.handlerCancelRelease();
        },
      });
    },

    // 终止发布
    async handlerCancelRelease() {
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.$route.query.release_id,
        };
        await this.$store.dispatch('plugin/cancelRelease', params);
        this.$bkMessage({
          theme: 'success',
          message: this.$t('已终止当前的发布流程'),
        });
        this.goVersionManager();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 200);
      }
    },

    goVersionManager() {
      this.$router.push({
        name: 'pluginVersionManager',
        query: {
          type: this.isOfficialVersion ? 'prod' : 'test',
        },
      });
    },

    // 计算当前正在执行的步骤
    calStageOrder(stage) {
      const defaultOrder = 1;
      if (!this.curAllStages) return defaultOrder;
      for (let index = 0; index < this.curAllStages.length; index++) {
        const step = this.curAllStages[index];
        if (step.stage_id === stage.stage_id) return index + 1;
      }
      return defaultOrder;
    },

    // 切换stpe回调
    async changeStep(data) {
      // 开启loading
      this.isLoading = true;
      // 手动切换步骤不展示按钮组，切换回当前执行步骤展示按钮组
      this.isShowButtonGroup = false;
      // 点击返回了这在执行的发布步骤
      const id = this.pluginDetailedData?.current_stage?.stage_id || this.stageId;
      const curIndex = this.curAllStages.findIndex(v => v.stage_id === id) + 1;
      let isPolling = false;
      // 点击步骤为当前执行步骤
      if (curIndex === this.curStep) {
        this.isShowButtonGroup = true;
        // 切换回执行步骤，重新轮询接口
        isPolling = true;
      }
      // 获取当前基本信息
      await this.getReleaseDetail();
      // 获取当前步骤信息
      this.getReleaseStageDetail(!isPolling ? data.id : '');
    },

    // 请求接口更新步骤状态
    async updateStepStatus(status) {
      try {
        await this.$store.dispatch('plugin/updateStepStatus', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.releaseId,
          stageId: this.stageId,
          data: {
            // successful、failed、pending、initial、interrupted
            status,
          },
        });
        this.getReleaseDetail();
        this.getReleaseStageDetail();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>
<style lang="scss">
.deploy-action-box {
    max-width: calc(100% - 100px);
    margin: 0 auto;
}
.test-phase-container {
    max-width: 100%;
}
.plugin-release-top {
    .bg-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 52px;
        padding: 0 24px;
        background: #fff;
        box-shadow: 0 3px 4px 0 #0000000a;
    }
    .father-wrapper {
        position: fixed;
        margin-left: 241px;
        left: 0;
        top: 50px;
        right: 0;
        padding-bottom: 16px;
        background: #fff;
        z-index: 99;
    }
}
.content-container {
  flex: 1;
  overflow-y: auto;
  background: #F5F6FA;
  height: calc(100% - 52px);
  padding: 16px 24px 0;
  &.with-footer {
    height: calc(100% - 100px);
  }
  .steps-warp-cls {
    margin-bottom: 16px;
  }
  .component-card-cls {
    flex: 1;
    margin-bottom: 24px;
    min-height: 0;
    box-shadow: 0 2px 4px 0 #1919290d;
    border-radius: 2px;
    background: #fff;
  }
}
#release-timeline-box {
    width: 230px;
    height: calc(100vh - 288px);
    overflow-y: auto;
    &::-webkit-scrollbar {
        width: 4px;
        background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
        height: 5px;
        border-radius: 2px;
        background-color: #C4C6CC;
    }
}
.steps-warp{
    width: 80%;
    margin: 0 auto;
}
.failed{
    background: #FFDDDD !important;
}
.release-info-box{
    padding: 0px 15px;
    min-height: 40px;
    background: #E1ECFF;
    border-radius: 2px;
    margin-bottom: 16px;
    .time-text{
        font-size: 12px;
        color: #63656E;
    }
    .deploy-round-loading{
        width: 21px;
        height: 21px;
    }
    .ext-cls-btn{
        border: 1px solid #3A84FF;
        border-radius: 2px;
        background: #E1ECFF;
        color: #3A84FF;
    }
    .ext-cls-btn:hover {
        color: #fff;
        background: #3A84FF !important;
    }
    .error-left-warp{
        .error-icon{
            color: #EA3636;
            font-size: 18px;
        }
    }
    &.warning {
        background: #ff9c0129;
    }
    &.failed {
        background: #FFDDDD;
    }
    &.interrupted {
        background: #F5F7FA;
    }
}
.success {
    background: rgba(45, 203, 86, 0.16) !important;
}
.w600{
    width: 600px;
}
.btn-warp{
    margin-left: 100px;
    margin-top: 50px;
}
.footer-btn-warp {
    position: fixed;
    bottom: 0;
    left: 241px;
    // max-width: 1140px;
    width: 100%;
    padding-left: 48px;
    height: 48px;
    line-height: 48px;
    background: #FAFBFD;
    box-shadow: 0 -1px 0 0 #DCDEE5;
    // background: #FFFFFF;
    // box-shadow: 1px -2px 4px 0 rgba(0,0,0,0.08);
}
.edit-form-item{
    margin-bottom: 20px;
}
.time-cls{
    color: #C4C6CC;
}
.discontinued {
    font-size: 14px;
    i {
      margin-right: 3px;
    }
}
.success-check-wrapper,
.interrupted-check-wrapper,
.warning-check-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    background: #2dcb56;
    border-radius: 50%;
    line-height: 24px;
    color: #fff;
    text-align: center;
    z-index: 1;
    i {
        font-size: 24px;
        line-height: 24px;
        font-weight: 500;
        margin-top: 2px;
    }
}
.warning-check-wrapper {
    color: #FFB848;
    background: transparent;
}
.interrupted-check-wrapper {
    background-color: #C4C6CC;
    i {
        color: #fff;
        font-size: 16px;
    }
}
.info-left-warp .info-time {
    line-height: 24px;
}
.visible-range-release {
  background: #F5F6FA;
  height: 100%;
  .loader-phase-container,
  .content-container {
    display: flex;
    flex-direction: column;
  }
  .app-container {
    margin-top: 0;
    padding-top: 0;
  }
}

.custom-step-cls {
  .bk-step {
    &.done,
    &.current {
      .bk-step-number,
      .bk-step-content {
        cursor: pointer;
      }
    }
    &.done .bk-step-number:hover+.bk-step-content .bk-step-title {
      color: #3A84FF !important;
    }
    &.done .bk-step-content:hover .bk-step-title {
      color: #3A84FF !important;
    }
    &.current .bk-step-number:hover+.bk-step-content .bk-step-title {
      color: #3A84FF !important;
    }
    &.current:hover .bk-step-content:hover .bk-step-title {
      color: #3A84FF !important;
    }
  }
}
</style>
<style>
    .visible-range-release .editor .ql-snow .ql-formats {
        line-height: 24px;
    }
    .visible-range-release .editor {
        display: flex;
        flex-direction: column;
        height: 300px;
    }
</style>
