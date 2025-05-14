<template>
  <ul class="switch-group-container">
    <li
      v-for="item in list"
      :class="['group-item', { active: item.name === value }]"
      :key="item.name"
      @click="handleClick(item)"
    >
      <slot
        name="icon"
        :item="item"
      ></slot>
      <slot :item="item">
        <span>{{ item.label }}</span>
      </slot>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'CustomRadioCapsule',
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    value: {
      type: String,
      default: '',
    },
  },
  methods: {
    handleClick(item) {
      this.$emit('input', item.name); // 用于 v-model
      this.$emit('change', item); // 保留原有 change 事件
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
    flex-shrink: 0;
    position: relative;
    height: 24px;
    line-height: 24px;
    padding: 0 12px;
    font-size: 12px;
    background: #eaebf0;
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.2s;

    /* 每个 li 右侧的分割线（除了最后一个） */
    &:not(:first-child)::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 1px;
      height: 10px;
      background: #c4c6cc;
    }

    /* 高亮时，隐藏自己的左侧分割线 */
    &.active::before {
      display: none;
    }

    &.active + .group-item::before {
      display: none;
    }

    /* 高亮样式 */
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
    }
  }
}
</style>
