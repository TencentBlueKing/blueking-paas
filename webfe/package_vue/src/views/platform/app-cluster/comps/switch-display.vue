<template>
  <ul class="switch-group-container">
    <li
      v-for="item in list"
      :class="['group-item', { active: item.name === active }]"
      :key="item.name"
      @click="() => $emit('change', item)"
    >
      {{ item.label }}
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
    }
  }
}
</style>
