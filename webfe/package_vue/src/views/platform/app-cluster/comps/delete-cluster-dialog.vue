<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="$t('确认删除集群？')"
    @value-change="valueChange"
  >
    <div slot="footer">
      <bk-button
        theme="danger"
        :disabled="isDeletable"
        :loading="dialogLoading"
        @click="handleDeleteCluster"
      >
        {{ $t('删除') }}
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
      <bk-alert
        class="mb16"
        type="warning"
        :title="
          $t(
            '删除集群仅会解除与开发者中心的托管关系，集群中已部署的应用和组件仍然可用。如不再需要，请到集群中手动进行清理。'
          )
        "
      ></bk-alert>
      <div>
        <p class="label">
          {{ `${$t('该操作不可撤销，请输入集群名称')}：` }}
          <span>{{ config.row.name }}</span>
          {{ $t('进行确认') }}
        </p>
        <bk-input
          v-model="clusterName"
          :placeholder="$t('请输入集群名称：{n}', { n: config.row.name })"
        ></bk-input>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'SandboxDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      clusterName: '',
      dialogLoading: false,
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
    isDeletable() {
      return this.clusterName !== this.config.row.name;
    },
  },
  methods: {
    valueChange() {
      this.clusterName = '';
    },
    // 删除集群
    async handleDeleteCluster() {
      this.dialogLoading = true;
      try {
        await this.$store.dispatch('tenant/deleteCluster', {
          clusterName: this.config.row.name,
        });
        this.dialogVisible = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功！'),
        });
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .label {
    font-size: 12px;
    margin-bottom: 4px;
    span {
      color: #eb3131;
      font-weight: 700;
    }
  }
  .mb16 {
    margin-bottom: 16px;
  }
}
</style>
