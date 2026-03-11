<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="960"
    show-mask
    ext-cls="service-sideslider-cls"
    :title="$t('增强服务')"
    :before-close="handleBeforeClose"
    @shown="handleShown"
    @hidden="reset"
  >
    <div
      class="sideslider-content-cls"
      ref="sideslider"
      slot="content"
    >
      <div class="main">
        <bk-form
          :label-width="120"
          :model="formData"
          :rules="rules"
          ref="formRef"
        >
          <bk-form-item
            label="LOGO"
            :required="true"
            :property="'logo'"
            ext-cls="logo-form-item-cls"
            :rules="rules.logo"
            :error-display-type="'normal'"
          >
            <bk-upload
              :files="files"
              :theme="'picture'"
              accept="image/jpeg, image/png"
              :multiple="false"
              ext-cls="app-logo-upload-cls"
              :custom-request="customRequest"
              @on-delete="handleDelete"
            ></bk-upload>
          </bk-form-item>
          <bk-form-item
            :label="$t('服务 ID')"
            :required="true"
            :property="'name'"
            :error-display-type="'normal'"
          >
            <bk-input v-model="formData.name"></bk-input>
          </bk-form-item>
          <bk-form-item
            :label="$t('服务名称')"
            :required="true"
            :property="'display_name'"
            :error-display-type="'normal'"
          >
            <bk-input v-model="formData.display_name"></bk-input>
          </bk-form-item>
          <bk-form-item
            :label="$t('分类')"
            :required="true"
            :property="'category_id'"
            :error-display-type="'normal'"
          >
            <bk-select v-model="formData.category_id">
              <bk-option
                v-for="option in categoryList"
                :key="option.value"
                :id="option.value"
                :name="option.text"
              ></bk-option>
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('是否可见')"
            :required="true"
            :property="'is_visible'"
          >
            <bk-switcher
              v-model="formData.is_visible"
              theme="primary"
            ></bk-switcher>
          </bk-form-item>
          <template v-if="formData.origin === 'local'">
            <bk-form-item
              :label="$t('配置项')"
              :required="true"
            >
              <ConfigItemsTable
                ref="configItemsTableRef"
                v-model="formData.config.config_items"
              />
            </bk-form-item>
            <bk-form-item
              :label="$t('支持 TLS')"
              :required="true"
            >
              <bk-switcher
                v-model="formData.config.tls"
                theme="primary"
              ></bk-switcher>
              <p class="g-tip">
                {{
                  $t(
                    '开启 TLS 后，添加实例时需上传 TLS 相关证书。应用部署后，平台会将 TLS 证书路径写入内置环境变量中。'
                  )
                }}
              </p>
            </bk-form-item>
            <bk-form-item
              :label="$t('环境变量模板')"
              :required="true"
              :desc="$t('通过配置环境变量模板，可将增强服务配置信息注入应用环境变量。')"
            >
              <EnvTemplateTable
                :service-id="formData.name"
                :config-items="formData.config.config_items"
                @update="handleEnvTemplateUpdate"
              />
            </bk-form-item>
          </template>
          <bk-form-item
            :label="$t('服务介绍')"
            :required="true"
            :property="'description'"
            :error-display-type="'normal'"
          >
            <bk-input
              :type="'textarea'"
              :rows="2"
              :maxlength="100"
              v-model="formData.description"
            ></bk-input>
          </bk-form-item>
          <bk-form-item
            :label="$t('使用指南')"
            :required="true"
            :property="'instance_tutorial'"
            :error-display-type="'normal'"
            ext-cls="instance-tutorial-item-cls"
          >
            <quill-editor
              ref="editor"
              :style="{ height: '300px' }"
              v-model="formData.instance_tutorial"
              class="service-quill-editor-cls"
              :options="editorOption"
              @blur="quillEditorBlur"
              @focus="quillEditorFocus"
            />
          </bk-form-item>
        </bk-form>
      </div>
    </div>
    <div
      slot="footer"
      class="service-footer-btns"
    >
      <bk-button
        :theme="'primary'"
        class="mr8"
        :loading="submitLoading"
        @click="handleSubmit"
      >
        {{ $t('保存') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        @click="close"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
  </bk-sideslider>
</template>

<script>
import xss from 'xss';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import { marked } from 'marked';
import { quillEditor } from 'vue-quill-editor';
import { TOOLBAR_OPTIONS } from '@/common/constants';
import ConfigItemsTable from './config-items-table.vue';
import EnvTemplateTable from './env-template-table.vue';
import 'quill/dist/quill.core.css';
import 'quill/dist/quill.snow.css';
import 'quill/dist/quill.bubble.css';

// 获取默认表单数据
function getDefaultFormData() {
  return {
    logo: '',
    // 服务ID
    name: '',
    // 服务名称
    display_name: '',
    // 分类
    category_id: '',
    // 配置信息
    config: {
      // 配置项
      config_items: [],
      // 支持 TLS
      tls: false,
      // 环境变量模板
      template: [],
    },
    // 是否可见
    is_visible: true,
    // 服务介绍
    description: '',
    // 使用指南
    instance_tutorial: '',
    is_active: true,
    origin: 'local',
    // available_languages、long_description 后续接口会移出必填特性
    available_languages: 'Python',
    long_description: 'test',
  };
}

export default {
  name: 'ServiceCreateEditSideslider',
  mixins: [sidebarDiffMixin],
  components: {
    quillEditor,
    ConfigItemsTable,
    EnvTemplateTable,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    type: {
      type: String,
      default: 'new',
    },
  },
  data() {
    const requiredRules = [
      {
        required: true,
        message: '必填项',
        trigger: 'blur',
      },
    ];
    return {
      // 预览图
      files: [],
      // 分类列表
      categoryList: [],
      categoryLoading: true,
      // 富文本框配置
      editorOption: {
        placeholder: this.$t('使用指南会在增强服务实例页面上展示出来'),
        modules: {
          toolbar: TOOLBAR_OPTIONS,
        },
      },
      formData: getDefaultFormData(),
      submitLoading: false,
      rules: {
        logo: [
          {
            validator: () => {
              return this.files?.length > 0;
            },
            message: '请上传 logo',
            trigger: 'change',
          },
        ],
        name: [
          ...requiredRules,
          {
            regex: /^[a-zA-Z][a-zA-Z0-9_-]{1,30}[a-zA-Z0-9]$/,
            message: this.$t('由 3-32 位字母、数字、连接符(-)、下划线(_) 字符组成，以字母开头，字母或数字结尾'),
            trigger: 'blur',
          },
        ],
        display_name: [...requiredRules],
        category_id: [...requiredRules],
        description: [...requiredRules],
        instance_tutorial: [
          {
            validator: function (val) {
              return val !== '';
            },
            message: '必填项',
            trigger: 'blur',
          },
        ],
      },
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
    isEdit() {
      return this.type === 'edit';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  methods: {
    close() {
      this.sidesliderVisible = false;
    },
    reset() {
      this.formData = getDefaultFormData();
      this.files = [];
    },
    // 获取提交用的 config 数据（本地服务返回完整配置，远程服务返回空对象）
    getSubmitConfig() {
      if (this.formData.origin !== 'local') {
        return {};
      }
      // 过滤 config_items 中的 isEditing、isNew 字段
      const config_items = (this.formData.config.config_items || []).map(({ isEditing, isNew, ...rest }) => rest);
      return {
        ...this.formData.config,
        config_items,
      };
    },
    // 显示侧栏，数据回填
    handleShown() {
      this.reset();
      this.getServicesCategory();
      const { name, logo, instance_tutorial } = this.data;
      if (this.isEdit) {
        // 编辑时先禁用编辑器，防止内容变更时自动聚焦和滚动
        const quill = this.$refs.editor?.quill;
        if (quill) {
          quill.enable(false);
        }
        this.formData = {
          ...this.data,
          config: {
            config_items: [],
            tls: false,
            template: [],
            ...(this.data.config || {}),
          },
          instance_tutorial: marked(instance_tutorial),
        };
        this.setPreviewImage(name, logo);
      }
      this.$nextTick(() => {
        // 打开侧栏时，获取当前侧栏数据
        this.initSidebarFormData(this.formData);
        if (this.isEdit) {
          this.resetQuillEditor();
        }
      });
    },
    // 重置编辑器状态，移除焦点并重新启用
    resetQuillEditor() {
      const quill = this.$refs.editor?.quill;
      if (quill) {
        quill.blur();
        quill.enable(true);
      }
    },
    handleDelete() {
      this.files = [];
    },
    // 更新环境变量模板
    handleEnvTemplateUpdate(template) {
      this.formData.config.template = template;
    },
    async quillEditorBlur() {
      // 手动触发校验
      this.$refs.formRef.validateField('instance_tutorial').catch((e) => {
        console.error(e);
      });
    },
    quillEditorFocus() {
      // 清除单个错误提示
      this.$refs.formRef?.clearFieldError('instance_tutorial');
    },
    // 获取图片base64url
    getBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = (error) => reject(error);
      });
    },
    // 自定义上传
    async customRequest(file) {
      const fileData = file.fileObj.origin;
      // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
      const imgSize = fileData.size / 1024;
      const maxSize = 2 * 1024;
      if (imgSize > maxSize) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件大小应<2M！'),
        });
        return;
      }
      const previewImageUrl = await this.getBase64(fileData);
      this.formData.logo = previewImageUrl;
      this.setPreviewImage(fileData.name, previewImageUrl);
      // 手动logo触发校验
      this.$refs.formRef.validateField('logo');
    },
    // 设置当前预览图
    setPreviewImage(name, imageUrl) {
      this.files = [
        {
          name,
          url: imageUrl,
        },
      ];
    },
    // 获取服务分类
    async getServicesCategory() {
      try {
        const ret = await this.$store.dispatch('tenant/getServicesCategory');
        this.categoryList = ret.category_list || [];
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.categoryLoading = false;
      }
    },
    // 新增服务
    async addPlatformService(data) {
      this.submitLoading = true;
      try {
        await this.$store.dispatch('tenant/addPlatformService', { data });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新增成功'),
        });
        this.close();
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
    },
    // 编辑服务
    async updatePlatformService(data) {
      this.submitLoading = true;
      try {
        await this.$store.dispatch('tenant/updatePlatformService', { serviceId: data.uuid, data });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
        this.close();
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
    },
    // 提交
    async handleSubmit() {
      let validateArr = [this.$refs.formRef?.validate()];
      if (this.formData.origin === 'local') {
        validateArr.push(this.$refs.configItemsTableRef?.validate());
      }
      await Promise.all(validateArr)
        .then(() => {
          // 过滤xss
          const params = {
            ...this.formData,
            config: this.getSubmitConfig(),
            logo: this.files[0]?.url || '',
            instance_tutorial: xss(this.formData.instance_tutorial),
          };
          this.isEdit ? this.updatePlatformService(params) : this.addPlatformService(params);
        })
        .catch((e) => {
          console.error(e);
        });
    },
    // 侧栏关闭前置检查，变更需要离开提示
    async handleBeforeClose() {
      return this.$isSidebarClosed(JSON.stringify(this.formData));
    },
  },
};
</script>

<style lang="scss" scoped>
.sideslider-content-cls {
  padding: 24px 40px 120px;
  .logo-form-item-cls {
    display: flex;
    align-items: center;
    ::v-deep .bk-form-content {
      margin-left: 0 !important;
      i.tooltips-icon {
        display: none;
      }
    }
  }
  .app-logo-upload-cls {
    ::v-deep .file-wrapper {
      height: auto;
      padding-top: 0 !important;
    }
  }
  .instance-tutorial-item-cls.is-error {
    ::v-deep .ql-toolbar {
      border-bottom-color: #ea3636;
    }
    ::v-deep .ql-container.ql-snow {
      border-color: #ea3636;
    }
  }
}
.service-sideslider-cls {
  ::v-deep .bk-sideslider-content {
    max-height: calc(-52px + 100vh) !important;
    height: calc(100vh - 52px);
  }
  ::v-deep .bk-sideslider-footer {
    position: absolute;
    padding: 0 24px;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 48px;
    line-height: 48px;
    background: #fafbfd;
    box-shadow: 0 -1px 0 0 #dcdee5;
  }
  ::v-deep .bk-sideslider-wrapper {
    overflow-y: hidden !important;
  }
}
.service-quill-editor-cls {
  display: flex;
  flex-direction: column;
  ::v-deep .ql-container {
    flex: 1;
    min-height: 0;
  }
  ::v-deep .ql-toolbar {
    flex-shrink: 0;
  }
  ::v-deep .ql-editor.ql-blank::before {
    font-style: normal;
    font-size: 14px;
    color: #c4c6cc;
  }
}
</style>
