<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    :width="width"
    :title="title"
    ext-cls="editor-sideslider-cls"
  >
    <div
      slot="header"
      class="flex-row align-items-center"
    >
      {{ title }}
      <span
        v-if="subTitle"
        class="header-sub-title"
      >
        {{ subTitle }}
      </span>
    </div>
    <div
      :class="['editor-sideslider-content', { 'full-screen': isFullscreen }]"
      slot="content"
    >
      <template v-if="!isFullscreen">
        <slot name="header-alert"></slot>
      </template>
      <div class="tools">
        <i
          v-bk-tooltips="isFullscreen ? $t('收起') : $t('展开')"
          :class="['paasng-icon', isFullscreen ? 'paasng-un-full-screen' : 'paasng-full-screen']"
          @click="isFullscreen = !isFullscreen"
        ></i>
        <i
          v-bk-tooltips="$t('复制')"
          class="paasng-icon paasng-general-copy mr20"
          v-copy="value"
        ></i>
      </div>
      <div
        class="editor-container"
        ref="editorContainer"
      ></div>
    </div>
  </bk-sideslider>
</template>

<script>
import * as monaco from 'monaco-editor';

export default {
  name: 'DetailComponentsSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    subTitle: {
      type: String,
      default: '',
    },
    width: {
      type: [String, Number],
      default: 640,
    },
    // 编辑器初始值
    value: {
      type: String,
      default: '',
    },
    // 语言
    language: {
      type: String,
      default: 'yaml',
    },
    // 主题
    theme: {
      type: String,
      default: 'vs-dark',
    },
    // 是否只读
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      editor: null, // Monaco 编辑器实例
      resizeObserver: null,
      isFullscreen: false,
    };
  },
  computed: {
    sidesliderVisible: {
      get() {
        return this.show;
      },
      set(val) {
        this.$emit('update:show', val);
      },
    },
  },
  watch: {
    // 监听 value 变化并更新编辑器内容
    value(newValue) {
      if (this.editor && newValue !== this.editor.getValue()) {
        this.editor.setValue(newValue);
      }
    },
    // 当侧边栏显示时初始化编辑器
    show(newValue) {
      if (newValue) {
        this.$nextTick(() => {
          this.init();
        });
      }
    },
  },
  beforeDestroy() {
    // 组件销毁前清理编辑器和事件监听
    if (this.editor) {
      this.editor.dispose();
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    this.resizeObserver = null;
  },
  methods: {
    // 初始化 Monaco 编辑器
    init() {
      this.editor = monaco.editor.create(this.$refs.editorContainer, {
        value: this.value,
        language: this.language,
        theme: this.theme,
        automaticLayout: false,
        readOnly: this.readOnly,
      });

      // 监听编辑器内容变化
      this.editor.onDidChangeModelContent(() => {
        const value = this.editor.getValue();
        if (value !== this.value) {
          this.$emit('input', value);
        }
      });

      // 使用 ResizeObserver 监听容器大小变化
      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          this.editor.layout();
        });
      });
      this.resizeObserver.observe(this.$refs.editorContainer);
    },
  },
};
</script>

<style lang="scss" scoped>
.editor-sideslider-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  &.full-screen {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: 0;
    z-index: 99;
  }
  .tools {
    height: 40px;
    display: flex;
    align-items: center;
    padding-right: 16px;
    flex-direction: row-reverse;
    flex-shrink: 0;
    background-color: #1e1e1e;
    i {
      font-size: 14px;
      color: #979ba5;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
      }
      &.paasng-general-copy {
        font-size: 16px;
      }
    }
  }
  .editor-container {
    flex: 1;
    width: 100%;
    height: 100%;
    border-radius: 0 0 2px 2px;

    /deep/ .monaco-editor {
      border-radius: 0 0 2px 2px;
      .overflow-guard {
        border-radius: 0 0 2px 2px;
      }
    }
  }
}
.editor-sideslider-cls {
  .header-sub-title {
    margin-left: 6px;
    font-size: 12px;
    color: #979ba5;
  }
}
</style>
