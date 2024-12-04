<template>
  <div class="right-main description-file-conversion">
    <div class="ps-top-bar">
      <h2>{{ $t('应用描述文件转换') }}</h2>
    </div>
    <div class="content">
      <title-bar />
      <bk-alert
        type="info"
        class="alert-cls"
      >
        <div slot="title">
          <p>
            {{
              $t(
                '如果您的应用描述文件版本是 spec_version: 2 且应用为云原生应用：直接将描述文件转换为 specVersion: 3 后即可部署。如果您的应用是普通应用：需要先将应用迁移到云原生应用，再更新描述文件版本'
              )
            }}
          </p>
        </div>
      </bk-alert>
      <!-- 文件转换 -->
      <div
        class="editor-box"
        ref="editorBox"
      >
        <div :class="['source-files', 'file', { 'full-screen': fullscreen.source }]">
          <tools
            name="spec_version: 2"
            :code="sourceCode"
            :is-upload="true"
            @toggle="toggleFullScreen"
            @upload="uploadHandle"
          />
          <monaco-editor
            :style="{ height: `${editorHeight}px` }"
            v-model="sourceCode"
          />
        </div>
        <div
          class="icon-box flex-row flex-column align-items-center justify-content-center"
          :style="{ height: `${editorHeight + 40}px` }"
        >
          <div
            class="conversion-icon flex-row align-items-center justify-content-center"
            :class="{ loading: isLoading }"
            @click="getDescriptionFileConversion"
          >
            <div
              class="loading-icon flex-row"
              v-if="isLoading"
            >
              <div class="dot"></div>
              <div class="dot center"></div>
              <div class="dot"></div>
            </div>
            <i
              class="paasng-icon paasng-zhuanhuan"
              v-else
            ></i>
          </div>
          <span class="text">{{ $t('转换') }}</span>
        </div>
        <div :class="['target-files', 'file', { 'full-screen': fullscreen.target }]">
          <tools
            name="specVersion: 3"
            :code="targetCode"
            :status="conversionStatus"
            @toggle="toggleFullScreen"
          />
          <monaco-editor
            :style="{ height: `${editorHeight}px` }"
            v-model="targetCode"
            :read-only="true"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import MonacoEditor from './comps/monaco-editor.vue';
import titleBar from './comps/title-bar.vue';
import Tools from './comps/tools.vue';
import yamljs from 'js-yaml';

// spec_version: 2 默认示例
const defaultExample = {
  spec_version: 2,
  module: {
    language: 'Python',
    processes: {
      web: {
        command: 'gunicorn wsgi -w 4 -b [::]:${PORT}',
      },
      worker: {
        command: 'celery -A app -l info',
      },
    },
  },
};

export default {
  components: { titleBar, MonacoEditor, Tools },
  name: 'DescriptionFileConversion',
  data() {
    return {
      sourceCode: yamljs.dump(defaultExample, { indent: 2 }),
      targetCode: `# ${this.$t('请先在左侧输入 `spec_version: 2` 版本的应用描述文件，点击转换后将自动生成新版本')}`,
      editorHeight: 0,
      fullscreen: {
        source: false,
        target: false,
      },
      conversionStatus: '',
      isLoading: false,
    };
  },
  mounted() {
    this.init();
  },
  methods: {
    init() {
      // 创建 ResizeObserver 实例
      this.resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const newHeight = entry.contentRect.height;
          // 如果高度发生变化
          if (newHeight !== this.editorHeight + 32) {
            window.requestAnimationFrame(() => {
              this.editorHeight = newHeight + 32;
            });
          }
        }
      });
      this.resizeObserver.observe(this.$refs.editorBox);
    },
    // 获取应用转换后文件
    async getDescriptionFileConversion() {
      if (this.isLoading) return;
      this.isLoading = true;
      try {
        const yamlData = {
          data: this.sourceCode,
          config: {
            headers: {
              'Content-Type': 'application/yaml',
            },
          },
        };
        const buffer = await this.$store.dispatch('tool/getDescriptionFileConversion', yamlData);
        if (buffer instanceof ArrayBuffer) {
          const uint8Array = new Uint8Array(buffer);
          const decoder = new TextDecoder('utf-8');
          const text = decoder.decode(uint8Array);
          this.targetCode = text;
        } else {
          this.targetCode = buffer;
        }
        this.conversionStatus = 'success';
        this.$bkMessage({
          theme: 'success',
          message: this.$t('转换成功'),
        });
      } catch (e) {
        // 兼容两种错误处理
        const errroMsg = typeof e.response?.data === 'string' ? e.response?.data : e.detail;
        this.targetCode = errroMsg;
        this.conversionStatus = 'failed';
        this.$bkMessage({
          theme: 'error',
          message: this.$t('转换错误'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 100);
      }
    },
    // 全屏/收起
    toggleFullScreen(data) {
      this.fullscreen[data.key] = data.value;
    },
    // 本地yaml文件上传
    uploadHandle(data) {
      this.sourceCode = data;
    },
  },
};
</script>

<style lang="scss" scoped>
.description-file-conversion {
  .content {
    margin: 16px 24px;
    display: flex;
    flex-direction: column;
  }
  .editor-box {
    display: flex;
    margin-top: 24px;
    height: calc(100vh - 390px);
    .file {
      width: 50%;
      min-width: 0;
      &.full-screen {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        height: 100vh;
        z-index: 9999;
      }
    }
    .icon-box {
      width: 80px;
      margin: 0 16px;
      background: #e1ecff;
      .conversion-icon {
        height: 40px;
        width: 40px;
        background: #3a84ff;
        border-radius: 50%;
        cursor: pointer;
        &:hover {
          background: #699df4;
        }
        &.loading {
          background: #a3c5fd;
        }
      }
      .text {
        margin-top: 8px;
        font-size: 12px;
        color: #4d4f56;
      }
      .loading-icon {
        .dot {
          width: 4px;
          height: 4px;
          opacity: 0.75;
          border-radius: 50%;
          background: #ffffff;
          &.center {
            opacity: 1;
            margin: 0 4px;
          }
        }
      }
      i {
        color: #fff;
        font-size: 24px;
        transform: translateY(0);
      }
    }
  }
}
</style>
