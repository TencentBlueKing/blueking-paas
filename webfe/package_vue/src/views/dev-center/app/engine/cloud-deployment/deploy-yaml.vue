<template>
  <paas-content-loader
    :is-loading="screenIsLoading"
    placeholder="deploy-yaml-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="cloud-yaml-container">
      <resource-editor
        ref="editorRef"
        key="editor"
        v-model="detail"
        :readonly="true"
        v-bkloading="{ isLoading, opacity: 1, color: '#1a1a1a' }"
        :height="fullScreen ? clientHeight : height"
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
<script>import appBaseMixin from '@/mixins/app-base-mixin.js';
import ResourceEditor from './comps/deploy-resource-editor';
import EditorStatus from './comps/deploy-resource-editor/editor-status';
// import _ from 'lodash';
export default {
  components: {
    ResourceEditor,
    EditorStatus,
  },
  mixins: [appBaseMixin],
  props: {
    cloudAppData: {
      type: Array,
      default: [],
    },
    height: {
      type: Number,
      default: 600,
    },
  },
  data() {
    return {
      fullScreen: false,
      clientHeight: document.body.clientHeight,
      isLoading: false,
      editorErr: {
        type: '',
        message: '',
      },
      detail: {},
      screenIsLoading: true,
    };
  },
  computed: {
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.length) {
          console.log(11111, val);
          this.$nextTick(() => {
            setTimeout(() => {
              this.detail = val[0];
              this.$refs.editorRef?.setValue(val[0]);
            }, 500);
          });
        }
      },
      immediate: true,
      deep: true,
    },
    detail: {
      handler(val) {
        if (val && Object.keys(val).length) {
          const webData = val.spec.processes.find(e => e.name === 'web');
          if (!webData) {
            this.handleEditorErr('至少需要一个web进程');
          } else {
            this.handleEditorErr();
          }
          setTimeout(() => {
            this.screenIsLoading = false;
          }, 500);
        }
      },
      immediate: true,
      deep: true,
    },
  },
  mounted() {
  },
  methods: {
    handleEditorErr(err) { // 捕获编辑器错误提示
      this.editorErr.type = 'content'; // 编辑内容错误
      this.editorErr.message = err;
    },

    formDataValidate(index) {
      if (index) {
        return false;
      }
    },
  },
};
</script>
<style scope>
</style>
