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
          :label-width="labelWidth"
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
            :label="$t('供应商')"
            :required="true"
            :property="'provider_name'"
            :error-display-type="'normal'"
          >
            <bk-select
              v-model="formData.provider_name"
              searchable
            >
              <bk-option
                v-for="option in providerChoices"
                :key="option.id"
                :id="option.id"
                :name="option.name"
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
import 'quill/dist/quill.core.css';
import 'quill/dist/quill.snow.css';
import 'quill/dist/quill.bubble.css';

export default {
  name: 'ServiceCreateEditSideslider',
  mixins: [sidebarDiffMixin],
  components: {
    quillEditor,
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
      // 供应商列表
      providerChoices: [],
      providerLoading: true,
      // 富文本框配置
      editorOption: {
        placeholder: this.$t('使用指南会在增强服务实例页面上展示出来'),
        modules: {
          toolbar: TOOLBAR_OPTIONS,
        },
      },
      formData: {},
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
        name: [...requiredRules],
        display_name: [...requiredRules],
        category_id: [...requiredRules],
        provider_name: [...requiredRules],
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
    labelWidth() {
      return this.localLanguage === 'en' ? 120 : 80;
    },
  },
  methods: {
    close() {
      this.sidesliderVisible = false;
    },
    reset() {
      this.formData = {
        logo: '',
        // 服务ID
        name: '',
        // 服务名称
        display_name: '',
        // 分类
        category_id: '',
        config: {},
        provider_name: '',
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
      this.files = [];
    },
    // 显示侧栏，数据回填
    handleShown() {
      this.reset();
      Promise.all([this.getServicesCategory(), this.getServicesProviderChoices()]);
      const { name, logo, instance_tutorial } = this.data;
      if (this.isEdit) {
        this.formData = {
          ...this.data,
          instance_tutorial: marked(instance_tutorial),
        };
        this.setPreviewImage(name, logo);
      }
      this.$nextTick(() => {
        // 打开侧栏时，获取当前侧栏数据
        this.initSidebarFormData(this.formData);
        // 聚焦
        const quill = this.$refs.editor.quill;
        quill.focus();
        quill.setSelection(quill.getLength(), 0);
      });
    },
    handleDelete() {
      this.files = [];
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
    // 获取供应商
    async getServicesProviderChoices() {
      try {
        const ret = await this.$store.dispatch('tenant/getServicesProviderChoices');
        this.providerChoices = Object.entries(ret.provider_choices || {}).map(([key, value]) => {
          return { id: key, name: value };
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.providerLoading = false;
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
    handleSubmit() {
      this.$refs.formRef.validate().then(
        () => {
          // 过滤xss
          const params = {
            ...this.formData,
            logo: this.files[0]?.url || '',
            instance_tutorial: xss(this.formData.instance_tutorial),
          };
          this.isEdit ? this.updatePlatformService(params) : this.addPlatformService(params);
        },
        (e) => {
          console.error(e);
        }
      );
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
