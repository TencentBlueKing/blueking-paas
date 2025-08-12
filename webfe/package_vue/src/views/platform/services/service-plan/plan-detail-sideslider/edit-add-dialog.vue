<template>
  <bk-dialog
    v-model="dialogVisible"
    width="640"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="isAdd ? $t('添加实例') : $t('编辑实例')"
    @value-change="valueChange"
  >
    <div slot="footer">
      <bk-button
        theme="primary"
        :loading="dialogLoading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        type="submit"
        class="ml8"
        @click="dialogVisible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <div class="dialog-content">
      <bk-alert
        class="mb16"
        type="info"
        :title="
          $t('实例配置将以环境变量方式注入至应用运行时环境（每个配置项将添加 {n} 前缀，且会转换成全大写字母）', {
            n: this.data.service,
          })
        "
        closable
      ></bk-alert>
      <bk-form
        ref="formRef"
        :label-width="200"
        form-type="vertical"
      >
        <bk-form-item
          :label="$t('可回收复用')"
          :required="true"
        >
          <bk-switcher
            theme="primary"
            v-model="formData.recyclable"
          ></bk-switcher>
        </bk-form-item>
        <bk-form-item
          :label="$t('实例凭证')"
          :required="true"
          :desc="credentialDesc"
        >
          <div class="json-editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="jsonEditor"
              style="width: 100%; height: 100%"
              v-model="valuesJson"
              :debounce="20"
              :mode="'text'"
            />
          </div>
        </bk-form-item>
        <bk-form-item
          :label="`TLS ${$t('配置')}`"
          :desc="tlsDesc"
        >
          <div class="json-editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="tlsConfigEditor"
              style="width: 100%; height: 100%"
              v-model="tlsConfigJson"
              :debounce="20"
              :mode="'text'"
            />
          </div>
        </bk-form-item>
      </bk-form>
    </div>
  </bk-dialog>
</template>

<script>
import JsonEditorVue from 'json-editor-vue';
import { validateJson } from '../../validators';
export default {
  name: 'SandboxDialog',
  components: {
    JsonEditorVue,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      formData: {
        recyclable: true,
        config: {},
      },
      valuesJson: {},
      dialogLoading: false,
      // tls配置
      tlsConfigJson: {},
    };
  },
  computed: {
    dialogVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    isAdd() {
      return this.data.type === 'add';
    },
    tlsDesc() {
      return `${this.$t('配置示例')}：{ "ca": "...", "cert": "...", "key": "..." }`;
    },
    credentialDesc() {
      return `${this.$t('配置示例')}：{ "host": "127.0.0.1", "port": 6379, "password": "" }`;
    },
  },
  methods: {
    parseJsonData(data) {
      return typeof data === 'string' ? JSON.parse(data) : data;
    },
    valueChange(flag) {
      this.dialogLoading = false;
      if (flag && !this.isAdd) {
        const { row = {} } = this.data;
        this.formData.recyclable = row.config?.recyclable ?? false;
        this.valuesJson = JSON.parse(row.credentials);
        this.tlsConfigJson = row.config?.tls ? this.parseJsonData(row.config.tls) : {};
      } else {
        this.valuesJson = {};
        this.tlsConfigJson = {};
        this.formData = {
          recyclable: true,
          config: {},
        };
      }
    },
    close() {
      this.dialogVisible = false;
    },
    formatConfig() {
      const config = {};
      // 可回收复用：开启
      if (this.formData.recyclable) {
        config.recyclable = true;
      }
      const tls = this.parseJsonData(this.tlsConfigJson);
      if (Object.keys(tls || {}).length) {
        config.tls = tls;
      }
      return config;
    },
    // 确认
    handleConfirm() {
      this.$refs.formRef
        ?.validate()
        .then(() => {
          // 基础JSON校验
          const validateResult = validateJson(this.valuesJson, this.$refs.jsonEditor?.jsonEditor);
          const tlsValidateResult = validateJson(this.tlsConfigJson, this.$refs.tlsConfigEditor?.jsonEditor);
          if (!validateResult || !tlsValidateResult) {
            return;
          }
          this.dialogLoading = true;
          const params = {
            plan: this.data.planId,
            // 实例配置：JSON格式
            credentials: typeof this.valuesJson === 'object' ? JSON.stringify(this.valuesJson) : this.valuesJson,
            config: this.formatConfig(),
          };
          if (this.isAdd) {
            this.addResourcePool(params);
          } else {
            this.updateResourcePool(params);
          }
        })
        .catch((e) => {
          console.warn(e);
        });
    },
    // 添加资源池
    async addResourcePool(data, isClone = false) {
      try {
        await this.$store.dispatch('tenant/addResourcePool', {
          planId: this.data.planId,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: isClone ? this.$t('克隆成功') : this.$t('添加成功'),
        });
        this.$emit('refresh', true);
        // 关闭弹窗
        this.close();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
    // 编辑资源池
    async updateResourcePool(data) {
      try {
        const { planId, row } = this.data;
        await this.$store.dispatch('tenant/updateResourcePool', {
          planId,
          id: row.uuid,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
        this.$emit('refresh', true);
        // 关闭弹窗
        this.close();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .mb16 {
    margin-bottom: 16px;
  }
  .json-editor-wrapper {
    height: 220px;
  }
  .pt-json-editor-custom-cls .jse-main .jse-message.jse-error {
    display: none;
  }
}
</style>
