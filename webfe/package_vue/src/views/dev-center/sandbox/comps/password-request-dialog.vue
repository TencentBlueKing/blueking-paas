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
    @value-change="handleValueChange"
  >
    <div slot="footer">
      <span
        v-copy="sandboxPassword"
        ref="copyRef"
      ></span>
      <bk-button
        theme="primary"
        @click="handleConfirm"
      >
        {{ $t('复制密码并关闭弹窗') }}
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
        <p>{{ $t('沙箱环境密码') }}</p>
        <div class="password">
          <span>{{ sandboxPassword || '--' }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="sandboxPassword"
          ></i>
        </div>
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
  },
  data() {
    return {
      sandboxPassword: '',
    };
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
    code() {
      return this.$route.query.code;
    },
    module() {
      return this.$route.query.module;
    },
  },
  methods: {
    handleConfirm() {
      if (!this.sandboxPassword) {
        return;
      }
      this.$refs.copyRef.click();
      this.dialogVisible = false;
    },
    // 获取密码
    async getSandboxPassword() {
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxPassword', {
          appCode: this.code,
          moduleId: this.module,
        });
        this.sandboxPassword = res.password;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleValueChange(flag) {
      if (flag) {
        this.getSandboxPassword();
      }
      this.sandboxPassword = '';
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
      color: #63656e;
      line-height: 22px;
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
  }
}
</style>
