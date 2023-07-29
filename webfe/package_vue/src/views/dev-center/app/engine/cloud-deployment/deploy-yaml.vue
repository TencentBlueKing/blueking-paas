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
import _ from 'lodash';
export default {
  components: {
    ResourceEditor,
    EditorStatus,
  },
  mixins: [appBaseMixin],
  props: {
    cloudAppData: {
      type: Object,
      default: {},
    },
  },
  data() {
    return {
      fullScreen: false,
      clientHeight: document.body.clientHeight,
      height: 600,
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
        if (val.spec) {
          val.spec.processes.forEach((element) => {
            if (typeof element.isEdit === 'boolean') { // false 也需要删除
              delete element.isEdit;
            }
          });
          val.spec.configuration.env.forEach((element) => {
            if (element.envName) { // envName 删除
              delete element.envName;
            }
            if (element.isAdd) {
              delete element.isAdd;
            }
          });
          this.localCloudAppData = _.cloneDeep(val);
          if (Object.keys(val).length) {
            this.$nextTick(() => {
              setTimeout(() => {
                this.detail = val;
                this.$refs.editorRef?.setValue(val);
              }, 500);
            });
          }
        }
      },
      immediate: true,
    },
    detail: {
      handler(val) {
        if (val.spec) {
          const { processes } = val.spec;
          const webData = processes.find(e => e.name === 'web');
          if (!webData) {
            this.handleEditorErr('至少需要一个web进程');
          } else {
            this.handleEditorErr();
            this.$store.commit('cloudApi/updateCloudAppData', val);
            setTimeout(() => {
              this.screenIsLoading = false;
            }, 500);
          }
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
