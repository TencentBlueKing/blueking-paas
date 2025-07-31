<template>
  <ul class="switch-group-container">
    <li
      v-for="item in list"
      :class="['group-item', { active: item.name === active }]"
      :key="item.name"
      @click="() => $emit('change', item)"
    >
      <slot :item="item">
        <template v-if="hasIcon">
          <i
            v-if="item.name === 'all'"
            class="paasng-icon paasng-app-store"
          ></i>
          <span
            v-else
            :class="['dot', item.name]"
          ></span>
        </template>
        <span>{{ item.label }}</span>
        <span
          v-if="hasCount"
          class="count"
        >
          ({{ item.count }})
        </span>
      </slot>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'SwitchGroup',
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    active: {
      type: String,
      default: '',
    },
    hasIcon: {
      type: Boolean,
      default: false,
    },
    hasCount: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss" scoped>
.switch-group-container {
  width: fit-content;
  display: flex;
  align-items: center;
  padding: 4px;
  border-radius: 2px;
  background: #eaebf0;
  .group-item {
    height: 24px;
    line-height: 24px;
    padding: 0 12px;
    font-size: 12px;
    background: #eaebf0;
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.2s;
    &.active {
      background: #fff;
      color: #3a84ff;
      i {
        color: #3a84ff !important;
      }
    }
    i {
      font-size: 14px;
      margin-right: 3px;
      transform: translateY(0px);
    }
  }
  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #fce5c0;
    border: 1px solid #f59500;
    margin-right: 4px;
    &.configured {
      background: #cbf0da;
      border: 1px solid #2caf5e;
    }
    i {
      font-size: 14px;
      margin-right: 3px;
      transform: translateY(0px);
    }
  }
  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #fce5c0;
    border: 1px solid #f59500;
    margin-right: 4px;
    &.configured {
      background: #cbf0da;
      border: 1px solid #2caf5e;
    }
  }
}
</style>
