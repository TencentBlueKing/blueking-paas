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
            :required="true"
            :property="'category'"
          >
            <div
              slot="tip"
              v-bk-tooltips.top="{
                content: `${$t('分类由插件管理员定义，如分类不满足需求可联系插件管理员：')}${adminStr}`,
                disabled: !adminStr,
              }"
              class="lable-wrapper"
            >
              <span v-dashed class="label">{{ $t('应用分类') }}</span>
            </div>
            <bk-select
              v-model="form.category"
              :loading="cateLoading"
              :clearable="false"
              :placeholder="$t('应用分类')"
              :disabled="isManualSwitchSteps"
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
            <bk-input
              v-model="form.introduction"
              :disabled="isManualSwitchSteps"
            />
          </bk-form-item>
          <bk-form-item
            :label="$t('应用联系人')"
            :required="true"
            property="contact"
          >
            <user
              v-model="form.contact"
              :disabled="isManualSwitchSteps"
            />
          </bk-form-item>
          <bk-form-item
            class="edit-form-item"
            :label="$t('详细描述')"
            :property="'description'"
          >
            <quill-editor
              ref="editor"
              v-model="form.description"
              class="editor"
              :options="editorOption"
              :disabled="isManualSwitchSteps"
            />
          </bk-form-item>
        </bk-form>
      </div>
    </div>
  </div>
</template>
<script>
import { cloneDeep } from 'lodash';
import user from '@/components/user';
import { quillEditor } from 'vue-quill-editor';
import 'quill/dist/quill.core.css';
import 'quill/dist/quill.snow.css';
import 'quill/dist/quill.bubble.css';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import stageBaseMixin from './stage-base-mixin';
import { TOOLBAR_OPTIONS } from '@/common/constants';
import { filterRichText } from '@/utils/xss-filter.js';

export default {
  components: {
    user,
    quillEditor,
  },
  mixins: [stageBaseMixin, pluginBaseMixin],
  props: {
    stageData: Object,
    isManualSwitch: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      winHeight: 300,
      cateLoading: true,
      categoryList: [],
      form: {
        category: '',
        introduction: '',
        description: '',
        contact: [],
      },
      curPluginData: {},
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
    adminStr() {
      const pluginAdministrator = this.curPluginInfo.pd_administrator || [];
      return pluginAdministrator.join(';');
    },
    // 是否为手动切换步骤, 手动切换禁用表单项
    isManualSwitchSteps() {
      return !this.isManualSwitch;
    },
  },
  watch: {
    'form.description'(newDescription) {
      if (newDescription) {
        this.$refs.editor.options.placeholder = '';
      }
    },
  },
  created() {
    this.fetchCategoryList();
    this.fetchMarketInfo();
  },
  methods: {
    // 获取市场信息
    async fetchMarketInfo() {
      try {
        const params = {
          pdId: this.pdId,
          pluginId: this.pluginId,
        };
        const res = await this.$store.dispatch('plugin/getMarketInfo', params);
        this.form = res;
        this.form.description = filterRichText(res.description);
        if (res.contact) {
          this.form.contact = res.contact.split(',') || [];
        } else {
          const founder = this.curPluginInfo?.latest_release?.creator || '';
          this.form.contact = founder.split(',');
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 200);
      }
    },
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
        }, 200);
      }
    },
    // 保存
    async nextStage(resolve) {
      await this.$refs.visitForm.validate().then(async () => {
        try {
          const data = cloneDeep(this.form);
          data.contact = data.contact.join(',');
          data.description = filterRichText(data.description);
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
          await resolve();
        } catch (e) {
          this.catchErrorHandler(e);
        } finally {
          this.cateLoading = false;
        }
      }, (e) => {
        console.error(e);
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.release-warp .info-mt {
  padding: 24px;
}
.lable-wrapper {
  position: absolute;
  top: 0;
  left: -100px;
  width: 100px;
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
    padding-bottom: 2px;
  }
}
.edit-form-item .editor {
  /deep/ .ql-container {
    height: calc(100% - 48px);
  }
}
</style>
