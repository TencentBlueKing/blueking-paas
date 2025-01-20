<template>
  <div :class="['platform-top-bar', { 'has-tab': tabPanels.length }]">
    <div class="title">{{ title }}</div>
    <div
      v-if="tabPanels.length"
      class="top-tab"
    >
      <bk-tab
        :active.sync="active"
        :scroll-step="100"
        type="unborder-card"
        ext-cls="platform-tab-cls"
        @tab-change="handleTabChange"
      >
        <bk-tab-panel
          v-for="(panel, index) in tabPanels"
          v-bind="panel"
          :key="index"
        ></bk-tab-panel>
      </bk-tab>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    title: {
      type: String,
      default: '',
    },
    tabPanels: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      active: this.$route.query?.active || '',
    };
  },
  computed: {
    displayTabPanels() {
      return this.tabPanels.map((item) => {
        return {
          name: item,
          label: this.$t(item),
        };
      });
    },
  },
  methods: {
    handleTabChange(activeName) {
      this.$emit('tab-change', activeName);
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-top-bar {
  position: relative;
  font-size: 14px;
  color: #333;
  background: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;
  min-height: 52px;
  line-height: 52px;
  z-index: 1;
  &.has-tab {
    line-height: 36px;
  }
  .title {
    padding-left: 24px;
    font-size: 16px;
    color: #313238;
  }
}
.platform-tab-cls {
  min-width: 0;
  padding-left: 12px;
  /deep/ .bk-tab-section {
    padding: 0 !important;
  }
  /deep/ .bk-tab-header {
    height: 50px !important;
    background-image: none !important;
    .bk-tab-scroll-controller {
      border-bottom: none;
    }
  }
}
</style>
