<template lang="html">
  <bk-dialog
    v-model="visible"
    theme="primary"
    :width="845"
    :mask-close="false"
    header-position="left"
    ext-cls="paasng-api-batch-renewal-dialog"
    :title="$t(title)"
    @after-leave="handleAfterLeave"
  >
    <div class="content">
      <paasng-alert>
        <div slot="title">
          {{ $t('将续期') }} <span style="color: #34d97b;">{{ renewalRows.length }}</span> {{ $t('个') }}{{ isComponent ? $t('组件API') : $t('网关API') }} {{ $t('权限') }} {{ applyRows.length > 0 ? '；' : '。' }}
          <template v-if="applyRows.length > 0">
            <span style="color: #ff5656;">{{ applyRows.length }}</span> {{ $t('个权限不可续期，无权限、权限已过期、权限大于30天不支持续期。') }}
          </template>
        </div>
      </paasng-alert>
      <div class="api-batch-apply-content">
        <bk-table
          :key="renewKey"
          :data="rows"
          :size="'small'"
          :max-height="250"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column :label="isComponent ? $t('系统') : $t('网关')">
            <template slot-scope="props">
              {{ isComponent ? props.row.system_name : props.row.api_name }}
            </template>
          </bk-table-column>
          <bk-table-column
            label="API"
            prop="name"
            :show-overflow-tooltip="true"
          />
          <bk-table-column
            :label="$t('续期前的过期时间')"
            prop="expires"
          >
            <template slot-scope="props">
              {{ getExpiredTime(props.row) }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('续期后的过期时间')"
            prop="expires"
          >
            <template slot-scope="props">
              <span
                v-if="props.row.permission_action === 'apply'"
                style="color: #ff5656;"
              > {{ $t('无权限，不可续期') }} </span>
              <span
                v-else
                style="color: #ffb400;"
              >{{ applyNewTime }}</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
      <bk-form
        :label-width="80"
        :model="formData"
        style="margin-top: 25px;"
      >
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
    import { formatDate } from '@/common/tools';
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
            title: {
                type: String,
                default: '批量续期权限'
            },
            rows: {
                type: Array,
                default: () => []
            },
            appCode: {
                type: String,
                default: ''
            },
            apiName: {
                type: String,
                default: ''
            },
            isComponent: {
                type: Boolean,
                default: false
            }
        },
        data () {
            return {
                visible: false,
                loading: false,
                formData: {
                    expired: 6
                },
                renewKey: -1,
                applyNewTime: 0
            };
        },
        computed: {
            applyRows () {
                return this.rows.filter(item => item.permission_action === 'apply');
            },
            renewalRows () {
                return this.rows.filter(item => item.permission_action === 'renew');
            }
        },
        watch: {
            show: {
                handler (value) {
                    this.visible = !!value;
                    if (this.visible) {
                        const timestamp = (new Date().getTime()) + this.formData.expired * 30 * 24 * 60 * 60 * 1000;
                        this.applyNewTime = formatDate(timestamp);
                        this.renewKey = +new Date();
                    }
                },
                immediate: true
            },
            'formData.expired' (value) {
                const timestamp = (new Date().getTime()) + value * 30 * 24 * 60 * 60 * 1000;
                this.applyNewTime = formatDate(timestamp);
                this.renewKey = +new Date();
            }
        },
        created () {
            this.curTime = new Date().getTime();
        },
        methods: {
            async handleConfirm () {
                this.loading = true;
                try {
                    const params = {
                        data: {
                            expire_days: this.formData.expired * 30
                        },
                        appCode: this.appCode
                    };
                    if (this.isComponent) {
                        params.data.component_ids = this.renewalRows.map(item => item.id);
                    } else {
                        params.data.resource_ids = this.renewalRows.map(item => item.id);
                    }
                    const methods = this.isComponent ? 'sysRenewal' : 'renewal';
                    await this.$store.dispatch(`cloudApi/${methods}`, params);
                    this.$emit('on-renewal');
                } catch (e) {
                    this.catchErrorHandler(e);
                } finally {
                    this.loading = false;
                }
            },

            getExpiredTime (payload) {
                if (!payload.expires_in) {
                    return '--';
                }
                const timestamp = this.curTime + payload.expires_in * 1000;
                return formatDate(timestamp);
            },

            computedExpires (currentExpires) {
                if (!currentExpires) {
                    return '--';
                }
                return `${Math.ceil(currentExpires / (24 * 3600))}${this.$t('天')}`;
            },

            computedExpiresAfterRenewal (currentExpires) {
                if (!currentExpires) {
                    return `${this.formData.expired * 30}${this.$t('天')}`;
                }
                return `${Math.ceil(currentExpires / (24 * 3600)) + this.formData.expired * 30}${this.$t('天')}`;
            },

            handleCancel () {
                this.visible = false;
            },

            handleAfterLeave () {
                this.formData.expired = 6;
                this.$emit('update:show', false);
                this.$emit('after-leave');
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paasng-api-batch-renewal-dialog {
        .api-batch-apply-content {
            position: relative;
            margin-top: 10px;
        }
    }
</style>
