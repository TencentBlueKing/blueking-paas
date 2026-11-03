<template>
  <bk-sideslider
    :is-show.sync="visible"
    :width="800"
    quick-close
    ext-cls="sandbox-guide-slider"
    show-mask
  >
    <div slot="header" class="guide-header">
      <span>{{ $t('使用指南') }}</span>
      <a :href="guideDocsUrl" class="guide-doc-link" target="_blank" rel="noopener noreferrer">
        {{ $t('查看文档') }}
        <i class="paasng-icon paasng-jump-link" aria-hidden="true" />
      </a>
    </div>
    <div
      slot="content"
      class="sandbox-guide"
    >
      <section class="guide-step">
        <h3><span>1</span>{{ $t('创建 API Key 并选择模板') }}</h3>
        <ul class="guide-list">
          <i18n path="在 {apiKeys} 页面创建并存储 API Key。API Key 需在环境变量中配置，请参见 Step3。" tag="li">
            <bk-button slot="apiKeys" class="keys-link" theme="primary" text @click="$emit('api-keys')">
              【API Keys】
            </bk-button>
          </i18n>
          <li>{{ $t('在【Agent 沙箱】→【沙箱模板】查看 templateID，创建沙箱时传入该值，请参见 Step4。') }}</li>
        </ul>
      </section>
      <section class="guide-step">
        <h3><span>2</span>{{ $t('安装 SDK') }}</h3>
        <bk-radio-group v-model="sandboxType">
          <bk-radio-button value="code">{{ $t('代码沙箱') }}</bk-radio-button>
        </bk-radio-group>
        <div class="code-block">
          <button
            v-copy="installCommand"
            type="button"
            class="copy-code"
            :aria-label="$t('复制')"
            :title="$t('复制')"
          ><i class="paasng-icon paasng-general-copy" aria-hidden="true" /></button>
          <pre><code class="hljs" v-dompurify-html="highlightedInstallCommand" /></pre>
        </div>
      </section>
      <section class="guide-step">
        <h3><span>3</span>{{ $t('配置环境变量') }}</h3>
        <bk-radio-group v-model="environmentMode">
          <bk-radio-button value="python">{{ $t('方式一') }}</bk-radio-button>
          <bk-radio-button value="dotenv">{{ $t('方式二') }}</bk-radio-button>
        </bk-radio-group>
        <div class="code-block">
          <button
            v-copy="environmentCode"
            type="button"
            class="copy-code"
            :aria-label="$t('复制')"
            :title="$t('复制')"
          ><i class="paasng-icon paasng-general-copy" aria-hidden="true" /></button>
          <pre><code class="hljs" v-dompurify-html="highlightedEnvironmentCode" /></pre>
        </div>
      </section>
      <section class="guide-step">
        <h3><span>4</span>{{ $t('启动沙箱') }}</h3>
        <div class="guide-template">
          <span>{{ $t('模板') }} ID</span>
          <bk-select
            v-model="selectedTemplateId"
            class="template-select"
            :clearable="false"
            :loading="templateLoading"
            :placeholder="$t('请选择模板')"
            searchable
          >
            <bk-option
              v-for="id in templateOptions"
              :id="id"
              :key="id"
              :name="id"
            />
          </bk-select>
        </div>
        <bk-radio-group v-model="clientType">
          <bk-radio-button value="python">Python SDK</bk-radio-button>
          <bk-radio-button value="browser">{{ $t('浏览器 SDK') }}</bk-radio-button>
          <bk-radio-button value="http">HTTP API</bk-radio-button>
        </bk-radio-group>
        <p class="guide-description">{{ exampleDescription }}</p>
        <div class="code-block">
          <button
            v-copy="exampleCode"
            type="button"
            class="copy-code"
            :aria-label="$t('复制')"
            :title="$t('复制')"
          ><i class="paasng-icon paasng-general-copy" aria-hidden="true" /></button>
          <pre><code class="hljs" v-dompurify-html="highlightedExampleCode" /></pre>
        </div>
      </section>
    </div>
  </bk-sideslider>
</template>

<script>
import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import python from 'highlight.js/lib/languages/python';
import { buildEnvironmentCode, buildSandboxExample } from '../guide-examples';

hljs.registerLanguage('bash', bash);
hljs.registerLanguage('python', python);

export default {
  name: 'SandboxAccessGuide',
  props: {
    appCode: {
      type: String,
      required: true,
    },
    templateId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      visible: false,
      sandboxType: 'code',
      environmentMode: 'python',
      clientType: 'python',
      templates: [],
      templateLoading: false,
    };
  },
  computed: {
    guideDocsUrl() {
      return `${this.GLOBAL.LINK.BK_APP_DOC.replace(/\/+$/, '')}/topics/paas/paas3_e2b_sandbox`;
    },
    selectedTemplateId: {
      get() {
        return this.templateId;
      },
      set(value) {
        this.$emit('update:templateId', value);
      },
    },
    templateOptions() {
      return [...new Set([...this.templates.map(template => template.template_id), this.templateId])].filter(Boolean);
    },
    apiUrl() {
      const apiName = window.GLOBAL_CONFIG.APP_VERSION === 'te' ? 'paasv3' : 'bkpaas3';
      const apiUrl = (window.BK_API_URL_TMPL || '').replace('{api_name}', apiName).replace(/\/+$/, '');
      return apiUrl ? `${apiUrl}/prod/agent_sandbox/e2b` : '';
    },
    installCommand() {
      return 'pip install \'e2b==2.44.0\' \'e2b-code-interpreter==2.10.0\'';
    },
    highlightedInstallCommand() {
      return hljs.highlight(this.installCommand, { language: 'bash' }).value;
    },
    environmentCode() {
      return buildEnvironmentCode({
        apiUrl: this.apiUrl,
        environmentMode: this.environmentMode,
        t: key => this.$t(key),
      });
    },
    highlightedEnvironmentCode() {
      return hljs.highlight(this.environmentCode, { language: 'python' }).value;
    },
    exampleDescription() {
      if (this.clientType === 'http') {
        return this.$t('使用 HTTP API 创建沙箱，templateID 取自「沙箱模板」，timeout 为存活秒数：');
      }
      return this.clientType === 'browser'
        ? this.$t('运行以下示例来创建一个浏览器沙箱，并通过 CDP 连接浏览器：')
        : this.$t('运行以下示例来创建一个代码沙箱，并运行指定命令：');
    },
    exampleCode() {
      return buildSandboxExample({
        apiUrl: this.apiUrl,
        templateId: this.templateId,
        environmentMode: this.environmentMode,
        clientType: this.clientType,
        t: key => this.$t(key),
      });
    },
    highlightedExampleCode() {
      const language = this.clientType === 'http' ? 'bash' : 'python';
      return hljs.highlight(this.exampleCode, { language }).value;
    },
  },
  watch: {
    visible(value) {
      if (!value) {
        this.$emit('close');
      }
    },
  },
  mounted() {
    this.visible = true;
    this.loadTemplates();
  },
  methods: {
    async loadTemplates() {
      this.templateLoading = true;
      try {
        this.templates = await this.$store.dispatch('agentSandbox/listTemplates', { appCode: this.appCode });
        if (!this.templateId && this.templateOptions.length) {
          this.selectedTemplateId = this.templateOptions[0];
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.templateLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-guide-slider {
  /deep/ .bk-sideslider-wrapper {
    overflow: hidden;
  }
  /deep/ .bk-sideslider-header,
  /deep/ .bk-sideslider-title,
  /deep/ .bk-sideslider-closer {
    height: 52px;
    line-height: 52px;
  }
  /deep/ .bk-sideslider-title {
    font-size: 16px;
  }
}
.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.guide-doc-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #3a84ff;
  font-size: 12px;
}
.sandbox-guide {
  padding: 24px 32px 40px 72px;
  color: #63656e;
}
.guide-step {
  position: relative;
  padding-bottom: 28px;
  &:not(:last-child)::before {
    position: absolute;
    top: 28px;
    bottom: 4px;
    left: -28px;
    width: 1px;
    background: #e1ecff;
    content: '';
  }
  &:last-child {
    padding-bottom: 0;
  }
  h3 {
    margin: 0 0 8px;
    color: #313238;
    font-size: 14px;
    line-height: 22px;
    span {
      position: absolute;
      left: -40px;
      top: 0;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #e1ecff;
      color: #3a84ff;
      font-size: 12px;
      line-height: 24px;
      text-align: center;
    }
  }
}
.guide-list {
  padding: 0 0 0 18px;
  margin: 0;
  font-size: 13px;
  line-height: 24px;
  list-style: none;
}
.keys-link {
  height: auto;
  font-size: inherit;
  line-height: inherit;
}
.guide-template {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.template-select {
  width: 280px;
}
.guide-description {
  margin: 12px 0 10px;
  font-size: 13px;
  line-height: 22px;
  & + .code-block {
    margin-top: 0;
  }
}
.code-block {
  position: relative;
  margin-top: 12px;
  padding: 12px 40px 12px 16px;
  background: #f5f7fa;
  pre {
    margin: 0;
    overflow-x: hidden;
    color: #313238;
    line-height: 22px;
    font-family: Consolas, monospace;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-all;
    code {
      display: block;
      overflow-x: hidden;
      padding: 0;
      border-radius: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      white-space: inherit;
    }
  }
}
.copy-code {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #979ba5;
  font-size: 14px;
  line-height: 14px;
  cursor: pointer;
  &:hover,
  &:focus {
    color: #3a84ff;
  }
}
</style>
