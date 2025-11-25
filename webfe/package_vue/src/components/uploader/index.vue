<template>
  <article
    class="config-upload"
    :class="{ 'content-hover': beforeUpload, isdrag: isdrag }"
  >
    <!--上传界面-->
    <section
      v-if="beforeUpload"
      class="config-upload-content"
    >
      <slot
        name="upload-content"
        v-bind="{ acceptTips }"
      >
        <span class="content-icon"><i class="paasng-icon paasng-upload-2" /></span>
        <slot name="tip">
          <span class="content-drop">{{ $t('点击选择或拖拽文件至此') }}</span>
          <span class="content-tip">{{ acceptTips }}</span>
        </slot>
      </slot>
    </section>
    <!--上传过程-->
    <section
      v-else
      class="config-upload-file"
    >
      <slot
        name="upload-file"
        v-bind="{ beforeAbortUpload, file }"
      >
        <span class="file-abort">
          <i
            class="paasng-icon paasng-close-circle-shape"
            @click="beforeAbortUpload"
          />
        </span>
        <div class="file-info">
          <span class="info-icon"><i class="paasng-icon paasng-order-shape" /></span>
          <div class="info-name">
            <span>{{ file.name || '' }}</span>
          </div>
          <div class="info-progress">
            <div
              class="progress-bar"
              :class="{ 'fail-background': file.hasError }"
              :style="{ width: file.percentage || 0 }"
            />
          </div>
          <span
            class="info-status"
            :class="{ 'fail-message': file.hasError }"
          >
            {{ fileStatusMap[file.status] || file.errorMsg }}
          </span>
          <slot
            v-if="file.hasError"
            name="custom-error"
            v-bind="{ file }"
          ></slot>
        </div>
      </slot>
    </section>
    <!--上传文件框-->
    <section
      v-show="beforeUpload || file.hasError"
      class="config-upload-input"
    >
      <slot
        name="upload-input"
        v-bind="{ file, handleChange, accept }"
      >
        <input
          ref="uploadel"
          :class="{ 'input-hide': file.hasError }"
          :accept="accept"
          :multiple="false"
          :name="name"
          title=""
          :disabled="!beforeUpload && !isdrag"
          type="file"
          @change="handleChange"
        />
      </slot>
    </section>
    <!--上传提示-->
    <section class="config-upload-footer">
      <slot
        name="upload-footer"
        v-bind="{ importConfigExplain }"
      >
        <div class="footer-explain" />
      </slot>
    </section>
  </article>
</template>

<script>
export default {
  name: 'ImportConfigurationUpload',
  props: {
    // 上传至服务器的名称
    name: {
      type: String,
      default: 'file_data',
    },
    // mime类型
    accept: {
      type: String,
      default: 'application/x-tar,application/x-gzip,application/gzip,application/x-compressed',
    },
    // 接受类型提示信息
    acceptTips: {
      type: String,
      default() {
        return `${this.$t('仅支持导入')}".gz .tgz .bz2" ${this.$t('gzip或bzip2压缩')} ${this.$t('格式文件')}`;
      },
    },
    // URL
    action: {
      required: true,
      type: String,
    },
    // 最大文件大小
    maxSize: {
      type: [Number, String],
      default: 500, // 单位M
    },
    // 请求头
    headers: {
      type: [Array, Object],
    },
    withCredentials: {
      type: Boolean,
      default: false,
    },
    otherParams: {
      type: Object,
      default: () => ({}),
    },
    // 文件状态
    fileStatusMap: {
      type: Object,
      default() {
        return {
          ready: this.$t('文件准备中...'),
          uploading: this.$t('正在上传文件...'),
        };
      },
    },
    // 验证文件名是否合法的
    validateName: {
      type: RegExp,
    },
    // 上传失败回调
    onUploadError: {
      type: Function,
      default: () => {},
    },
    // 上传成功回调
    onUploadSuccess: {
      type: Function,
      default: () => {},
    },
    // 上传进度回调
    onUploadProgress: {
      type: Function,
      default: () => {},
    },
  },
  data() {
    return {
      isdrag: false, // 是否在拖拽
      file: {}, // 当前文件对象
      reqsMap: {}, // 文件请求Map（用于终止）
      beforeUpload: true, // 文件上传步骤
      fileIndex: 1, // 文件索引
    };
  },
  mounted() {
    // 注册拖拽事件
    const uploadEl = this.$refs.uploadel;
    uploadEl.addEventListener('dragenter', () => {
      this.isdrag = true;
    });
    uploadEl.addEventListener('dragleave', () => {
      this.isdrag = false;
    });
    uploadEl.addEventListener('dragend', () => {
      this.isdrag = false;
    });
  },
  methods: {
    // 文件变更
    handleChange(e) {
      this.isdrag = false;
      const file = e.target.files[0];
      this.$emit('file-change', e);
      if (this.validateFile(file)) {
        this.file = {};
        this.handleUploadFiles(file);
      } else {
        this.$refs.uploadel.value = '';
      }
    },
    // 组装文件对象，添加额外属性
    handleAssembleFile(file) {
      return {
        name: file.name,
        type: file.type,
        size: file.size,
        percentage: 0,
        uid: Date.now() + (this.fileIndex += 1),
        originFile: file,
        status: 'ready',
        hasError: false,
        errorMsg: '',
      };
    },
    // 校验文件
    validateFile(file) {
      if (!file) return false;
      const validate = {
        message: '',
        success: true,
      };
      if (file.size > this.maxSize * 1024 * 1024) {
        validate.success = false;
        validate.message = `${this.$t('文件不能超过')}${this.maxSize} MB`;
      }
      if (!this.accept.split(',').includes(file.type)) {
        validate.success = false;
        validate.message = this.acceptTips;
      }
      if (this.validateName && !this.validateName.test(file.name)) {
        validate.success = false;
        validate.message = this.$t(
          '格式错误，只能包含字母(a-zA-Z)、数字(0-9)和半角连接符(-)、下划线(_)、空格( )和点(.)'
        );
      }
      if (!validate.success) {
        this.$bkMessage({
          theme: 'error',
          message: validate.message,
          ellipsisLine: 0,
        });
      }
      return validate.success;
    },
    // 上传文件
    handleUploadFiles(file) {
      this.beforeUpload = false;
      // 修改原file对象的属性
      this.file = this.handleAssembleFile(file);
      const { originFile, uid } = this.file;
      this.$refs.uploadel.value = null;
      const options = {
        headers: this.headers,
        withCredentials: this.withCredentials,
        file: originFile,
        filename: this.name,
        action: this.action,
        onProgress: (e) => {
          this.handleHttpProgress(e, originFile);
        },
        onSuccess: (res) => {
          this.handleHttpSuccess(res, originFile);
          delete this.reqsMap[uid];
        },
        onError: (err) => {
          this.handleHttpError(err, originFile);
          delete this.reqsMap[uid];
        },
      };
      const req = this.handleHttpRequest(options);
      this.reqsMap[uid] = req;
    },
    beforeAbortUpload() {
      if (this.file.hasError) {
        this.handleAbortUpload();
      } else {
        this.$bkInfo({
          title: this.$t('确定要终止上传?'),
          maskClose: true,
          confirmFn: () => {
            this.handleAbortUpload();
          },
        });
      }
    },
    // 终止文件上传
    handleAbortUpload() {
      if (this.file.uid && this.reqsMap[this.file.uid]) {
        this.reqsMap[this.file.uid].abort();
        delete this.reqsMap[this.file.uid];
      }
      this.file = {};
      this.beforeUpload = true;
    },
    // 配置说明链接
    importConfigExplain() {
      console.warn(this.$t('需要配置说明地址'));
    },
    // 发送HTTP请求
    handleHttpRequest(option) {
      if (typeof XMLHttpRequest === 'undefined') return;

      const xhr = new XMLHttpRequest();
      if (xhr.upload) {
        xhr.upload.onprogress = (e) => {
          if (e.total > 0) {
            e.percent = Math.round((e.loaded * 100) / e.total);
          }
          option.onProgress(e);
        };
      }

      const formData = new FormData();
      formData.append(option.filename, option.file, option.file.name);
      // append 自定义参数
      for (const key in this.otherParams) {
        formData.append(key, this.otherParams[key]);
      }
      xhr.onerror = (e) => {
        option.onError(e);
      };

      const { action } = option;
      xhr.onload = () => {
        if (xhr.status < 200 || xhr.status >= 300) {
          return option.onError(this.onError(action, xhr));
        }
        option.onSuccess(this.onSuccess(xhr));
      };
      xhr.open('post', action, true);

      if ('withCredentials' in xhr) {
        xhr.withCredentials = option.withCredentials;
      }
      const { headers } = option;
      if (headers) {
        if (Array.isArray(headers)) {
          headers.forEach((head) => {
            const headerKey = head.name;
            const headerVal = head.value;
            xhr.setRequestHeader(headerKey, headerVal);
          });
        } else {
          const headerKey = headers.name;
          const headerVal = headers.value;
          xhr.setRequestHeader(headerKey, headerVal);
        }
      }
      xhr.send(formData);
      return xhr;
    },
    // 默认失败回调
    onError(action, xhr) {
      let msg;
      if (xhr.response) {
        msg = `${JSON.parse(xhr.response).detail || xhr.response}`;
      } else if (xhr.responseText) {
        msg = `${xhr.responseText}`;
      } else {
        msg = `fail to post ${action} ${xhr.status}`;
      }

      const err = {};
      err.message = msg;
      err.status = xhr.status;
      err.method = 'post';
      err.url = action;
      return err;
    },
    // 默认成功回调
    onSuccess(xhr) {
      const text = xhr.responseText || xhr.response;
      if (!text) return text;

      try {
        return JSON.parse(text);
      } catch (e) {
        return text;
      }
    },
    // 获取进度并触发props函数
    handleHttpProgress(e, postFiles) {
      this.file.percentage = `${e.percent}%`;
      this.file.status = 'uploading';
      this.onUploadProgress(e, postFiles);
    },
    // 成功处理并触发props函数
    handleHttpSuccess(res, postFiles) {
      this.file.status = 'success';
      this.onUploadSuccess(res, postFiles);
    },
    // 失败处理并触发props函数
    handleHttpError(err, postFiles) {
      this.file.hasError = true;
      this.file.errorMsg = err.message;
      this.file.status = 'error';
      this.onUploadError(err, postFiles);
    },
    // $t (val) {
    //     return val;
    // }
  },
};
</script>

<style lang="scss" scoped>
@import './common';
$contentBackground: #f5f9ff;
$whiteBackground: #fafbfd;
$contentTipColor: #979ba5;
$grayBackground: #f0f1f5;

@mixin layout-flex($flexDirection, $alignItems, $justifyContent) {
  display: flex;
  flex-direction: $flexDirection;
  align-items: $alignItems;
  justify-content: $justifyContent;
}
@mixin content-hover {
  background: $contentBackground;

  @include border-dashed-1px($primaryFontColor);
}

.content-hover {
  cursor: pointer;
  &:hover {
    @include content-hover;
  }
}
article {
  .isdrag {
    @include content-hover;
  }
}
.config-upload {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 2px;
  background: $whiteBackground;

  @include layout-flex(column, center, flex-start);
  @include border-dashed-1px($unsetColor);
  &-content {
    padding: 70px 0 100px 0;
    @include layout-flex(column, center, flex-start);
    .content-icon {
      height: 64px;
      width: 64px;
      text-align: center;
      font-size: 50px;
      color: #979ba5;
    }
    .content-drop {
      margin-top: 10px;
      line-height: 19px;
      font-size: 14px;
      font-weight: bold;
      color: $defaultFontColor;
    }
    .content-tip {
      width: 440px;
      text-align: center;
      margin-top: 6px;
      line-height: 16px;
      color: #979ba5;
      font-size: 12px;
    }
  }
  &-file {
    width: 100%;
    .file-abort {
      position: absolute;
      right: 0;
      top: 0;
      width: 32px;
      height: 32px;
      line-height: 32px;
      font-size: 16px;
      text-align: center;
      color: $slightFontColor;
      z-index: 2;
      cursor: pointer;
      &:hover {
        background: $grayBackground;
        border-radius: 50%;
      }
    }
    .file-info {
      width: 100%;

      @include layout-flex(column, center, flex-start);
      .info-icon {
        font-size: 40px;
        color: $primaryFontColor;
      }
      .info-name {
        margin-top: 8px;
        font-size: 14px;
        font-weight: bold;
        color: $defaultFontColor;
      }
      .info-progress {
        margin-top: 8px;
        width: 76%;
        height: 6px;
        background: $grayBackground;
        border-radius: 3px;
        .progress-bar {
          width: 10%;
          height: 6px;
          border-radius: 3px;
          background: $primaryFontColor;
          transition: width 0.3s ease-in-out;
        }
        .fail-background {
          background: $failFontColor;
        }
      }
      .info-status {
        margin-top: 12px;
        padding: 0 20px;
        line-height: 16px;
        color: $primaryFontColor;
        word-break: break-all;
      }
      .fail-message {
        color: $failFontColor;
      }
    }
  }
  &-input {
    input {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      cursor: pointer;
      opacity: 0;
    }
    .input-hide {
      cursor: default;
    }
  }
  &-footer {
    position: absolute;
    bottom: 20px;
    .footer-explain {
      line-height: 16px;
      color: $unsetIconColor;
      &-button {
        color: $primaryFontColor;
        cursor: pointer;
        z-index: 2;
      }
    }
  }
  &:hover {
    .config-upload-content .content-icon {
      color: #3a84ff;
    }
  }
}
</style>
