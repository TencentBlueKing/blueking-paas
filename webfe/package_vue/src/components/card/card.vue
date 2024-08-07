<template>
  <div class="card-wrapper card-style">
    <!-- 基于卡片组件，改造样式 -->
    <bk-card
      ref="card"
      v-bind="$attrs"
      :collapse-icons="icons"
    >
      <template v-for="(value, name) in $slots" #[name]="slotData">
        <slot :name="name" v-bind="slotData || {}"></slot>
      </template>
    </bk-card>
  </div>
</template>

<script>
export default {
  name: 'PaasCard',
  props: {
    icons: {
      type: Array,
      default: (() => ['icon-right-shape', 'icon-down-shape']),
    },
  },
};
</script>

<style lang="scss" scoped>
.card-wrapper /deep/ .bk-card {
  border: none;
  cursor: unset;
  &:hover {
    box-shadow: unset;
  }
  .bk-card-head {
    border: none;
    cursor: pointer;
    .title {
      color: #313238;
      font-weight: 700;
      user-select: none;
    }
    i {
      color: #63656E;
    }
  }
  .bk-card-body {
    padding: 16px 20px 24px;
  }
}
</style>
