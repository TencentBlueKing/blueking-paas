<template>
  <div class="container visible-range-release right-main-release">
    <!-- 测试阶段宽度占满 -->
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-inner-loading"
      :offset-top="20"
      :offset-left="20"
      :class="curStageComponmentType === 'test' ? 'test-phase-container' : 'deploy-action-box'"
    >
      <!-- 部署信息概览 -->
      <div
        class="plugin-release-top"
        :style="`height: ${ releaseTopHeight }px;`"
      >
        <div class="father-wrapper">
          <div class="bg-top">
            <div class="bg-content">
              <div class="title-warp flex-row align-items-center justify-content-between">
                <paas-plugin-title :version="curVersion" />
                <!-- 结束发布流程禁用终止发布 -->
                <bk-button
                  v-if="pluginFeatureFlags.CANCEL_RELEASE"
                  class="discontinued"
                  :disabled="isPostedSuccessfully"
                  @click="showInfoCancelRelease"
                >
                  <i class="paasng-icon paasng-stop-2" />
                  {{ $t('终止发布') }}
                </bk-button>
              </div>
              <div
                v-if="!isSingleStage"
                class="steps-warp mt20"
              >
                <!-- 只有一个阶段的发布, 不展示发布步骤 -->
                <bk-steps
                  ext-cls="custom-step-cls"
                  :status="stepsStatus"
                  :steps="stepAllStages"
                  :cur-step.sync="curStep"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 内容 -->
      <component
        :is="curStageComponmentType"
        v-if="stageData"
        ref="curStageComponment"
        :stage-data="stageData"
        :plugin-data="pluginDetailedData"
        :is-next="isAllowNext"
        :manual-preview="isManualPreview"
        @rerunStage="rerunStage"
      />
      <template v-else-if="!finalStageIsOnline">
        <online
          :stage-data="stageData"
          @rerunStage="rerunStage"
        />
      </template>

      <!-- 手动预览与发布完成不展示 -->
      <div class="footer-btn-warp" v-if="isShowButtonGroup && !isPostedSuccessfully">
        <bk-popover placement="top" :disabled="isAllowPrev && !isItsmStage">
          <bk-button
            v-if="!isFirstStage"
            theme="default"
            class="ml5"
            style="width: 120px"
            :disabled="!isAllowPrev"
            @click="handlerPrev"
          >
            {{ $t('上一步') }}
          </bk-button>
          <div slot="content" style="white-space: normal;">
            {{ $t('单据正在审批中，无法回到上一步，如有修改需求，请先撤销提单') }}
          </div>
        </bk-popover>
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
            {{ nextTips.content }}
          </div>
        </bk-popover>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>import paasPluginTitle from '@/components/pass-plugin-title';
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
    };
  },
  computed: {
    releaseId() {
      return this.$route.query.release_id;
    },
    stageId() {
      return this.$store.state.plugin.curRelease.current_stage && this.$store.state.plugin.curRelease.current_stage.stage_id;
    },
    curVersion() {
      return this.$route.query.version || this.titleVersion;
    },
    titleVersion() {
      const releaseData = this.$store.state.plugin.curRelease;
      return `${releaseData.version} (${releaseData.source_version_name})`;
    },
    status() {
      return this.$store.state.plugin.curRelease.status;
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
      return this.stageData.stage_id;
    },
    finalStageIsOnline() {
      return this.curAllStages.length > 0 && this.curAllStages[this.curAllStages.length - 1].name === 'online';
    },
    isSingleStage() {
      return this.curAllStages.length === 1;
    },
    // 是否禁用上一步
    isAllowPrev() {
      switch (this.curStageComponmentType) {
        case 'itsm':
          const itemStatus = this.stageData.status || this.pluginDetailedData.current_stage?.status;
          // 已撤销、审批不通过，才显示上一步，其余情况禁用
          const isDisabledList = ['interrupted', 'failed'];
          return !!isDisabledList.includes(itemStatus);
          break;
        default:
          const isRunningDeploy = this.stageData.stage_id === 'deploy' && this.stageData.status === 'pending';
          return !isRunningDeploy && this.status !== 'successful';
          break;
      }
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
  },
  watch: {
    stageData: {
      handler() {
        // 获取 stage 对应的序号
        const curStep = this.calStageOrder(this.stageData);
        this.isFirstStage = curStep === 1;
        this.isFinalStage = this.curAllStages.length === curStep;
        this.curStep = curStep;
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
    await this.getReleaseDetail();
    this.stepAllStages = this.curAllStages;
    this.getReleaseStageDetail();
    bus.$emit('release-stage-changes', this.stageId);

    // 组件销毁前
    this.$once('hook:beforeDestroy', () => {
      // 关闭基本信息编辑态
      bus.$emit('release-stage-changes', 'leave');
    });
  },
  methods: {
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
    // 获取发布步骤详情
    async getReleaseStageDetail() {
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.releaseId,
          stageId: this.clickStageId || this.stageId,
        };
        this.currentStepId = params.stageId;
        if (Object.values(params).some(value => value === undefined)) {
          return;
        }
        const stageData = await this.$store.dispatch('plugin/getPluginReleaseStage', params);
        this.stageData = stageData;
        // 所有阶段都需要进行轮询 && 手动切换不用轮询
        if (this.stageData.status === 'pending' && !this.clickStageId) {
          this.pollingReleaseStageDetail();
        }
        switch (this.stageData.stage_id) {
          case 'market':
            break;
          case 'deploy':
            if (this.stageData.status === 'failed') {
              // 改变状态
              this.stepsStatus = 'error';
              this.failedMessage = stageData.fail_message;
            } else {
              this.stepsStatus = '';
            }
            break;
        }
        if (this.clickStageId) {
          this.clickStageId = null;
          this.isLoading = false;
        }
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
        if (this.clickStageId) {
          this.clickStageId = null;
          this.isLoading = false;
        }
      } finally {
        setTimeout(() => {
          if (!this.clickStageId) this.isLoading = false;
          this.stepsBindingClick();
        }, 500);
      }
    },

    // 给step绑定点击事件
    stepsBindingClick() {
      const stepsEl = document.querySelector('.custom-step-cls');
      const stepList = Array.from(stepsEl?.childNodes || []);
      // 根据对应当前id获取DOM
      const i = this.curAllStages.findIndex(v => v.stage_id === this.stageId);
      let bingElementList = [];
      bingElementList = stepList.slice(0, i + 1);
      this.curStepIndex = i + 1;
      // 设置步骤状态
      this.setStepsData();

      // 重置点击事件，防止点击上一步状态变更事件带来的接口错误
      this.clearEventSideEffects(stepList);

      // 已成功步骤绑定点击事件
      bingElementList.forEach((el, index) => {
        const childList = Array.from(el.childNodes);
        childList.forEach((child) => {
          child.onclick = () => {
            // 如果点击当前显示的当前步骤，不做操作
            if (clickStageId !== this.stageId && this.curStep === (index + 1)) {
              return;
            }
            // 给已发布完成的步骤添加状态

            // 点击更新步骤
            this.curStep = index + 1;
            // 当前点击的stage_id
            const clickStageId = this.curAllStages[index].stage_id;
            this.isLoading = true;
            // 手动点击切换步骤不显示底部操作
            this.isShowButtonGroup = false;
            this.clickStageId = clickStageId;

            // 获取当前基本信息
            this.getReleaseDetail();
            // 获取当前步骤信息
            this.getReleaseStageDetail();

            // 点击返回了这在执行的发布步骤
            if (this.curStepIndex === this.curStep) {
              this.isShowButtonGroup = true;
              // 重置点击的 stageId, 重新轮询接口
              this.clickStageId = null;
            }
          };
        });
      });
    },

    clearEventSideEffects(steps) {
      steps.forEach((stepEl) => {
        const childList = Array.from(stepEl.childNodes);
        childList.forEach((child) => {
          child.onclick = () => {};
        });
      });
    },

    setStepsData() {
      const curIndex = this.curStepIndex;
      this.stepAllStages = this.curAllStages.map((v, index) => ({
        ...v,
        // 已完成步骤设置状态
        status: index < curIndex ? 'done' : '',
      }));
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
        // 获取 stage 对应的序号
        this.curStep = this.calStageOrder(releaseData.current_stage);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 重新执行发布步骤
    async rerunStage() {
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        releaseId: this.releaseId,
        stageId: this.stageId,
      };
      this.stepsStatus = '';
      try {
        const releaseData = await this.$store.dispatch('plugin/rerunStage', params);
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
      this.isLoading = true;
      await this.$refs.curStageComponment.nextStage(async () => {
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
        } finally {
          setTimeout(() => {
            this.isLoading = false;
          }, 200);
        }
      });
    },

    showInfoCancelRelease() {
      this.$bkInfo({
        title: `${this.$t('确认终止发布版本')}${this.curVersion} ？`,
        width: 480,
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

    // 上一步
    async handlerPrev() {
      this.isLoading = true;
      this.isPrevious = true;
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.$route.query.release_id,
        };
        const releaseData = await this.$store.dispatch('plugin/backRelease', params);
        this.$store.commit('plugin/updateCurRelease', releaseData);
        await this.getReleaseDetail();
        await this.getReleaseStageDetail();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
          this.stepsStatus = '';
          this.isPrevious = false;
        }, 200);
      }
    },

    goVersionManager() {
      this.$router.push({
        name: 'pluginVersionManager',
      });
    },

    calStageOrder(stage) {
      const defaultOrder = 1;
      if (!this.curAllStages) return defaultOrder;
      for (let index = 0; index < this.curAllStages.length; index++) {
        const element = this.curAllStages[index];
        if (element.stage_id === stage.stage_id) return index + 1;
      }
      return defaultOrder;
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
    .plugin-release-top .father-wrapper {
      padding-bottom: 0px;
    }
}
.plugin-release-top {
    height: 117px;
    margin: 0 auto;
    .father-wrapper {
        position: fixed;
        margin-left: 241px;
        left: 0;
        top: 50px;
        right: 0;
        padding-bottom: 16px;
        background: #fff;
        z-index: 99;
        .bg-top {
            padding: 16px 0;
            background: #FAFBFD;
            border-bottom: 1px solid #EAEBF0;
            .bg-content {
                max-width: calc(100% - 100px);
                margin: 0 50px;
                .title-warp {
                    // min-width: 1243px;
                }
            }
        }
        // .release-info-box {
        //     max-width: calc(100% - 100px);
        //     // min-width: 1243px;
        //     margin: 0 50px;
        //     margin-top: 16px;
        // }
    }
}
#release-timeline-box {
    width: 230px;
    height: calc(100vh - 272px);
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
    background: #FFFFFF;
    box-shadow: 1px -2px 4px 0 rgba(0,0,0,0.08);
}
.edit-form-item{
    margin-bottom: 20px;
}
.time-cls{
    color: #C4C6CC;
}
.discontinued {
    color: #979BA5;
    font-size: 14px;
    i {
        font-size: 16px;
    }
}
.release-log-warp {
    margin-left: 6px;
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
.successful-container {
    margin-top: 140px;
    text-align: center;
    .success-cls {
        font-size: 50px;
        line-height: 50px;
        border-radius: 50%;
        color: #fff;
        background-color: #2dcb56;
    }
    .title {
        margin: 15px 0 10px;
        font-size: 16px;
        font-weight: 700;
    }
    .tips-link {
        cursor: pointer;
        font-size: 12px;
        color: #3A84FF;
    }
}
.visible-range-release .app-container {
    margin-top: 0;
    padding-top: 0;
}
.release-warp .info-mt {
    margin-top: 72px;
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
