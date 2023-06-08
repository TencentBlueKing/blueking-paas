<template lang="html">
  <div class="right-main">
    <app-top-bar
      v-if="isEngineEnabled"
      :title="$t('访问日志统计')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <div
      v-else
      class="ps-top-bar"
    >
      <h2> {{ $t('访问日志统计') }} </h2>
    </div>

    <paas-content-loader
      :is-loading="isLoading"
      placeholder="analysis-loading"
      :offset-top="20"
      class="app-container middle log-analy-container"
    >
      <app-analysis
        :backend-type="'ingress'"
        tab-name="logAnalysis"
        :engine-enabled="isEngineEnabled"
        @data-ready="handleDataReady"
      />
    </paas-content-loader>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import analysis from './comps/analysis.vue';

export default {
  components: {
    appTopBar,
    appAnalysis: analysis,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isEngineEnabled: true,
      isLoading: true,
    };
  },
  watch: {
    '$route'() {
      this.isEngineEnabled = this.curAppInfo.web_config.engine_enabled;
      this.isLoading = true;
    },
  },
  created() {
    this.isEngineEnabled = this.curAppInfo.web_config.engine_enabled;
  },
  methods: {
    handleDataReady() {
      this.isLoading = false;
    },
  },
};
</script>
<style scoped lang="scss">
.log-analy-container{
  background: #fff;
  margin-top: 16px;
  padding: 1px 24px;
}
</style>
