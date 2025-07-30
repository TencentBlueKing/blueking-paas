<template>
  <div class="market-info-wrapper">
    <paas-plugin-title />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="plugin-market-info-loading"
      class="app-container middle"
    >
      <div class="market-Info plugin-base-info">
        <bk-form
          ref="visitForm"
          :model="form"
          :rules="rules"
          :label-width="104"
        >
          <bk-form-item
            class="w600"
            :required="true"
            :property="'category'"
          >
            <div
              slot="tip"
              v-bk-tooltips.top="{
                content: `${$t('分类由插件管理员定义，如分类不满足需求可联系插件管理员：')}${administratorStr}`,
                disabled: !administratorStr,
              }"
              class="lable-wrapper"
            >
              <span class="label">{{ $t('应用分类') }}</span>
            </div>
            <bk-select
              v-model="form.category"
              :loading="cateLoading"
              :clearable="false"
              :placeholder="$t('应用分类')"
              ext-cls="app-classification-cls"
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
              ref="editor"
              v-model="form.description"
              class="editor"
              :options="editorOption"
            />
          </bk-form-item>
        </bk-form>
      </div>

      <div class="btn-warp mt5">
        <bk-button
          theme="primary"
          @click="handlerSave"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          theme="default"
          style="margin-left: 8px"
          @click="goBack"
        >
          {{ $t('取消') }}
        </bk-button>
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
import { cloneDeep } from 'lodash';
import { filterRichText } from '@/utils/xss-filter.js';
export default {
  components: {
    paasPluginTitle,
    quillEditor,
    user,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      form: {
        category: '',
        introduction: '',
        description: '',
        contact: [],
      },
      categoryList: [],
      cateLoading: true,
      isLoading: true,
      editorOption: {
        placeholder: this.$t('开始编辑...'),
        modules: {
          toolbar: TOOLBAR_OPTIONS,
        },
      },
      rules: {
        category: [
          {
            required: true,
            message: this.$t('该字段为必填项'),
            trigger: 'blur',
          },
        ],
        introduction: [
          {
            required: true,
            message: this.$t('该字段为必填项'),
            trigger: 'blur',
          },
        ],
        description: [
          {
            required: true,
            message: this.$t('请输入'),
            trigger: 'blur',
          },
        ],
        contact: [
          {
            required: true,
            message: this.$t('该字段为必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    administratorStr() {
      const administrators = this.curPluginInfo.pd_administrator || [];
      return administrators.join(';');
    },
  },
  watch: {
    'form.description'(newDescription) {
      if (newDescription) {
        this.$refs.editor.options.placeholder = '';
      }
    },
  },
  mounted() {
    this.fetchMarketInfo();
    this.fetchCategoryList();
    this.$nextTick(() => {
      addQuillTitle();
    });
  },
  methods: {
    // 应用分类
    async fetchCategoryList() {
      try {
        const params = {
          pdId: this.pdId,
        };
        const res = await this.$store.dispatch('plugin/getCategoryList', params);
        this.categoryList = res.category;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.cateLoading = false;
        setTimeout(() => {
          this.isLoading = false;
        }, 300);
      }
    },
    // 获取市场信息
    async fetchMarketInfo() {
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
        };
        const res = await this.$store.dispatch('plugin/getMarketInfo', params);
        this.form = {
          ...res,
          description: filterRichText(res.description),
          contact: (res.contact && res.contact.split(',')) || [],
        };
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 300);
      }
    },
    // 保存
    async handlerSave() {
      this.$refs.visitForm.validate().then(
        async () => {
          try {
            const data = cloneDeep(this.form);
            // XSS 过滤处理
            data.description = filterRichText(data.description);
            data.contact = data.contact.join(',');
            const params = {
              pdId: this.pdId,
              pluginId: this.pluginId,
              data,
            };
            await this.$store.dispatch('plugin/saveMarketInfo', params);
            this.$bkMessage({
              theme: 'success',
              message: this.$t('保存成功!'),
            });
            this.goBack();
          } catch (e) {
            this.$bkMessage({
              theme: 'error',
              message: e.detail || e.message || this.$t('接口异常'),
            });
          } finally {
            this.cateLoading = false;
          }
        },
        (validator) => {
          // 显示第一个出错位置
          console.warn(validator.content);
        }
      );
    },
    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>
<style lang="scss" scoped>
.market-Info {
  .w600 {
    width: 600px;
  }
}
.btn-warp {
  transform: translateY(65px);
  margin-left: 104px;
}
.lable-wrapper {
  position: absolute;
  top: 0;
  left: -104px;
  width: 104px;
  min-height: 32px;
  text-align: right;
  vertical-align: middle;
  line-height: 32px;
  float: left;
  font-size: 14px;
  font-weight: normal;
  color: #63656e;
  box-sizing: border-box;
  padding: 0 24px 0 0;
  &::after {
    content: '*';
    position: absolute;
    top: 50%;
    height: 8px;
    line-height: 1;
    color: #ea3636;
    font-size: 12px;
    display: inline-block;
    vertical-align: middle;
    transform: translate(3px, -50%);
  }
  .label {
    display: inline-block;
    line-height: 20px;
    background: linear-gradient(to left, transparent 0%, transparent 50%, #979ba5 50%, #979ba5 100%);
    background-size: 10px 1px;
    background-repeat: repeat-x;
    background-position-y: 100%;
  }
}
.app-classification-cls {
  background: #fff;
}
</style>
<style>
.market-info-wrapper .editor {
  height: 300px;
}
.market-info-wrapper .editor .ql-snow {
  background: #fff;
}
.market-info-wrapper .editor .ql-snow .ql-formats {
  line-height: 24px;
}
</style>
