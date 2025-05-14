<template>
  <bk-popover
    ref="popover"
    theme="light navigation-message"
    ext-cls="custom-table-filter-cls"
    placement="bottom"
    :arrow="false"
    offset="40, 0"
    trigger="click"
  >
    <div class="filter-view">
      <span class="label">{{ label }}</span>
      <span
        id="filter-icon"
        :class="[iconClass, { 'is-selected': selected !== 'all' }]"
      ></span>
    </div>
    <template #content>
      <ul class="panel-list-cls">
        <li
          v-for="item in filterList"
          :key="item.value"
          :class="['panel-item', { selected: item.value === selected }, { disabled: item.disabled }]"
          @click="handleSelect(item)"
        >
          {{ item.text }}
        </li>
      </ul>
    </template>
  </bk-popover>
</template>

<script>
export default {
  name: 'CustomtableFilter',
  props: {
    active: {
      type: String,
    },
    label: {
      type: String,
    },
    iconClass: {
      type: String,
    },
    filterList: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      selected: '',
    };
  },
  watch: {
    active: {
      immediate: true,
      handler(newValue) {
        this.selected = newValue;
      },
    },
  },
  methods: {
    handleSelect(data) {
      if (data.disabled) return;
      this.$refs.popover.instance.hide();
      this.$emit('filter-change', data);
    },
  },
};
</script>

<style lang="scss">
.custom-table-filter-cls {
  top: -12px !important;
  .tippy-tooltip.light-theme {
    box-shadow: 0 0 6px 0 #dcdee5 !important;
    border-radius: 4px !important;
    padding: 0;
  }

  .panel-list-cls {
    color: #26323d;
    min-width: 70px;
    background-color: #fff;
    padding: 5px 0;
    margin: 0;
    max-height: 250px;
    list-style: none;
    overflow-y: auto;

    .panel-item {
      padding: 0 10px;
      font-size: 12px;
      line-height: 26px;
      cursor: pointer;
      &:hover {
        background-color: #eaf3ff;
        color: #3a84ff;
      }
      &.selected {
        background-color: #f4f6fa;
        color: #3a84ff;
      }
      &.disabled {
        cursor: not-allowed;
        color: #c4c6cc;
      }
    }
  }
}
.filter-view {
  #filter-icon {
    display: inline-block;
    width: 20px;
    height: 20px;
    line-height: 20px;
    font-size: 14px;
    text-align: center;
    cursor: pointer;
    color: #c4c6cc;

    &.is-selected {
      color: #3a84ff;
    }
  }
}
</style>
