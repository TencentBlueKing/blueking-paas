<template lang="html">
  <section>
    <h3
      class="title"
      v-if="isSaveOperation"
    >
      {{ $t('方案信息') }}
      <bk-button
        text
        size="small"
        theme="primary"
        style="font-weight: normal"
        @click="handleOpenGuide"
      >
        {{ $t('使用指南') }}
      </bk-button>
    </h3>
    <section :class="['content', { 'not-title': !isSaveOperation }]">
      <bk-form
        :model="formData"
        :label-width="150"
      >
        <bk-form-item
          :label="$t('方案')"
          v-if="data.static_plans"
        >
          <bk-radio-group v-model="formData.plan">
            <bk-radio-button
              v-for="item in data.static_plans"
              :key="item.uuid"
              :value="item.uuid"
            >
              <span class="ml5">{{ item.name }}</span>
            </bk-radio-button>
          </bk-radio-group>
        </bk-form-item>
        <template v-else>
          <bk-form-item
            v-for="(value, key) in data.env_specific_plans"
            :label="getEnvironmentName(key)"
            :key="key"
          >
            <bk-radio-group v-model="formData[key]">
              <bk-radio-button
                v-for="item in value"
                :key="item.uuid"
                :value="item.uuid"
              >
                <span class="ml5">{{ item.name }}</span>
              </bk-radio-button>
            </bk-radio-group>
          </bk-form-item>
        </template>
      </bk-form>
      <p
        v-if="mode === ''"
        class="info"
      >
        {{ $t('部署后则不能再修改方案信息') }}
      </p>
    </section>
    <section
      class="action"
      v-if="isSaveOperation"
    >
      <template v-if="mode === ''">
        <bk-button
          :loading="enableLoadingUse"
          @click="handleEnabled"
        >
          {{ $t('启用服务') }}
        </bk-button>
      </template>
      <template v-else>
        <section>
          <bk-button
            :loading="saveLoadingUse"
            theme="primary"
            @click="handleSave"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            style="margin-left: 4px"
            @click="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </section>
      </template>
    </section>

    <bk-sideslider
      :is-show.sync="isShow"
      :title="$t('使用指南')"
      :width="640"
      :quick-close="true"
    >
      <div slot="content">
        <div id="markdown">
          <div
            class="markdown-body"
            v-dompurify-html="compiledMarkdown"
          />
        </div>
      </div>
    </bk-sideslider>
  </section>
</template>

<script>
import { marked } from 'marked';

export default {
  name: 'ConfigEdit',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    enableLoading: {
      type: Boolean,
      default: false,
    },
    saveLoading: {
      type: Boolean,
      default: false,
    },
    // '' 表示正常启用态，'edit'表示编辑态
    mode: {
      type: String,
      default: '',
      validator(value) {
        if (['', 'edit'].indexOf(value) < 0) {
          console.error(`mode is not valid: '${value}'`);
          return false;
        }
        return true;
      },
    },
    guide: {
      type: String,
      default: '',
    },
    isSaveOperation: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      enableLoadingUse: this.enableLoading,
      saveLoadingUse: this.saveLoading,
      isShow: false,
      formData: {
        plan: '',
        prod: '',
        stag: '',
      },
    };
  },
  computed: {
    compiledMarkdown() {
      this.$nextTick(() => {
        $('#markdown')
          .find('a')
          .each(function () {
            $(this).attr('target', '_blank');
          });
      });
      return marked(this.guide);
    },
  },
  watch: {
    data(value) {
      this.setDefault(value);
    },
    enableLoading(value) {
      this.enableLoadingUse = !!value;
    },
    saveLoading(value) {
      this.saveLoadingUse = !!value;
    },
  },
  mounted() {
    this.setDefault(this.data);
  },
  methods: {
    handleOpenGuide() {
      this.isShow = true;
    },
    // 启动服务
    handleEnabled() {
      const params = this.formatParams();
      this.$emit('on-change', 'enabled', params);
    },
    // 弹窗模式保存
    handleSave() {
      const params = this.formatParams();
      this.$emit('on-change', 'save', params);
    },
    // 格式化请求参数
    formatParams() {
      const { plan, prod, stag } = this.formData;
      if (this.data.static_plans) {
        return {
          key: 'plan_id',
          value: plan,
        };
      } else {
        return {
          key: 'env_plan_id_map',
          value: {
            prod,
            stag,
          },
        };
      }
    },
    handleCancel() {
      this.$emit('on-change', 'cancel', {});
    },
    // 设置配置项默认值
    setDefault(data) {
      if (data === null || !Object.keys(data).length) return;
      if (data.static_plans?.length) {
        // 选择方案
        this.formData.plan = data.static_plans[0]?.uuid;
      } else {
        // 环境
        Object.keys(data.env_specific_plans).forEach((key) => {
          this.formData[key] = data.env_specific_plans[key][0]?.uuid;
        });
      }
    },
    getEnvironmentName(key) {
      return key === 'prod' ? this.$t('方案（生产环境）') : this.$t('方案（预发布环境）');
    },
  },
};
</script>

<style lang="scss" scoped>
.title {
  color: #1b1f23;
  font-weight: 600;
}
.content {
  padding: 25px 10px 10px 10px;
  border-bottom: 1px solid #dcdee5;
  &.not-title {
    padding: 0;
    border-bottom: none;
  }
  .item {
    display: flex;
    align-items: center;
    &.mb {
      margin-bottom: 20px;
    }
    .config-label {
      display: inline-block;
      padding-right: 10px;
      width: 85px;
      color: #313238;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      vertical-align: middle;
    }
    .bk-button-group {
      button {
        min-width: 100px;
        &:hover {
          color: #3a84ff;
        }
        &.is-disabled:hover {
          color: #c4c6cc;
        }
      }
    }
    .error {
      padding-left: 98px;
      margin-top: 5px;
      font-size: 12px;
      color: #ea3636;
    }
  }
  .info {
    margin-top: 10px;
    padding-left: 150px;
    font-size: 12px;
    color: #979ba5;
  }
}
.action {
  margin-top: 10px;
}
.markdown-body {
  box-sizing: border-box;
  min-width: 200px;
  margin: 0 auto;
  padding: 5px 20px;

  h2 {
    color: var(--color-fg-default);
  }
}
</style>
<style lang="scss">
#markdown h2 {
  padding-bottom: 0.3em;
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding: 0;
  padding-bottom: 10px;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

#markdown h3 {
  color: var(--color-fg-default);
  line-height: 52px;
  font-size: 14px;
  position: relative;
}

#markdown h2 .octicon-link {
  color: #1b1f23;
  vertical-align: middle;
  visibility: hidden;
}

#markdown h2:hover .anchor {
  text-decoration: none;
}

#markdown h2:hover .anchor .octicon-link {
  visibility: visible;
}

#markdown code,
#markdown kbd,
#markdown pre {
  font-size: 1em;
}

#markdown code {
  font-size: 12px;
}

#markdown pre {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 12px;
}

#markdown pre {
  word-wrap: normal;
}

#markdown code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  color: inherit;
}

#markdown pre > code {
  padding: 0;
  margin: 0;
  font-size: 100%;
  word-break: normal;
  white-space: pre;
  background: transparent;
  border: 0;
}

#markdown .highlight {
  margin-bottom: 16px;
}

#markdown .highlight pre {
  margin-bottom: 0;
  word-break: normal;
}

#markdown .highlight pre,
#markdown pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: var(--color-canvas-subtle);
  border-radius: 3px;
}

#markdown pre code {
  display: inline;
  max-width: auto;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

#markdown p {
  margin-top: 0;
  margin-bottom: 10px;
}

#markdown a {
  background-color: transparent;
}

#markdown a:active,
#markdown a:hover {
  outline-width: 0;
}

#markdown a {
  color: #0366d6;
  text-decoration: none;
}

#markdown a:hover {
  text-decoration: underline;
}

#markdown a:not([href]) {
  color: inherit;
  text-decoration: none;
}

#markdown ul,
#markdown ol {
  padding-left: 0;
  margin-top: 0;
  margin-bottom: 0;
  list-style: unset !important;
}

#markdown ol ol,
#markdown ul ol {
  list-style-type: lower-roman;
}

#markdown ul ul ol,
#markdown ul ol ol,
#markdown ol ul ol,
#markdown ol ol ol {
  list-style-type: lower-alpha;
}

#markdown ul,
#markdown ol {
  padding-left: 2em;
}

#markdown ul ul,
#markdown ul ol,
#markdown ol ol,
#markdown ol ul {
  margin-top: 0;
  margin-bottom: 0;
}
</style>
