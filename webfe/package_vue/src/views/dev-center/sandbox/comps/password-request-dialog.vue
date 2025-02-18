<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="$t('获取沙箱环境密码')"
  >
    <div slot="footer">
      <span
        v-copy="password"
        ref="copyRef"
      ></span>
      <bk-button
        theme="primary"
        @click="handleConfirm"
      >
        {{ $t('复制密码并关闭') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        type="submit"
        class="ml8"
        @click="dialogVisible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <div class="dialog-content">
      <div class="password-box">
        <p class="mb6">{{ $t('沙箱环境密码') }}</p>
        <div class="password">
          <span>{{ password || '--' }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="password"
          ></i>
        </div>
        <p class="tips">{{ $t('获取密码后，请在 “Welcome to code-server” 界面的 PASSWORD 处输入') }}</p>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'PasswordRequestDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    password: {
      type: String,
      default: '',
    },
  },
  computed: {
    dialogVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
  },
  methods: {
    handleConfirm() {
      if (!this.password) {
        return;
      }
      this.$refs.copyRef.click();
      this.dialogVisible = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .ml12 {
    margin-left: 12px;
  }
  .ml8 {
    margin-left: 8px;
  }
  .password-box {
    margin-top: 16px;
    p {
      font-size: 14px;
      color: #4d4f56;

      line-height: 22px;
    }
    .mb6 {
      margin-bottom: 6px;
    }
    .password {
      position: relative;
      height: 48px;
      line-height: 48px;
      padding: 0 12px;
      font-size: 14px;
      color: #313238;
      background: #f0f1f5;
      .paasng-general-copy {
        position: absolute;
        right: 16px;
        top: 50%;
        transform: translateY(-50%);
        color: #3a84ff;
        cursor: pointer;
      }
    }
    .tips {
      font-size: 12px;
      margin-top: 6px;
      color: #63656e;
    }
  }
}
</style>
