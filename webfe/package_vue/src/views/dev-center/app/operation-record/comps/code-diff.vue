<template>
  <div
    ref="container"
    class="editor-container"
    style="width: 100%; height: 100%"
  ></div>
</template>

<script>
import * as monaco from 'monaco-editor';

export default {
  name: 'CodeDiffEditor',
  props: {
    oldContent: {
      type: String,
      default: '',
    },
    newContent: {
      type: String,
      default: '',
    },
    language: {
      type: String,
      default: 'yaml',
    },
  },
  data() {
    return {
      editor: null,
      originalModel: null,
      modifiedModel: null,
    };
  },
  watch: {
    oldContent: 'updateModels',
    newContent: 'updateModels',
  },
  mounted() {
    this.$nextTick(() => {
      this.editor = monaco.editor.createDiffEditor(this.$refs.container, {
        theme: 'vs-dark',
        readOnly: true,
        unicodeHighlight: {
          ambiguousCharacters: false, // 禁用对模糊字符的高亮
          invisibleCharacters: false, // 禁用对不可见字符的高亮
          nonBasicASCII: false, // 禁用对非基本 ASCII 字符的高亮
        },
      });
      this.updateModels();
      this.editor.layout();
    });
  },
  beforeUnmount() {
    if (this.editor) {
      this.editor.dispose();
    }
    this.disposeModels();
  },
  methods: {
    updateModels() {
      if (!this.editor) return;

      if (this.originalModel?.getValue() !== this.oldContent || this.modifiedModel?.getValue() !== this.newContent) {
        this.disposeModels();

        this.originalModel = monaco.editor.createModel(this.oldContent, this.language);
        this.modifiedModel = monaco.editor.createModel(this.newContent, this.language);

        this.editor.setModel({
          original: this.originalModel,
          modified: this.modifiedModel,
        });
      }
    },
    disposeModels() {
      if (this.originalModel) {
        this.originalModel.dispose();
        this.originalModel = null;
      }
      if (this.modifiedModel) {
        this.modifiedModel.dispose();
        this.modifiedModel = null;
      }
    },
    layout() {
      this.editor.layout();
    },
  },
};
</script>
