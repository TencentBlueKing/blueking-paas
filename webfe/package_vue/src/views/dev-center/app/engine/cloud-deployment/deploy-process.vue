<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-process-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="process-container">
      <div class="tab-container">
        <div class="tab-list">
          <div
            v-for="(panel, index) in panels"
            :key="index"
            class="tab-item"
            :class="[{ 'isActive': panelActive === index }]"
            @click="handlePanelClick(index, $event, 'add')"
            @mouseenter="handlePanelEnter(index)"
            @mouseleave="handlePanelLeave"
          >
            <div v-if="panel.isEdit">
              <bk-input
                ref="panelInput"
                v-model="itemValue"
                style="width: 100px"
                :placeholder="$t('进程名称')"
                ext-cls="bk-input-cls"
                @enter="handleEnter"
                @blur="handleBlur"
              />
            </div>
            <span
              v-else
              class="panel-name"
            >{{ panel.name }}</span>
            <i
              v-if="showEditIconIndex === index && !panel.isEdit"
              class="paasng-icon paasng-icon-close item-close-icon"
              @click.stop="handleDelete(index)"
            />
            <i
              v-if="showEditIconIndex === index && !panel.isEdit && panelActive !== index"
              class="paasng-icon paasng-edit2 edit-name-icon"
              @click.stop="handleIconClick(index)"
            />
          </div>
          <i
            class="paasng-icon paasng-plus-thick add-icon"
            @click="handleAddData"
          />
        </div>
      </div>
      <div class="form-deploy">
        <div
          class="create-item"
          data-test-id="createDefault_item_baseInfo"
        >
          <bk-form
            ref="formDeploy"
            :model="formData"
            :rules="rules"
            ext-cls="form-process"
          >
            <bk-form-item
              :label="$t('容器镜像地址')"
              :required="true"
              :label-width="120"
              :property="'image'"
            >
              <bk-input
                ref="mirrorUrl"
                v-model="formData.image"
                style="width: 500px;"
                :placeholder="$t('请输入带标签的镜像地址')"
              />
              <p class="whole-item-tips">
                {{ $t('示例镜像：') }}
                <span v-if="['ce', 'ee'].includes(GLOBAL.APP_VERSION)">
                  nginx:latest
                </span>
                <span v-else>
                  mirrors.tencent.com/bkpaas/django-helloworld:latest
                </span>
                &nbsp;
                <span
                  class="whole-item-tips-text"
                  @click.stop="useExample"
                >{{ $t('使用示例镜像') }}</span>
              </p>
              <p :class="['whole-item-tips', localLanguage === 'en' ? '' : 'no-wrap']">
                <span>{{ $t('镜像应监听“容器端口”处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>&nbsp;
                <a
                  target="_blank"
                  :href="GLOBAL.DOC.BUILDING_MIRRIRS_DOC"
                >{{ $t('帮助：如何构建镜像') }}</a>
              </p>
            </bk-form-item>

            <!-- 镜像凭证 -->
            <bk-form-item
              v-if="panels[panelActive]"
              :label="$t('镜像凭证')"
              :label-width="120"
              :property="'command'"
            >
              <bk-select
                v-model="bkappAnnotations[imageCrdlAnnoKey]"
                :disabled="false"
                style="width: 500px;"
                ext-cls="select-custom"
                ext-popover-cls="select-popover-custom"
                searchable
              >
                <bk-option
                  v-for="option in imageCredentialList"
                  :id="option.name"
                  :key="option.name"
                  :name="option.name"
                />
                <div
                  slot="extension"
                  style="cursor: pointer;"
                  @click="handlerCreateImageCredential"
                >
                  <i class="bk-icon icon-plus-circle mr5" />{{ $t('新建凭证') }}
                </div>
              </bk-select>
              <p class="whole-item-tips">
                {{ $t('私有镜像需要填写镜像凭证才能拉取镜像') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('启动命令')"
              :label-width="120"
              :property="'command'"
            >
              <bk-tag-input
                v-model="formData.command"
                style="width: 500px"
                ext-cls="tag-extra"
                :placeholder="$t('留空将使用镜像的默认 entry point 命令')"
                :allow-create="allowCreate"
                :allow-auto-match="true"
                :has-delete-icon="hasDeleteIcon"
                :paste-fn="copyStartMommand"
              />
              <p class="whole-item-tips">
                {{ $t('示例：start_server，多个命令可用回车键分隔') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('命令参数')"
              :label-width="120"
              :property="'args'"
            >
              <bk-tag-input
                v-model="formData.args"
                style="width: 500px"
                ext-cls="tag-extra"
                :placeholder="$t('请输入命令参数')"
                :allow-create="allowCreate"
                :allow-auto-match="true"
                :has-delete-icon="hasDeleteIcon"
                :paste-fn="copyCommandParameter"
              />
              <p class="whole-item-tips">
                {{ $t('示例：--env prod，多个参数可用回车键分隔') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('容器端口')"
              :label-width="120"
              :property="'targetPort'"
            >
              <bk-input
                v-model="formData.targetPort"
                style="width: 500px"
                :placeholder="$t('请输入 1 - 65535 的整数，非必填')"
              />
              <i
                v-show="isTargetPortErrTips"
                v-bk-tooltips.top-end="targetPortErrTips"
                class="bk-icon icon-exclamation-circle-shape tooltips-icon"
                tabindex="0"
                style="right: 8px;"
              />
              <p class="whole-item-tips">
                {{ $t('请求将会被发往容器的这个端口。推荐不指定具体端口号，让容器监听 $PORT 环境变量') }}
              </p>
            </bk-form-item>
          </bk-form>
        </div>

        <div class="form-resource">
          <div class="item-title">
            {{ $t('副本数和资源') }}
          </div>
          <bk-form
            ref="formResource"
            :model="formData"
            form-type="inline"
            style="padding-left: 30px"
          >
            <bk-form-item
              :label="$t('副本数量')"
              :required="true"
              :property="'replicas'"
              class="mb20"
              :rules="rules.replicas"
            >
              <bk-input
                v-model="formData.replicas"
                type="number"
                :max="5"
                :min="1"
                style="width: 150px"
              />
            </bk-form-item>
            <br>
            <bk-form-item
              class="pl20"
              :label="$t('内存')"
              :property="'memory'"
            >
              <bk-select
                v-model="formData.memory"
                allow-create
                :disabled="false"
                style="width: 150px;"
                searchable
              >
                <bk-option
                  v-for="option in memoryData"
                  :id="option.value"
                  :key="option.key"
                  :name="option.value"
                />
              </bk-select>
              <span class="whole-item-tips">{{ $t('每个容器能使用的最大内存') }}</span>
            </bk-form-item>
            <bk-form-item
              :label="$t('CPU(核数)')"
              :property="'cpu'"
            >
              <bk-select
                v-model="formData.cpu"
                allow-create
                :disabled="false"
                style="width: 150px;"
                searchable
              >
                <bk-option
                  v-for="option in cpuData"
                  :id="option.value"
                  :key="option.key"
                  :name="option.value"
                />
              </bk-select>
              <span class="whole-item-tips">{{ $t('每个容器能使用的CPU核心数量') }}</span>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
    </div>
  </paas-content-loader>
</template>

<script>
    import _ from 'lodash';

    export default {
        components: {
        },
        props: {
            moduleId: {
                type: String,
                default: ''
            },
            cloudAppData: {
                type: Object,
                default: {}
            }
        },
        data () {
            return {
                panels: [],
                active: 'mission',
                currentType: 'card',
                showEditIconIndex: null,
                iconIndex: '',
                panelActive: 0,
                itemValue: '',
                formData: {
                    image: '',
                    command: [],
                    args: [],
                    memory: '256Mi',
                    cpu: '500m',
                    replicas: 1,
                    targetPort: 8080
                },
                bkappAnnotations: {},
                preFormData: {
                    loaclEnabled: false,
                    command: [],
                    args: []
                },
                isEdited: false,
                command: [],
                args: [],
                allowCreate: true,
                hasDeleteIcon: true,
                processData: [],
                localCloudAppData: {},
                memoryData: [
                    { key: '256 Mi', value: '256Mi' },
                    { key: '512 Mi', value: '512Mi' },
                    { key: '1024 Mi', value: '1024Mi' }
                ],
                cpuData: [
                    { key: '500m', value: '500m' },
                    { key: '1000m', value: '1000m' },
                    { key: '2000m', value: '2000m' }
                ],
                hooks: null,
                isLoading: true,
                rules: {
                    image: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        },
                        {
                            regex: /^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$/,
                            message: this.$t('地址格式不正确'),
                            trigger: 'blur'
                        }
                    ],
                    replicas: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        },
                        {
                            min: 1,
                            message: this.$t('有效值范围1-5'),
                            trigger: 'blur'
                        },
                        {
                            max: 5,
                            message: this.$t('有效值范围1-5'),
                            trigger: 'blur'
                        }
                    ]
                },
                isBlur: true,
                imageCredential: '',
                imageCredentialList: [],
                targetPortErrTips: '',
                isTargetPortErrTips: false
            };
        },
        computed: {
            localLanguage () {
                return this.$store.state.localLanguage;
            },
            appCode () {
                return this.$route.params.id;
            },
            imageCrdlAnnoKey () {
                return `bkapp.paas.bk.tencent.com/image-credentials.${this.panels[this.panelActive].name}`;
            }
        },
        watch: {
            cloudAppData: {
                handler (val) {
                    if (val.spec) {
                        this.localCloudAppData = _.cloneDeep(val);
                        this.processData = val.spec.processes;
                        this.hooks = val.spec.hooks;
                        this.preFormData.loaclEnabled = !!this.hooks && !!(this.hooks.preRelease.command.length || this.hooks.preRelease.args.length);
                        if (this.preFormData.loaclEnabled) {
                            this.preFormData.command = (this.hooks && this.hooks.preRelease.command) || [];
                            this.preFormData.args = (this.hooks && this.hooks.preRelease.args) || [];
                        }
                        this.formData = this.processData[this.panelActive];
                        this.bkappAnnotations = this.localCloudAppData.metadata.annotations;
                    }
                    this.setPanelsData();
                },
                immediate: true
                // deep: true
            },
            formData: {
                handler (val) {
                    if (this.localCloudAppData.spec) {
                        val.name = this.panels[this.panelActive] && this.panels[this.panelActive].name;
                        val.replicas = val.replicas && Number(val.replicas);
                        if (val.targetPort && /^\d+$/.test(val.targetPort)) { // 有值且为数字字符串
                            val.targetPort = Number(val.targetPort);
                        }
                        this.$set(this.localCloudAppData.spec.processes, this.panelActive, val);
                        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                    }
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                },
                immediate: true,
                deep: true
            },
            preFormData: {
                handler (val) {
                    if (this.localCloudAppData.spec) {
                        let hooks = { preRelease: { command: val.command, args: val.args } };
                        if (!this.preFormData.loaclEnabled || (!this.preFormData.command.length && !this.preFormData.args.length)) {
                            hooks = null;
                        }
                        this.$set(this.localCloudAppData.spec, 'hooks', hooks);
                        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                    }
                },
                immediate: true,
                deep: true
            },
            'preFormData.loaclEnabled' (value) {
                if (!value) {
                    this.$set(this.localCloudAppData.spec, 'hooks', null);
                    this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                }
            },
            bkappAnnotations: {
                handler (val) {
                    if (val[this.imageCrdlAnnoKey]) {
                        this.$set(this.localCloudAppData.metadata, 'annotations', val);
                        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                    } else {
                        delete val[this.imageCrdlAnnoKey];
                    }
                },
                deep: true
            },
            'formData.targetPort' (value) {
                if (value === null || value === '') {
                    this.isTargetPortErrTips = false;
                    return false;
                }
                if (value) {
                    if (isNaN(Number(value))) {
                        this.isTargetPortErrTips = true;
                        this.targetPortErrTips = this.$t('只能输入数字');
                    } else {
                        if (!(value >= 1 && value <= 65535)) {
                            this.isTargetPortErrTips = true;
                            this.targetPortErrTips = this.$t('端口有效范围1-65535');
                        } else {
                            this.isTargetPortErrTips = false;
                        }
                    }
                }
            }
        },
        created () {
            this.getImageCredentialList();
        },
        mounted () {
            this.$refs.mirrorUrl.focus();
        },
        methods: {
            setPanelsData () {
                this.panels = this.processData.map(e => {
                    e.isEdit = false;
                    return e;
                });
            },
            handlePanelClick (i, e, isAdd) {
                this.panelActive = i;
                this.formData = this.processData[i] || {
                    name: this.itemValue,
                    image: '',
                    command: [],
                    args: [],
                    memory: '256Mi',
                    cpu: '500m',
                    replicas: 1,
                    targetPort: null
                };
                if (e && e.target === document.querySelector('.bk-input-cls input')) {
                    this.$nextTick(() => {
                        this.$set(this.panels[i], 'isEdit', true);
                    });
                } else {
                    !isAdd && this.$refs.mirrorUrl.focus();
                }
                // tab切换清除提示
                this.$refs.formDeploy.clearError();
                this.$refs.formResource.clearError();
            },
            handlePanelEnter (i) {
                if (i === 0) return;
                this.showEditIconIndex = i;
            },
            handlePanelLeave (i) {
                this.showEditIconIndex = null;
            },
            handleIconClick (i) {
                this.resetData();
                this.panels[i].isEdit = true;
                this.iconIndex = i;
                this.itemValue = this.panels[i].name;
                this.handlePanelClick(i, null, 'add');
                setTimeout(() => {
                    this.$refs.panelInput && this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
                }, 500);
            },

            // 删除item 需要重置
            handleDelete (i) {
                this.panelActive = 0;
                this.processData.splice(i, 1);
                this.setPanelsData();
                setTimeout(() => {
                    this.handlePanelClick(0);
                    this.$set(this.localCloudAppData.spec, 'processes', this.processData);
                    this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                }, 500);
            },

            // 鼠标失去焦点
            handleBlur () {
                console.log('this.panels[this.iconIndex]', this.panels[this.iconIndex]);
                if (this.panels[this.iconIndex]) { // 编辑
                    if (!this.itemValue) {
                        this.panels.splice(this.iconIndex, 1);
                    } else {
                        const canHandel = this.handleRepeatData(this.iconIndex);
                        if (!canHandel) return;
                        this.panels[this.iconIndex].name = this.itemValue;
                    }
                } else { // 新增
                    const canHandel = this.handleRepeatData();
                    if (!canHandel) return;
                    if (!this.itemValue) {
                        this.panels.splice(this.panels.length - 1, 1);
                    } else {
                        this.panels[this.panels.length - 1].name = this.itemValue;
                        this.handlePanelClick(this.panels.length - 1);
                    }
                }
                this.panels = this.panels.map(e => {
                    e.isEdit = false;
                    return e;
                });
            },

            // 处理重复添加
            handleRepeatData (index) {
                if (!this.isBlur) return;
                this.isBlur = false; // 处理enter会触发两次的bug
                let panels = this.panels;
                if (index) {
                    panels = this.panels.filter((e, i) => i !== index);
                }
                const panelName = panels.map(e => e.name);
                if (this.itemValue !== 'name' && panelName.includes(this.itemValue)) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('不允许添加同名进程')
                    });
                    setTimeout(() => {
                        this.isBlur = true;
                        this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
                    }, 100);
                    return false;
                } else {
                    setTimeout(() => {
                        this.isBlur = true;
                    }, 100);
                }
                return true;
            },

            // 处理回车
            handleEnter () {
                this.handleBlur();
            },

            // 点击icon新增数据
            handleAddData () {
                this.iconIndex = '';
                this.resetData();
                this.panels.push({
                    name: 'name',
                    isEdit: true
                });
                this.itemValue = 'name';
                this.panelActive = this.panels.length - 1;
                this.handlePanelClick(this.panelActive, null, 'add');
                setTimeout(() => {
                    this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
                }, 100);
            },

            resetData () {
                this.panels.forEach(element => {
                    element.isEdit = false;
                });
            },

            // 是否开启部署前置命令
            togglePermission () {
                this.preFormData.loaclEnabled = !this.preFormData.loaclEnabled;
            },

            async formDataValidate (index) {
                console.log('触发', index);
                try {
                  await this.$refs.formResource.validate();
                  await this.$refs.formDeploy.validate();
                  if (index) {
                      this.handlePanelValidateSwitch(index);
                  }
                  return true;
                } catch (error) {
                  console.error(error);
                  return false;
                }
            },

            // 切换至未符合规则的Panel
            handlePanelValidateSwitch (i) {
                this.panelActive = i;
                this.formData = this.localCloudAppData.spec.processes[i] || {
                    image: '',
                    command: [],
                    args: [],
                    memory: '256Mi',
                    cpu: '500m',
                    replicas: 1,
                    targetPort: 8080
                };
                this.$refs.mirrorUrl.focus();
            },

            trimStr (str) {
                return str.replace(/(^\s*)|(\s*$)/g, '');
            },

            // 启动命令复制
            copyStartMommand (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.formData.command.includes(item)) {
                        this.formData.command.push(item);
                    }
                });
                return this.formData.command;
            },

            copyCommandParameter (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.formData.args.includes(item)) {
                        this.formData.args.push(item);
                    }
                });
                return this.formData.args;
            },

            useExample () {
                if (['ce', 'ee'].includes(this.GLOBAL.APP_VERSION)) {
                    this.formData.image = 'nginx:latest';
                    this.formData.command = [];
                    this.formData.args = [];
                    this.formData.targetPort = 80;
                    return;
                }
                this.formData.image = 'mirrors.tencent.com/bkpaas/django-helloworld:latest';
                this.formData.command = ['bash', '/app/start_web.sh'];
                this.formData.args = [];
                this.formData.targetPort = 5000;
            },

            // 获取凭证列表
            async getImageCredentialList () {
                try {
                    const appCode = this.appCode;
                    const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode });
                    this.imageCredentialList = res;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                }
            },

            // 前往创建镜像凭证页面
            handlerCreateImageCredential () {
                this.$router.push({ name: 'imageCredential' });
            }
        }
    };
</script>
<style lang="scss">
    .process-container{
        margin-top: 20px;
        border: 1px solid #e6e9ea;
        border-top: none;
    }
    .tab-container {
        position: relative;
        line-height:50px;
        height: 50px;
        .tab-list {
            display: flex;
            align-items: center;
            background: #FAFBFD;
            border: 1px solid #DCDEE5;
            border-left: none;
            border-right: none;
            height: 52px;
            .tab-item{
                padding: 0 18px;
                border-right: 1px solid #dcdee5;
                cursor: pointer;
                position: relative;
            }
            .tab-item :hover {
                background: #fff;
            }
            .edit-name-icon {
                cursor: pointer;
            }
            .isActive{
                border-bottom: 2px solid #fff;
                border-top: 1px solid #dcdee5;
                background: #fff;
                color: #3a84ff;
                cursor: default;
            }
            .add-icon{
                font-size: 18px;
                padding-left: 10px;
                cursor: pointer;
            }
            .item-close-icon{
                position: absolute;
                top: 1px;
                right: 0px;
                font-size: 20px;
                color: #ea3636;
                cursor: pointer;
            }
        }
    }
    .tab-container .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item{
        padding: 0 18px;
        margin-right: 0px;
    }

    .form-deploy{
        margin: 20px 40px;
        .item-title{
            font-weight: Bold;
            font-size: 14px;
            color: #313238;
            margin: 24px 0;
        }
        .whole-item-tips{
            line-height: 26px;
            color: #979ba5;
            font-size: 12px;
            .whole-item-tips-text {
                color: #3a84ff;
                &:hover {
                    cursor: pointer;
                }
            }
        }
        .no-wrap {
            position: relative;
            width: 600px;
        }
        .create-item{
            padding-bottom: 10px;
            border-bottom: 1px solid #DCDEE5;
           .form-group-dir{
            display: flex;
            .form-label {
                color: #63656e;
                line-height: 32px;
                font-size: 14px;
                padding-top: 10px;
                width: 90px;
                text-align: right;
                margin-right: 10px;
            }
            .form-group-flex{
                width: 520px;
                margin-top: 10px;
            }
           }
        }
        .form-resource{
           .form-resource-flex{
                display: flex;
           }
        }

        .form-pre {
            border-top: 1px solid #DCDEE5;
        }

        .form-pre-command.bk-form.bk-inline-form .bk-form-input {
            height: 32px !important;
        }

        .form-process{
            width: 625px;
        }
    }
</style>
