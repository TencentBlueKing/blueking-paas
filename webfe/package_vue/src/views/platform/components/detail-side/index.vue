<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    ext-cls="detail-sideslider-cls"
    v-bind="$attrs"
    @shown="shown"
    @hidden="reset"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ title }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <bk-tab
        :active.sync="tabActive"
        type="card"
        ext-cls="paas-custom-tab-card-grid"
      >
        <bk-tab-panel
          v-for="panel in panels"
          v-bind="panel"
          :key="panel.name"
        ></bk-tab-panel>
        <div class="tab-content">
          <slot :active="tabActive"></slot>
        </div>
      </bk-tab>
    </div>
  </bk-sideslider>
</template>

<script>
export default {
  name: 'DetailSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    panels: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      tabActive: '',
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
  },
  methods: {
    shown() {
      this.tabActive = this.panels[0]?.name || '';
    },
    reset() {
      this.tabActive = '';
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-sideslider-cls {
  .sideslider-content {
    padding-top: 16px;
    background-color: #f5f7fa;
  }
  /deep/ .bk-tab-header {
    padding-left: 40px;
    background: #f5f7fa;
  }
  /deep/ .bk-tab-section {
    border: none;
    background-color: #fff;
    padding: 16px 40px;
  }
}
</style>
