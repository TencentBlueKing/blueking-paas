<template>
  <bk-collapse :accordion="true" @item-click="handlerClick" class="collapse-cls">
    <bk-collapse-item
      :hide-arrow="true">
      <i
        class="paasng-icon paasng-bold"
        :class="isFold ? 'paasng-right-shape' : 'paasng-down-shape'"
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
  },
  data() {
    return {
      isFold: true,
    };
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
