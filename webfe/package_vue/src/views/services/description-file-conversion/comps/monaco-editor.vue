<template>
  <div
    class="editor-container"
    ref="editorContainer"
  ></div>
</template>

<script>
import * as monaco from 'monaco-editor';

export default {
  name: 'MonacoEditor',
  props: {
    value: {
      type: String,
      default: '',
    },
    language: {
      type: String,
      default: 'yaml',
    },
    theme: {
      type: String,
      default: 'vs-dark',
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      editor: null,
      resizeObserver: null,
    };
  },
  watch: {
    value(newValue) {
      if (this.editor && newValue !== this.editor.getValue()) {
        this.editor.setValue(newValue);
      }
    },
  },
  mounted() {
    this.editor = monaco.editor.create(this.$refs.editorContainer, {
      value: this.value,
      language: this.language,
      theme: this.theme,
      automaticLayout: false,
      readOnly: this.readOnly,
    });

    this.editor.onDidChangeModelContent(() => {
      const value = this.editor.getValue();
      if (value !== this.value) {
        this.$emit('input', value);
      }
    });

    // 使用 ResizeObserver 监听容器大小变化
    this.resizeObserver = new ResizeObserver(() => {
      this.editor.layout();
    });
    this.resizeObserver.observe(this.$refs.editorContainer);

    window.addEventListener('resize', this.handleResize);
  },
  beforeDestroy() {
    if (this.editor) {
      this.editor.dispose();
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    handleResize() {
      if (this.editor) {
        this.editor.layout();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.editor-container {
  width: 100%;
  height: 500px;
  border-radius: 0 0 2px 2px;
  /deep/ .monaco-editor {
    border-radius: 0 0 2px 2px;
    .overflow-guard {
      border-radius: 0 0 2px 2px;
    }
  }
}
.full-screen .editor-container {
  height: 100vh !important;
}
</style>
