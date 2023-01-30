<template>
  <div :class="`container visible-range ${isEditorHeight ? 'beyond-container' : ''}`">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="plugin-market-info-loading"
      class="app-container middle"
    >
      <div :class="`app-container middle ${isEditorHeight ? 'beyond' : ''}`">
        <paas-plugin-title />
        <div class="market-Info plugin-base-info">
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

        <div
          class="btn-warp mt5"
        >
          <bk-button
            theme="primary"
            @click="handlerSave"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            theme="default"
            style="margin-left: 4px;"
            @click="goBack"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
    import paasPluginTitle from '@/components/pass-plugin-title';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import user from '@/components/user';
    import { quillEditor } from 'vue-quill-editor';
    import { addQuillTitle } from '@/common/quill-title.js';
    import { TOOLBAR_OPTIONS } from '@/common/constants';
    import 'quill/dist/quill.core.css';
    import 'quill/dist/quill.snow.css';
    import 'quill/dist/quill.bubble.css';
    import _ from 'lodash';
    export default {
        components: {
            paasPluginTitle,
            quillEditor,
            user
        },
        mixins: [pluginBaseMixin],
        data () {
            return {
              form: {
                  category: '',
                  introduction: '',
                  description: '',
                  contact: []
              },
              categoryList: [],
              cateLoading: true,
              isLoading: true,
              editorOption: {
                  placeholder: this.$t('开始编辑...'),
                  modules: {
                      toolbar: TOOLBAR_OPTIONS
                  }
              },
              isEditorHeight: false,
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
        mounted () {
            this.fetchMarketInfo();
            this.fetchCategoryList();
            this.$nextTick(() => {
                addQuillTitle();
            });
        },
        methods: {
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
                    }, 300);
                }
            },
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
                    }, 300);
                }
            },
            // 保存
            async handlerSave () {
                this.$refs.visitForm.validate().then(async () => {
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
                        this.goBack();
                    } catch (e) {
                        this.$bkMessage({
                            theme: 'error',
                            message: e.detail || e.message || this.$t('接口异常')
                        });
                    } finally {
                        this.cateLoading = false;
                    }
                });
            },
            goBack () {
                this.$router.go(-1);
            },
            onEditorChange (e) {
                this.$set(this.form, 'description', e.html);
            }
        }
    };
</script>
<style lang="scss" scoped>
    .market-Info {
        margin-top: 24px;
        .w600{
            width: 600px;
        }
    }
    .btn-warp{
        position: fixed;
        bottom: 0;
        left: 0;
        padding-top: 8px;
        padding-bottom: 20px;
        margin-left: 240px;
        padding-left: 150px;
        background: #fff;
        width: 100%;
        z-index: 99;
    }

    .app-container {
        max-width: calc(100% - 50px) !important;
        margin: 0 auto;
        border: none;
    }

    .visible-range .editor {
        min-height: 300px;
    }

    @media screen and (max-width: 1366px) {
        .visible-range .editor {
            height: calc(100vh - 362px) !important;
        }
        .visible-range.beyond-container .editor {
            height: calc(100vh - 408px) !important;
        }
    }
</style>
<style>
    .visible-range .editor .ql-snow .ql-formats {
        line-height: 24px;
    }
    .app-container .market-Info.plugin-base-info .edit-form-item .bk-form-content .editor {
        height: calc(100vh - 350px);
        display: flex;
        flex-direction: column;
    }
    .app-container.beyond .market-Info.plugin-base-info .edit-form-item .bk-form-content .editor {
        height: calc(100vh - 392px);
    }
    .app-container .market-Info.plugin-base-info .edit-form-item .bk-form-content .editor .ql-container {
        flex: 1;
    }
</style>
