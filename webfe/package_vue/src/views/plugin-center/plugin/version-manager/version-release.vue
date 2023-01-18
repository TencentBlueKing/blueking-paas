<template>
  <div class="container visible-range-release right-main-release">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-inner-loading"
      :offset-top="20"
      :offset-left="20"
      class="deploy-action-box"
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
                <bk-button
                  v-if="pluginFeatureFlags.CANCEL_RELEASE"
                  class="discontinued"
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
                  ext-cls="custom-icon"
                  :status="stepsStatus"
                  :steps="curAllStages"
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
        @rerunStage="rerunStage"
      />
      <template v-else-if="!finalStageIsOnline">
        <online
          :stage-data="stageData"
          @rerunStage="rerunStage"
        />
      </template>

      <div class="footer-btn-warp">
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
        <!-- 构建完成可以进入下一步 -->
        <bk-button
          theme="primary"
          v-if="!isFinalStage"
          class="ml5"
          style="width: 120px"
          :disabled="!isAllowNext"
          @click="handlerNext()"
        >
          <template v-if="stageId !== 'market'">
            {{ $t('下一步') }}
          </template>
          <template v-else>
            {{ $t('保存') }}
          </template>
        </bk-button>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import deployStage from './release-stages/deploy';
    import marketStage from './release-stages/market';
    import onlineStage from './release-stages/online';

    export default {
        components: {
            paasPluginTitle,
            deploy: deployStage,
            market: marketStage,
            online: onlineStage
        },
        mixins: [pluginBaseMixin],
        data () {
            console.log('this', this);
            return {
                stagesIndex: 0,
                curStep: 1,
                isLoading: true,
                stageData: {},
                failedMessage: '',
                stepsStatus: ''
            };
        },
        computed: {
            releaseId () {
                return this.$route.query.release_id;
            },
            stageId () {
                return this.$store.state.plugin.curRelease.current_stage !== undefined ? this.$store.state.plugin.curRelease.current_stage.stage_id : undefined;
            },
            curVersion () {
                return this.$route.query.version || this.titleVersion;
            },
            titleVersion () {
                let releaseData = this.$store.state.plugin.curRelease;
                return `${releaseData.version} (${releaseData.source_version_name})`;
            },
            status () {
                return this.$store.state.plugin.curRelease.status;
            },
            releaseTopHeight () {
                let topHeight = this.stageId === 'deploy' ? 117 : 117 - 56;
                // 是否展示steps
                return this.isSingleStage ? topHeight : topHeight - 44;
            },
            curFirstStep () {
                return this.curAllStages.length > 0 ? this.curAllStages[0] : {};
            },
            curStageComponmentType () {
              return this.stageData.stage_id;
            },
            finalStageIsOnline () {
              return this.curAllStages.length > 0 && this.curAllStages[this.curAllStages.length - 1].name === 'online';
            },
            isSingleStage () {
              return this.curAllStages.length === 1;
            },
            isFirstStage () {
                return this.calStageOrder(this.stageData) === 1;
            },
            isFinalStage () {
                return this.curAllStages.length === this.calStageOrder(this.stageData);
            },
            isAllowPrev () {
              let isRunningDeploy = this.stageData.stage_id === 'deploy' && this.stageData.status === 'pending';
              return !isRunningDeploy;
            },
            isAllowNext () {
              return this.stageData.status === 'successful' || this.stageData.stage_id === 'market';
            }
        },
        watch: {
            curRelease: {
                handler () {
                    this.getReleaseStageDetail();
                }
            }
        },
        created () {
            this.getReleaseStageDetail();
        },
        async mounted () {
            await this.getReleaseDetail();
        },
        methods: {
            async pollingReleaseStageDetail () {
                const ctx = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.releaseId,
                    stageId: this.stageId
                };
                await new Promise(resolve => {
                    setTimeout(resolve, 2000);
                });
                const currentCtx = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.releaseId,
                    stageId: this.stageId
                };
                // 页面状态改变, 停止轮询
                if (ctx === currentCtx) this.getReleaseStageDetail();
            },
            // 获取发布步骤详情
            async getReleaseStageDetail () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.releaseId,
                        stageId: this.stageId
                    };
                    if (Object.values(params).some(value => value === undefined)) {
                        return;
                    }
                    const stageData = await this.$store.dispatch('plugin/getPluginReleaseStage', params);
                    this.$set('stageData', stageData);
                    switch (this.stageId) {
                        case 'market':
                            break;
                        case 'deploy':
                            if (this.status === 'pending') {
                                this.pollingReleaseStageDetail();
                            } else if (this.status === 'failed') {
                                // 改变状态
                                this.stepsStatus = 'error';
                                this.failedMessage = stageData.fail_message;
                            } else {
                                this.stepsStatus = '';
                            }
                            break;
                        default:
                            this.curStep = 1;
                            break;
                    }
                    // if (stageData.status === 'successful') {
                    //     this.stagesIndex = this.stagesIndex + 1;
                    //     this.curStep = this.stagesIndex + 1;
                    //     this.getReleaseStageDetail();
                    // }
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                }
            },

            // 获取版本详情
            async getReleaseDetail () {
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.releaseId
                };
                try {
                    const releaseData = await this.$store.dispatch('plugin/getReleaseDetail', data);
                    this.$store.commit('plugin/updateCurRelease', releaseData);
                    // 获取 stage 对应的序号
                    this.curStep = this.calStageOrder(releaseData.current_stage);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            // 重新执行发布步骤
            async rerunStage () {
                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.releaseId,
                    stageId: this.stageId
                };
                this.stepsStatus = '';
                try {
                    const releaseData = await this.$store.dispatch('plugin/rerunStage', {
                        ...params
                    });
                    this.$store.commit('plugin/updateCurRelease', releaseData);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 重新发布, 重置之前的发布状态
            async republish () {
                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.$route.query.release_id
                };
                try {
                    const releaseData = await this.$store.dispatch('plugin/republishRelease', {
                        ...params
                    });
                    this.$store.commit('plugin/updateCurRelease', releaseData);
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 下一步
            async handlerNext () {
                console.log('handlerNext', this);
                if (!this.isAllowNext) {
                  return;
                }
                this.isLoading = true;
                await this.$refs.curStageComponment.nextStage(async () => {
                  try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id
                    };
                    const releaseData = await this.$store.dispatch('plugin/nextStage', params);
                    this.$store.commit('plugin/updateCurRelease', releaseData);
                  } catch (e) {
                      this.$bkMessage({
                          theme: 'error',
                          message: e.detail || e.message || this.$t('接口异常')
                      });
                  } finally {
                      setTimeout(() => {
                          this.isLoading = false;
                      }, 200);
                  }
                });
            },

            showInfoCancelRelease () {
                this.$bkInfo({
                    title: `确认终止发布版本${this.curVersion} ？`,
                    width: 480,
                    maskClose: true,
                    confirmFn: () => {
                        this.handlerCancelRelease();
                    }
                });
            },

            // 终止发布
            async handlerCancelRelease () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id
                    };
                    await this.$store.dispatch('plugin/cancelRelease', params);
                    this.$bkMessage({
                        theme: 'success',
                        message: '已终止当前的发布流程'
                    });
                    this.goVersionManager();
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 上一步
            async handlerPrev () {
                this.isLoading = true;
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id
                    };
                    const releaseData = await this.$store.dispatch('plugin/backRelease', params);
                    this.$store.commit('plugin/updateCurRelease', releaseData);
                    this.$router.push({ name: 'pluginVersionRelease', query: { release_id: this.releaseId } });
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                        this.stepsStatus = '';
                    }, 200);
                }
            },

            goVersionManager () {
                this.$router.push({
                    name: 'pluginVersionManager'
                });
            },

            calStageOrder (stage) {
                const defaultOrder = 1;
                if (!this.curAllStages) return defaultOrder;
                for (let index = 0; index < this.curAllStages.length; index++) {
                    const element = this.curAllStages[index];
                    if (element.stage_id === stage.stage_id) return index + 1;
                }
                return defaultOrder;
            }
        }
    };
</script>
<style lang="scss">
.deploy-action-box {
    max-width: calc(100% - 100px);
    margin: 0 auto;
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
                    min-width: 1243px;
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
    height: 40px;
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
}
.success {
    background: rgba(45, 203, 86, 0.16) !important;
}
.w600{
    width: 600px;
}
.btn-warp{
    margin-left: 100px;
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
    height: 26px;
    line-height: 26px;
    color: #979BA5;
    font-size: 12px;
    i {
        font: 14px;
    }
}
.release-log-warp {
    margin-left: 6px;
}
.success-check-wrapper {
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
