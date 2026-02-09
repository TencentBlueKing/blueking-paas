<template>
  <div class="prefix-select-container">
    <bk-select
      :value="value"
      :placeholder="$t(placeholder)"
      :disabled="disabled"
      class="flex-1"
      ext-cls="prefix-select-cls"
      @change="handleChange"
    >
      <div
        slot="trigger"
        class="trigger-container"
      >
        <div class="prefix">{{ prefix }}</div>
        <div
          class="value"
          v-if="value"
        >
          {{ currentLabel }}
        </div>
        <div
          class="placeholder"
          v-else
        >
          {{ placeholder }}
        </div>
        <i class="bk-icon icon-angle-down dropdown-icon"></i>
      </div>
      <bk-option
        v-for="option in options"
        :key="option.value"
        :id="option.value"
        :name="option.label"
      ></bk-option>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'LabelSelect',
  props: {
    prefix: {
      type: String,
      default: '',
    },
    value: {
      type: [String, Number],
      default: '',
    },
    options: {
      type: Array,
      default: () => [],
    },
    placeholder: {
      type: String,
      default: '请选择',
    },
    width: {
      type: [String, Number],
      default: 300,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    currentLabel() {
      if (!this.value) return '';
      const option = this.options.find((item) => item.value === this.value);
      return option?.label || this.value;
    },
    selectWidth() {
      return `${this.width}px`;
    },
  },
  methods: {
    handleChange(value) {
      this.$emit('input', value);
      this.$emit('change', value);
    },
  },
};
</script>

<style lang="scss" scoped>
.prefix-select-container {
  width: v-bind(selectWidth);
  .prefix-select-cls {
    background-color: #fff;
    .trigger-container {
      position: relative;
      height: 100%;
      display: flex;
      text-align: center;
      .prefix {
        height: fit-content;
        line-height: 30px;
        flex-shrink: 0;
        padding: 0 16px;
        color: #4d4f56;
        background: #fafbfd;
        border-right: 1px solid #c4c6cc;
      }
      .value {
        padding: 0 36px 0 10px;
      }
      .placeholder {
        padding: 0 36px 0 10px;
        color: #c3cdd7;
        cursor: pointer;
        user-select: none;
      }
      .dropdown-icon {
        position: absolute;
        right: 2px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 22px;
        color: #979ba5;
        transition: transform 0.3s;
        pointer-events: none;
      }
    }
    &.is-focus {
      .dropdown-icon {
        transform: translateY(-50%) rotate(180deg);
      }
    }
    &.is-disabled {
      background: #fafbfd;
      .trigger-container .prefix {
        border-color: #dcdee5;
      }
    }
  }
}
</style>
