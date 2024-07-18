<template>
  <!-- 设置css变量 -->
  <ul class="version-steps">
    <li
      v-for="(item, index) in steps"
      :key="item.id"
      :class="[
        'item',
        { 'done': item?.status === 'done' },
        { 'active': curStep === (index + 1)},
      ]"
      @click="handleItemClick(item, index + 1)"
    >
      <span
        v-if="item.icon < maxConversionCount"
        class="numeric-symbols">
        {{ CIRCLED_NUMBERS[item.icon - 1] }}
      </span>
      <div class="icon" v-else>
        <span>{{ item.icon }}</span>
      </div>
      <span>{{ item.name }}</span>
    </li>
  </ul>
</template>

<script>
import { CIRCLED_NUMBERS } from '@/common/constants';
export default {
  name: 'VersionSteps',
  props: {
    steps: {
      type: Array,
      default: () => [],
    },
    curStep: {
      type: Number,
      default: 1,
    },
    controllable: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      CIRCLED_NUMBERS,
      maxConversionCount: 20,
    };
  },
  methods: {
    handleItemClick(item, index) {
      // 是否可以点击切换
      if (!this.controllable) {
        return;
      }
      // 未完成状态不可点击
      if (item.status !== 'done') {
        return;
      }
      this.$emit('update:cur-step', index);
      // 请求数据更新
      this.$emit('change', item);
    },
  },
};
</script>

<style lang="scss" scoped>
.version-steps {
  display: flex;
  overflow: hidden;
  .item {
    position: relative;
    flex: 1;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: #979BA5;
    background: #EAEBF0;

    &.done {
      cursor: pointer;
      color: #FFF;
      background: #BED6FE;
      &::after {
        background: #BED6FE !important;
      }
    }

    &.active {
      color: #FFF;
      background: #3A84FF;
      &::after {
        background: #3A84FF !important;
      }
    }

    &:not(:last-child) {
      &::before {
        content: '';
        position: absolute;
        right: -15px;
        width: 32px;
        height: 32px;
        background: #FFF;
        transform: rotateZ(45deg);
        z-index: 9;
      }
      &::after {
        content: '';
        position: absolute;
        position: absolute;
        right: -7px;
        width: 32px;
        height: 32px;
        // var(--content-color); /* 使用CSS变量 */
        background: #EAEBF0;
        transform: rotateZ(45deg);
        z-index: 99;
      }
    }

    .numeric-symbols {
      margin-right: 5px;
      font-size: 12px;
    }

    .icon {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-right: 5px;
      font-size: 10px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      text-align: center;
      color: #979BA5;
      border: 1px solid #979BA5;
      transform: translateY(0);
    }
    &.done,
    &.active {
      .icon {
        color: #fff;
        border: 1px solid #fff;
      }
      .numeric-symbols {
        color: #fff;
      }
    }
  }
}
</style>
