<template>
  <div class="agent-sandbox-detail">
    <section class="ps-top-bar detail-header">
      <div class="back" @click="goBack">
        <i class="paasng-icon paasng-arrows-left icon-cls-back" />
        <span class="back-text">{{ $t('Agent 沙箱') }}</span>
      </div>
      <span class="divider" />
      <span class="detail-name">{{ template ? template.name || template.template_id : templateId }}</span>
    </section>
    <div class="app-container middle">
      <div v-bkloading="{ isLoading: loading, zIndex: 10 }" class="template-card card-style">
        <template v-if="errorMessage">
          <bk-alert type="error" :title="errorMessage" />
          <div class="detail-error-actions">
            <bk-button theme="primary" @click="loadTemplate">{{ $t('重试') }}</bk-button>
            <bk-button @click="goBack">{{ $t('返回列表') }}</bk-button>
          </div>
        </template>
        <template v-else-if="template">
          <h3>{{ $t('模板详情') }}</h3>
          <dl class="template-fields">
            <template v-for="field in fields">
              <dt :key="`${field.key}-label`">{{ field.label }}</dt>
              <dd :key="field.key">{{ field.value }}</dd>
            </template>
          </dl>
          <div class="detail-actions">
            <bk-button theme="primary" @click="$refs.tools.openGuide(template.template_id)">
              {{ $t('接入示例') }}
            </bk-button>
            <bk-button @click="$refs.tools.openKeys()">API Keys</bk-button>
          </div>
        </template>
      </div>
    </div>
    <sandbox-tools :key="appCode" ref="tools" :app-code="appCode" />
  </div>
</template>

<script>
import SandboxTools from './comps/tools.vue';
import { formatResources, formatTimeout } from './format';
import { getErrorMessage, isNil } from './utils';

export default {
  name: 'AgentSandboxTemplateDetail',
  components: { SandboxTools },
  data() {
    return { template: null, loading: false, errorMessage: '', requestId: 0 };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    templateId() {
      return this.$route.params.templateId;
    },
    templateContext() {
      return `${this.appCode}/${this.templateId}`;
    },
    fields() {
      const template = this.template;
      if (!template) return [];
      return [
        { key: 'template_id', label: `${this.$t('模板')} ID`, value: template.template_id },
        { key: 'description', label: this.$t('描述'), value: template.description },
        { key: 'image', label: this.$t('镜像'), value: template.image },
        { key: 'resources', label: this.$t('资源'), value: formatResources(template) },
        { key: 'timeout', label: this.$t('生命周期 TTL'), value: formatTimeout(template.timeout) },
        { key: 'network', label: this.$t('网络'), value: template.network },
        { key: 'region', label: this.$t('地域'), value: template.region },
        { key: 'prewarm_count', label: this.$t('预热'), value: template.prewarm_count },
      ].filter(({ key }) => {
        const values = key === 'resources'
          ? [template.cpu_count, template.memory_mb, template.disk_size_mb]
          : [template[key]];
        return values.some(value => !isNil(value) && value !== '');
      });
    },
  },
  watch: {
    templateContext: {
      immediate: true,
      handler: 'loadTemplate',
    },
  },
  beforeDestroy() {
    this.requestId += 1;
  },
  methods: {
    async loadTemplate() {
      this.requestId += 1;
      const requestId = this.requestId;
      const context = this.templateContext;
      this.template = null;
      this.errorMessage = '';
      this.loading = true;
      try {
        const result = await this.$store.dispatch('agentSandbox/getTemplate', {
          appCode: this.appCode,
          templateId: this.templateId,
        });
        if (requestId !== this.requestId || context !== this.templateContext) return;
        if (!result || !result.template_id) throw new Error(this.$t('加载失败，请重试'));
        this.template = result;
      } catch (error) {
        if (requestId !== this.requestId || context !== this.templateContext) return;
        this.errorMessage = error.status === 404
          ? this.$t('模板不存在或已下线，请返回列表查看可用模板。')
          : getErrorMessage(error, this.$t('加载失败，请重试'));
      } finally {
        if (requestId === this.requestId && context === this.templateContext) this.loading = false;
      }
    },
    goBack() {
      this.$router.push({
        name: 'agentSandbox',
        params: { id: this.appCode },
        query: { tab: this.$route.query.tab === 'instances' ? 'instances' : 'templates' },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-header {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 24px;
  line-height: 1;
}
.app-container {
  padding-top: 24px;
}
.back {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  color: #313238;
  font-size: 16px;
  cursor: pointer;
  .icon-cls-back {
    margin-right: 5px;
    color: #3a84ff;
    font-size: 18px;
    font-weight: 700;
  }
}
.divider {
  flex-shrink: 0;
  width: 1px;
  height: 14px;
  margin: 0 8px;
  background-color: #dcdee5;
}
.detail-name {
  min-width: 0;
  overflow: hidden;
  color: #979ba5;
  font-size: 14px;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.template-card {
  min-height: 300px;
  padding: 24px;
  background: #fff;
  h3 {
    margin: 0 0 24px;
    color: #313238;
    font-size: 14px;
    font-weight: bold;
    line-height: 20px;
  }
}
.template-fields {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  row-gap: 12px;
  margin: 0;
  font-size: 12px;
  line-height: 20px;
  dt,
  dd {
    padding: 6px 0;
  }
  dt {
    color: #979ba5;
    text-align: right;
    &::after {
      content: '：';
    }
  }
  dd {
    margin-left: 0;
    color: #313238;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
}
.detail-actions {
  display: flex;
  gap: 12px;
  margin: 24px 0 0 120px;
}
.detail-error-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}
</style>
