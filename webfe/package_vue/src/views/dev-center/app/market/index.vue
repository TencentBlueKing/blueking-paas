<template>
  <div class="right-main">
    <div class="ps-top-bar">
      <h2> {{ $t('应用市场') }} </h2>
    </div>
    <paas-content-loader
      :is-loading="isDataLoading || isManagerDataLoading"
      placeholder="market-loading"
      :offset-top="25"
      class="app-container overview-middle"
    >
      <section v-show="!isDataLoading && !isManagerDataLoading">
        <!-- <bk-tab
          class="mt5"
          :active.sync="active"
          type="unborder-card"
          ext-cls="mark-info-tab-cls"
          @tab-change="handleTabChange"
        >
          <bk-tab-panel
            name="visitInfo"
            :label="$t('发布管理')"
          />
          <bk-tab-panel
            name="baseInfo"
            :label="$t('修改市场信息')"
          />
        </bk-tab> -->

        <market-info
          @data-ready="handleDataReady"
        />
        <market-manager
          @data-ready="handleManagerDataReady"
        />
      </section>
    </paas-content-loader>
  </div>
</template>

<script>import MarketInfo from './market-info';
import MarketManager from './market-manager';

export default {
  components: {
    MarketInfo,
    MarketManager,
  },
  data() {
    return {
      isDataLoading: true,
      isManagerDataLoading: true,
    };
  },
  created() {
  },
  methods: {

    handleDataReady() {
      this.isDataLoading = false;
    },
    handleManagerDataReady() {
      this.isManagerDataLoading = false;
    },
  },
};
</script>

<style lang="scss" scoped>
    @import 'index.scss';
</style>
