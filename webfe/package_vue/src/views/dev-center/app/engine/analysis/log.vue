<template lang="html">
  <div class="right-main">

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
  props: {
    appType: {
      type: String,
      default: 'normal',
    },
  },
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
  margin: 16px auto 30px;
  padding: 1px 24px;
  width: calc(100% - 50px);
  padding-bottom: 24px;
}
</style>
