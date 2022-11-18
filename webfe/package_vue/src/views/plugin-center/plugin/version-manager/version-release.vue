<template>
  <div class="container visible-range">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-inner-loading"
      :offset-top="20"
      :offset-left="20"
      class="deploy-action-box"
    >
      <div class="app-container middle">
        <div class="title-warp flex-row align-items-center justify-content-between">
          <paas-plugin-title :version="curVersion" />
          <bk-button
            class="discontinued"
            @click="handlerCancelRelease"
          >
            <i class="paasng-icon paasng-stop-2" />
            {{ $t('终止发布') }}
          </bk-button>
        </div>
        <div class="steps-warp mt20">
          <bk-steps
            ext-cls="custom-icon"
            theme="success"
            :steps="allStages"
            :cur-step.sync="curStep"
          />
        </div>
        <div
          id="release-box"
          class="release-warp mt20"
        >
          <template v-if="stageId === 'deploy'">
            <div
              class="wrapper primary
                            release-info-box
                            flex-row
                            justify-content-between
                            align-items-center"
              :class="[{ 'failed': status === 'failed' }]"
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
              <div class="info-right-warp">
                <bk-button
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
            <!-- 部署模块 -->
            <div class="release-log-warp mt30 flex-row">
              <div
                id="release-timeline-box"
                style="width: 230px"
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

          <!-- 完善市场信息模块 -->
          <div v-if="stageId === 'market'">
            <bk-form
              ref="visitForm"
              :model="form"
              :rules="rules"
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
              <bk-form-item
                :label="$t('应用联系人')"
                :required="true"
                property="contact"
              >
                <user v-model="form.contact" />
              </bk-form-item>
            </bk-form>
          </div>

          <div
            v-if="stageId === 'market'"
            class="btn-warp mt30"
          >
            <!-- <bk-button>上一步</bk-button> -->
            <bk-button
              theme="primary"
              @click="handlerSave"
            >
              保存
            </bk-button>
            <bk-button
              theme="primary"
              :disabled="!isNext"
              @click="handlerNext"
            >
              下一步
            </bk-button>
          </div>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
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
                    placeholder: '@通知他人，ctrl+enter快速提交'
                },
                isNext: false,
                status: '',
                stepsData: [],
                timer: null,
                logs: [],
                failedMessage: '',
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
                return this.$route.query.version;
            },
            stagesData () {
                return this.$store.state.plugin.stagesData;
            }
        },
        watch: {},
        mounted () {
            if (this.stagesData.length) {
                this.allStages = this.stagesData;
            } else {
                this.getVersionDetail();
            }
            this.stageId = this.$route.query.stage_id;
            if (this.stageId === 'market') {
                this.fetchCategoryList();
                this.fetchMarketInfo();
            } else {
                this.fetchPluginRelease();
            }
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
                    this.form.contact = res.contact && res.contact.split(',');
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isTableLoading = false;
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
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 获取部署详情
            async fetchPluginRelease () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id,
                        stageId: this.stageId
                    };
                    const res = await this.$store.dispatch('plugin/getPluginRelease', params);
                    this.stageId = res.stage_id;
                    this.isNext = res.status === 'successful';
                    this.status = res.status;
                    switch (this.stageId) {
                        case 'market':
                            this.curStep = 1;
                            break;
                        case 'deploy':
                            this.stepsData = this.modifyStepsData(res.detail.steps);
                            this.logs = res.detail.logs;
                            this.curStep = 2;
                            if (this.status === 'pending') {
                                this.setTimeFetchPluginRelease();
                            } else if (this.status === 'failed') {
                                this.failedMessage = res.fail_message;
                            } else {
                                if (this.timer) {
                                    clearTimeout(this.timer);
                                }
                            }
                            break;
                        default:
                            this.curStep = 1;
                            break;
                    }
                    console.log('this.stepsData', this.stepsData);
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
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
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
                    const stagesData = res.all_stages.map((e, i) => {
                        e.icon = i + 1;
                        e.title = e.name;
                        return e;
                    });
                    this.allStages = stagesData;
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
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
                }
            },

            modifyStepsData (data) {
                return data.map(item => {
                    console.log('satus', item.status);
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
                            message: this.$t('保存成功，请点击下一步部署!')
                        });
                        this.fetchPluginRelease();
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
            async handlerNext () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        releaseId: this.$route.query.release_id
                    };
                    const res = await this.$store.dispatch('plugin/nextRelease', params);
                    this.stageId = res.current_stage.stage_id;
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
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
                }
            },

            // 富文本编辑
            onEditorChange (e) {
                this.$set(this.form, 'description', e.html);
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
                        this.isTableLoading = false;
                        this.isLoading = false;
                    }, 200);
                }
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
.w600{
    width: 600px;
}
.btn-warp{
    margin-left: 150px;
}
.edit-form-item{
    height: 300px;
    .editor{
        height: 200px;
    }
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
</style>
