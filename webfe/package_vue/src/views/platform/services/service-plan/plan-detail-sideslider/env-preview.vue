<template>
  <div class="env-preview-collapse">
    <div
      class="preview-header"
      @click="expanded = !expanded"
    >
      <i class="paasng-icon paasng-eye mr5"></i>
      <span class="preview-title">{{ $t('预览环境变量') }}</span>
      <span class="preview-desc">{{ $t('配置项将以环境变量方式注入至应用运行时环境') }}</span>
      <i
        style="color: #c4c6cc"
        class="paasng-icon paasng-info-line ml-8"
        v-bk-tooltips="previewDesc"
      ></i>
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
    // 服务名称（用于生成提示中的前缀）
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
      return this.template.map((tpl) => {
        const value = tpl.value.replace(/\{\{(\w+)\}\}/g, (_, key) => {
          const actualValue = this.configValues[key];
          return actualValue !== undefined && actualValue !== '' ? actualValue : `{{${key}}}`;
        });
        return `${tpl.key}:${value}`;
      });
    },
    previewDesc() {
      const id = this.serviceName ? this.serviceName.toUpperCase().replace(/-/g, '_').replace(/_$/, '') : 'ID';
      return this.$t(
        'TLS 相关的配置（证书和密钥）以文件形式存储在容器内; 环境变量 {id}_CERT、{id}_KEY、{id}_CA 分别指向对应文件的路径',
        { id }
      );
    },
  },
  watch: {
    defaultExpanded(val) {
      this.expanded = val;
    },
  },
  methods: {
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
