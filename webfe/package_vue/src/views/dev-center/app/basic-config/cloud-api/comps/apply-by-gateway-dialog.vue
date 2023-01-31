<template lang="html">
  <bk-dialog
    v-model="visible"
    theme="primary"
    :width="845"
    :mask-close="false"
    header-position="left"
    ext-cls="paasng-by-gateway-apply-dialog"
    :title="$t('按网关申请权限')"
    @after-leave="handleAfterLeave"
  >
    <div class="content">
      <paasng-alert :title="`${$t('将申请网关')} ${apiName} ${$t('下所有API的权限，包括未来新创建的API。')}`" />
      <bk-form
        :label-width="80"
        :model="formData"
        style="margin-top: 25px;"
      >
        <bk-form-item
          :label="$t('申请理由')"
          required
          property="reason"
        >
          <bk-input
            v-model="formData.reason"
            type="textarea"
            :maxlength="120"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('有效时间')"
          required
          property="expired"
        >
          <div class="bk-button-group bk-button-group-cls">
            <bk-button
              :class="formData.expired === 6 ? 'is-selected' : ''"
              @click="formData.expired = 6"
            >
              {{ $t('6个月') }}
            </bk-button>
            <bk-button
              :class="formData.expired === 12 ? 'is-selected' : ''"
              @click="formData.expired = 12"
            >
              {{ $t('12个月') }}
            </bk-button>
          </div>
        </bk-form-item>
      </bk-form>
    </div>
    <template slot="footer">
      <bk-button
        theme="primary"
        :disabled="formData.reason === ''"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        style="margin-left: 10px;"
        @click="handleCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </template>
  </bk-dialog>
</template>
<script>
    import PaasngAlert from './paasng-alert';
    export default {
        name: '',
        components: {
            PaasngAlert
        },
        props: {
            show: {
                type: Boolean,
                default: false
            },
            appCode: {
                type: String,
                default: ''
            },
            apiId: {
                type: [String, Number],
                default: ''
            },
            apiName: {
                type: String,
                default: ''
            }
        },
        data () {
            return {
                visible: false,
                loading: false,
                formData: {
                    reason: '',
                    expired: 6
                }
            };
        },
        watch: {
            show: {
                handler (value) {
                    this.visible = !!value;
                },
                immediate: true
            }
        },
        methods: {
            async handleConfirm () {
                this.loading = true;
                try {
                    const params = {
                        data: {
                            resource_ids: [],
                            reason: this.formData.reason,
                            expire_days: this.formData.expired * 30,
                            grant_dimension: 'api',
                            gateway_name: this.apiName
                        },
                        appCode: this.appCode,
                        apiId: this.apiId
                    };
                    await this.$store.dispatch('cloudApi/apply', params);
                    this.$emit('on-api-apply');
                } catch (e) {
                    this.catchErrorHandler(e);
                } finally {
                    this.loading = false;
                }
            },

            handleCancel () {
                this.visible = false;
            },

            handleAfterLeave () {
                this.formData = Object.assign({}, {
                    reason: '',
                    expired: 6
                });
                this.$emit('update:show', false);
                this.$emit('after-leave');
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paasng-by-gateway-apply-dialog {}
</style>
