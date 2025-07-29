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
                {{ applyNewTime }}
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
        :disabled="formData.reason === ''"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        style="margin-left: 10px"
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
      applyNewTime: 0,
    };
  },
  computed: {
    // 可申请
    applyRows() {
      return this.rows.filter((item) => !item.applyDisabled);
    },
    // 可续期
    renewalRows() {
      return this.rows.filter((item) => !item.renewDisabled);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    dialogTips() {
      if (!this.applyRows.length) {
        return this.$t('您将续期 <i>{n1}</i> 个权限；', { n1: this.renewalRows.length });
      }
      return this.$t(
        '您将续期 <i>{n1}</i> 个权限；<i class="n2">{n2}</i> 个权限不可续期，API 无权限、权限已过期、权限永久有效等情况不支持续期',
        { n1: this.renewalRows.length, n2: this.applyRows.length }
      );
    },
  },
  watch: {
    show: {
      handler(value) {
        this.visible = !!value;
        if (this.visible) {
          const timestamp = new Date().getTime() + this.formData.expired * 30 * 24 * 60 * 60 * 1000;
          this.applyNewTime = formatDate(timestamp);
          this.renewKey = +new Date();
        }
      },
      immediate: true,
    },
    'formData.expired'(value) {
      const timestamp = new Date().getTime() + value * 30 * 24 * 60 * 60 * 1000;
      this.applyNewTime = formatDate(timestamp);
      this.renewKey = +new Date();
    },
  },
  created() {
    this.curTime = new Date().getTime();
  },
  methods: {
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

    getExpiredTime(payload) {
      if (!payload.expires_in) {
        return '--';
      }
      const timestamp = this.curTime + payload.expires_in * 1000;
      return formatDate(timestamp);
    },

    computedExpires(currentExpires) {
      if (!currentExpires) {
        return '--';
      }
      return `${Math.ceil(currentExpires / (24 * 3600))}${this.$t('天')}`;
    },

    computedExpiresAfterRenewal(currentExpires) {
      if (!currentExpires) {
        return `${this.formData.expired * 30}${this.$t('天')}`;
      }
      return `${Math.ceil(currentExpires / (24 * 3600)) + this.formData.expired * 30}${this.$t('天')}`;
    },

    handleCancel() {
      this.visible = false;
    },

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
