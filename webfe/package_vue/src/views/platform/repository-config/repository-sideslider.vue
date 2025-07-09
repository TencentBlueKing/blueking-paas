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
        <span>{{ $t('代码库配置') }}</span>
        <div>
          <bk-button
            class="p0"
            :text="true"
            title="primary"
            size="small"
            @click="backfillDefault('github')"
          >
            {{ $t('填充 {a} 默认设置', { a: 'Github' }) }}
          </bk-button>
          <span class="line"></span>
          <bk-button
            class="p0"
            :text="true"
            title="primary"
            size="small"
            @click="backfillDefault('gitee')"
          >
            {{ $t('填充 {a} 默认设置', { a: 'Gitee' }) }}
          </bk-button>
        </div>
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
            :loading="configClass.loading"
            searchable
          >
            <bk-option
              v-for="option in configClass.list"
              :id="option.id"
              :name="option.id"
              :key="option.id"
            ></bk-option>
          </bk-select>
          <bk-switcher
            v-else-if="item.type === 'switcher'"
            theme="primary"
            v-model="formData[item.property]"
          ></bk-switcher>
        </bk-form-item>
        <bk-form-item
          :label="$t('服务配置')"
          property="server_config"
        >
          <div class="editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="configEditor"
              style="width: 100%; height: 100%"
              v-model="formData.server_config"
              :debounce="20"
              :mode="'text'"
            />
          </div>
        </bk-form-item>
      </bk-form>

      <!-- OAuth授权信息 -->
      <div class="form-sub-title mt-24">{{ $t('OAuth 授权信息') }}</div>
      <bk-form
        ref="oauthFormRef"
        :model="formData"
      >
        <bk-form-item
          v-for="item in oauthFormItems"
          :label="$t(item.label)"
          :required="item.required"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
          :desc="$t(item.desc)"
        >
          <bk-input
            v-model="formData[item.property]"
            v-if="item.type === 'input'"
          ></bk-input>
          <div
            v-else-if="item.type === 'json'"
            class="editor-wrapper"
          >
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              :ref="item.ref"
              style="width: 100%; height: 100%"
              v-model="formData[item.property]"
              :debounce="20"
              :mode="'text'"
              :key="item.ref"
            />
          </div>
        </bk-form-item>
      </bk-form>

      <!-- 展示信息 -->
      <div class="form-sub-title mt-24">{{ $t('展示信息') }}</div>
      <bk-form :model="formData">
        <bk-form-item
          :label="$t('绑定信息（中）')"
          :property="'display_info_zh_cn'"
          :desc="$t('若填写该项则必须包含字段：name，description')"
        >
          <div class="editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="displayZhEditorRef"
              style="width: 100%; height: 100%"
              v-model="formData.display_info_zh_cn"
              :debounce="20"
              :mode="'text'"
            />
          </div>
        </bk-form-item>
        <bk-form-item
          :label="$t('绑定信息（英）')"
          :property="'display_info_en'"
          :desc="$t('若填写该项则必须包含字段：name，description')"
        >
          <div class="editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="displayEnEditorRef"
              style="width: 100%; height: 100%"
              v-model="formData.display_info_en"
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
        @click="submitData"
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
import { validateJson } from '../services/validators';

// 基本信息
const BASE_INFO_FORM_CONFIG = [
  {
    property: 'name',
    label: '服务名称',
    type: 'input',
    placeholder: '只能由字符 [a-zA-Z0-9-_] 组成',
    rules: [
      {
        required: true,
        message: i18n.t('必填项'),
        trigger: 'blur',
      },
      {
        regex: /^[a-zA-Z0-9\-_]+$/,
        message: i18n.t('以英文字母、数字或下划线(_)组成'),
        trigger: 'blur',
      },
    ],
  },
  {
    property: 'label_zh_cn',
    label: '标签（中文）',
    type: 'input',
  },
  {
    property: 'label_en',
    label: '标签（英文）',
    type: 'input',
  },
  {
    property: 'enabled',
    label: '是否默认开放',
    type: 'switcher',
    desc: '关闭后，用户将无法创建与该源码类型仓库关联的新应用，可以通过 “用户特性” 为特定用户单独开启此功能。',
  },
  {
    property: 'spec_cls',
    label: '配置类',
    type: 'select',
  },
];

// OAuth授权信息
const OAUTH_FORM_CONFIG = [
  { property: 'authorization_base_url', label: 'OAuth 授权链接', type: 'input' },
  { property: 'client_id', label: 'Client ID', type: 'input' },
  { property: 'client_secret', label: 'Client Secret', type: 'input' },
  { property: 'redirect_uri', label: '回调地址', type: 'input' },
  { property: 'token_base_url', label: '获取 Token 链接', type: 'input' },
  {
    property: 'oauth_display_info_zh_cn',
    label: 'OAuth 信息（中）',
    type: 'json',
    ref: 'zhCnEditor',
    desc: '可用字段：icon，display_name，address，description，auth_docs',
  },
  {
    property: 'oauth_display_info_en',
    label: 'OAuth 信息（英）',
    type: 'json',
    ref: 'enEditor',
    desc: '可用字段：icon，display_name，address，description，auth_docs',
  },
];

// 基本信息表单数据
const INITIAL_FORM_DATA = {
  name: '',
  label_zh_cn: '',
  label_en: '',
  enabled: true,
  spec_cls: '',
  server_config: {},
  authorization_base_url: '',
  client_id: '',
  client_secret: '',
  redirect_uri: '',
  token_base_url: '',
  oauth_display_info_zh_cn: {},
  oauth_display_info_en: {},
  display_info_zh_cn: {},
  display_info_en: {},
};

// oauth表单，非必填项
const OPTIONAL_FIELDS = ['BareSvnSourceTypeSpec', 'BareGitSourceTypeSpec'];

const requiredRule = {
  required: true,
  message: i18n.t('必填项'),
  trigger: 'blur',
};

export default {
  name: 'EditAddRepositoryConfig',
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
      type: Number,
      default: -1,
    },
  },
  data() {
    return {
      saveLoading: false,
      configClass: {
        list: [],
        loading: false,
      },
      formData: { ...INITIAL_FORM_DATA },
      // 基本信息form配置
      baseInfoFormItems: Object.freeze(
        BASE_INFO_FORM_CONFIG.map((item) => ({
          ...item,
          required: true,
          rules: item.rules ? item.rules : [{ ...requiredRule }],
        }))
      ),
      defaultConfig: {},
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
    // OAuth授权信息表单配置项
    oauthFormItems() {
      const { spec_cls } = this.formData;
      const isRequired = spec_cls ? !OPTIONAL_FIELDS.includes(spec_cls) : false;
      return OAUTH_FORM_CONFIG.map((field) => ({
        ...field,
        required: isRequired,
        rules: isRequired ? [{ ...requiredRule }] : [],
      }));
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
  },
  methods: {
    close() {
      this.sidesliderVisible = false;
    },
    shown() {
      this.getSpecClsChoices();
      this.getDefaultConfigsTemplates();
      if (!this.isAdd) {
        // 编辑数据回填
        this.formData = { ...this.data };
      }
    },
    reset() {
      this.formData = { ...INITIAL_FORM_DATA };
    },
    // JSON 验证方法
    validateAllJsonFields() {
      const jsonFieldsToValidate = [
        {
          data: this.formData.server_config,
          ref: this.$refs.configEditor?.jsonEditor,
          fieldName: 'server_config',
        },
        // OAuth 信息（中）
        {
          data: this.formData.oauth_display_info_zh_cn,
          ref: this.$refs.zhCnEditor[0]?.jsonEditor,
          fieldName: 'oauth_display_info_zh_cn',
        },
        {
          data: this.formData.oauth_display_info_en,
          ref: this.$refs.enEditor[0]?.jsonEditor,
          fieldName: 'oauth_display_info_en',
        },
        // 绑定信息（中）
        {
          data: this.formData.display_info_zh_cn,
          ref: this.$refs.displayZhEditorRef?.jsonEditor,
          fieldName: 'display_info_zh_cn',
        },
        {
          data: this.formData.display_info_en,
          ref: this.$refs.displayEnEditorRef?.jsonEditor,
          fieldName: 'display_info_en',
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
    submitData() {
      // JSON校验
      if (!this.validateAllJsonFields()) {
        return;
      }
      const validateArr = [this.$refs.infoFormRef?.validate()];
      if (this.formData.spec_cls && !OPTIONAL_FIELDS.includes(this.formData.spec_cls)) {
        validateArr.push(this.$refs.oauthFormRef?.validate());
      }
      Promise.all(validateArr)
        .then(() => {
          this.handleRepositoryConfig();
        })
        .catch((e) => {
          console.error(e);
        });
    },
    // 获取配置类列表
    async getSpecClsChoices() {
      this.configClass.loading = true;
      try {
        const res = await this.$store.dispatch('tenantConfig/getSpecClsChoices');
        this.configClass.list = res.map((v) => ({ id: v }));
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.configClass.loading = false;
      }
    },
    toJsonObject(jsonData) {
      if (jsonData === undefined || jsonData === null) return {};
      return typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
    },
    // 处理接口数据
    formatData() {
      // 需要处理的json
      const jsonFields = [
        'server_config',
        'oauth_display_info_zh_cn',
        'oauth_display_info_en',
        'display_info_zh_cn',
        'display_info_en',
      ];

      const transformFields = (fields, formData) => {
        return fields.reduce((acc, field) => {
          acc[field] = this.toJsonObject(formData[field]);
          return acc;
        }, {});
      };

      return {
        ...this.formData,
        ...transformFields(jsonFields, this.formData),
      };
    },
    // 代码库配置（创建或更新）
    async handleRepositoryConfig() {
      try {
        this.saveLoading = true;
        const data = this.formatData();
        const action = this.isAdd ? 'createRepositoryConfig' : 'updateRepositoryConfig';
        const payload = this.isAdd ? { data } : { id: this.id, data };
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
    // 默认配置项
    async getDefaultConfigsTemplates() {
      try {
        const ret = await this.$store.dispatch('tenantConfig/getDefaultConfigsTemplates');
        this.defaultConfig = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    backfillDefault(key) {
      const curDefaultConfig = this.defaultConfig[key] || {};
      this.formData = {
        ...this.formData,
        ...curDefaultConfig,
      };
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
    .line {
      display: inline-block;
      height: 12px;
      width: 1px;
      margin: 0 8px;
      background: #3a84ff;
      transform: translateY(2px);
    }
    .desc {
      height: 22px;
      margin-left: 10px;
      padding-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }
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
