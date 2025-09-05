<template>
  <div class="add-env-popover-content">
    <div class="popover-title">
      {{ title }}
      <div
        class="popover-subtitle mt-4"
        v-if="type === 'edit'"
      >
        {{ $t('环境变量的修改仅对当前沙箱环境生效，不会影响其他环境') }}
      </div>
    </div>
    <div class="popover-body">
      <bk-form
        :model="formData"
        :rules="rules"
        ref="validateForm"
        form-type="vertical"
      >
        <bk-form-item
          label="Key"
          :required="true"
          :property="'key'"
          :error-display-type="'normal'"
        >
          <bk-input
            :disabled="type === 'edit'"
            v-model="formData.key"
            ref="keyInput"
            ext-cls="paas-custom-input-dark-cls"
          ></bk-input>
        </bk-form-item>
        <bk-form-item
          label="Value"
          :required="true"
          :property="'value'"
          :error-display-type="'normal'"
        >
          <bk-input
            ref="valueInput"
            v-model="formData.value"
            ext-cls="paas-custom-input-dark-cls"
          ></bk-input>
        </bk-form-item>
      </bk-form>
    </div>
    <div class="popover-footer">
      <bk-button
        theme="primary"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        ext-cls="cancel-popover-btn"
        theme="default"
        class="ml8"
        @mousedown.prevent="handleCancelMouseDown"
        @click.stop="hidePopover"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    type: {
      type: String,
      default: 'add',
    },
    title: {
      type: String,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      formData: {
        key: '',
        value: '',
      },
      isClosing: false, // 添加关闭状态标识
      rules: {
        key: [
          { required: true, message: this.$t('该字段是必填项'), trigger: 'change' },
          {
            max: 64,
            message: this.$t('不能超过64个字符'),
            trigger: 'blur',
          },
          {
            validator: (value) => {
              // 如果正在关闭弹窗或者没有值，跳过验证
              if (this.isClosing || !value) {
                return true;
              }
              // 只在有值时进行正则验证
              return /^[A-Z][A-Z0-9_]*$/.test(value);
            },
            message: this.$t('只能以大写字母开头，仅包含大写字母、数字与下划线'),
            trigger: 'blur',
          },
        ],
        value: [
          { required: true, message: this.$t('该字段是必填项'), trigger: 'change' },
          {
            max: 2048,
            message: this.$t('不能超过2048个字符'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  beforeDestroy() {
    this.resetForm();
  },
  methods: {
    init(data) {
      // 重置关闭状态
      this.isClosing = false;
      this.resetForm();
      this.$nextTick(() => {
        this.$refs.validateForm?.clearError();
      });
      // 如果有数据则填充
      if (data) {
        const { key = '', value = '' } = data;
        this.formData = {
          key,
          value,
        };
      }
      this.$nextTick(() => {
        setTimeout(() => {
          const focusInput = this.type === 'edit' ? this.$refs.valueInput : this.$refs.keyInput;
          focusInput?.focus();
        }, 100);
      });
    },
    handleConfirm() {
      this.$refs.validateForm
        ?.validate(() => {
          this.$emit('confirm', this.formData, this.type);
        })
        .catch((err) => {
          console.error(err);
        });
    },

    handleCancelMouseDown() {
      // 设置关闭状态，防止后续验证
      this.isClosing = true;
      // 在鼠标按下时立即清理验证错误，防止blur触发验证
      this.$refs.validateForm?.clearError();
    },

    hidePopover() {
      this.isClosing = true;
      this.$refs.validateForm?.clearError();
      this.$emit('hide');
      this.$nextTick(() => {
        this.resetForm();
        this.isClosing = false;
      });
    },

    // 新增重置表单的方法
    resetForm() {
      this.$refs.validateForm?.clearError();
      this.formData = {
        key: '',
        value: '',
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.add-env-popover-content {
  .popover-subtitle {
    font-size: 12px;
    color: #979ba5;
  }
  .popover-body {
    /deep/ .bk-form-item .bk-label {
      color: #979ba5;
    }
  }
}
.cancel-popover-btn {
  color: #f0f1f5;
  background-color: transparent;
  &:hover {
    color: #dcdee5;
    background-color: #242424;
    border: 1px solid #4d4f56;
  }
}
</style>
