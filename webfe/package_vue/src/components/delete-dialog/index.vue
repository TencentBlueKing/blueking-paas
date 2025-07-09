<template>
  <bk-dialog
    v-model="dialogVisible"
    header-position="left"
    theme="primary"
    :width="480"
    :mask-close="false"
    :title="title"
    ext-cls="custom-dialog-cls"
  >
    <!-- 默认插槽用于提示内容 -->
    <slot></slot>
    <bk-input
      style="margin-top: 8px"
      v-model="inputValue"
      :placeholder="placeholder"
    ></bk-input>
    <slot name="alert"></slot>
    <template slot="footer">
      <bk-button
        theme="danger"
        :disabled="!isConfirmValid"
        :loading="loading"
        @click="$emit('confirm')"
      >
        {{ $t(confirmText) }}
      </bk-button>
      <bk-button
        class="ml10"
        theme="default"
        @click="close"
      >
        {{ $t(cancelText) }}
      </bk-button>
    </template>
  </bk-dialog>
</template>

<script>
export default {
  name: 'ConfirmDeleteDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    confirmText: {
      type: String,
      default: '确定',
    },
    cancelText: {
      type: String,
      default: '取消',
    },
    placeholder: {
      type: String,
      default: '',
    },
    loading: {
      type: Boolean,
      default: false,
    },
    // 需要用户输入确认的文本
    expectedConfirmText: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      inputValue: '',
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
    isConfirmValid() {
      return this.inputValue === this.expectedConfirmText;
    },
  },
  watch: {
    dialogVisible(newVal) {
      if (!newVal) {
        this.inputValue = '';
      }
    },
  },
  methods: {
    close() {
      this.inputValue = '';
      this.dialogVisible = false;
      this.$emit('cancel');
    },
  },
};
</script>

<style lang="scss" scoped>
.ml10 {
  margin-left: 10px;
}
/deep/ .custom-dialog-cls {
  .bk-dialog-body {
    margin-top: 8px;
  }
  .hint-text {
    font-size: 12px;
    color: #4d4f56;
    letter-spacing: 0;
    line-height: 22px;
    word-break: break-all;
  }
  .sign {
    color: #ea3636;
  }
  .paasng-general-copy {
    margin-left: 3px;
    color: #3a84ff;
    cursor: pointer;
  }
  .delete-alert-cls {
    margin-bottom: 16px;
    font-size: 12px;
    color: #4d4f56;
    i.paasng-remind {
      margin-right: 9px;
      transform: translateY(0px);
      font-size: 14px;
      color: #ea3636;
    }
    .bk-button-text {
      line-height: 1 !important;
      height: 12px !important;
      padding: 0;
    }
  }
}
</style>
