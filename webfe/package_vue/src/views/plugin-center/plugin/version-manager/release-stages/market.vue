<template>
  <!-- 完善市场信息模块 -->
  <div class="plugin-container">
    <div
      id="release-box"
      class="release-warp"
    >
      <div class="info-mt">
        <bk-form
          ref="visitForm"
          :model="form"
          :rules="rules"
          :label-width="100"
        >
          <bk-form-item
            class="w600"
            :label="$t('应用分类')"
            :required="true"
            :property="'category'"
          >
            <bk-select
              v-model="form.category"
              :loading="cateLoading"
              :clearable="false"
              :placeholder="$t('应用分类')"
            >
              <bk-option
                v-for="(option, index) in categoryList"
                :id="option.value"
                :key="index"
                :name="option.name"
              />
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="$t('应用简介')"
            :required="true"
            :property="'introduction'"
          >
            <bk-input v-model="form.introduction" />
          </bk-form-item>
          <bk-form-item
            :label="$t('应用联系人')"
            :required="true"
            property="contact"
          >
            <user v-model="form.contact" />
          </bk-form-item>
          <bk-form-item
            class="edit-form-item"
            :label="$t('详细描述')"
            :required="true"
            :property="'description'"
          >
            <quill-editor
              v-model="form.description"
              class="editor"
              :options="editorOption"
              @change="onEditorChange($event)"
            />
          </bk-form-item>
        </bk-form>
      </div>
    </div>
  </div>
</template>
<script>
    import _ from 'lodash';
    import user from '@/components/user';
    import { quillEditor } from 'vue-quill-editor';
    import 'quill/dist/quill.core.css';
    import 'quill/dist/quill.snow.css';
    import 'quill/dist/quill.bubble.css';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import stageBaseMixin from './stage-base-mixin';

    export default {
        components: {
            user,
            quillEditor
        },
        mixins: [stageBaseMixin, pluginBaseMixin],
        props: {
            stageData: Object
        },
        data: function () {
            return {
                winHeight: 300,
                cateLoading: true,
                categoryList: [],
                form: {
                    category: '',
                    introduction: '',
                    description: '',
                    contact: []
                },
                editorOption: {
                        placeholder: '开始编辑...'
                    },
                rules: {
                    category: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ],
                    introduction: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ],
                    description: [
                        {
                            required: true,
                            message: this.$t('请输入'),
                            trigger: 'blur'
                        }
                    ],
                    contact: [
                        {
                            required: true,
                            message: this.$t('该字段为必填项'),
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },
        async mounted () {
            await Promise.all([this.fetchCategoryList(), this.fetchMarketInfo()]);
        },
        methods: {
            // 获取市场信息
            async fetchMarketInfo () {
                try {
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId
                    };
                    const res = await this.$store.dispatch('plugin/getMarketInfo', params);
                    this.form = res;
                    this.form.contact = res.contact && res.contact.split(',') || [];
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 应用分类
            async fetchCategoryList () {
                try {
                    const params = {
                        pdId: this.pdId
                    };
                    const res = await this.$store.dispatch('plugin/getCategoryList', params);
                    this.categoryList = res.category;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.cateLoading = false;
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 200);
                }
            },
            // 富文本编辑
            onEditorChange (e) {
                this.$set(this.form, 'description', e.html);
            },
            // 保存
            async nextStage (resolve) {
              await this.$refs.visitForm.validate().then(async () => {
                try {
                    const data = _.cloneDeep(this.form);
                    data.contact = data.contact.join(',');
                    const params = {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        data
                    };
                    await this.$store.dispatch('plugin/saveMarketInfo', params);
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('保存成功!')
                    });
                    await resolve();
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.cateLoading = false;
                }
              });
            }
        }
    };
</script>
