<template>
  <div>
    <bk-sideslider
      :is-show.sync="visible"
      :width="800"
      quick-close
      show-mask
    >
      <div slot="header" class="keys-header">
        <span>API Keys</span>
        <span class="keys-subtitle">{{ $t('用于创建和管理沙箱实例的唯一凭证') }}</span>
      </div>
      <div
        slot="content"
        class="p-24"
      >
        <div class="keys-toolbar">
          <bk-button
            theme="primary"
            :disabled="createEntryDisabled"
            @click="openCreate"
          >
            {{ $t('创建 API Key') }}
          </bk-button>
          <bk-button
            v-if="showGuide"
            class="back-guide"
            theme="primary"
            text
            @click="$emit('guide')"
          >
            {{ $t('返回接入示例') }}
          </bk-button>
        </div>
        <bk-table
          v-bkloading="{ isLoading: loading, zIndex: 10 }"
          :data="keys"
          :outer-border="false"
        >
          <bk-table-column
            :label="$t('名称')"
            min-width="110"
            show-overflow-tooltip
          >
            <template slot-scope="{ row }">{{ displayValue(row.name) }}</template>
          </bk-table-column>
          <bk-table-column
            label="API Key"
            min-width="160"
          >
            <template slot-scope="{ row }">
              <span
                v-bk-tooltips="$t('完整内容仅在创建时显示一次，无法再次查看。')"
                class="api-key-preview"
              >
                {{ row.key_prefix }}<span class="api-key-mask">••••••••</span>
              </span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('签发时间')"
            prop="created"
            min-width="120"
          >
            <template slot-scope="{ row }">
              <span v-bk-tooltips="displayValue(row.created)">{{ formatRelativeTime(row.created) }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('签发人')"
            min-width="100"
            show-overflow-tooltip
          >
            <template slot-scope="{ row }"><user-display :value="row.owner" /></template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            width="80"
          >
            <template slot-scope="{ row }">
              <bk-button
                theme="primary"
                text
                :disabled="revoking || creating"
                @click="confirmRevoke(row)"
              >
                {{ $t('删除') }}
              </bk-button>
            </template>
          </bk-table-column>
          <table-empty
            slot="empty"
            :is-error="isError"
            :explanation="errorMessage"
            @reacquire="loadKeys"
          />
        </bk-table>
      </div>
    </bk-sideslider>

    <bk-dialog
      v-model="createVisible"
      :title="$t('创建 API Key')"
      :width="520"
      :mask-close="false"
      :close-icon="!creating"
      :esc-close="!creating"
    >
      <bk-form
        ref="createForm"
        form-type="vertical"
        :model="form"
        :rules="createRules"
      >
        <bk-form-item
          :label="$t('名称')"
          :required="true"
          property="name"
          error-display-type="normal"
        >
          <bk-input
            v-model="form.name"
            :maxlength="nameMaxLength"
            :disabled="creating"
            :placeholder="$t('请输入名称，最多 64 个字符')"
          />
        </bk-form-item>
      </bk-form>
      <div slot="footer">
        <bk-button
          theme="primary"
          :loading="creating"
          :disabled="submitDisabled"
          @click="createKey"
        >
          {{ $t('创建') }}
        </bk-button>
        <bk-button
          :disabled="creating"
          @click="createVisible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="secretVisible"
      :title="$t('创建 API Key')"
      :width="680"
      :mask-close="false"
    >
      <div
        slot="header"
        class="secret-title"
      >
        {{ $t('创建 API Key') }}
      </div>
      <div v-if="secretVisible">
        <bk-alert
          class="secret-alert"
          type="success"
          :show-icon="false"
        >
          <div
            slot="title"
            class="secret-success-message"
          >
            <i class="paasng-icon paasng-pass" aria-hidden="true" />
            {{ $t('API Key 创建成功！请复制该 API Key，关闭弹窗后将无法再次看到它。') }}
          </div>
        </bk-alert>
        <p class="secret-label">API Key</p>
        <div class="secret-key">
          <span class="secret-value">{{ rawKey }}</span>
          <bk-button
            v-copy="rawKey"
            class="secret-copy"
            theme="primary"
            text
          >
            <i class="paasng-icon paasng-general-copy" aria-hidden="true" />
            {{ $t('复制') }}
          </bk-button>
        </div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          @click="clearSecret"
        >
          {{ $t('我已复制') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import UserDisplay from '@/components/user/user-display.vue';
import { displayValue, formatRelativeTime } from '../format';
import { getErrorMessage, isEmptyResponse } from '../utils';

// 单个应用允许持有的 API Key 上限
const MAX_KEY_COUNT = 5;
// API Key 名称长度上限
const NAME_MAX_LENGTH = 64;

export default {
  name: 'SandboxApiKeys',
  components: { UserDisplay },
  props: {
    appCode: {
      type: String,
      required: true,
    },
    showGuide: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      visible: false,
      keys: [],
      loading: false,
      isError: false,
      errorMessage: '',
      createVisible: false,
      form: { name: '' },
      createRules: {
        name: [
          {
            required: true,
            validator: value => Boolean(value.trim()),
            message: this.$t('名称不能为空'),
            trigger: 'blur',
          },
        ],
      },
      creating: false,
      secretVisible: false,
      rawKey: '',
      revokeDialog: null,
      keyToRevoke: null,
      revoking: false,
      contextVersion: 0,
      listRequestId: 0,
    };
  },
  computed: {
    nameMaxLength() {
      return NAME_MAX_LENGTH;
    },
    // 列表不可用（加载中或加载失败）时不允许创建
    listUnavailable() {
      return this.loading || this.isError;
    },
    reachedKeyLimit() {
      return this.keys.length >= MAX_KEY_COUNT;
    },
    createEntryDisabled() {
      return this.listUnavailable || this.reachedKeyLimit || this.creating;
    },
    submitDisabled() {
      return this.listUnavailable || this.reachedKeyLimit || this.form.name.length > NAME_MAX_LENGTH;
    },
  },
  watch: {
    visible(value) {
      if (!value) {
        this.invalidate();
        this.$emit('close');
      }
    },
    secretVisible(value) {
      if (!value) {
        this.rawKey = '';
      }
    },
    appCode() {
      this.invalidate();
      this.$emit('close');
    },
  },
  mounted() {
    this.visible = true;
    this.loadKeys();
  },
  beforeDestroy() {
    this.invalidate();
  },
  methods: {
    displayValue,
    formatRelativeTime,
    isCurrent(appCode, version) {
      return this.visible && this.appCode === appCode && this.contextVersion === version;
    },
    invalidate() {
      this.contextVersion += 1;
      this.clearSecret();
      this.createVisible = false;
      this.revokeDialog?.close();
      this.revokeDialog = null;
      this.keyToRevoke = null;
      this.keys = [];
    },
    clearSecret() {
      this.rawKey = '';
      this.secretVisible = false;
    },
    showError(error) {
      if (error.status === 401 || error.status === 403) {
        return;
      }
      this.$paasMessage({
        theme: 'error',
        message: getErrorMessage(error, this.$t('接口异常')),
      });
    },
    async loadKeys() {
      const { appCode, contextVersion } = this;
      this.listRequestId += 1;
      const requestId = this.listRequestId;
      this.loading = true;
      this.isError = false;
      this.errorMessage = '';
      try {
        const data = await this.$store.dispatch('agentSandbox/listApiKeys', { appCode });
        if (!this.isCurrent(appCode, contextVersion) || requestId !== this.listRequestId) {
          return;
        }
        if (!Array.isArray(data)) {
          this.isError = true;
          this.keys = [];
          return;
        }
        this.keys = data;
      } catch (error) {
        if (this.isCurrent(appCode, contextVersion) && requestId === this.listRequestId) {
          this.keys = [];
          this.isError = true;
          this.errorMessage = getErrorMessage(error, this.$t('接口异常'));
        }
      } finally {
        if (this.isCurrent(appCode, contextVersion) && requestId === this.listRequestId) {
          this.loading = false;
        }
      }
    },
    openCreate() {
      this.form.name = '';
      this.createVisible = true;
      this.$nextTick(() => {
        this.$refs.createForm.clearError();
      });
    },
    async createKey() {
      if (this.creating || this.submitDisabled) {
        return;
      }
      const { appCode, contextVersion } = this;
      this.creating = true;
      try {
        const valid = await this.$refs.createForm.validate().then(() => true, () => false);
        if (!valid || !this.isCurrent(appCode, contextVersion) || !this.createVisible) {
          return;
        }
        const data = await this.$store.dispatch('agentSandbox/createApiKey', {
          appCode,
          name: this.form.name,
        });
        if (!this.isCurrent(appCode, contextVersion)) {
          return;
        }
        if (!data || typeof data.api_key !== 'string' || !data.api_key) {
          return;
        }
        this.createVisible = false;
        this.rawKey = data.api_key;
        this.secretVisible = true;
        this.loadKeys();
      } catch (error) {
        if (this.isCurrent(appCode, contextVersion)) {
          this.showError(error);
          if (error.code === 'AGENT_SANDBOX_E2B_API_KEY_QUOTA_EXCEEDED') {
            this.loadKeys();
          }
        }
      } finally {
        if (this.isCurrent(appCode, contextVersion)) {
          this.creating = false;
        }
      }
    },
    confirmRevoke(key) {
      if (this.revoking || this.revokeDialog) {
        return;
      }
      this.keyToRevoke = key;
      this.revokeDialog = this.$bkInfo({
        type: 'warning',
        width: 480,
        title: this.$t('确认删除该 API Key？'),
        subTitle: this.$t('删除后无法恢复，使用该 API Key 的请求将立即被拒绝。'),
        okText: this.$t('确定'),
        cancelText: this.$t('取消'),
        maskClose: false,
        confirmLoading: true,
        confirmFn: this.revokeKey,
        afterLeaveFn: (dialog) => {
          if (this.revokeDialog === dialog) {
            this.revokeDialog = null;
            this.keyToRevoke = null;
          }
        },
      });
    },
    async revokeKey() {
      if (this.revoking || !this.keyToRevoke) {
        return false;
      }
      const { appCode, contextVersion } = this;
      const { uuid } = this.keyToRevoke;
      this.revoking = true;
      this.revokeDialog.escClose = false;
      try {
        const data = await this.$store.dispatch('agentSandbox/revokeApiKey', { appCode, uuid });
        if (!this.isCurrent(appCode, contextVersion) || !isEmptyResponse(data)) {
          return false;
        }
        this.$paasMessage({ theme: 'success', message: this.$t('删除成功') });
        this.loadKeys();
        return true;
      } catch (error) {
        if (this.isCurrent(appCode, contextVersion)) {
          this.showError(error);
          if (error.status === 404) {
            this.loadKeys();
            return true;
          }
        }
        return false;
      } finally {
        if (this.isCurrent(appCode, contextVersion)) {
          this.revoking = false;
          if (this.revokeDialog) {
            this.revokeDialog.escClose = true;
          }
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.keys-header {
  display: flex;
  align-items: center;
  height: 100%;
}
.keys-subtitle {
  margin-left: 12px;
  padding-left: 12px;
  border-left: 1px solid #dcdee5;
  color: #979ba5;
  font-size: 12px;
  line-height: 16px;
}
.keys-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.back-guide {
  margin-left: auto;
}
.api-key-preview {
  white-space: nowrap;
  cursor: help;
}
.api-key-mask {
  margin-left: 2px;
  color: #c4c6cc;
}
.secret-title {
  color: #313238;
  font-size: 20px;
  line-height: 28px;
  text-align: left;
}
.secret-alert {
  margin: 8px 0 24px;
}
.secret-success-message {
  display: flex;
  align-items: center;
  gap: 4px;
  line-height: 16px;
  .paasng-pass {
    color: #2dcb56;
  }
}
.secret-label {
  margin: 0 0 6px;
  line-height: 22px;
}
.secret-key {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 40px;
  padding: 9px 10px;
  border-radius: 2px;
  background: #e1ecff;
  color: #313238;
  line-height: 22px;
}
.secret-value {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.secret-copy {
  flex-shrink: 0;
  height: auto;
  line-height: 22px;
}
</style>
