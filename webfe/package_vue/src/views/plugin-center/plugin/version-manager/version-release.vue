<template>
  <div class="container visible-range-release right-main-release">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-inner-loading"
      :offset-top="20"
      :offset-left="20"
      class="deploy-action-box"
    >
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
                v-if="isNotStep"
                class="steps-warp mt20"
              >
                <bk-steps
                  ext-cls="custom-icon"
                  :status="stepsStatus"
                  :steps="allStages"
                  :cur-step.sync="curStep"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 内容 -->
      <div class="plugin-container">
        <!-- 部署状态 -->
        <div
          v-if="stageId === 'deploy'"
          class="wrapper primary
                                release-info-box
                                flex-row
                                justify-content-between
                                align-items-center"
          :class="[{ 'failed': status === 'failed' }, { 'success': status === 'successful' }]"
        >
          <div
            v-if="status === 'pending'"
            class="info-left-warp flex-row"
          >
            <round-loading
              size="small"
              ext-cls="deploy-round-loading"
            />
            <span class="info-time pl10">
              <span class="info-pending-text"> {{ $t('正在部署中...') }} </span>
              <!-- <span class="time-text"> {{ $t('耗时：') }} 13秒</span> -->
            </span>
          </div>
          <div
            v-else-if="status === 'failed'"
            class="error-left-warp flex-row align-items-center"
          >
            <i class="error-icon paasng-icon paasng-close-circle-shape" />
            <span class="info-time pl10">
              <span class="info-pending-text"> {{ $t('构建失败') }} </span>
              <span class="time-text">{{ failedMessage }}</span>
            </span>
          </div>
          <div
            v-else-if="status === 'successful'"
            class="info-left-warp flex-row"
          >
            <span class="success-check-wrapper">
              <i class="paasng-icon paasng-correct" />
            </span>
            <span class="info-time pl10">
              <span class="info-pending-text"> {{ $t('部署成功') }} </span>
            </span>
          </div>
          <div
            v-if="!isNext"
            class="info-right-warp"
          >
            <bk-button
              v-if="status !== 'pending'"
              size="small"
              theme="primary"
              :outline="true"
              :class="[{ 'failed': status === 'failed' }]"
              class="ext-cls-btn"
              @click="rightClick(status)"
            >
              {{ status === 'pending' ? $t('停止部署') : $t('重新部署') }}
            </bk-button>
          </div>
        </div>
        <div
          id="release-box"
          class="release-warp"
        >
          <template>
            <div
              v-if="stageId === 'online'"
              class="successful-container"
            >
              <i class="bk-icon icon-check-1 icon-finish success-cls" />
              <h3 class="title">
                {{ $t('插件已发布成功') }}
              </h3>
              <span
                class="tips-link"
                @click="goVersionManager"
              >
                {{ $t('返回插件版本列表') }}
              </span>
            </div>
            <template v-if="stageId === 'deploy'">
              <!-- 部署模块 -->
              <div class="release-log-warp flex-row">
                <div
                  id="release-timeline-box"
                  style="width: 230px;padding-left: 8px;"
                >
                  <release-timeline
                    ref="deployTimelineRef"
                    :list="stepsData"
                  />
                </div>
                <release-log
                  ref="deployLogRef"
                  :log="logs"
                />
              </div>
            </template>
          </template>

          <!-- 完善市场信息模块 -->
          <div
            v-if="stageId === 'market'"
            class="info-mt"
          >
            <bk-form
              ref="visitForm"
              :model="form"
              :rules="rules"
              :label-width="100"
            >
              <bk-form-item
                class="w600"
                :label="$t('应用分类')"
                :required="true"
                :property="'category'"
              >
                <bk-select
                  v-model="form.category"
                  :loading="cateLoading"
                  :clearable="false"
                  :placeholder="$t('应用分类')"
                >
                  <bk-option
                    v-for="(option, index) in categoryList"
                    :id="option.value"
                    :key="index"
                    :name="option.name"
                  />
                </bk-select>
              </bk-form-item>
              <bk-form-item
                :label="$t('应用简介')"
                :required="true"
                :property="'introduction'"
              >
                <bk-input v-model="form.introduction" />
              </bk-form-item>
              <bk-form-item
                :label="$t('应用联系人')"
                :required="true"
                property="contact"
              >
                <user v-model="form.contact" />
              </bk-form-item>
              <bk-form-item
                class="edit-form-item"
                :label="$t('详细描述')"
                :required="true"
                :property="'description'"
              >
                <quill-editor
                  v-model="form.description"
                  class="editor"
                  :options="editorOption"
                  @change="onEditorChange($event)"
                />
              </bk-form-item>
            </bk-form>
          </div>

          <div
            v-if="stageId === 'market'"
            class="btn-warp"
          >
            <!-- <bk-button>上一步</bk-button> -->
            <bk-button
              theme="primary"
              @click="handlerSave"
            >
              {{ $t('保存') }}
            </bk-button>
            <!-- 根据步骤来， 当前步骤的下一步 -->
            <!-- <bk-button
              theme="primary"
              :disabled="!isNext"
              @click="handlerNext"
            >
              {{ $t('下一步') }}
            </bk-button> -->
          </div>
        </div>
      </div>
      <div
        v-if="stageId === 'deploy' && isNotStep"
        class="footer-btn-warp"
      >
        <bk-button
          v-if="curFirstStep.id !== 'deploy'"
          theme="default"
          @click="handlerPrev"
        >
          {{ $t('上一步') }}
        </bk-button>
        <!-- 构建完成可以进入下一步 -->
        <bk-button
          theme="primary"
          class="ml5"
          style="width: 120px"
          :disabled="!isNext"
          @click="handlerNext(stageId)"
        >
          {{ $t('下一步') }}
        </bk-button>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
    import { bus } from '@/common/bus';
    import user from '@/components/user';
    import paasPluginTitle from '@/components/pass-plugin-title';
    import releaseTimeline from './release-timeline';
    import releaseLog from './release-log.vue';
    import { quillEditor } from 'vue-quill-editor';
    import _ from 'lodash';
    import 'quill/dist/quill.core.css';
    import 'quill/dist/quill.snow.css';
    import 'quill/dist/quill.bubble.css';
    export default {
        components: {
            paasPluginTitle,
            releaseTimeline,
            releaseLog,
            quillEditor,
            user
        },
        data () {
            return {
                allStages: [],
                stagesIndex: 0,
                curStep: 1,
                stageId: '',
                form: {
                    category: '',
                    introduction: '',
                    description: '',
                    contact: []
                },
                categoryList: [],
                cateLoading: true,
                isLoading: true,
                editorOption: {
                    placeholder: '开始编辑...'
                },
                isNext: false,
                status: '',
                stepsData: [],
                timer: null,
                logs: [],
                failedMessage: '',
                titleVersion: '',
                isStopDeploy: false,
                stepsStatus: '',
                curFirstStep: {},
                stpeMap: {},
                isNotStep: true,
                rules: {
                    category: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ],
                    introduction: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ],
                    description: [
                        {
                            required: true,
                            message: this.$t('请输入'),
                            trigger: 'blur'
                        }
                    ],
                    contact: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },
        computed: {
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            },
            curVersion () {
                return this.$route.query.version || this.titleVersion;
            },
            stagesData () {
                return this.$store.state.plugin.stagesData;
            },
            curStatus () {
                return this.$route.params.status;
            },
            pluginFeatureFlags () {
                return this.$store.state.plugin.pluginFeatureFlags;
            },
            releaseTopHeight () {
                let topHeight = this.stageId === 'deploy' ? 117 : 117 - 56;
                // 是否展示steps
                return this.isNotStep ? topHeight : topHeight - 44;
            }
        },
        watch: {
            allStages (newStages) {
                this.curFirstStep = newStages[0];
                // 创建step map映射
                newStages.forEach(item => {
                    this.$set(this.stpeMap, item.id, item.icon);
                });
            }
        },
        created () {
            bus.$on('stop-deploy', () => {
                this.isStopDeploy = true;
            });
        },
        async mounted () {
            this.stageId = this.$route.query.stage_id;
            this.status = this.$route.query.status;
            await this.getVersionDetail();
            // if (this.status === 'interrupted' || this.status === 'failed') {
            //     // 重新发布
            //     this.republish();
            // } else {
                if (this.stageId === 'market') {
                    this.fetchCategoryList();
                    this.fetchMarketInfo();
                } else {
                    this.fetchPluginRelease();
                }
            // }
        },
        beforeDestroy () {
            bus.$emit('stop-deploy', true);
        },
        methods: {
            setTimeFetchPluginRelease () {
                this.timer = setTimeout(() => {
                    this.fetchPluginRelease();
                }, 2000);
            },
            rightClick (status) {
                if (status === 'pending') {
                    console.log(status);
                } else {
                    this.pluginDeploy();
                    // this.fetchPluginRelease();
                }
            },

            // 获取市场信息
            async fetchMarketInfo () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId
                    };
                    const res = await this.$store.dispatch('plugin/getMarketInfo', params);
                    this.form = res;
                    this.form.contact = res.contact && res.contact.split(',') || [];
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
            // 应用分类
            async fetchCategoryList () {
                try {
                    const params = {
                        pdId: this.pdId
                    };
                    const res = await this.$store.dispatch('plugin/getCategoryList', params);
                    this.categoryList = res.category;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.cateLoading = false;
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 获取部署详情
            async fetchPluginRelease () {
                // 点击返回，停止部署接口轮询
                if (this.isStopDeploy) {
                    return;
                }
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id,
                        stageId: this.stageId
                    };
                    if (Object.values(params).some(value => value === undefined)) {
                        return;
                    }
                    const res = await this.$store.dispatch('plugin/getPluginRelease', params);
                    this.stageId = res.stage_id;
                    this.isNext = res.status === 'successful';
                    if (!this.isNotStep && res.status === 'successful') {
                        // 当步骤只有一步一时，部署成功后直接展示成功提示界面
                        this.stageId = 'online';
                    }
                    this.status = res.status;
                    switch (this.stageId) {
                        case 'market':
                            // 根据接口数据而定
                            // this.curStep = 1;
                            break;
                        case 'deploy':
                            this.stepsData = this.modifyStepsData(res.detail.steps);
                            this.logs = res.detail.logs;
                            // this.curStep = 2;
                            if (this.status === 'pending') {
                                this.setTimeFetchPluginRelease();
                            } else if (this.status === 'failed') {
                                // 改变状态
                                this.stepsStatus = 'error';
                                this.failedMessage = res.fail_message;
                            } else {
                                this.stepsStatus = '';
                                if (this.timer) {
                                    clearTimeout(this.timer);
                                }
                            }
                            break;
                        default:
                            this.curStep = 1;
                            break;
                    }
                    // if (res.status === 'successful') {
                    //     this.stagesIndex = this.stagesIndex + 1;
                    //     this.curStep = this.stagesIndex + 1;
                    //     this.fetchPluginRelease();
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
            async getVersionDetail () {
                const data = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.$route.query.release_id
                };
                try {
                    const res = await this.$store.dispatch('plugin/getVersionDetail', data);
                    const stagesData = this.allStagesMap(res.all_stages);
                    this.titleVersion = `${res.version} (${res.source_version_name})`;
                    this.allStages = stagesData;
                    this.status = res.status;
                    // 获取对应step
                    this.curStep = this.stpeMap[res.current_stage.stage_id];
                    if (this.allStages.length === 1) {
                        // 当步骤只存在一步时，不展示step与下一步
                        this.isNotStep = false;
                    }
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                }
            },

            // 重新部署
            async pluginDeploy () {
                const params = {
                    pdId: this.pdId,
                    pluginId: this.pluginId,
                    releaseId: this.$route.query.release_id,
                    stageId: this.stageId
                };
                const data = {};
                this.stepsStatus = '';
                try {
                    const res = await this.$store.dispatch('plugin/pluginDeploy', {
                        ...params,
                        data
                    });
                    this.stageId = res.stage_id;
                    this.status = res.status;
                    const query = JSON.parse(JSON.stringify(this.$route.query));
                    query.stage_id = this.stageId;
                    this.$router.push({ name: 'pluginVersionRelease', query });
                    this.fetchPluginRelease();
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
                    const res = await this.$store.dispatch('plugin/republishRelease', {
                        ...params
                    });
                    this.stageId = res.current_stage && res.current_stage.stage_id;
                    this.status = res.status;
                    this.fetchPluginRelease();
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

            modifyStepsData (data) {
                return data.map(item => {
                    // da根据 steps[i].status 来决定当前部署的状态
                    item.time = this.computedDeployTime(item.start_time, item.complete_time);
                    if (item.status === 'successful' || item.status === 'failed') {
                        item.tag = `
                        <div style="width: 185px" class="flex-row justify-content-between">
                            <div>${item.name}</div>
                            <div style="color: #C4C6CC" class="time-cls">${item.time}</div>
                        </div>
                        `;
                    } else {
                        item.tag = `
                        <div style="width: 185px" class="flex-row justify-content-between">
                            <div>${item.name}</div>
                        </div>
                        `;
                    }
                    switch (item.status) {
                        case 'successful':
                            item.type = 'success';
                            break;
                        case 'failed':
                            item.type = 'danger';
                            break;
                        case 'pending':
                            item.type = 'primary';
                            item.icon = <round-loading size="small" ext-cls="deploy-round-loading" />;
                            break;
                    }
                    return item;
                });
            },

            getDisplayTime (payload) {
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
             * 计算部署进程间的所花时间
             */
            computedDeployTime (startTime, endTime) {
                const start = new Date(startTime).getTime();
                const end = new Date(endTime).getTime();
                const interval = (end - start) / 1000;

                if (!interval) {
                    return `< 1${this.$t('秒')}`;
                }

                return this.getDisplayTime(interval);
            },

            // 保存
            async handlerSave () {
                this.$refs.visitForm.validate().then(async () => {
                    try {
                        const data = _.cloneDeep(this.form);
                        data.contact = data.contact.join(',');
                        const params = {
                            pdId: this.pdId,
                            pluginId: this.pluginId,
                            data
                        };
                        await this.$store.dispatch('plugin/saveMarketInfo', params);
                        this.$bkMessage({
                            theme: 'success',
                            message: this.$t('保存成功!')
                        });
                        await this.handlerNext();
                    } catch (e) {
                        this.$bkMessage({
                            theme: 'error',
                            message: e.detail || e.message || this.$t('接口异常')
                        });
                    } finally {
                        this.cateLoading = false;
                    }
                });
            },

            // 下一步
            async handlerNext (status) {
                // 根据当前状态更改
                this.isLoading = true;
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id
                    };
                    const res = await this.$store.dispatch('plugin/nextRelease', params);
                    this.stageId = res.current_stage.stage_id;
                    this.getVersionDetail();
                    if (this.stageId === 'market') {
                        const query = JSON.parse(JSON.stringify(this.$route.query));
                        query.stage_id = this.stageId;
                        this.$router.push({ name: 'pluginVersionRelease', query });
                        this.fetchCategoryList();
                        this.fetchMarketInfo();
                    } else if (this.stageId === 'deploy') {
                        const query = JSON.parse(JSON.stringify(this.$route.query));
                        query.stage_id = this.stageId;
                        this.fetchPluginRelease();
                        this.$router.push({ name: 'pluginVersionRelease', query });
                    } else {
                        this.stepsStatus = '';
                    }
                    // 更新对应 step
                    this.curStep = this.stpeMap[res.current_stage.stage_id];
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

            // 富文本编辑
            onEditorChange (e) {
                this.$set(this.form, 'description', e.html);
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
                    const res = await this.$store.dispatch('plugin/backRelease', params);
                    const stagesData = this.allStagesMap(res.all_stages);
                    this.allStages = stagesData;
                    this.stageId = res.current_stage.stage_id;
                    this.changeStep(res.current_stage.stage_id);
                    this.$store.commit('plugin/updateStagesData', stagesData);
                    const query = JSON.parse(JSON.stringify(this.$route.query));
                    query.stage_id = res.current_stage.stage_id;
                    this.$router.push({ name: 'pluginVersionRelease', query });
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

            changeStep (curStageId) {
                switch (curStageId) {
                    case 'market':
                        // this.curStep = 1;
                        this.fetchCategoryList();
                        this.fetchMarketInfo();
                        break;
                    default:
                        break;
                }
            },

            allStagesMap (allStages) {
                return allStages.map((e, i) => {
                    e.icon = i + 1;
                    e.title = e.name;
                    return e;
                });
            },

            goVersionManager () {
                this.$router.push({
                    name: 'pluginVersionManager'
                });
            }
        }
    };
</script>
<style lang="scss" scoped>
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
.container.visible-range-release {
     width: 85vw !important;
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
