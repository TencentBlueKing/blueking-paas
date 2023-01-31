<template>
  <div class="bk-create-plugin-warp mt30">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="create-plugin-loading"
    >
      <paas-plugin-title />
      <!-- 返回 -->
      <div class="base-info-tit">
        {{ $t('基本信息') }}
      </div>
      <bk-form
        ref="pluginForm"
        style="width: 730px;"
        :model="form"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('插件类型')"
          :required="true"
          :icon-offset="105"
          :property="'pd_id'"
        >
          <div class="flex-row">
            <bk-select
              v-model="form.pd_id"
              class="w480"
              ext-cls="slot-class"
              searchable
              :clearable="false"
              :placeholder="$t('插件类型')"
              @change="changePluginType"
            >
              <bk-option
                v-for="(option, index) in pluginTypeList"
                :id="option.plugin_type.id"
                :key="index"
                v-bind="option"
              >
                <div
                  id="guide-wrap"
                  class="guide-container"
                >
                  <div class="guide-list">
                    <div class="flex-row align-items-center guide-item">
                      <img
                        :src="option.plugin_type.logo"
                        onerror="this.src='/static/images/plugin-default.svg'"
                      >
                      <div class="guide-right pl10">
                        <div class="guide-plugin-name">
                          {{ option.plugin_type.name }}
                        </div>
                        <div
                          v-bk-tooltips.right="option.plugin_type.description"
                          class="guide-plugin-desc"
                        >
                          {{ option.plugin_type.description }}
                        </div>
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
            >
              <i class="paasng-icon paasng-question-circle" />
              {{ $t('插件指引') }}
            </a>
          </div>
          <div
            v-if="curPluginItem.plugin_type && curPluginItem.plugin_type.approval_config && curPluginItem.plugin_type.approval_config.enabled"
            class="plugin-info w480 mt15"
          >
            <i
              style="color: #3A84FF;"
              class="paasng-icon paasng-info-circle"
            />
            {{ curPluginItem.plugin_type.approval_config.tips }}
            <a
              target="_blank"
              :href="curPluginItem.plugin_type.approval_config.docs"
            >{{ $t('详见文档') }}</a>
          </div>
        </bk-form-item>
        <bk-form-item
          :label="$t('插件 ID')"
          :required="true"
          :icon-offset="105"
          :property="'plugin_id'"
          error-display-type="normal"
        >
          <bk-input
            v-model="form.plugin_id"
            class="w480"
            :placeholder="$t(pdIdPlaceholder)"
            :maxlength="pdIdMaxLength"
            :show-word-limit="true"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('插件名称')"
          :required="true"
          :icon-offset="105"
          :property="'name'"
          :rules="rules.name"
          error-display-type="normal"
        >
          <bk-input
            v-model="form.name"
            class="w480"
            :placeholder="$t(namePlaceholder)"
            :maxlength="nameMaxLength"
            :show-word-limit="true"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('开发语言')"
          :required="true"
          :icon-offset="105"
          :property="'language'"
        >
          <bk-select
            v-model="form.language"
            class="w480"
            :clearable="false"
            :placeholder="$t('开发语言')"
            @change="changePluginLanguage"
          >
            <bk-option
              v-for="(option, index) in pluginLanguage"
              :id="option.id"
              :key="index"
              :name="option.language"
            />
          </bk-select>
        </bk-form-item>
        <bk-form-item
          v-if="languageData.applicableLanguage"
          :label="$t('适用语言')"
          :required="true"
          :icon-offset="105"
          :property="'applicableLanguage'"
        >
          <bk-select
            v-model="form.applicableLanguage"
            class="w480"
            :clearable="false"
            :placeholder="$t('适用语言')"
          >
            <bk-option
              v-for="(option, index) in applicableLanguageList"
              :id="option.id"
              :key="index"
              :name="option.text"
            />
          </bk-select>
        </bk-form-item>
        <bk-form-item
          :label="$t('初始化模板')"
          :required="true"
          :icon-offset="105"
          :property="'templateName'"
        >
          <bk-select
            v-model="form.templateName"
            class="w480"
            :clearable="false"
            :placeholder="$t('初始化模板')"
          >
            <bk-option
              v-for="(option, index) in pluginTemplateList"
              :id="option.id"
              :key="index"
              :name="option.name"
            />
          </bk-select>
        </bk-form-item>
        <bk-form-item
          :label="$t('代码仓库')"
          :required="true"
          :icon-offset="105"
          :property="'repositoryTemplateUrl'"
        >
          <bk-input
            v-model="form.repositoryTemplateUrl"
            class="w480"
            disabled
            :placeholder="$t('代码仓库')"
          />
          <div class="tips">
            {{ $t('将自动创建该开源仓库，将模板代码初始化到仓库中，并将创建者初始化为仓库管理员') }}
          </div>
        </bk-form-item>
      </bk-form>
      <template v-if="Object.keys(extraFields).length">
        <div class="base-info-tit">
          {{ $t('更多信息') }}
        </div>
        <bk-form
          ref="form"
          :model="form"
          :rules="informationRules"
        >
          <bk-form-item
            :label="$t('连接器类型')"
            :required="true"
            :property="'type'"
          >
            <bk-radio-group v-model="form.type">
              <bk-radio
                :key="'数据源接入'"
                :value="1"
              >
                {{ $t('数据源接入') }}
              </bk-radio>
              <bk-radio
                :key="'数据入库'"
                :value="2"
              >
                {{ $t('数据入库') }}
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item
            :label="$t('建议使用场景')"
            :required="true"
            :property="'type'"
          >
            <div class="flex-row">
              <bk-select
                v-model="form.type"
                class="w480"
                :clearable="false"
                :placeholder="$t('建议使用场景')"
              >
                <bk-option
                  v-for="(option, index) in pluginTypeList"
                  :id="option.id"
                  :key="index"
                  :name="option.text"
                />
              </bk-select>
            </div>
          </bk-form-item>
          <bk-form-item
            :label="$t('建议日数据量')"
            :required="true"
            :property="'type'"
          >
            <bk-select
              v-model="form.type"
              class="w480"
              :clearable="false"
              :placeholder="$t('建议日数据量')"
            >
              <bk-option
                v-for="(option, index) in pluginTypeList"
                :id="option.id"
                :key="index"
                :name="option.text"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('查询模式')"
            :required="true"
            :property="'type'"
          >
            <bk-select
              v-model="form.type"
              class="w480"
              :clearable="false"
              :placeholder="$t('查询模式')"
            >
              <bk-option
                v-for="(option, index) in pluginTypeList"
                :id="option.id"
                :key="index"
                :name="option.text"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            class="edit-form-item"
            :label="$t('使用说明')"
            :required="true"
            :property="'type'"
          >
            <quill-editor
              v-model="form.type"
              class="editor"
              :options="editorOption"
              @change="onEditorChange($event)"
            />
          </bk-form-item>
        </bk-form>
      </template>

      <div class="button-warp">
        <bk-button
          :theme="'primary'"
          :title="$t('提交')"
          class="mr10"
          :loading="buttonLoading"
          @click="submitPluginForm"
        >
          {{ $t('提交') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          :title="$t('取消')"
          class="mr10"
          @click="back"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
    import { quillEditor } from 'vue-quill-editor';
    import 'quill/dist/quill.core.css';
    import 'quill/dist/quill.snow.css';
    import 'quill/dist/quill.bubble.css';
    import paasPluginTitle from '@/components/pass-plugin-title';
    export default {
        components: {
            quillEditor,
            paasPluginTitle
        },
        data () {
            return {
                form: {
                    pd_id: '',
                    plugin_id: '',
                    name: '',
                    language: '',
                    applicableLanguage: '',
                    templateName: '',
                    repositoryTemplateUrl: ''
                },
                rules: {
                    pd_id: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    plugin_id: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    name: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],

                    language: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    applicableLanguage: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    templateName: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ],
                    repositoryTemplateUrl: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        }
                    ]
                },
                informationRules: {},
                pluginTypeList: [],
                pluginTypeData: { plugin_type: {}, schema: {} },
                pluginLanguage: [],
                languageData: {},
                applicableLanguageList: [],
                pluginTemplateList: [],
                extraFields: {},
                buttonLoading: false,
                editorOption: {
                    placeholder: this.$t('@通知他人，ctrl+enter快速提交')
                },
                curPluginItem: {},
                pdIdPlaceholder: '',
                namePlaceholder: '',
                pdIdMaxLength: 16,
                nameMaxLength: 20,
                isLoading: true
            };
        },
        computed: {
            curPluginInfo () {
                const curPluginData = this.pluginTypeList.filter(item => item.plugin_type.id === this.form.pd_id);
                return this.form.pd_id ? curPluginData[0] : this.pluginTypeList[0];
            }
        },
        watch: {
            'form.plugin_id' (value) {
                if (this.pluginTypeData.schema.repository_group && value) {
                    this.form.repositoryTemplateUrl = `${this.pluginTypeData.schema.repository_group}${value}.git`;
                }
            },
            'form.pd_id' (value) {
                const selected = this.pluginTypeList.filter(item => item.plugin_type.id === value);
                this.curPluginItem = selected[0];
                this.addRules();
                this.changePlaceholder();
            }
        },
        mounted () {
            this.fetchPluginTypeList();
        },
        methods: {
            // 获取插件类型数据
            async fetchPluginTypeList () {
                try {
                    const res = await this.$store.dispatch('plugin/getPluginsTypeList');
                    this.pluginTypeList = res && res.map(e => {
                        e.name = e.plugin_type.name;
                        return e;
                    });
                    this.addRules();
                    this.changePlaceholder();
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 添加校验规则
            addRules () {
                if (this.curPluginInfo.schema) {
                    this.pdIdMaxLength = this.curPluginInfo.schema.id.maxlength || 16;
                    this.nameMaxLength = this.curPluginInfo.schema.name.maxlength || 20;
                }
                const baseRule = {
                    required: true,
                    message: this.$t('该字段是必填项'),
                    trigger: 'blur'
                };
                const rulesPluginId = [baseRule];
                const rulesName = [baseRule];
                // 插件ID
                rulesPluginId.push({
                    regex: new RegExp(this.curPluginInfo.schema.id.pattern),
                    message: this.$t(this.curPluginInfo.schema.id.description),
                    trigger: 'blur change'
                });
                rulesPluginId.push({
                    max: this.curPluginInfo.schema.id.maxlength || 16,
                    message: this.$t(`不能多于{maxLength}个字符`, { maxLength: this.curPluginInfo.schema.id.maxlength || 16 }),
                    trigger: 'blur change'
                });
                // 插件名称
                rulesName.push({
                    regex: new RegExp(this.curPluginInfo.schema.name.pattern),
                    message: this.$t(this.curPluginInfo.schema.name.description),
                    trigger: 'blur change'
                });
                rulesName.push({
                    max: this.curPluginInfo.schema.name.maxlength || 20,
                    message: this.$t(`不能多于{maxLength}个字符`, { maxLength: this.curPluginInfo.schema.id.maxlength || 20 }),
                    trigger: 'blur change'
                });
                this.rules.plugin_id = rulesPluginId;
                this.rules.name = rulesName;
            },
            changePlaceholder () {
                this.pdIdPlaceholder = this.curPluginInfo.schema.id.description || this.$t('由小写字母、数字、连字符(-)组成，长度小于 16 个字符');
                this.namePlaceholder = this.curPluginInfo.schema.name.description || this.$t('由汉字、英文字母、数字组成，长度小于 20 个字符');
            },
            // 选中具体插件类型
            changePluginType (value) {
                this.form.pd_id = value;
                this.pluginTypeData = this.pluginTypeList.find(e => e.plugin_type.id === value);
                this.form.repositoryTemplateUrl = this.form.plugin_id
                    ? `${this.pluginTypeData.schema.repository_group}${this.form.plugin_id}.git`
                    : this.pluginTypeData.schema.repository_template;
                this.pluginLanguage = this.pluginTypeData.schema.init_templates;
                this.extraFields = this.pluginTypeData.schema.extra_fields;
            },
            // 选中具体插件开发语言
            changePluginLanguage (value) {
                this.languageData = this.pluginLanguage.find(e => e.id === value);
                // 初始化模板
                this.pluginTemplateList = this.pluginLanguage.filter(e => e.language === this.languageData.language);
            },
            // 富文本编辑
            onEditorChange (e) {
                this.$set(this.formData, 'description', e.html);
            },

            submitPluginForm () {
                this.$refs.pluginForm.validate().then(validator => {
                    this.buttonLoading = true;
                    this.save();
                }).catch(() => {
                    this.buttonLoading = false;
                });
            },

            // 提交
            async save () {
                try {
                    this.buttonLoading = true;
                    const params = {
                        id: this.form.plugin_id,
                        name: this.form.name,
                        template: this.form.templateName,
                        pd_id: this.form.pd_id,
                        extra_fields: this.extraFields
                    };
                    const res = await this.$store.dispatch('plugin/savePlugins', params);
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('插件创建成功！')
                    });
                    this.$router.push({
                        name: 'pluginSummary',
                        params: { pluginTypeId: res.pd_id, id: res.id }
                    });
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                } finally {
                    this.buttonLoading = false;
                }
            },

            // 取消
            back () {
                this.$router.push({
                    name: 'plugin'
                });
            }
        }
    };
</script>
<style lang="scss" scoped>
.bk-create-plugin-warp {
    padding: 28px 0 44px;
    width: calc(100% - 120px);
    margin: 0 auto;
    min-height: calc(100vh - 120px);
    .base-info-tit{
        margin: 5px 0 20px;
        font-weight: Bold;
        color: #63656E;
        padding: 5px 16px;
        background: #F5F7FA;
        border-radius: 2px;
    }
    .w480{
        width: 480px;
    }
    .tips{
        color: #979ba5;
        font-size: 12px;
    }
    .plugin-info{
        background: #F0F8FF;
        border: 1px solid #A3C5FD;
        font-size: 12px;
        color: #666666;
        padding: 0 9px;
    }
    .edit-form-item{
        height: 300px;
        .editor{
            width: 800px;
            height: 200px;
        }
    }
}
.button-warp {
    margin: 30px 0 0 150px;
}
.guide-container{
    background: #fff;
    .guide-item{
        cursor: pointer;
        height: 64px;
        img{
            width: 48px;
            height: 48px;
        }
        .guide-plugin-name{
            font-size: 14px;
            color: #313238;
        }
        .guide-plugin-desc{
            line-height: 24px;
            font-size: 12px;
            color: #63656E;
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
}
.plugin-top-title {
    margin: 12px 0 14px;
}
</style>
<style>
    .guide-input input {
        border: none;
        border-bottom: 1px solid #c4c6cc;
    }
</style>
