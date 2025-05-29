<template>
  <paas-content-loader
    :is-loading="loading"
    placeholder="deploy-yaml-loading"
    class="deploy-action-box"
  >
    <div class="cloud-yaml-container">
      <resource-editor
        ref="editorRef"
        key="editor"
        v-model="detail"
        :readonly="true"
        :height="height"
        @error="handleEditorErr"
      />
      <EditorStatus
        v-show="!!editorErr.message"
        class="status-wrapper"
        :message="editorErr.message"
      />
    </div>
  </paas-content-loader>
</template>
<script>
import ResourceEditor from '@/components/deploy-resource-editor';
import EditorStatus from '@/components/deploy-resource-editor/editor-status';
export default {
  components: {
    ResourceEditor,
    EditorStatus,
  },
  props: {
    cloudAppData: {
      type: Array,
      default: [],
    },
    height: {
      type: Number,
      default: 600,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      editorErr: {
        type: '',
        message: '',
      },
      detail: {},
    };
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.length) {
          this.$nextTick(() => {
            this.detail = val[0];
            this.$refs.editorRef?.setValue(val[0]);
          });
        }
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    // 捕获编辑器错误提示
    handleEditorErr(err) {
      this.editorErr.type = 'content'; // 编辑内容错误
      this.editorErr.message = err;
    },
  },
};
</script>
