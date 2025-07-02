<template>
  <div class="tenant-select-container">
    <div
      class="tab-label-text"
      v-if="label"
    >
      {{ label }}
    </div>
    <bk-select
      v-model="localValue"
      style="width: 240px"
      ext-cls="tenant-select-custom-cls"
      :clearable="false"
      :searchable="true"
      :search-placeholder="$t('请输入租户名')"
      @change="handleTabChange"
    >
      <bk-option
        v-for="option in panels"
        :key="option.name"
        :id="option.name"
        :name="option.label"
      >
        <template>{{ hasCount ? `${option.label}（${countMap[option.name] || 0}）` : option.label }}</template>
      </bk-option>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'TenantSelect',
  props: {
    value: {
      type: String,
      default: '',
    },
    panels: {
      type: Array,
      required: true,
      default: () => [],
    },
    label: {
      type: String,
      default: '',
    },
    countMap: {
      type: Object,
      default: () => {},
    },
    hasCount: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      localValue: this.value,
    };
  },
  watch: {
    value(newVal) {
      this.localValue = newVal;
    },
  },
  methods: {
    handleTabChange(newValue) {
      this.localValue = newValue;
      this.$emit('input', newValue); // 兼容 v-model
      this.$emit('update:value', newValue); // 兼容 .sync 和 v-model:value
      this.$emit('change', newValue); // 额外提供 change 事件
    },
  },
};
</script>

<style lang="scss" scoped>
.tenant-select-container {
  display: flex;
  align-items: center;
  height: 32px;
  border-radius: 2px;
  .tenant-select-custom-cls {
    border-radius: 0 2px 2px 0;
  }
  .tab-label-text {
    flex-shrink: 0;
    font-size: 12px;
    height: 100%;
    padding: 0 6px 0 8px;
    line-height: 30px;
    border-radius: 2px 0 0 2px;
    background: #fafbfd;
    border: 1px solid #c4c6cc;
    border-right: none;
  }
}
</style>
