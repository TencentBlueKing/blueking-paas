<template>
  <bk-dialog
    v-model="dialogCofig.visible"
    width="600"
    :theme="'primary'"
    :title="dialogCofig.title"
    :header-position="'left'"
    :mask-close="false"
    ext-cls="entry-change-dialog-cls"
    :loading="dialogCofig.loading"
    @confirm="handleDialogConfirm"
    @after-leave="handleAfterLeave"
  >
    <div class="dialog-content">
      <div class="copywriter">
        <p
          class="cancel"
          v-if="isCancelEntry"
        >
          {{ $t('取消后，该模块将不再提供外部访问地址（如：{r}）。', { r: address }) }}
        </p>
        <p
          class="change"
          v-else
        >
          {{ $t('每个模块可以设置一个访问入口，请求访问地址时（如：{r}）会被转发到访问入口指向的目标服务上。', { r: address }) }}
        </p>
      </div>
      <bk-alert
        type="warning"
        :title="$t('访问入口修改后，需重新部署对应环境才能生效。')"
      ></bk-alert>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'EntryChangeDialog',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => {},
    },
    address: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      dialogCofig: {
        visible: false,
        title: '',
        loading: false,
      },
    };
  },
  computed: {
    isCancelEntry() {
      return this.config?.type === 'cancel';
    },
  },
  watch: {
    value(newVal) {
      this.dialogCofig.visible = newVal;
      if (newVal) {
        this.init();
      }
    },
  },
  methods: {
    init() {
      const data = this.config.entryData;
      this.dialogCofig.title = this.isCancelEntry
        ? this.$t('确认取消访问入口')
        : this.$t('确认将 {p} 进程的 {s} 端口设置为访问入口', { p: data.processName, s: data.servieName });
    },
    handleAfterLeave() {
      this.dialogCofig.loading = false;
      this.$emit('change', false);
    },
    handleDialogConfirm() {
      this.dialogCofig.loading = true;
      this.$emit('confirm');
    },
  },
};
</script>

<style lang="scss" scoped>
.entry-change-dialog-cls {
  .copywriter {
    word-break: break-all;
    font-size: 14px;
    color: #63656e;
    line-height: 22px;
    margin-top: 8px;
    margin-bottom: 16px;
  }
}
</style>
