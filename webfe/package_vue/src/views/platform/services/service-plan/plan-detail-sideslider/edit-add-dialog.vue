<template>
  <bk-dialog
    v-model="dialogVisible"
    width="640"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    ext-cls="resource-pool-dialog"
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
      <bk-form
        ref="formRef"
        form-type="vertical"
        :model="formData"
        :rules="formRules"
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

        <!-- 配置项标题 -->
        <div class="section-title">{{ $t('配置项') }}</div>

        <!-- 根据 service_config.config_items 动态生成配置项 -->
        <bk-form-item
          v-for="item in configItems"
          :key="item.key"
          :label="item.key"
          :required="item.required"
          :property="`configValues.${item.key}`"
        >
          <bk-switcher
            v-if="item.type === 'boolean' || item.type === 'bool'"
            theme="primary"
            v-model="formData.configValues[item.key]"
          ></bk-switcher>
          <!-- 数字类型：使用 input type=number -->
          <bk-input
            v-else-if="item.type === 'integer' || item.type === 'number'"
            v-model="formData.configValues[item.key]"
            type="number"
            :placeholder="item.example ? `${$t('示例')}：${item.example}` : $t('请输入')"
          ></bk-input>
          <!-- 字符串类型：使用 input，带示例 placeholder -->
          <bk-input
            v-else
            v-model="formData.configValues[item.key]"
            :placeholder="item.example ? `${$t('示例')}：${item.example}` : $t('请输入')"
          ></bk-input>
        </bk-form-item>

        <!-- TLS 配置（仅当 service_config.tls 为 true 时显示） -->
        <template v-if="showTlsConfig">
          <div class="section-title">{{ $t('TLS 配置') }}</div>
          <bk-form-item
            label="ca"
            :required="true"
            property="tlsConfig.ca"
          >
            <TextareaUpload
              v-model="formData.tlsConfig.ca"
              :placeholder="$t('请输入')"
              :tip="$t('支持扩展名：.key .pem .txt .yaml')"
            />
          </bk-form-item>
          <bk-form-item
            label="cert"
            :required="true"
            property="tlsConfig.cert"
          >
            <TextareaUpload
              v-model="formData.tlsConfig.cert"
              :placeholder="$t('请输入')"
              :tip="$t('支持扩展名：.key .pem .txt .yaml')"
            />
          </bk-form-item>
          <bk-form-item
            label="key"
            :required="true"
            property="tlsConfig.key"
          >
            <TextareaUpload
              v-model="formData.tlsConfig.key"
              :placeholder="$t('请输入')"
              :tip="$t('支持扩展名：.key .pem .txt .yaml')"
            />
          </bk-form-item>
          <!-- insecure_skip_verify -->
          <bk-form-item
            label="insecure_skip_verify"
            :required="false"
          >
            <bk-switcher
              theme="primary"
              v-model="formData.tlsConfig.insecure_skip_verify"
            ></bk-switcher>
          </bk-form-item>
        </template>

        <!-- 预览环境变量（可折叠） -->
        <EnvPreview
          :template="envTemplate"
          :config-values="formData.configValues"
          :service-name="data.service || ''"
        />

        <!-- 分配方式 -->
        <bk-form-item
          :label="$t('分配方式')"
          :required="true"
        >
          <SwitchDisplay
            class="switch-cls"
            :list="methodList"
            :active="methodValue"
            @change="handlerChange"
          >
            <template #default="{ item }">
              <i
                v-if="item.name === methodValue"
                class="paasng-icon paasng-app-store"
              ></i>
              <span>{{ item.label }}</span>
            </template>
          </SwitchDisplay>
          <bk-alert
            v-if="methodValue === 'uniform'"
            class="mt-16"
            type="info"
            :title="$t('应用申请增强服务实例时，按 FIFO（先进先出）顺序分配。')"
          ></bk-alert>
          <RuleBasedForm
            ref="ruleBasedForm"
            v-else
          />
        </bk-form-item>
      </bk-form>
    </div>
  </bk-dialog>
</template>

<script>
import SwitchDisplay from '@/components/switch-display';
import RuleBasedForm from './rule-based-form.vue';
import EnvPreview from './env-preview.vue';
import TextareaUpload from './textarea-upload.vue';

export default {
  name: 'EditAddDialog',
  components: {
    SwitchDisplay,
    RuleBasedForm,
    EnvPreview,
    TextareaUpload,
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
    // 服务配置信息
    serviceConfig: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      formData: {
        recyclable: true,
        configValues: {},
        tlsConfig: {
          ca: '',
          cert: '',
          key: '',
          insecure_skip_verify: false,
        },
      },
      dialogLoading: false,
      methodList: [
        { name: 'uniform', label: this.$t('按顺序分配') },
        { name: 'rule_based', label: this.$t('按规则分配'), icon: 'paasng-grid' },
      ],
      methodValue: 'uniform',
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
    // 配置项列表
    configItems() {
      return this.serviceConfig?.config_items || [];
    },
    // 是否显示 TLS 配置
    showTlsConfig() {
      return this.serviceConfig?.tls === true;
    },
    // 环境变量模板
    envTemplate() {
      return this.serviceConfig?.template || [];
    },
    // 动态生成表单校验规则
    formRules() {
      const rules = {};
      // 配置项校验
      this.configItems.forEach((item) => {
        if (item.required) {
          rules[`configValues.${item.key}`] = [
            {
              required: true,
              message: this.$t('必填项'),
              trigger: 'blur',
            },
          ];
        }
      });
      // TLS 配置校验
      if (this.showTlsConfig) {
        ['ca', 'cert', 'key'].forEach((field) => {
          rules[`tlsConfig.${field}`] = [
            {
              required: true,
              message: this.$t('必填项'),
              trigger: 'blur',
            },
          ];
        });
      }
      return rules;
    },
  },
  watch: {
    // 监听配置项变化，初始化 configValues
    configItems: {
      immediate: true,
      handler(items) {
        if (items && items.length) {
          const configValues = {};
          items.forEach((item) => {
            // 布尔类型默认 false，其他默认空字符串
            if (item.type === 'boolean' || item.type === 'bool') {
              configValues[item.key] = false;
            } else {
              configValues[item.key] = '';
            }
          });
          this.formData.configValues = configValues;
        }
      },
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
        // 解析 credentials 填充配置项
        try {
          const credentials = JSON.parse(row.credentials || '{}');
          this.configItems.forEach((item) => {
            if (item.type === 'boolean' || item.type === 'bool') {
              this.formData.configValues[item.key] = credentials[item.key] ?? false;
            } else {
              this.formData.configValues[item.key] = credentials[item.key] ?? '';
            }
          });
        } catch (e) {
          console.warn('解析 credentials 失败', e);
        }
        // 填充 TLS 配置
        if (this.showTlsConfig && row.config?.tls) {
          const tlsData = this.parseJsonData(row.config.tls);
          this.formData.tlsConfig = {
            ca: tlsData.ca || '',
            cert: tlsData.cert || '',
            key: tlsData.key || '',
            insecure_skip_verify: tlsData.insecure_skip_verify ?? false,
          };
        }
        // 填充分配方式（根据 binding_policy 是否存在且有值来判断）
        const hasBindingPolicy = row.binding_policy && Object.keys(row.binding_policy).length > 0;
        this.methodValue = hasBindingPolicy ? 'rule_based' : 'uniform';
        // 填充规则数据（需要等待 RuleBasedForm 组件渲染完成）
        if (hasBindingPolicy) {
          this.$nextTick(() => {
            // 双层 nextTick 确保条件渲染的组件已挂载
            this.$nextTick(() => {
              const rulesList = this.parseBindingPolicy(row.binding_policy);
              this.$refs.ruleBasedForm?.setData(rulesList);
            });
          });
        }
      } else {
        // 重置表单
        const configValues = {};
        this.configItems.forEach((item) => {
          if (item.type === 'boolean' || item.type === 'bool') {
            configValues[item.key] = false;
          } else {
            configValues[item.key] = '';
          }
        });
        this.formData = {
          recyclable: true,
          configValues,
          tlsConfig: {
            ca: '',
            cert: '',
            key: '',
            insecure_skip_verify: false,
          },
        };
        // 重置分配方式
        this.methodValue = 'uniform';
      }
    },
    close() {
      this.dialogVisible = false;
    },
    // 格式化配置项为 credentials JSON
    formatCredentials() {
      const credentials = {};
      this.configItems.forEach((item) => {
        const value = this.formData.configValues[item.key];
        if (value !== '' && value !== undefined) {
          // 数字类型转换
          if (item.type === 'integer' || item.type === 'number') {
            credentials[item.key] = Number(value);
          } else if (item.type === 'boolean' || item.type === 'bool') {
            credentials[item.key] = Boolean(value);
          } else {
            credentials[item.key] = value;
          }
        }
      });
      return JSON.stringify(credentials);
    },
    formatConfig() {
      const config = {
        // 可回收复用始终传递
        recyclable: this.formData.recyclable,
      };
      // TLS 配置
      if (this.showTlsConfig) {
        const { ca, cert, key, insecure_skip_verify } = this.formData.tlsConfig;
        if (ca || cert || key || insecure_skip_verify) {
          config.tls = {
            ca,
            cert,
            key,
            insecure_skip_verify,
          };
        } else {
          config.tls = null;
        }
      } else {
        config.tls = null;
      }
      return config;
    },
    // 解析 binding_policy 为规则列表（用于编辑回显）
    parseBindingPolicy(bindingPolicy) {
      const rulesList = [];
      // 反向字段映射：接口的 binding_policy key -> rule-based-form 中的 field
      const fieldMap = {
        app_code: 'app_id',
        module_name: 'module_name',
        env_name: 'environment',
      };
      Object.entries(bindingPolicy).forEach(([policyKey, values]) => {
        const field = fieldMap[policyKey];
        if (field) {
          // 环境字段为单选，其他字段为数组
          if (field === 'environment' && Array.isArray(values)) {
            // 环境每个值单独一条规则
            values.forEach((value) => {
              rulesList.push({ field, value });
            });
          } else {
            // 其他字段保持数组格式
            rulesList.push({ field, value: Array.isArray(values) ? values : [values] });
          }
        }
      });
      return rulesList.length > 0 ? rulesList : [{ field: '', value: [] }];
    },
    // 格式化规则数据为 binding_policy
    formatBindingPolicy(rulesList) {
      const bindingPolicy = {};
      // 字段映射：rule-based-form 中的 field -> 接口的 binding_policy key
      const fieldMap = {
        app_id: 'app_code',
        module_name: 'module_name',
        environment: 'env_name',
      };
      rulesList.forEach((rule) => {
        const policyKey = fieldMap[rule.field];
        if (policyKey) {
          // 值统一转为数组格式
          const values = Array.isArray(rule.value) ? rule.value : [rule.value];
          // 如果已存在该字段，合并数组
          if (bindingPolicy[policyKey]) {
            bindingPolicy[policyKey] = [...bindingPolicy[policyKey], ...values];
          } else {
            bindingPolicy[policyKey] = values;
          }
        }
      });
      return bindingPolicy;
    },
    // 确认
    async handleConfirm() {
      try {
        await this.$refs.formRef?.validate();

        // 按规则分配，校验规则表单
        if (this.methodValue === 'rule_based') {
          const ruleValidate = await this.$refs.ruleBasedForm?.validate();
          if (!ruleValidate?.flag) return;
        }
        this.dialogLoading = true;

        // 构建请求参数
        const params = {
          plan: this.data.planId,
          credentials: this.formatCredentials(),
          config: this.formatConfig(),
          allocation_type: this.methodValue === 'rule_based' ? 'policy' : 'fifo',
        };

        // 按规则分配时添加 binding_policy
        if (this.methodValue === 'rule_based') {
          const ruleData = this.$refs.ruleBasedForm?.getData();
          params.binding_policy = this.formatBindingPolicy(ruleData);
        }

        await this.submitResourcePool(params);
      } catch (e) {
        console.warn('表单校验失败', e);
      }
    },
    // 提交资源池（添加/编辑/克隆）
    async submitResourcePool(data, isClone = false) {
      const { planId, row } = this.data;
      const isUpdate = !this.isAdd && !isClone;

      const actionMap = {
        update: {
          action: 'tenant/updateResourcePool',
          payload: { planId, id: row?.uuid, data },
          message: this.$t('编辑成功'),
        },
        clone: {
          action: 'tenant/addResourcePool',
          payload: { planId, data },
          message: this.$t('克隆成功'),
        },
        add: {
          action: 'tenant/addResourcePool',
          payload: { planId, data },
          message: this.$t('添加成功'),
        },
      };

      const type = isUpdate ? 'update' : isClone ? 'clone' : 'add';
      const { action, payload, message } = actionMap[type];

      try {
        await this.$store.dispatch(action, payload);
        this.$paasMessage({ theme: 'success', message });
        this.$emit('refresh', true);
        this.close();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
    handlerChange(item) {
      this.methodValue = item.name;
    },
    // 克隆资源池（对外暴露的方法）
    cloneResourcePool(params) {
      this.submitResourcePool(params, true);
    },
  },
};
</script>

<style lang="scss" scoped>
/deep/ .resource-pool-dialog {
  .bk-dialog-body {
    max-height: 60vh;
    overflow-y: auto;
  }
}
.dialog-content {
  .section-title {
    height: 32px;
    line-height: 32px;
    margin-top: 8px;
  }
}
</style>
