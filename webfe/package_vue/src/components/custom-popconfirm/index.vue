<template>
  <bk-popconfirm
    v-bind="$attrs"
    offset="-15, 0"
    ext-cls="replicas-policy-popconfirm-cls"
    @confirm="$emit('confirm')"
    @cancel="$emit('cancel')"
  >
    <slot></slot>
    <div
      slot="content"
      class="pb-6"
    >
      <slot name="content"></slot>
    </div>
  </bk-popconfirm>
</template>

<style lang="scss">
.replicas-policy-popconfirm-cls {
  .tippy-tooltip {
    padding: 0;
    border-radius: 2px !important;
    .tippy-content {
      padding: 0 !important;
    }
    .bk-popconfirm-content {
      padding: 0 !important;
      display: flex;
      flex-direction: column;
    }
    .popconfirm-content {
      padding: 12px 16px;
    }
    .popconfirm-operate {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      height: 42px;
      padding: 0 16px;
      border-top: 1px solid #dcdee5;
      background: #fafbfd;
    }
  }
  .tippy-arrow {
    left: 15px !important;
  }
}
</style>
