<template>
  <div class="code-source-selector m0">
    <div
      v-for="(item, index) in items"
      :key="index"
      :class="['code-source-item', { on: getIsSelected(item, index) }]"
      @click="handleItemClick(item, index)"
    >
      <img :src="'/static/images/' + item.imgSrc + '.png'" />
      <p
        class="text-ellipsis"
        style="line-height: 1"
      >
        {{ item.name }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CodeSourceSelector',
  props: {
    // 选项列表
    items: {
      type: Array,
      default: () => [],
    },
    // 当前选中的值
    value: {
      type: [String, Number],
      default: null,
    },
    // 选中逻辑类型：'index' 表示按索引选中，'value' 表示按值选中
    selectionType: {
      type: String,
      default: 'index',
    },
    // 是否可点击
    clickable: {
      type: Boolean,
      default: true,
    },
    // 当只有一项时是否默认选中
    autoSelectSingle: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    selectedValue() {
      if (this.selectionType === 'index') {
        return this.value;
      }
      return this.items.findIndex((item) => item.value === this.value);
    },
  },
  mounted() {
    if (this.autoSelectSingle && this.items.length === 1 && this.value === null) {
      this.handleItemClick(this.items[0], 0);
    }
  },
  methods: {
    // 判断是否选中
    getIsSelected(item, index) {
      if (this.selectionType === 'index') {
        return index === this.value;
      }
      return item.value === this.value;
    },

    handleItemClick(item, index) {
      if (!this.clickable) return;
      this.$emit('change', item, index);
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/border-active-logo.scss';

.code-source-selector {
  overflow: hidden;
  display: flex;
  gap: 10px;
  .code-source-item {
    position: relative;
    width: 145px;
    height: 88px;
    text-align: center;
    background: #f0f1f5;
    border-radius: 2px;
    cursor: pointer;
    img {
      height: 36px;
      margin: 12px 0 6px;
      width: 40px;
    }
    p {
      margin: 0;
      font-size: 14px;
      color: #63656e;
    }
  }
  .on {
    border: solid 2px #3a84ff;
    background-color: #fff;
    color: #3a84ff;
    @include border-active-logo;
    p {
      color: #3a84ff;
    }
  }
}
</style>
