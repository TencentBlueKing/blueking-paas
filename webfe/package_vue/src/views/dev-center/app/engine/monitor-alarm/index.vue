<template lang="html">
  <div
    :key="appCode"
    class="right-main"
  >
    <app-top-bar
      :title="$t('告警记录')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    >
      <div
        slot="right"
        style="line-height: 50px;"
      >
        <bk-button
          text
          theme="primary"
          size="small"
          @click="handleHelp"
        >
          {{ $t('文档：如何处理常见告警？') }}
        </bk-button>
      </div>
    </app-top-bar>
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="alarm-record-loading"
      :offset-top="10"
      class="app-container middle alarm-middle"
    >
      <alarm-record @data-ready="handleDataReady" />
    </paas-content-loader>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import AlarmRecord from './alarm-record';
export default {
  name: '',
  components: {
    appTopBar,
    AlarmRecord,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
    };
  },
  watch: {
    '$route'() {
      this.isLoading = true;
    },
  },
  methods: {
    handleHelp() {
      window.open(this.GLOBAL.DOC.MONITOR_INTRO);
    },
    handleDataReady() {
      this.isLoading = false;
    },
  },
};
</script>
<style lang="scss" scoped>
    .alarm-middle {
        margin: 16px auto 30px;
        width: calc(100% - 48px);
        background: #fff;
        padding: 16px 24px
    }
</style>
