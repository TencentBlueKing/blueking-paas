<template>
  <div class="capsule-tab-container">
    <div
      class="tab-label-text"
      v-if="label && panels.length === 1"
    >
      {{ label }}
    </div>
    <!-- 根据tab，封装的胶囊tab切换 -->
    <bk-tab
      v-model:active="localValue"
      type="card-tab"
      ext-cls="custom-capsule-tab-cls"
      @tab-change="handleTabChange"
    >
      <bk-tab-panel
        v-for="item in panels"
        :name="item.name"
        :label="item.label"
        :key="item.name"
      >
        <template #label>
          <slot :option="item"></slot>
        </template>
      </bk-tab-panel>
    </bk-tab>
  </div>
</template>

<script>
export default {
  name: 'CapsuleButtonTab',
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
.capsule-tab-container {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 4px;
  background-color: #f0f1f5;
  border-radius: 2px;
  .tab-label-text {
    margin: 0 8px 0 4px;
  }
  ::v-deep .custom-capsule-tab-cls {
    flex: 1;
    min-width: 0;
    .bk-tab-header {
      height: 24px !important;
      border-radius: 0 !important;
      .bk-tab-label-list {
        height: 24px !important;
      }
      .bk-tab-label-item {
        min-width: auto;
        padding: 0 10px;
        line-height: 24px !important;
        border-radius: 2px !important;
        font-size: 12px;
        color: #4d4f56;
        &::before {
          height: 12px;
          margin-top: -6px;
          background: #dcdee5;
        }
        &.is-last::after {
          background: transparent;
        }
        &:hover {
          color: #4d4f56;
        }
        &.active {
          color: #3a84ff;
        }
      }
      .bk-tab-scroll-controller {
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
        height: 24px !important;
        line-height: 24px !important;
        &.disabled {
          box-shadow: none;
        }
      }
    }
    .bk-tab-section {
      display: none;
    }
  }
}
</style>
