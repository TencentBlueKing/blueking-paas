<template>
  <div class="flex-row align-items-center tab-container mb20">
    <div
      v-for="item in visibleItems"
      :key="item.value"
      class="tab-item template"
      :class="[{ active: value === item.value }]"
      @click="handleChange(item.value)"
    >
      {{ $t(item.label) }}
    </div>
  </div>
</template>

<script>
import { TEMPLATE_SOURCE_TYPES } from './template-source-types';

export default {
  name: 'TemplateSourceTabs',
  props: {
    value: {
      type: Number,
      default: TEMPLATE_SOURCE_TYPES.BK_DEVOPS,
    },
    showPlugin: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    visibleItems() {
      return [
        {
          label: '蓝鲸开发框架',
          value: TEMPLATE_SOURCE_TYPES.BK_DEVOPS,
        },
        {
          label: '蓝鲸插件',
          value: TEMPLATE_SOURCE_TYPES.BK_PLUGIN,
          hidden: !this.showPlugin,
        },
        {
          label: '空模板',
          value: TEMPLATE_SOURCE_TYPES.EMPTY_TEMPLATE,
        },
      ].filter((item) => !item.hidden);
    },
  },
  methods: {
    handleChange(value) {
      this.$emit('change', value);
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/border-active-logo.scss';

.tab-container {
  .tab-item {
    margin-right: 10px;
    width: 144px;
    height: 32px;
    line-height: 32px;
    text-align: center;
    background: #f0f1f5;
    border-radius: 2px;
    font-size: 14px;
    color: #63656e;
    cursor: pointer;
    position: relative;
  }
  .template {
    width: 200px;
    height: 48px;
    line-height: 48px;
  }
  .active {
    background: #fff;
    border: 2px solid #3a84ff;
    border-radius: 2px;
    color: #3a84ff;
    @include border-active-logo;
  }
}
</style>
