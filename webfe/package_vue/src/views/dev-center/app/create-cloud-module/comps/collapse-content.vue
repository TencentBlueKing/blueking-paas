<template>
  <bk-collapse
    class="collapse-cls"
    v-model="active"
    :accordion="true"
    @item-click="handlerClick"
  >
    <bk-collapse-item
      :hide-arrow="true"
      :name="collapseItemName"
    >
      <i
        class="paasng-icon paasng-bold"
        :class="isFold ? 'paasng-down-shape' : 'paasng-right-shape'"
      />
      <span class="pl10 item-title">{{title}}</span>
      <div slot="content">
        <div class="ml20">
          <slot></slot>
        </div>
      </div>
    </bk-collapse-item>
  </bk-collapse>
</template>
<script>
export default {
  props: {
    title: {
      type: String,
      default() {
        return 'title';
      },
    },
    activeName: {
      type: String,
      default: '',
    },
    collapseItemName: {
      type: String,
      default: '',
    },
    fold: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      isFold: true,
      active: '',
    };
  },
  watch: {
    fold: {
      handler(v) {
        this.isFold = v;
      },
      immediate: true,
    },
  },
  created() {
    // 未传高亮 activeName， 默认不高亮
    this.active = this.activeName || (`${new Date()}`);
  },
  methods: {
    handlerClick() {
      this.isFold = !this.isFold;
    },
  },
};
</script>
<style lang="scss" scoped>
    .item-title{
      color: #313238;
      font-weight: 700;
      font-size: 14px;
    }
    .collapse-cls{
      padding: 10px 20px 15px 20px;
      background: #fff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }
</style>
