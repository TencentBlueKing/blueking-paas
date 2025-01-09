<template>
  <div class="file-preview">
    <div class="left-info">
      <img src="/static/images/basic-info-file.png" />
      <div class="file-info">
        <p>{{ file.name }}</p>
        <p :class="['status', status]">
          <i class="paasng-icon paasng-correct"></i>
          <span>{{ $t(statusText) }}</span>
        </p>
      </div>
    </div>
    <div class="size">{{ file.size }}M</div>
  </div>
</template>

<script>
export default {
  name: 'SmartFilePreview',
  props: {
    file: {
      type: Object,
      default: () => ({}),
    },
    status: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'error'].includes(value),
    },
    statusText: {
      type: String,
      default: '上传成功',
    },
  },
};
</script>

<style lang="scss" scoped>
.file-preview {
  font-size: 12px;
  height: 60px;
  background: #ffffff;
  border: 1px solid #c4c6cc;
  border-radius: 2px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  .left-info {
    display: flex;
    align-items: center;
    img {
      width: 32px;
      margin-right: 12px;
    }
    .file-info p {
      line-height: 20px;
    }
    .status {
      position: relative;
      .paasng-correct {
        position: absolute;
        left: -5px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 22px;
      }
      span {
        margin-left: 16px;
      }
      &.success {
        color: #2dcb56;
      }
      &.error {
        color: #ea3636;
      }
    }
  }
  .size {
    font-weight: 700;
    color: #63656e;
  }
}
</style>
