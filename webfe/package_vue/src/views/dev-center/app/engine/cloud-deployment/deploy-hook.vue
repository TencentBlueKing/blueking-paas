<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-hook-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="form-pre">
      <div class="item-title-container">
        <div class="item-title">
          {{ $t('部署前置命令') }}
        </div>
        <div>
          <div
            class="ps-switcher-wrapper mr10"
            @click="togglePermission"
          >
            <bk-switcher
              v-model="preFormData.loaclEnabled"
            />
          </div>
          <span>{{ preFormData.loaclEnabled ? $t('已启用') : $t('未启用') }}</span>
        </div>
      </div>
      <bk-form
        v-if="preFormData.loaclEnabled"
        :model="preFormData"
        class="info-special-form form-pre-command"
      >
        <div class="item-info">
          {{ $t('容器镜像地址') }} <i
            v-bk-tooltips="cloudInfoTip"
            class="paasng-icon paasng-info-circle"
          />：
          {{ processData[0].image }}
        </div>
        <bk-form-item
          :label="$t('启动命令')"
          class="pt20"
          style="width: 510px; position:relative; margin-left: 5px"
        >
          <bk-tag-input
            v-model="preFormData.command"
            style="width: 500px"
            :placeholder="$t('请输入启动命令')"
            :allow-create="allowCreate"
            :allow-auto-match="true"
            :has-delete-icon="hasDeleteIcon"
            :paste-fn="copyCommand"
          />
          <span class="whole-item-tips">{{ $t('该命令使用web进程的配置，在每次部署前执行。如需执行多条命令请将其封装在一个脚本中，') }} ./bin/pre-task.sh</span>
        </bk-form-item>
        <bk-form-item
          :label="$t('命令参数')"
          class="pt20"
          style="width: 510px; position:relative; margin-left: 5px;"
        >
          <bk-tag-input
            v-model="preFormData.args"
            style="width: 500px"
            ext-cls="tag-extra"
            :placeholder="$t('请输入命令参数')"
            :allow-create="allowCreate"
            :allow-auto-match="true"
            :has-delete-icon="hasDeleteIcon"
            :paste-fn="copyCommandParameter"
          />
        </bk-form-item>
      </bk-form>
    </div>
  </paas-content-loader>
</template>

<script>
    import _ from 'lodash';
    import i18n from '@/language/i18n.js';

    export default {
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
                preFormData: {
                    loaclEnabled: false,
                    command: [],
                    args: []
                },
                allowCreate: true,
                hasDeleteIcon: true,
                isLoading: true,
                localCloudAppData: {},
                hooks: null,
                processData: [],
                cloudInfoTip: i18n.t('web进程的容器镜像地址')
            };
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
                    }
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                },
                immediate: true
                // deep: true
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
            }
        },

        methods: {
            // 是否开启部署前置命令
            togglePermission () {
                this.preFormData.loaclEnabled = !this.preFormData.loaclEnabled;
            },

            trimStr (str) {
                return str.replace(/(^\s*)|(\s*$)/g, '');
            },

            copyCommand (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.preFormData.command.includes(item)) {
                        this.preFormData.command.push(item);
                    }
                });
                return this.preFormData.command;
            },

            copyCommandParameter (val) {
                const value = this.trimStr(val);
                if (!value) {
                    this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
                    return [];
                }
                const commandArr = value.split(',');
                commandArr.forEach(item => {
                    if (!this.preFormData.args.includes(item)) {
                        this.preFormData.args.push(item);
                    }
                });
                return this.preFormData.args;
            },

            // tab不在当前项进行发布，校验调用防止警告
            formDataValidate (index) {
                if (index) {
                    return false;
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .form-pre {
        padding: 20px;
        min-height: 300px;
        width: 800px;

        .item-title-container{
            display: flex;
            align-items: center;
            margin-top: 24px;
        }

        .item-title{
            font-weight: Bold;
            font-size: 14px;
            color: #313238;
        }

        .item-info{
            font-size: 14px;
            color: #313238;
            margin: 24px 0 0 30px;
        }

        .whole-item-tips {
            line-height: 26px;
            color: #979ba5;
            font-size: 12px;
        }
    }

    .info-special-form.bk-form.bk-inline-form {
        width: auto;
    }

    .form-pre-command.bk-form.bk-inline-form .bk-form-input {
        height: 32px !important;
    }
</style>
