<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :mask-close="false"
    :ok-text="$t('提交')"
    @confirm="handleConfirm"
    @value-change="handleValueChange"
  >
    <div class="dialog-content">
      <p>{{ $t('验证码已发送至您的企业微信，请注意查收！') }}</p>
      <div class="mt15 flex-row align-items-center">
        <b>{{ $t('验证码：') }}</b>
        <bk-input
          v-model="appSecretVerificationCode"
          type="text"
          :placeholder="$t('请输入验证码')"
          style="width: 200px; margin-right: 10px"
        />
        <bk-button
          v-if="appSecretTimer !== 0"
          theme="default"
          :disabled="true"
        >
          {{ appSecretTimer }}s&nbsp;{{ $t('后重新获取') }}
        </bk-button>
        <bk-button
          v-else
          theme="default"
          @click="sendMsg"
        >
          {{ $t('重新获取') }}
        </bk-button>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'VerificationCodeDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    func: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      dialogLoading: false,
      appSecretVerificationCode: '',
      appSecretTimer: 0,
      appSecretTimeInterval: null,
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
  },
  methods: {
    handleConfirm() {
      this.dialogVisible = false;
      if (!this.appSecretVerificationCode) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请输入验证码！'),
        });
        return;
      }
      this.$emit('confirm', this.appSecretVerificationCode);
    },
    handleValueChange(flag) {
      if (flag) {
        this.sendMsg();
      }
      this.appSecretVerificationCode = '';
    },
    sendMsg() {
      // 硬编码，需前后端统一
      return new Promise((resolve, reject) => {
        // 验证码正在倒计时
        if (this.appSecretTimer > 0) {
          resolve();
          return;
        }
        const url = `${BACKEND_URL}/api/accounts/verification/generation/`;
        // 验证码间隔时间默认为60s
        this.appSecretTimer = 60;
        this.$http.post(url, { func: this.func }).then(
          () => {
            this.appSecretVerificationCode = '';
            resolve();
            if (!this.appSecretTimeInterval) {
              this.appSecretTimeInterval = setInterval(() => {
                if (this.appSecretTimer > 0) {
                  // eslint-disable-next-line no-plusplus
                  this.appSecretTimer--;
                } else {
                  clearInterval(this.appSecretTimeInterval);
                  this.appSecretTimeInterval = null;
                }
              }, 1000);
            }
          },
          () => {
            this.appSecretVerificationCode = '';
            reject(new Error(this.$t('请求失败，请稍候重试！')));
          }
        );
      });
    },
  },
};
</script>
