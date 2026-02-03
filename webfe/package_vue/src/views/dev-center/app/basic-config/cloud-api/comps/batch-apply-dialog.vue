<template lang="html">
  <bk-dialog
    v-model="visible"
    theme="primary"
    :width="845"
    :mask-close="false"
    header-position="left"
    ext-cls="paasng-api-batch-apply-dialog"
    :title="$t(title)"
    @after-leave="handleAfterLeave"
  >
    <div class="content">
      <paasng-alert
        v-if="!isMcpService"
        class="mb-16"
      >
        <div slot="title">
          <span v-dompurify-html="alertTxt"></span>
          {{ renewalRows.length > 0 ? '，' : '。' }}
          <template v-if="renewalRows.length > 0">
            <span style="color: #ff9c01">{{ renewalRows.length }}</span>
            {{ $t('个网关 API 已有权限，不可重复申请。') }}
          </template>
        </div>
      </paasng-alert>
      <bk-table
        ref="batchTable"
        style="width: 100%"
        :data="rows"
        :max-height="240"
        ext-cls="batch-apply-table-cls"
      >
        <bk-table-column
          :label="getTypeLabel()"
          width="200"
        >
          <template slot-scope="{ row }">
            {{ getItemDisplayName(row) }}
          </template>
        </bk-table-column>
        <bk-table-column
          v-if="!isMcpService"
          label="API"
          width="200"
        >
          <template slot-scope="{ row }">
            {{ row.name }}
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('描述')">
          <template slot-scope="{ row }">
            <template v-if="row.permission_action === 'renew'">
              <span style="color: #ff9c01">{{ $t('已有权限，不可重复申请') }}</span>
            </template>
            <template v-else>
              {{ row.description || '--' }}
            </template>
          </template>
        </bk-table-column>
      </bk-table>
      <bk-form
        :label-width="localLanguage === 'en' ? 110 : 80"
        :model="formData"
        class="mt-24"
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
          v-if="isApplyTime"
          :label="$t('有效时间')"
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
import PaasngAlert from './paasng-alert';
import i18n from '@/language/i18n';
import { mapState } from 'vuex';

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
      default: i18n.t('批量申请权限'),
    },
    rows: {
      type: Array,
      default: () => [],
    },
    appCode: {
      type: String,
      default: '',
    },
    apiId: {
      type: [String, Number],
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
    apiType: {
      type: String,
      default: 'gateway',
      validator: (value) => ['gateway', 'component', 'mcp-service'].includes(value),
    },
    // 是否需要申请时间
    isApplyTime: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      visible: false,
      loading: false,
      formData: {
        reason: '',
        expired: 12,
      },
    };
  },
  computed: {
    ...mapState(['curUserInfo']),
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
    // 当前类型，兼容旧的 isComponent prop
    currentApiType() {
      if (this.apiType !== 'gateway') {
        return this.apiType;
      }
      return this.isComponent ? 'component' : 'gateway';
    },
    // 是否为 MCP 服务类型
    isMcpService() {
      return this.currentApiType === 'mcp-service';
    },
    alertTxt() {
      return this.$t('将申请{t} {n} 下 <i class="l1">{l}</i> 个{y}API的权限', {
        t: this.isComponent ? this.$t('系统') : this.$t('网关'),
        n: this.apiName,
        l: this.applyRows.length,
        y: this.isComponent ? this.$t('组件') : this.$t('网关'),
      });
    },
  },
  watch: {
    show: {
      handler(value) {
        this.visible = !!value;
        if (value) {
          // 弹窗显示时，延迟重新计算表格布局
          setTimeout(() => {
            this.resizeTable();
          }, 100);
        }
      },
      immediate: true,
    },
  },
  methods: {
    // 获取权限类型
    getTypeLabel() {
      const typeMap = {
        gateway: this.$t('网关'),
        component: this.$t('系统'),
        'mcp-service': 'MCP Server',
      };
      return typeMap[this.currentApiType] || this.$t('网关');
    },

    // 获取申请权限的名称
    getItemDisplayName(item) {
      switch (this.currentApiType) {
        case 'component':
          return item.system_name;
        case 'mcp-service':
          return item.name;
        case 'gateway':
        default:
          return item.api_name;
      }
    },

    // 构建申请参数
    buildApplyParams() {
      const commonData = {
        reason: this.formData.reason,
      };

      // 公共扩展参数
      const extendedData = {
        expire_days: this.formData.expired * 30,
        gateway_name: this.apiName,
      };

      // 根据不同类型构建特定参数
      const typeSpecificParams = {
        component: {
          systemId: this.apiId,
          data: {
            ...commonData,
            ...extendedData,
            component_ids: this.applyRows.map((item) => item.id),
          },
        },
        'mcp-service': {
          data: {
            ...commonData,
            mcp_server_ids: this.applyRows.map((item) => item.id),
            applied_by: this.curUserInfo.username,
          },
        },
        gateway: {
          apiId: this.apiId,
          data: {
            ...commonData,
            ...extendedData,
            resource_ids: this.applyRows.map((item) => item.id),
            grant_dimension: 'resource',
          },
        },
      };

      return {
        appCode: this.appCode,
        ...(typeSpecificParams[this.currentApiType] || typeSpecificParams.gateway),
      };
    },

    // 获取 actions name
    getDispatchMethod() {
      const methodMap = {
        component: 'sysApply',
        gateway: 'apply',
        'mcp-service': 'applyMcpServerPermission',
      };
      return methodMap[this.currentApiType] || 'apply';
    },

    // 重新计算表格布局
    resizeTable() {
      this.$refs.batchTable?.doLayout();
    },

    // 确认申请
    async handleConfirm() {
      this.loading = true;
      try {
        const params = this.buildApplyParams();
        const method = this.getDispatchMethod();
        await this.$store.dispatch(`cloudApi/${method}`, params);
        this.$emit('on-apply');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
      }
    },

    handleCancel() {
      this.visible = false;
    },

    handleAfterLeave() {
      this.formData = Object.assign(
        {},
        {
          reason: '',
          expired: 6,
        }
      );
      this.$emit('update:show', false);
      this.$emit('after-leave');
    },
  },
};
</script>
<style lang="scss">
.paasng-api-batch-apply-dialog {
  .l1 {
    color: #2dcb56;
    font-style: normal;
  }
  .batch-apply-table-cls {
    .bk-table-empty-block {
      height: 180px;
    }
  }
}
</style>
