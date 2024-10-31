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
      <bk-button
        theme="primary"
        v-copy="sandboxPassword"
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
      <div class="get-code">
        <bk-input
          :disabled="true"
          v-model="username"
        ></bk-input>
        <bk-button
          v-if="secretTimer !== 0"
          theme="primary"
          :outline="true"
          class="ml12"
          :disabled="true"
        >
          {{ secretTimer }}s {{ $t('后重新获取') }}
        </bk-button>
        <bk-button
          v-else
          theme="primary"
          :outline="true"
          class="ml12"
          @click="sendVerificationCode"
        >
          {{ $t('发送验证码') }}
        </bk-button>
      </div>
      <bk-input
        :placeholder="$t('请输入验证码')"
        v-model="verificationCode"
      ></bk-input>
      <bk-button
        :theme="'primary'"
        :disabled="isPasswordBtnLodaing"
        class="get-password-btn"
        @click="getSandboxPassword"
      >
        {{ $t('获取密码') }}
      </bk-button>
      <div
        class="password-box"
        v-if="sandboxPassword"
      >
        <p>{{ $t('沙箱环境密码') }}</p>
        <div class="password">
          <span>{{ sandboxPassword }}</span>
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
      verificationCode: '',
      secretTimer: 0,
      secretTimeInterval: null,
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
    isPasswordBtnLodaing() {
      return !this.verificationCode;
    },
    curUserInfo() {
      return this.$store.state.curUserInfo;
    },
    username() {
      return this.curUserInfo.username;
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
      this.dialogVisible = false;
    },
    // 获取验证码
    sendVerificationCode() {
      return new Promise((resolve, reject) => {
        if (this.secretTimer > 0) {
          resolve();
          return;
        }
        const url = `${BACKEND_URL}/api/accounts/verification/generation/`;

        this.secretTimer = 60;
        this.$http.post(url, { func: 'GET_CODE_EDITOR_PASSWORD' }).then(
          () => {
            this.verificationCode = '';
            resolve();
            if (!this.secretTimeInterval) {
              this.secretTimeInterval = setInterval(() => {
                if (this.secretTimer > 0) {
                  // eslint-disable-next-line no-plusplus
                  this.secretTimer--;
                } else {
                  clearInterval(this.secretTimeInterval);
                  this.secretTimeInterval = null;
                }
              }, 1000);
            }
          },
          () => {
            this.verificationCode = '';
            reject(new Error(this.$t('请求失败，请稍候重试！')));
          }
        );
      });
    },
    // 获取密码
    async getSandboxPassword() {
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxPassword', {
          appCode: this.code,
          moduleId: this.module,
          data: {
            verification_code: this.verificationCode,
          },
        });
        this.sandboxPassword = res.password;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleValueChange() {
      this.sandboxPassword = '';
      this.verificationCode = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .get-code {
    display: flex;
    margin-bottom: 16px;
    /deep/ .bk-button {
      flex-shrink: 0;
    }
  }
  .ml12 {
    margin-left: 12px;
  }
  .ml8 {
    margin-left: 8px;
  }
  .get-password-btn {
    margin-top: 24px;
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
