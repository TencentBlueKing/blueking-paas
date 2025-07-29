<template>
  <bk-dialog
    v-model="dialogVisible"
    header-position="left"
    theme="primary"
    :width="480"
    :mask-close="false"
    :auto-close="false"
    :title="$t('确认分配实例')"
    :loading="loading"
    ext-cls="assign-instance-dialog-cls"
    @confirm="$emit('confirm')"
    @cancel="close"
  >
    <!-- 默认插槽用于提示内容 -->
    <div
      v-if="!loading"
      v-dompurify-html="confirmTip"
      class="assign-instance-info"
    ></div>
    <div
      class="dialog-instance-loading-wrapper"
      v-else
    >
      <round-loading
        size="small"
        class="round-loading-cls"
      />
      <p class="text">{{ $t('正在分配中') }}</p>
    </div>
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
    data: {
      type: Object,
      default: () => {},
    },
    loading: {
      type: Boolean,
      default: false,
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
    confirmTip() {
      return this.$t('确认给 <i>{m}</i> 模块的预发布环境分配 <i>{n}</i> 增强服务实例', {
        m: this.data?.moduleName,
        n: this.data?.service?.display_name,
      });
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
/deep/ .assign-instance-dialog-cls {
  .bk-dialog-body {
    margin-top: 8px;
  }
  .dialog-instance-loading-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 20px 0;
    .round-loading-cls {
      margin: 0;
      transform: scale(1.5);
    }
    .text {
      margin-left: 18px;
      font-weight: 700;
      font-size: 16px;
      color: #313238;
    }
  }
  .assign-instance-info i {
    font-style: normal;
    color: #e71818;
  }
}
</style>
