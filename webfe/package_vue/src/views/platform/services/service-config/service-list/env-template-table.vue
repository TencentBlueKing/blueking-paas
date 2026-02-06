<template>
  <div class="env-template-table">
    <bk-table
      :data="templateList"
      :outer-border="false"
      :header-border="false"
      :border="false"
      ext-cls="env-table-cls"
    >
      <template slot="empty">{{ $t('请先添加配置项') }}</template>
      <bk-table-column
        label="Key"
        prop="key"
      >
        <template slot-scope="{ row }">
          <span>{{ row.key }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        label="Value"
        prop="value"
      >
        <template slot-scope="{ row }">
          <span>{{ row.value }}</span>
        </template>
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
export default {
  name: 'EnvTemplateTable',
  props: {
    // 服务ID
    serviceId: {
      type: String,
      default: '',
    },
    // 配置项列表
    configItems: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    // 环境变量模板列表：根据配置项和服务ID生成
    templateList() {
      return (this.configItems || [])
        .filter((item) => item.key && !item.isNew)
        .map((item) => ({
          key: `${this.serviceId}_${item.key}`.toUpperCase(),
          value: `{{${item.key}}}`,
        }));
    },
    // 环境变量模板数组：用于提交到后端
    templateArray() {
      return this.templateList.map((item) => ({
        key: item.key,
        value: item.value,
      }));
    },
  },
  watch: {
    templateArray: {
      handler(val) {
        this.$emit('update', val);
      },
      deep: true,
      immediate: true,
    },
  },
};
</script>

<style lang="scss" scoped>
.env-template-table {
  /deep/ .bk-table-empty-block {
    min-height: 42px;
    height: 42px;
    border-bottom: 1px solid #e8e8e8;
  }
}
</style>
