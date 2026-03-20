<template>
  <div class="textarea-upload">
    <bk-input
      :value="value"
      type="textarea"
      :placeholder="placeholder"
      :rows="rows"
      :maxlength="maxlength"
      @input="handleInput"
    ></bk-input>
    <div class="upload-row">
      <bk-button
        theme="default"
        @click="handleUploadClick"
      >
        <i class="paasng-icon paasng-upload-2 mr5"></i>
        {{ $t('上传文件') }}
      </bk-button>
      <span class="upload-tip">{{ tip }}</span>
    </div>
    <input
      ref="fileInput"
      type="file"
      :accept="accept"
      style="display: none"
      @change="onFileChange"
    />
  </div>
</template>

<script>
export default {
  name: 'TextareaUpload',
  props: {
    value: {
      type: String,
      default: '',
    },
    placeholder: {
      type: String,
      default: '',
    },
    rows: {
      type: Number,
      default: 4,
    },
    maxlength: {
      type: Number,
      default: 4096,
    },
    // 上传提示文字
    tip: {
      type: String,
      default: '',
    },
    // 接受的文件类型
    accept: {
      type: String,
      default: '.key,.pem,.txt,.yaml',
    },
  },
  methods: {
    handleInput(val) {
      this.$emit('input', val);
    },
    handleUploadClick() {
      this.$refs.fileInput.click();
    },
    onFileChange(e) {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        this.$emit('input', event.target.result);
      };
      reader.onerror = () => {
        this.$bkMessage({
          theme: 'error',
          message: this.$t('文件读取失败'),
        });
      };
      reader.readAsText(file);
      // 清空 input，以便重复上传同一文件
      e.target.value = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.textarea-upload {
  .upload-row {
    display: flex;
    align-items: center;
    margin-top: 8px;

    .upload-tip {
      margin-left: 12px;
      font-size: 12px;
      color: #979ba5;
    }
  }
}
</style>
