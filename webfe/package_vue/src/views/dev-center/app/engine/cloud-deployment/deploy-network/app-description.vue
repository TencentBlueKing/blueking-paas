<template>
  <div class="app-description">
    <div
      class="description item"
      @click="toPage"
    >
      <i class="paasng-icon paasng-page-fill"></i>
      {{ $t('应用描述文件介绍') }}
    </div>
  </div>
</template>

<script>
export default {
  props: {
    doc: {
      type: String,
      default: '',
    },
  },
  methods: {
    toPage() {
      window.open(this.doc, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.app-description {
  margin-top: 16px;
  .item {
    padding: 0 12px;
    display: inline-block;
    height: 32px;
    line-height: 32px;
    background: #f1f5ff;
    color: #3a84ff;
    border-radius: 2px;
    cursor: pointer;
    &:hover {
      background: #e4edfd;
    }
  }
}
</style>
