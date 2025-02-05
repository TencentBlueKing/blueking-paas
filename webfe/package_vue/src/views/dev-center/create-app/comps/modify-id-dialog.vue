<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="$t('修改应用 ID')"
    @value-change="handleValueChange"
  >
    <div
      slot="footer"
      class="footer-cls"
    >
      <bk-checkbox v-model="isAware">
        {{ $t('我已知晓风险') }}
      </bk-checkbox>
      <div class="btns">
        <bk-button
          theme="primary"
          :disabled="!isAware"
          @click="handleConfirm"
        >
          {{ $t('确定') }}
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
    </div>
    <div class="dialog-content">
      <bk-form
        form-type="vertical"
        :model="formData"
        ref="form"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('应用 ID')"
          :required="true"
          :property="'code'"
          :error-display-type="'normal'"
        >
          <bk-input v-model="formData.code"></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('应用名称')"
          :property="'name'"
          :error-display-type="'normal'"
        >
          <bk-input v-model="formData.name"></bk-input>
        </bk-form-item>
      </bk-form>
      <bk-alert
        class="mt15"
        type="warning"
        :title="$t('应用 ID 修改后，将导致应用访问地址、API 授权信息等发生变更，请务必确认相关风险。')"
      ></bk-alert>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'ModifyIdDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    verifyCode: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      formData: {
        code: '',
        name: '',
      },
      isAware: false,
      rules: {
        code: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator: (value) => {
              if (!this.verifyCode) {
                return true;
              }
              return this.verifyCode !== value;
            },
            message: this.$t('已存在'),
            trigger: 'blur',
          },
        ],
        name: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
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
      this.$refs.form.validate().then(
        () => {
          this.$emit('confirm', { ...this.formData });
          this.dialogVisible = false;
        },
        (validator) => {
          console.error(validator);
        }
      );
    },
    handleValueChange(v) {
      this.isAware = false;
      if (v) {
        this.formData = { ...this.data };
        return;
      }
      this.formData = {
        code: '',
        name: '',
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.footer-cls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dialog-content {
  .mb16 {
    margin-bottom: 16px;
  }
}
</style>
