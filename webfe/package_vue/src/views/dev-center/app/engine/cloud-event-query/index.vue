<template>
  <div class="cloud-event-query">
    <cloud-app-top-bar
      :title="$t('事件查询')"
      :module-id="curModuleId"
      :app-code="appCode"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <div class="app-container middle main">
      <bk-tab
        :active.sync="active"
        type="unborder-card"
        @tab-change="handleTabChange"
      >
        <bk-tab-panel
          v-for="(panel, index) in panels"
          v-bind="panel"
          :key="index"
        >
          <process-event
            :key="panel.name"
            :is-loading="isTableLoading"
            :app-code="appCode"
            :environment="panel.name"
            :events="eventList"
          ></process-event>
        </bk-tab-panel>
      </bk-tab>
    </div>
  </div>
</template>

<script>
import processEvent from './comps/process-event.vue';
import appTopBar from '@/components/paas-app-bar';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'cloud-event-query',
  components: {
    processEvent,
    appTopBar,
    cloudAppTopBar
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'stag',
      panels: [
        { name: 'stag', label: this.$t('预发布环境') },
        { name: 'prod', label: this.$t('生产环境') },
      ],
      eventList: [],
      isTableLoading: true,
    };
  },
  computed: {
    curEnv() {
      return this.$router.query?.env || 'stag';
    },
  },
  watch: {
    curModuleId(val) {
      this.getCloudAppInfo();
    },
  },
  created() {
    this.active = this.curEnv;
    this.pushCurrentRoute();
    this.getCloudAppInfo();
  },
  methods: {
    handleTabChange() {
      this.isTableLoading = true;
      this.pushCurrentRoute();
      this.getCloudAppInfo();
    },
    /**
     * 更新当前query
     */
    pushCurrentRoute() {
      const route = this.$route;
      this.$router.push({
        ...route,
        query: {
          env: this.active,
        },
      });
    },
    /**
     * 获取当前当前应用信息
     */
    async getCloudAppInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getCloudAppStatus', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.active,
        });
        this.eventList = res.events;
      } catch (e) {
        this.eventList = [];
        if (e.code !== 'GET_DEPLOYMENT_FAILED') {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      } finally {
        this.isTableLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.cloud-event-query {
  .main {
    padding-top: 0;
    margin-top: 16px;
    background: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 #1919290d;
  }
}
</style>
