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
          <div
            v-dompurify-html="dialogTips"
            class="renew-tips-container"
          ></div>
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
              {{ isComponent ? props.row.system_name : props.row.gateway_name }}
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
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ getExpiredTime(props.row) }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('续期后的过期时间')"
            prop="expires"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <span style="color: #ffb400">
                {{ getExpiredTimeAfterRenewal(props.row) }}
              </span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
      <bk-form
        :label-width="localLanguage === 'en' ? 110 : 80"
        :model="formData"
        style="margin-top: 25px"
      >
        <bk-form-item
          :label="$t('授权期限')"
          required
          property="expired"
        >
          <bk-radio-group v-model="formData.expired">
            <bk-radio-button :value="6">
              {{ $t('6个月') }}
            </bk-radio-button>
            <bk-radio-button :value="12">
              {{ $t('12个月') }}
            </bk-radio-button>
            <bk-radio-button :value="0">
              {{ $t('永久') }}
            </bk-radio-button>
          </bk-radio-group>
        </bk-form-item>
      </bk-form>
    </div>
    <template slot="footer">
      <bk-button
        theme="primary"
        :disabled="!renewalRows.length"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        style="margin-left: 10px"
        @click="visible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </template>
  </bk-dialog>
</template>
<script>
import { mapState } from 'vuex';
import { formatDate } from '@/common/tools';
import PaasngAlert from './paasng-alert';
import i18n from '@/language/i18n';
export default {
  name: '',
  components: {
    PaasngAlert,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: i18n.t('批量续期权限'),
    },
    rows: {
      type: Array,
      default: () => [],
    },
    appCode: {
      type: String,
      default: '',
    },
    apiName: {
      type: String,
      default: '',
    },
    isComponent: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      visible: false,
      loading: false,
      formData: {
        expired: 12,
      },
      renewKey: -1,
    };
  },
  computed: {
    ...mapState(['localLanguage']),
    // 可续期
    renewalRows() {
      return this.rows.filter((item) => !item.renewDisabled);
    },
    // 不可续期
    unavailableRows() {
      return this.rows.filter((item) => item.renewDisabled);
    },
    dialogTips() {
      if (!this.unavailableRows.length) {
        return this.$t('您将续期 <i>{n1}</i> 个权限；', { n1: this.renewalRows.length });
      }
      return this.$t(
        '您将续期 <i>{n1}</i> 个权限；<i class="n2">{n2}</i> 个权限不可续期，API 无权限、权限永久有效等情况不支持续期',
        { n1: this.renewalRows.length, n2: this.unavailableRows.length }
      );
    },
  },
  watch: {
    show: {
      handler(value) {
        this.visible = !!value;
        if (this.visible) {
          this.curTime = new Date().getTime();
          this.renewKey = +new Date();
        }
      },
      immediate: true,
    },
    'formData.expired'() {
      this.renewKey = +new Date();
    },
  },
  created() {
    this.curTime = new Date().getTime();
  },
  methods: {
    /**
     * 提交续期申请：仅提交可续期的权限，网关 API 与组件 API 使用不同的 ID 字段。
     */
    async handleConfirm() {
      this.loading = true;
      try {
        const params = {
          data: {
            expire_days: this.formData.expired * 30,
          },
          appCode: this.appCode,
        };
        if (this.isComponent) {
          params.data.component_ids = this.renewalRows.map((item) => item.id);
        } else {
          params.data.resource_ids = this.renewalRows.map((item) => item.id);
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

    /**
     * 获取续期前的过期时间，expires_in 为基于当前时间的剩余秒数。
     */
    getExpiredTime(payload) {
      if (!payload.expires_in) {
        return '--';
      }
      const timestamp = this.curTime + payload.expires_in * 1000;
      return formatDate(timestamp);
    },

    /**
     * 获取续期后的过期时间：未过期权限基于原过期时间续期，已过期权限基于当前时间续期。
     */
    getExpiredTimeAfterRenewal(payload) {
      if (payload.renewDisabled) {
        return '--';
      }
      if (this.formData.expired === 0) {
        return this.$t('永久');
      }
      const renewalDuration = this.formData.expired * 30 * 24 * 60 * 60 * 1000;
      const expiresIn = Number(payload.expires_in);
      const baseTime =
        payload.permission_status === 'expired' || !expiresIn || expiresIn <= 0
          ? this.curTime
          : this.curTime + expiresIn * 1000;
      return formatDate(baseTime + renewalDuration);
    },

    /**
     * 将剩余秒数转换为剩余天数文案。
     */
    computedExpires(currentExpires) {
      if (!currentExpires) {
        return '--';
      }
      return `${Math.ceil(currentExpires / (24 * 3600))}${this.$t('天')}`;
    },

    /**
     * 将续期后的剩余秒数转换为剩余天数文案。
     */
    computedExpiresAfterRenewal(currentExpires) {
      if (!currentExpires) {
        return `${this.formData.expired * 30}${this.$t('天')}`;
      }
      return `${Math.ceil(currentExpires / (24 * 3600)) + this.formData.expired * 30}${this.$t('天')}`;
    },

    /**
     * 弹窗关闭后重置表单状态，并通知父组件清理弹窗数据。
     */
    handleAfterLeave() {
      this.formData.expired = 6;
      this.$emit('update:show', false);
      this.$emit('after-leave');
    },
  },
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
<style lang="scss">
.renew-tips-container {
  i {
    font-style: normal;
    color: #34d97b;
  }
  .n2 {
    color: #ff5656;
  }
}
</style>
