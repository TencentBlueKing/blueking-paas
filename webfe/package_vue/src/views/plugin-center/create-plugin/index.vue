<template>
  <div
    class="bk-create-plugin-warp"
    :style="{ paddingTop: `${isShowNotice ? GLOBAL.NOTICE_HEIGHT + 50 : 50}px` }"
  >
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="create-plugin-loading"
    >
      <paas-plugin-title :no-shadow="true" />
      <section class="info-container card-style">
        <div class="base-info-tit">
          {{ $t('基本信息') }}
        </div>
        <bk-form
          ref="pluginForm"
          :label-width="170"
          :model="form"
          :rules="rules"
        >
          <bk-form-item
            :label="$t('插件类型')"
            :required="true"
            :property="'pd_id'"
          >
            <div class="plugin-type">
              <bk-select
                v-model="form.pd_id"
                ext-popover-cls="plugin-type-custom"
                searchable
                :clearable="false"
                :placeholder="$t('插件类型')"
                @change="changePluginType"
              >
                <bk-option
                  v-for="option in pluginTypeList"
                  :id="option.plugin_type.id"
                  :key="option.plugin_type.id"
                  v-bind="option"
                >
                  <div
                    id="guide-wrap"
                    class="guide-container"
                  >
                    <div class="flex-row align-items-center guide-item">
                      <img
                        :src="option.plugin_type.logo"
                        onerror="this.src='/static/images/plugin-default.svg'"
                      />
                      <div class="guide-right pl10">
                        <div class="guide-plugin-name">
                          {{ option.plugin_type.name }}
                        </div>
                        <div
                          v-bk-overflow-tips="option.plugin_type.description"
                          class="guide-plugin-desc"
                        >
                          {{ option.plugin_type.description }}
                        </div>
                      </div>
                    </div>
                  </div>
                </bk-option>
              </bk-select>

              <a
                v-if="curPluginItem.plugin_type"
                target="_blank"
                :href="curPluginItem.plugin_type.docs"
                class="plugin-guide"
                :style="{ right: `${getGuideOffset()}px` }"
              >
                <i class="paasng-icon paasng-question-circle" />
                {{ $t('插件指引') }}
              </a>
            </div>
            <div
              v-if="
                curPluginItem.plugin_type &&
                curPluginItem.plugin_type.approval_config &&
                curPluginItem.plugin_type.approval_config.enabled
              "
              class="plugin-info mt15"
            >
              <i
                style="color: #3a84ff"
                class="paasng-icon paasng-info-circle"
              />
              {{ curPluginItem.plugin_type.approval_config.tips }}
              <a
                target="_blank"
                :href="curPluginItem.plugin_type.approval_config.docs"
              >
                {{ $t('详见文档') }}
              </a>
            </div>
          </bk-form-item>
          <bk-form-item
            :label="$t('插件 ID')"
            :required="true"
            :property="'plugin_id'"
            error-display-type="normal"
          >
            <bk-input
              v-model="form.plugin_id"
              :placeholder="$t(pdIdPlaceholder)"
              :maxlength="pdIdMaxLength"
              :show-word-limit="true"
              :spellcheck="false"
            />
          </bk-form-item>
          <bk-form-item
            :label="$t('插件名称')"
            :required="true"
            :property="'name'"
            :rules="rules.name"
            error-display-type="normal"
          >
            <bk-input
              v-model="form.name"
              :placeholder="$t(namePlaceholder)"
              :maxlength="nameMaxLength"
              :show-word-limit="true"
              :spellcheck="false"
            />
          </bk-form-item>
          <bk-form-item
            :label="$t('开发语言')"
            :required="true"
            :property="'language'"
          >
            <bk-select
              v-model="form.language"
              :clearable="false"
              :placeholder="$t('开发语言')"
              @change="changePluginLanguage"
            >
              <bk-option
                v-for="option in developmentLanguages"
                :id="option.id"
                :key="option.id"
                :name="option.language"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            v-if="languageData.applicableLanguage"
            :label="$t('适用语言')"
            :required="true"
            :property="'applicableLanguage'"
          >
            <bk-select
              v-model="form.applicableLanguage"
              :clearable="false"
              :placeholder="$t('适用语言')"
            >
              <bk-option
                v-for="option in applicableLanguageList"
                :id="option.id"
                :key="option.id"
                :name="option.text"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('初始化模板')"
            :required="true"
            :property="'templateName'"
          >
            <bk-select
              v-model="form.templateName"
              :clearable="false"
              :placeholder="$t('初始化模板')"
              @change="templateChange"
            >
              <bk-option
                v-for="option in pluginTemplateList"
                :id="option.id"
                :key="option.id"
                :name="option.name"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('代码仓库')"
            :required="true"
            :property="'repositoryTemplateUrl'"
          >
            <bk-input
              v-model="form.repositoryTemplateUrl"
              disabled
              :placeholder="$t('代码仓库')"
            />
            <i
              v-copy="form.repositoryTemplateUrl"
              class="paasng-icon paasng-general-copy copy-icon"
            />
            <div class="tips">
              {{ $t('将自动创建该开源仓库，将模板代码初始化到仓库中，并将创建者初始化为仓库管理员') }}
            </div>
          </bk-form-item>
        </bk-form>
      </section>
      <!-- 更多信息根据接口字段动态生成、AI插件特殊处理 -->
      <section
        v-if="Object.keys(extraFields).length || isAiPlugin"
        :class="['info-container', 'card-style', 'mt16', { mb75: isSticky }]"
      >
        <div class="base-info-tit">
          {{ $t('更多信息') }}
        </div>
        <bk-form
          ref="moreForm"
          :model="isAiPlugin ? bkAiSpaces : form"
        >
          <template v-if="isAiPlugin">
            <bk-form-item
              :label="$t('AI 空间')"
              :required="true"
              :property="'spaceId'"
              :rules="requiredRules"
            >
              <bk-select v-model="bkAiSpaces.spaceId">
                <bk-option
                  v-for="option in bkAiSpaces.spacesList"
                  :key="option.space_id"
                  :id="option.space_id"
                  :name="option.space_name"
                ></bk-option>
              </bk-select>
            </bk-form-item>
          </template>
          <BkSchemaForm
            v-else
            :key="form.pd_id"
            class="bk-form-warp"
            v-model="schemaFormData"
            ref="bkForm"
            :http-adapter="{ request }"
            :label-width="170"
            :schema="schema"
            :layout="layout"
          ></BkSchemaForm>
        </bk-form>
      </section>

      <div :class="['create-button-warp', { sticky: isSticky }]">
        <bk-button
          :theme="'primary'"
          :title="$t('提交')"
          class="mr8"
          :loading="buttonLoading"
          @click="submitPluginForm"
        >
          {{ $t('提交') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          :title="$t('取消')"
          @click="back"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
import http from '@/api';
import 'quill/dist/quill.core.css';
import 'quill/dist/quill.snow.css';
import 'quill/dist/quill.bubble.css';
import paasPluginTitle from '@/components/pass-plugin-title';
import createForm from '@blueking/bkui-form';
import { throttle, uniqBy } from 'lodash';
import i18n from '@/language/i18n';

const BkSchemaForm = createForm();
// 必填校验
const requiredRule = {
  required: true,
  message: i18n.t('该字段是必填项'),
  trigger: 'blur',
};

export default {
  components: {
    paasPluginTitle,
    BkSchemaForm,
  },
  data() {
    return {
      form: {
        pd_id: '',
        plugin_id: '',
        name: '',
        language: '',
        applicableLanguage: '',
        templateName: '',
        repositoryTemplateUrl: '',
      },
      requiredRules: [requiredRule],
      rules: {
        pd_id: [requiredRule],
        plugin_id: [requiredRule],
        name: [requiredRule],
        language: [requiredRule],
        applicableLanguage: [requiredRule],
        templateName: [requiredRule],
        repositoryTemplateUrl: [requiredRule],
      },
      pluginTypeList: [],
      pluginTypeData: { plugin_type: {}, schema: {} },
      pluginLanguage: [],
      languageData: {},
      applicableLanguageList: [],
      pluginTemplateList: [],
      extraFields: {},
      buttonLoading: false,
      curPluginItem: {},
      pdIdPlaceholder: '',
      namePlaceholder: '',
      pdIdMaxLength: 16,
      nameMaxLength: 20,
      isLoading: true,
      schemaFormData: {},
      schema: {},
      layout: {
        prop: 0,
        container: {
          display: 'grid',
          gridGap: '0',
        },
      },
      isSticky: false,
      // AI空间
      bkAiSpaces: {
        spaceId: '',
        spacesList: [],
      },
    };
  },
  computed: {
    curPluginInfo() {
      const curPluginData = this.pluginTypeList.filter((item) => item.plugin_type.id === this.form.pd_id);
      return this.form.pd_id ? curPluginData[0] : this.pluginTypeList[0];
    },
    defaultPluginType() {
      return this.$route.query.plugin_type;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    developmentLanguages() {
      return uniqBy(this.pluginLanguage, 'language');
    },
    // AI插件由前端特殊处理
    isAiPlugin() {
      return this.form.pd_id === 'bk-saas' && this.form.templateName === 'bk-ai-plugin-python';
    },
  },
  watch: {
    'form.plugin_id'(value) {
      if (this.pluginTypeData.schema.repository_group && value) {
        this.form.repositoryTemplateUrl = `${
          this.pluginTypeData.schema.repository_group
        }${value.toLocaleLowerCase()}.git`;
      }
    },
    'form.pd_id'(value) {
      const selected = this.pluginTypeList.filter((item) => item.plugin_type.id === value);
      this.curPluginItem = selected[0];
      this.addRules();
      this.changePlaceholder();
    },
    isAiPlugin(newVal) {
      if (newVal && !this.bkAiSpaces.spacesList?.length) {
        this.getBkaidevSpaces();
      }
    },
  },
  mounted() {
    this.fetchPluginTypeList();
    window.addEventListener('resize', this.handleBottomAdsorption);
    this.$once('hook:beforeDestroy', () => {
      window.removeEventListener('resize', this.handleBottomAdsorption);
    });
  },
  methods: {
    // 获取插件类型数据
    async fetchPluginTypeList() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginsTypeList');
        // 当前是否存在该插件类型
        let isQuery = false;
        this.pluginTypeList = res.map((e) => {
          if (e.plugin_type.id === this.defaultPluginType) {
            isQuery = true;
          }
          e.name = e.plugin_type.name;
          // 多选表单添加必填校验
          e.properties = this.addValidation(e.schema.extra_fields);
          return e;
        });
        // 参数指定插件类型，没有指定默认为第一项
        this.form.pd_id = isQuery ? this.defaultPluginType : res[0].plugin_type.id;

        // 默认为第一项
        const properties = this.pluginTypeList[0]?.schema?.extra_fields;
        // 根据 extra_fields_order 字段排序
        const extraFieldsOrder = this.pluginTypeList[0]?.schema.extra_fields_order || [];
        const sortdProperties = this.sortdSchema(extraFieldsOrder, properties);
        this.schema = {
          type: 'object',
          required: this.getRequiredFields(sortdProperties),
          properties: sortdProperties,
        };
        this.addRules();
        this.changePlaceholder();
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
          this.handleBottomAdsorption();
        }, 200);
      }
    },
    // 多选添加校验
    addValidation(properties) {
      if (!Object.keys(properties).length) {
        return properties;
      }
      for (const key in properties) {
        if (
          Object.prototype.hasOwnProperty.call(properties[key], 'ui:rules') &&
          Array.isArray(properties[key].default)
        ) {
          // 多选校验
          properties[key]['ui:rules'] = [
            {
              validator: '{{ $self.value.length > 0 }}',
              message: this.$t('必填项'),
            },
          ];
        }
      }
      return properties;
    },
    /**
     * 根据 fieldsOrder 字段排序 schema
     * @param  {Array} fieldsOrder 排序字段列表
     * @param  {Object} properties 数据
     */
    sortdSchema(fieldsOrder = [], properties) {
      const sortdProperties = {};
      if (fieldsOrder.length) {
        fieldsOrder.map((key) => {
          sortdProperties[key] = properties[key];
        });
        return sortdProperties;
      }
      return properties;
    },
    // 获取必填项字段列表
    getRequiredFields(properties) {
      if (!Object.keys(properties).length) {
        return;
      }
      const requiredFields = [];
      for (const key in properties) {
        if (Object.prototype.hasOwnProperty.call(properties[key], 'ui:rules')) {
          requiredFields.push(key);
        }
      }
      return requiredFields;
    },
    // 添加校验规则
    addRules() {
      if (this.curPluginInfo.schema) {
        this.pdIdMaxLength = this.curPluginInfo.schema.id.maxlength || 16;
        this.nameMaxLength = this.curPluginInfo.schema.name.maxlength || 20;
      }
      const rulesPluginId = [requiredRule];
      const rulesName = [requiredRule];
      // 插件ID
      rulesPluginId.push({
        regex: new RegExp(this.curPluginInfo.schema.id.pattern),
        message: this.$t(this.curPluginInfo.schema.id.description),
        trigger: 'blur',
      });
      rulesPluginId.push({
        max: this.curPluginInfo.schema.id.maxlength || 16,
        message: this.$t('不能多于{maxLength}个字符', { maxLength: this.curPluginInfo.schema.id.maxlength || 16 }),
        trigger: 'blur',
      });
      // 插件名称
      rulesName.push({
        regex: new RegExp(this.curPluginInfo.schema.name.pattern),
        message: this.$t(this.curPluginInfo.schema.name.description),
        trigger: 'blur',
      });
      rulesName.push({
        max: this.curPluginInfo.schema.name.maxlength || 20,
        message: this.$t('不能多于{maxLength}个字符', { maxLength: this.curPluginInfo.schema.id.maxlength || 20 }),
        trigger: 'blur',
      });
      this.rules.plugin_id = rulesPluginId;
      this.rules.name = rulesName;
    },
    changePlaceholder() {
      this.pdIdPlaceholder =
        this.$t(this.curPluginInfo.schema.id.description) ||
        this.$t('由小写字母、数字、连字符(-)组成，长度小于 16 个字符');
      this.namePlaceholder =
        this.$t(this.curPluginInfo.schema.name.description) ||
        this.$t('由汉字、英文字母、数字组成，长度小于 20 个字符');
    },
    // 选中具体插件类型
    changePluginType(value) {
      this.schemaFormData = {};
      this.resetPluinParams();
      this.form.pd_id = value;

      // 获取当前选中的插件类型数据
      this.pluginTypeData = this.pluginTypeList.find((e) => e.plugin_type.id === value);
      const { schema } = this.pluginTypeData;
      // 代码仓库链接
      this.form.repositoryTemplateUrl = this.form.plugin_id
        ? `${schema.repository_group}${this.form.plugin_id}.git`
        : schema.repository_template;

      this.pluginLanguage = schema.init_templates;
      this.extraFields = schema.extra_fields;

      // schema 排序
      const extraFieldsOrder = schema.extra_fields_order || [];
      const properties = this.sortdSchema(extraFieldsOrder, this.pluginTypeData.properties);
      // 根据数据添加必填字段
      this.schema = {
        type: 'object',
        required: this.getRequiredFields(properties),
        properties,
      };

      this.$nextTick(() => {
        this.handleBottomAdsorption();
        this.closeSpellcheck();
        this.validatePluginField('plugin_id');
      });
    },
    // 切换插件重置参数
    resetPluinParams() {
      this.form.language = '';
      this.form.templateName = '';
    },
    // 选中具体插件开发语言
    changePluginLanguage(value) {
      this.languageData = this.pluginLanguage.find((e) => e.id === value) || {};
      // 初始化模板
      this.pluginTemplateList = this.pluginLanguage.filter((e) => e.language === this.languageData.language);
      this.form.templateName = '';
      this.$nextTick(() => {
        this.validatePluginField('plugin_id');
      });
    },
    // 富文本编辑
    onEditorChange(e) {
      this.$set(this.formData, 'description', e.html);
    },

    submitPluginForm() {
      const formArray = [this.$refs.pluginForm.validate()];
      if (this.$refs.bkForm) {
        formArray.push(this.$refs.bkForm.validate());
      }
      if (this.isAiPlugin && this.$refs.moreForm) {
        formArray.push(this.$refs.moreForm.validate());
      }
      Promise.all(formArray)
        .then(() => {
          this.buttonLoading = true;
          this.save();
        })
        .catch((validator) => {
          this.buttonLoading = false;
          console.warn(validator);
        });
    },

    // 提交
    async save() {
      try {
        this.buttonLoading = true;
        const params = {
          id: this.form.plugin_id,
          name: this.form.name,
          template: this.form.templateName,
          pd_id: this.form.pd_id,
          extra_fields: this.schemaFormData,
          // 仅当是 AI 插件时才包含 ai_extra_fields 参数
          ...(this.isAiPlugin && {
            ai_extra_fields: {
              space_id: this.bkAiSpaces.spaceId,
            },
          }),
        };
        const res = await this.$store.dispatch('plugin/savePlugins', params);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('插件创建成功！'),
        });
        const pluginDataKey = `pluginInfo${Math.random().toString(36)}`;
        const data = {
          name: this.curPluginItem.name,
          docs: this.curPluginItem.plugin_type.docs,
          pluginName: params.name,
        };
        localStorage.setItem(pluginDataKey, JSON.stringify(data));
        // 插件引导页
        this.$router.push({
          name: 'createPluginSuccess',
          params: { pluginTypeId: res.pd_id, id: res.id },
          query: {
            key: pluginDataKey,
          },
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.buttonLoading = false;
      }
    },

    // 取消
    back() {
      this.$router.push({
        name: 'plugin',
      });
    },

    async request(url) {
      url = `${window.BACKEND_URL}/api/bk_plugin_distributors/`;
      try {
        const data = await http.get(url);
        return data.map((e) => ({ label: e.name, value: e.code_name }));
      } catch (error) {
        console.warn(error);
      }
    },

    // 获取插件指引偏移量
    getGuideOffset() {
      const guideDom = document.querySelector('.plugin-guide');
      if (guideDom) return -(guideDom?.offsetWidth + 15) || -78;
      return -78;
    },

    // 处理 footer 是否吸附
    handleBottomAdsorption: throttle(function () {
      const contentHeight = document.querySelector('.bk-create-plugin-warp')?.offsetHeight;
      const reserveHeight = this.isShowNotice ? 70 : 110;
      const viewportHeight = window.innerHeight - reserveHeight;
      this.isSticky = contentHeight > viewportHeight;
    }, 220),

    // 去除拼写波浪线提示
    closeSpellcheck() {
      const textarea = document.querySelector('.bk-form textarea');
      textarea && textarea.setAttribute('spellcheck', false);
    },

    // 获取AI空间下拉列表
    async getBkaidevSpaces() {
      try {
        const res = await this.$store.dispatch('plugin/getBkaidevSpaces');
        this.bkAiSpaces.spacesList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 校验某一项 form-item
    validatePluginField(fieldName) {
      if (this.$refs.pluginForm) {
        this.$refs.pluginForm.validateField(fieldName).catch((e) => {
          console.error(`Validation error on field ${fieldName}:`, e);
        });
      } else {
        console.warn('pluginForm reference not available');
      }
    },

    /**
     * 根据当前表单类型切换校验规则
     */
    templateChange() {
      if (this.form.pd_id === 'bk-saas') {
        // 当模板类型为 ai 插件时，需要校验插件的id必须以 ai- 开头
        this.rules.plugin_id = this.togglePrefixRule(this.rules.plugin_id, this.isAiPlugin);
      }
      this.validatePluginField('plugin_id');
    },

    /**
     * ai插件动态切换前缀校验规则
     * @param {Array} validationRules 原始校验规则数组
     * @param {Boolean} needPrefix 是否需要添加前缀规则
     * @returns {Array} 更新后的校验规则数组
     */
    togglePrefixRule(validationRules, needPrefix) {
      const PREFIX_RULE = {
        regex: /^ai-/,
        message: this.$t('蓝鲸 AI 插件 ID 必须以 ai- 开头'),
        trigger: 'blur',
      };
      // 查找是否已存在前缀规则
      const hasPrefixRule = validationRules.some((rule) => rule.regex?.source === PREFIX_RULE.regex.source);
      // 需要添加前缀但不存在时添加
      if (needPrefix && !hasPrefixRule) {
        return [...validationRules, PREFIX_RULE];
      }
      // 不需要前缀但存在时移除
      if (!needPrefix && hasPrefixRule) {
        return validationRules.filter((rule) => rule.regex?.source !== PREFIX_RULE.regex.source);
      }
      // 其他情况返回原规则
      return validationRules;
    },
  },
};
</script>
<style lang="scss" scoped>
.bk-create-plugin-warp {
  width: calc(100% - 366px);
  margin: 0 auto;
  .info-container {
    padding: 12px 130px 24px 24px;

    &.mb75 {
      margin-bottom: 75px;
    }
  }
  .base-info-tit {
    font-weight: Bold;
    color: #313238;
    font-size: 14px;
    margin-bottom: 16px;
  }
  .copy-icon {
    position: absolute;
    top: 11px;
    right: 10px;
    color: #3a84ff;
    cursor: pointer;
  }
  .mt16 {
    margin-top: 16px;
  }
  .mb60 {
    margin-bottom: 60px;
  }
  .w480 {
    width: 480px;
  }
  .tips {
    color: #979ba5;
    font-size: 12px;
  }
  .plugin-info {
    background: #f0f8ff;
    border: 1px solid #a3c5fd;
    font-size: 12px;
    color: #666666;
    padding: 0 9px;
  }
  .edit-form-item {
    height: 300px;
    .editor {
      width: 800px;
      height: 200px;
    }
  }
}
.create-button-warp {
  margin-top: 32px;
  margin-bottom: 28px;

  &.sticky {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    height: 48px;
    line-height: 48px;
    padding-left: 183px;
    background: #fafbfd;
    box-shadow: 0 -1px 0 0 #dcdee5;
    margin: 0;
    z-index: 99;
  }
}
.guide-container {
  background: #fff;
  .guide-item {
    cursor: pointer;
    height: 64px;
    img {
      width: 48px;
      height: 48px;
    }
    .guide-plugin-name {
      font-size: 14px;
      color: #313238;
    }
    .guide-plugin-desc {
      line-height: 24px;
      font-size: 12px;
      // 宽度
      color: #63656e;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .guide-right {
      overflow: hidden;
    }
  }
  .guide-item:hover {
    background: #e7f1fe;
  }
}
.plugin-guide {
  font-size: 12px;
  cursor: pointer;
  margin-left: 10px;
  position: absolute;
  top: 0;
}
.plugin-top-title {
  margin: 12px 0 14px;
}
.bk-form-warp /deep/ .bk-schema-form-item--error {
  [error] {
    border-color: #f5222d !important;
  }
  .bk-schema-form-item__error-tips {
    color: #f5222d;
  }
}
.bk-form-warp :deep(.bk-form-item) {
  .bk-form-content p.mt5 {
    color: #979ba5 !important;
  }
}
.plugin-type {
  position: relative;
}
.mr8 {
  margin-right: 8px;
}
</style>
<style lang="scss">
.guide-input input {
  border: none;
  border-bottom: 1px solid #c4c6cc;
}

.plugin-type-custom .is-selected .guide-container {
  background-color: #f4f6fa !important;
}
</style>
