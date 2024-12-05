<template>
  <div :class="['tools', status]">
    <div class="file-name">
      {{ name }}
      <span v-if="status === 'failed'">{{ $t('转换失败') }}</span>
    </div>
    <div class="right">
      <!-- 文件上传 -->
      <i
        v-if="isUpload"
        v-bk-tooltips="$t('支持上传 .yaml 和 .yml 格式的文件')"
        class="paasng-icon paasng-upload-2 mr20"
        @click="upload"
      ></i>
      <i
        v-bk-tooltips="$t('复制')"
        class="paasng-icon paasng-general-copy mr20"
        v-copy="code"
      ></i>
      <i
        v-bk-tooltips="isFullscreen ? $t('收起') : $t('展开')"
        :class="['paasng-icon', isFullscreen ? 'paasng-un-full-screen' : 'paasng-full-screen']"
        @click="toggleFullScreen"
      ></i>
      <input
        ref="upload"
        multiple="multiple"
        type="file"
        accept=".yaml,.yml"
        style="position: absolute; width: 0; height: 0"
        @change="handleUpload"
      />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    name: {
      type: String,
      default: '',
    },
    isUpload: {
      type: Boolean,
      default: false,
    },
    code: {
      type: String,
      default: '',
    },
    status: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      isFullscreen: false,
    };
  },
  methods: {
    toggleFullScreen() {
      this.isFullscreen = !this.isFullscreen;
      const key = this.name === 'spec_version: 2' ? 'source' : 'target';
      this.$emit('toggle', { key, value: this.isFullscreen });
    },
    upload() {
      this.$refs.upload.click();
    },
    // .yaml/.yml文件上传处理
    handleUpload(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target.result;
          this.$emit('upload', content);
        };
        reader.readAsText(file);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  font-size: 14px;
  padding-left: 25px;
  padding-right: 16px;
  color: #c4c6cc;
  background: #242424;
  border-radius: 2px 2px 0 0;
  // success
  &.failed {
    color: #e71818;
    background: #fff0f0;
  }
  .right {
    i {
      color: #c4c6cc;
      cursor: pointer;
      font-size: 14px;
      &:hover {
        color: #3a84ff;
      }
    }
    .paasng-general-copy,
    .paasng-upload-2 {
      font-size: 16px;
    }
  }
}
</style>
