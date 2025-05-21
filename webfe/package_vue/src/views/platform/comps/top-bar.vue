<template>
  <div :class="['platform-top-bar', { 'has-tab': tabPanels.length }]">
    <div class="title">
      <i
        v-if="showBackIcon"
        class="paasng-icon paasng-arrows-left icon-cls-back"
        @click="goBack"
      />
      {{ title }}
      <slot name="extra"></slot>
    </div>
    <div
      v-if="tabPanels.length"
      class="top-tab"
    >
      <bk-tab
        :active.sync="active"
        :scroll-step="100"
        :label-height="42"
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
    showBackIcon() {
      return this.$route.meta?.supportBack;
    },
  },
  watch: {
    $route(newRoute) {
      const newActive = newRoute.query?.active;
      if (newActive && newActive !== this.active) {
        this.active = newActive;
      }
    },
  },
  methods: {
    handleTabChange(activeName) {
      this.$emit('tab-change', activeName);
    },
    // 返回上一页
    goBack() {
      const { backRoute } = this.$route.meta;
      // 详情页单独编辑
      if (this.$route.query?.alone) {
        backRoute.query.type = 'detail';
        this.$store.commit('tenant/updateDetailActiveName', this.$route.query?.id);
      }
      if (backRoute) {
        this.$router.push(backRoute);
        return;
      }
      this.$router.back();
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-top-bar {
  flex-shrink: 0;
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
    .title {
      padding-top: 8px;
      height: 46px;
    }
  }
  .title {
    display: flex;
    align-items: center;
    padding-left: 24px;
    font-size: 16px;
    color: #313238;
  }
  .icon-cls-back {
    margin-right: 5px;
    color: #3a84ff;
    font-size: 20px;
    font-weight: bold;
    cursor: pointer;
  }
}
.platform-tab-cls {
  min-width: 0;
  padding-left: 12px;
  /deep/ .bk-tab-section {
    padding: 0 !important;
  }
  /deep/ .bk-tab-header {
    background-image: none !important;
    .bk-tab-scroll-controller {
      border-bottom: none;
    }
  }
}
</style>
