<template>
  <div>
    <bk-dialog
      v-model="versionDialogConf.visiable"
      :title="versionDialogConf.title"
      header-position="center"
      :width="600"
      @after-leave="handleCancel"
    >
      <bk-form
        ref="versionForm"
        class="mt20 mb10"
        style="width: 540px;"
        :label-width="80"
        :model="voucherParams"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('名称')"
          :required="true"
          :property="'name'"
        >
          <bk-input
            v-model="voucherParams.name"
            :placeholder="$t('以英文字母、数字或下划线(_)组成，不超过40个字')"
            :disabled="type === 'edit'"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('账号')"
          :required="true"
          :property="'username'"
        >
          <bk-input
            v-model="voucherParams.username"
            :placeholder="$t('请输入')"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('密码')"
          :required="true"
          :property="'password'"
        >
          <bk-input
            v-model="voucherParams.password"
            ext-cls="passwordEl"
            type="password"
            :placeholder="$t('请输入')"
            autocomplete="off"
          />
          <!-- <p v-else>******</p> -->
        </bk-form-item>
        <bk-form-item
          :label="$t('描述')"
          :property="'description'"
        >
          <bk-input
            v-model="voucherParams.description"
            type="textarea"
            :placeholder="$t('描述')"
          />
        </bk-form-item>
      </bk-form>
      <div slot="footer">
        <bk-button
          class="mr15"
          theme="primary"
          :loading="versionDialogConf.loading"
          @click="handleCreate"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button @click="handleCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
    import i18n from '@/language/i18n.js';
    export default {
        props: {
            config: {
                type: Object,
                default: () => {}
            },
            type: {
                type: String,
                default: 'new'
            },
            voucherDetail: {
                type: Object,
                default: () => {}
            }
        },
        data () {
            return {
                isDataLoading: false,
                voucherParams: {
                    name: '',
                    username: '',
                    password: '',
                    description: ''
                },
                versionDialogConf: {
                    loading: false,
                    visiable: false,
                    title: i18n.t('新增凭证')
                },
                isShowPassword: false,
                rules: {
                    name: [
                        {
                            required: true,
                            message: i18n.t('请填写名称'),
                            trigger: 'blur'
                        },
                        {
                            regex: /^[a-zA-Z0-9_]{0,40}$|^$/,
                            message: i18n.t('以英文字母、数字或下划线(_)组成，不超过40个字'),
                            trigger: 'blur'
                        }
                    ],
                    username: [
                        {
                            required: true,
                            message: i18n.t('该字段不能为空'),
                            trigger: 'blur'
                        }
                    ],
                    password: [
                        {
                            required: true,
                            message: i18n.t('该字段不能为空'),
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },

        computed: {
            appCode () {
                return this.$route.params.id;
            }
        },

        watch: {
            type (newVal) {
                this.type = newVal;
            },
            voucherDetail (newVal) {
                if (Object.keys(newVal).length) {
                    this.voucherParams = newVal;
                }
            }
        },

        created () {
            this.init();
        },

        mounted () {
            this.setAutocomplete();
        },

        methods: {
            init () {
                this.versionDialogConf = this.config;
            },

            // 新增凭证
            handleCreate () {
                // 表单校验，通过传递数据
                this.$refs.versionForm.validate().then(validator => {
                    if (this.type === 'new') {
                        this.$emit('confirm', this.voucherParams);
                    } else {
                        this.$emit('updata', this.voucherParams);
                    }
                }, err => {
                    return err;
                });
            },

            handleCancel () {
                this.voucherParams = {
                    name: '',
                    username: '',
                    password: '',
                    description: ''
                };
                this.$refs.versionForm.clearError();
                this.$emit('close', false);
            },

            handleSubmitVoucher () {
                this.isShowPassword = !this.isShowPassword;
            },

            setAutocomplete () {
                document.querySelector('.passwordEl input').setAttribute('autocomplete', 'off');
            }
        }
    };
</script>

<style scoped lang="postcss">

</style>
