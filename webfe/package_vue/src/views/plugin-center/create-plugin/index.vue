<template>
  <div class="bk-create-plugin-warp mt30">
    <div class="base-info-tit">
      {{ $t('基本信息') }}
    </div>
    <bk-form
      ref="pluginForm"
      :model="form"
      :rules="rules"
    >
      <bk-form-item
        :label="$t('插件类型')"
        :required="true"
        :icon-offset="557"
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
                <!-- <bk-input :left-icon="'bk-icon icon-search'" class="guide-input mb10" v-model="form.type" :placeholder="$t('输入关键字')"></bk-input> -->
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
        :label="$t('插件标识')"
        :required="true"
        :icon-offset="557"
        :property="'plugin_id'"
      >
        <bk-input
          v-model="form.plugin_id"
          class="w480"
          :placeholder="$t('唯一标识，创建后不可修改；由小写字母、数字、连接符(-)组成，须以字母开头')"
        />
      </bk-form-item>
      <bk-form-item
        :label="$t('插件名称')"
        :required="true"
        :icon-offset="557"
        :property="'name'"
      >
        <bk-input
          v-model="form.name"
          class="w480"
          :placeholder="$t('由汉字、英文字母、数字组成')"
        />
      </bk-form-item>
      <bk-form-item
        :label="$t('开发语言')"
        :required="true"
        :icon-offset="557"
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
        :icon-offset="557"
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
        :icon-offset="557"
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
        :icon-offset="557"
        :property="'repositoryTemplateUrl'"
      >
        <bk-input
          v-model="form.repositoryTemplateUrl"
          class="w480"
          disabled
          :placeholder="$t('代码仓库')"
        />
        <div class="tips">
          {{ $t('将自动创建该开源仓库，并将模板代码初始化到仓库中') }}
        </div>
      </bk-form-item>
    </bk-form>
    <template v-if="Object.keys(extraFields).length">
      <div class="base-info-tit">
        更多信息
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
              数据源接入
            </bk-radio>
            <bk-radio
              :key="'数据入库'"
              :value="2"
            >
              数据入库
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
  </div>
</template>
<script>
    import { quillEditor } from 'vue-quill-editor';
    import 'quill/dist/quill.core.css';
    import 'quill/dist/quill.snow.css';
    import 'quill/dist/quill.bubble.css';
    export default {
        components: {
            quillEditor
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
                        },
                        {
                            regex: /^[a-z][a-z0-9-]*$/,
                            message: this.$t('由小写字母、数字、连接符(-)组成，须以字母开头'),
                            trigger: 'blur'
                        }
                    ],
                    name: [
                        {
                            required: true,
                            message: this.$t('该字段是必填项'),
                            trigger: 'blur'
                        },
                        {
                            regex: /[a-zA-Z\d\u4e00-\u9fa5]+/,
                            message: this.$t('由汉字、英文字母、数字组成'),
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
                    placeholder: '@通知他人，ctrl+enter快速提交'
                },
                curPluginItem: {}
            };
        },
        watch: {
            'form.plugin_id' (value) {
                if (this.pluginTypeData.schema.repository_group && value) {
                    console.log('this.pluginTypeData.schema.repository_group', this.pluginTypeData.schema.repository_group);
                    this.form.repositoryTemplateUrl = `${this.pluginTypeData.schema.repository_group}${value}.git`;
                }
            },
            'form.pd_id' (value) {
                const selected = this.pluginTypeList.filter(item => item.plugin_type.id === value);
                this.curPluginItem = selected[0];
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
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: e.message
                    });
                }
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
                    await this.$store.dispatch('plugin/savePlugins', params);
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('插件创建成功！')
                    });
                    this.back();
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
    width: 1180px;
    margin: 0 auto;
    .base-info-tit{
        margin: 20px 0;
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
</style>
<style>
    .guide-input input {
        border: none;
        border-bottom: 1px solid #c4c6cc;
    }
</style>
