<template>
  <div class="env-preview-collapse">
    <div
      class="preview-header"
      @click="expanded = !expanded"
    >
      <i class="paasng-icon paasng-eye mr5"></i>
      <span class="preview-title">{{ $t('预览环境变量') }}</span>
      <span class="preview-desc">{{ $t('配置项将以环境变量方式注入至应用运行时环境') }}</span>
      <!-- paasng-icon paasng-ps-arrow-up -->
      <i :class="['paasng-icon', 'paasng-ps-arrow-up', 'toggle-icon', { 'is-collapsed': expanded }]"></i>
    </div>
    <div
      v-show="expanded"
      class="preview-content"
    >
      <div
        v-for="(item, index) in envVars"
        :key="index"
        class="env-var-item"
      >
        {{ item }}
      </div>
      <div
        v-if="envVars.length === 0"
        class="empty-tip"
      >
        {{ $t('暂无环境变量') }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EnvPreview',
  props: {
    // 环境变量模板
    template: {
      type: Array,
      default: () => [],
    },
    // 配置项值
    configValues: {
      type: Object,
      default: () => ({}),
    },
    // TLS 配置
    tlsConfig: {
      type: Object,
      default: () => ({}),
    },
    // 是否显示 TLS
    showTls: {
      type: Boolean,
      default: false,
    },
    // 服务名称（用于生成 TLS 前缀）
    serviceName: {
      type: String,
      default: '',
    },
    // 默认是否展开
    defaultExpanded: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      expanded: this.defaultExpanded,
    };
  },
  computed: {
    // 预览环境变量列表
    envVars() {
      // 根据 template 生成环境变量预览
      const templateVars = this.template.map((tpl) => {
        const value = tpl.value.replace(/\{\{(\w+)\}\}/g, (_, key) => {
          const actualValue = this.configValues[key];
          return actualValue !== undefined && actualValue !== '' ? actualValue : `{{${key}}}`;
        });
        return `${tpl.key}:${value}`;
      });

      // 添加 TLS 配置预览
      if (!this.showTls) return templateVars;

      const { ca, cert, key, insecure_skip_verify } = this.tlsConfig;
      if (!ca && !cert && !key && !insecure_skip_verify) return templateVars;

      const tlsObj = {
        ...(ca && { ca: this.truncateValue(ca) }),
        ...(cert && { cert: this.truncateValue(cert) }),
        ...(key && { key: this.truncateValue(key) }),
        ...(insecure_skip_verify && { insecure_skip_verify }),
      };

      return [...templateVars, `${this.getServicePrefix()}_TLS:${JSON.stringify(tlsObj)}`];
    },
  },
  watch: {
    defaultExpanded(val) {
      this.expanded = val;
    },
  },
  methods: {
    // 截取长字符串用于预览
    truncateValue(val, maxLen = 10) {
      if (!val) return '';
      return val.length > maxLen ? `${val.substring(0, maxLen)}...` : val;
    },
    // 获取服务前缀
    getServicePrefix() {
      return this.serviceName.toUpperCase().replace(/-/g, '_');
    },
    // 手动控制展开/折叠
    toggle(state) {
      if (typeof state === 'boolean') {
        this.expanded = state;
      } else {
        this.expanded = !this.expanded;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.env-preview-collapse {
  margin: 16px 0;
  background: #fff;
  border: 1px solid #dcdee5;
  border-radius: 2px;

  .preview-header {
    display: flex;
    align-items: center;
    height: 32px;
    padding: 0 12px;
    cursor: pointer;
    user-select: none;

    .preview-title {
      font-size: 14px;
      color: #313238;
      font-weight: 500;
    }

    .preview-desc {
      margin-left: 8px;
      font-size: 12px;
      color: #979ba5;
    }

    .toggle-icon {
      margin-left: auto;
      font-size: 14px;
      color: #979ba5;
      transition: transform 0.2s ease;
      transform-origin: center center;

      &.is-collapsed {
        transform: rotate(180deg);
      }
    }

    i {
      color: #63656e;
      font-size: 16px;
    }
  }

  .preview-content {
    padding: 8px 12px;
    background-color: #fafbfd;
    border-top: 1px solid #dcdee5;

    .env-var-item {
      padding: 4px 0;
      font-size: 12px;
      color: #313238;
      word-break: break-all;
      line-height: 20px;
      font-family: Consolas, Monaco, 'Courier New', monospace;
    }

    .empty-tip {
      font-size: 12px;
      color: #979ba5;
      text-align: center;
      padding: 12px 0;
    }
  }
}
</style>
