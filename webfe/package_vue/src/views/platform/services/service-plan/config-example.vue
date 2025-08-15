<template>
  <div class="plan-schema-container mt-8">
    <div
      :class="['schema-header', { show: isShowConfig }]"
      @click="isShowConfig = !isShowConfig"
    >
      {{ $t('配置示例') }}
      <i class="paasng-icon paasng-angle-double-down"></i>
    </div>
    <div
      v-if="isShowConfig"
      class="schema-body-container"
    >
      <i
        class="paasng-icon paasng-general-copy"
        v-copy="copyJson"
        :title="$t('复制')"
      ></i>
      <bk-table
        :data="schemaFields"
        size="small"
      >
        <bk-table-column
          :label="$t('字段')"
          prop="field"
          :width="200"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          :label="$t('类型')"
          prop="type"
          :width="120"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          :label="$t('必填')"
          prop="required"
          :width="80"
        >
          <template #default="{ row }">
            <bk-tag
              :theme="row.required ? 'danger' : 'default'"
              class="m0"
            >
              {{ row.required ? $t('是') : $t('否') }}
            </bk-tag>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('示例')"
          prop="example"
          :min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ row.example || '--' }}
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PlanSchemaExample',
  props: {
    schema: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      isShowConfig: false,
    };
  },
  computed: {
    // 将 schema 数据转换为表格数据
    schemaFields() {
      if (!this.schema) {
        return [];
      }

      const { properties = {}, required = [] } = this.schema;

      return Object.keys(properties).map((field) => {
        const { type = 'string', example = '' } = properties[field];
        return {
          field,
          type,
          required: required.includes(field),
          example,
        };
      });
    },
    copyJson() {
      const json = this.schemaFields.reduce((acc, field) => {
        acc[field.field] = field.example;
        return acc;
      }, {});
      return JSON.stringify(json, null, 2);
    },
  },
};
</script>

<style lang="scss" scoped>
.plan-schema-container {
  .schema-header {
    user-select: none;
    cursor: pointer;
    color: #3a84ff;
    line-height: 32px;

    i {
      transform: rotate(180deg) translateY(2px);
      transition: transform 0.3s;
    }

    &.show i {
      transform: rotate(0deg);
    }
  }
  .schema-body-container {
    position: relative;
    i.paasng-general-copy {
      position: absolute;
      right: 16px;
      top: 16px;
      z-index: 9;
      color: #3a84ff;
      cursor: pointer;
    }
  }
}
</style>
