<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    width="960"
    ext-cls="repository-sideslider-cls"
    @shown="shown"
    @hidden="reset"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t(isAdd ? '添加模版配置' : '修改模版配置') }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <!-- 基本信息 -->
      <div class="form-sub-title">{{ $t('基本信息') }}</div>
      <bk-form
        ref="infoFormRef"
        :model="formData"
      >
        <bk-form-item
          v-for="item in baseInfoFormItems"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :desc="$t(item.desc)"
        >
          <bk-input
            v-if="item.type === 'input'"
            v-model="formData[item.property]"
            :placeholder="$t(item.placeholder)"
          ></bk-input>
          <bk-select
            v-else-if="item.type === 'select'"
            v-model="formData[item.property]"
            searchable
          >
            <bk-option
              v-for="option in metadata[item.metadataKey] || []"
              :id="option.name"
              :name="option.label"
              :key="option.name"
            ></bk-option>
          </bk-select>
          <bk-switcher
            v-else-if="item.type === 'switcher'"
            theme="primary"
            v-model="formData[item.property]"
          ></bk-switcher>
        </bk-form-item>
      </bk-form>

      <!-- 普通模块 -->
      <template v-if="!isPluginType">
        <div class="form-sub-title mt-24">{{ $t('模版信息') }}</div>
        <bk-form
          :model="formData"
          ref="defaultFormRef"
        >
          <bk-form-item
            :label="$t('二进制包存储路径')"
            :property="'blob_url'"
            :required="isDisplay"
            :rules="isDisplay ? blobUrlRules : []"
          >
            <bk-input
              v-model="formData.blob_url"
              :placeholder="$t('请输入对象存储中的包路径')"
            ></bk-input>
          </bk-form-item>
        </bk-form>
      </template>

      <!-- 插件模块 -->
      <template v-else>
        <div class="form-sub-title mt-24">{{ $t('模版信息') }}</div>
        <bk-form
          :model="formData"
          ref="pluginFormRef"
        >
          <bk-form-item
            v-for="item in pluginFormItems"
            :label="$t(item.label)"
            :required="item.required"
            :property="item.property"
            :rules="item.rules"
            :key="item.label"
            :desc="$t(item.desc)"
          >
            <bk-input
              v-if="item.type === 'input'"
              v-model="formData[item.property]"
              :placeholder="$t(item.placeholder)"
            ></bk-input>
            <bk-select
              v-else-if="item.type === 'select'"
              v-model="formData[item.property]"
              searchable
            >
              <bk-option
                v-for="option in metadata[item.metadataKey] || []"
                :id="option.name"
                :name="option.label"
                :key="option.name"
              ></bk-option>
            </bk-select>
          </bk-form-item>
        </bk-form>
      </template>

      <div class="form-sub-title mt-24">{{ $t('配置信息') }}</div>
      <bk-form
        ref="configFormRef"
        :model="formData"
      >
        <bk-form-item
          v-for="item in configFormItems"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
        >
          <div class="editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              :ref="item.ref"
              style="width: 100%; height: 100%"
              v-model="formData[item.property]"
              :debounce="20"
              :mode="'text'"
            />
          </div>
        </bk-form-item>
      </bk-form>
    </div>
    <section
      class="footer-btns"
      slot="footer"
    >
      <bk-button
        class="mr-8"
        ext-cls="btn-cls"
        theme="primary"
        :loading="saveLoading"
        @click="handleSubmit"
      >
        {{ $t('提交') }}
      </bk-button>
      <bk-button
        ext-cls="btn-cls"
        theme="default"
        @click="close"
      >
        {{ $t('取消') }}
      </bk-button>
    </section>
  </bk-sideslider>
</template>

<script>
import i18n from '@/language/i18n.js';
import JsonEditorVue from 'json-editor-vue';
import { cloneDeep } from 'lodash';
import { validateJson } from '../services/validators';
import { BASE_INFO_FORM_CONFIG, PLUGIN_FORM_CONFIG, CONFIG_INFO_FORM_CONFIG } from './form-options';

// 模版表单数据
const INITIAL_FORM_DATA = {
  // 基本信息
  name: '',
  type: 'normal',
  render_method: 'django_template', // 渲染方式
  display_name_zh_cn: '',
  display_name_en: '',
  description_zh_cn: '',
  description_en: '',
  language: '',
  is_display: true,
  // 模块信息（模块）
  blob_url: '',
  // 模块信息（插件）
  repo_type: '',
  repo_url: '',
  source_dir: '',
  // 配置信息
  preset_services_config: {},
  required_buildpacks: [],
  processes: {},
};

// 基础必填校验
const requiredRule = {
  required: true,
  message: i18n.t('必填项'),
  trigger: 'blur',
};

// 模块信息-插件非必填项
const nonRequiredFields = ['repo_type', 'source_dir'];

export default {
  name: 'EditAddTemplateConfig',
  components: {
    JsonEditorVue,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    type: {
      type: String,
      default: 'add',
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    id: {
      type: Number | String,
      default: -1,
    },
    metadata: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      saveLoading: false,
      formData: cloneDeep(INITIAL_FORM_DATA),
      // 基本信息 form 配置
      baseInfoFormItems: BASE_INFO_FORM_CONFIG.map((item) => ({
        ...item,
        required: true,
        rules: item.rules ? item.rules : [{ ...requiredRule }],
      })),
      // 插件模块 form 配置
      pluginFormItems: Object.freeze(
        PLUGIN_FORM_CONFIG.map((item) => ({
          ...item,
          required: !nonRequiredFields.includes(item.property),
          rules: nonRequiredFields.includes(item.property) ? [] : [{ ...requiredRule }],
        }))
      ),
      blobUrlRules: [{ ...requiredRule }],
      // 配置信息 form 配置
      configFormItems: Object.freeze(CONFIG_INFO_FORM_CONFIG),
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    isAdd() {
      return this.type === 'add';
    },
    isPluginType() {
      return this.formData.type === 'plugin';
    },
    isDisplay() {
      return this.formData.is_display;
    },
    defaultRenderMethod() {
      return this.isPluginType ? 'cookiecutter' : 'django_template';
    },
  },
  watch: {
    data: {
      handler(newVal) {
        if (!this.isAdd) {
          this.formData = { ...newVal };
        }
      },
      deep: true,
    },
    'formData.is_display'(newVal) {
      if (!newVal) {
        this.$refs.defaultFormRef?.clearError();
      }
    },
    'formData.type'() {
      if (this.isAdd) {
        this.formData.render_method = this.defaultRenderMethod;
      }
    },
  },
  methods: {
    close() {
      this.sidesliderVisible = false;
    },
    shown() {
      if (!this.isAdd) {
        // 编辑数据回填
        this.formData = { ...this.data };
      }
    },
    reset() {
      this.formData = cloneDeep(INITIAL_FORM_DATA);
    },
    // JSON 验证方法
    validateAllJsonFields() {
      const jsonFieldsToValidate = [
        // 预设增强服务配置
        {
          data: this.formData.preset_services_config,
          ref: this.$refs.servicesEditor[0]?.jsonEditor,
          fieldName: 'preset_services_config',
        },
        // 必须的构建工具
        {
          data: this.formData.required_buildpacks,
          ref: this.$refs.buildEditor[0]?.jsonEditor,
          fieldName: 'required_buildpacks',
        },
        // 进程配置
        {
          data: this.formData.processes,
          ref: this.$refs.processesEditor[0]?.jsonEditor,
          fieldName: 'processes',
        },
      ];

      for (const { data, ref, fieldName } of jsonFieldsToValidate) {
        const isValid = validateJson(data, ref);
        if (!isValid) {
          console.error(`${fieldName} JSON 校验失败`);
          return false;
        }
      }

      return true;
    },
    // 提交-校验
    handleSubmit() {
      // JSON校验
      if (!this.validateAllJsonFields()) {
        return;
      }
      const validateArr = [this.$refs.infoFormRef?.validate()];
      const formRef = this.isPluginType ? 'pluginFormRef' : 'defaultFormRef';
      validateArr.push(this.$refs[formRef]?.validate());
      Promise.all(validateArr)
        .then(() => {
          this.handleRepositoryConfig();
        })
        .catch((e) => {
          console.error(e);
        });
    },
    toJsonObject(jsonData) {
      if (jsonData === undefined || jsonData === null) return {};
      return typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
    },
    // 处理接口数据
    formatData() {
      // 需要处理的json
      const jsonFields = ['preset_services_config', 'required_buildpacks', 'processes'];

      const transformFields = (fields, formData) => {
        return fields.reduce((acc, field) => {
          acc[field] = this.toJsonObject(formData[field]);
          return acc;
        }, {});
      };
      const getUrlFields = () =>
        this.isPluginType
          ? { blob_url: '' }
          : {
              repo_type: '',
              repo_url: '',
              source_dir: '',
            };
      return {
        ...this.formData,
        ...getUrlFields(),
        ...transformFields(jsonFields, this.formData),
      };
    },
    // 模版配置（创建|更新）
    async handleRepositoryConfig() {
      try {
        this.saveLoading = true;
        const data = this.formatData();
        const action = this.isAdd ? 'createTemplate' : 'updateTemplate';
        const payload = this.isAdd ? { data } : { templateId: this.id, data };
        await this.$store.dispatch(`tenantConfig/${action}`, payload);
        this.$paasMessage({
          theme: 'success',
          message: this.$t(this.isAdd ? '创建成功' : '修改成功'),
        });
        this.close();
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.saveLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.repository-sideslider-cls {
  .header-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  /deep/ .bk-sideslider-content {
    height: calc(100vh - 100px) !important;
  }
  /deep/ .bk-sideslider-footer {
    padding-left: 24px;
    border-top: 1px solid #dcdee5 !important;
    background-color: #dcdee5;
  }
  .sideslider-content {
    padding: 24px 40px;
    .form-sub-title {
      margin-bottom: 24px;
      padding-left: 8px;
      height: 32px;
      line-height: 32px;
      font-weight: 700;
      color: #313238;
      background: #f0f1f5;
      border-radius: 2px;
    }
    .btn-cls {
      min-width: 88px;
    }
    .editor-wrapper {
      height: 180px;
      /deep/ .jsoneditor-vue {
        height: 100%;
      }
    }
  }
}
</style>
