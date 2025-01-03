<template lang="html">
  <div class="right-main">
    <app-top-bar
      :paths="servicePaths"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
    />
    <div
      v-bkloading="{ isLoading }"
      class="app-container"
    >
      <ConfigEdit
        :data="serviceConfig"
        :guide="serviceMarkdown"
        :enable-loading="loading"
        @on-change="handleConfigChange"
      />
    </div>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import ConfigEdit from './comps/config-edit';

export default {
  components: {
    appTopBar,
    ConfigEdit,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      service: this.$route.params.service,
      servicePaths: [],
      loading: false,
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
      serviceConfig: this.$route.params.data,
    };
  },
  computed: {
    region() {
      return this.curAppInfo.application.region;
    },
  },
  watch: {
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
    if (!this.serviceConfig) {
      this.getServicePossiblePlans();
    }
  },
  methods: {
    init() {
      this.isLoading = true;
      this.$http.get(`${BACKEND_URL}/api/services/${this.service}/`).then((response) => {
        this.servicePaths = [];
        const resData = response.result;
        this.servicePaths.push({
          title: resData.category.name,
          routeName: 'appService',
        });
        this.servicePaths.push({
          title: this.curModuleId,
        });
        this.servicePaths.push({
          title: `${this.$t('启用')}${resData.display_name}`,
        });

        if (resData.instance_tutorial && resData.instance_tutorial.length > 0) {
          this.serviceMarkdown = resData.instance_tutorial;
        }
        this.isLoading = false;
      });
    },
    async handleConfigChange(action, payload) {
      this.loading = true;
      const params = {
        service_id: this.service,
        module_name: this.curModuleId,
        code: this.curAppCode,
        [payload.key]: payload.value,
      };
      try {
        await this.$store.dispatch('service/enableServices', params);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('服务启用成功'),
        });
        this.$router.push({
          name: 'appServiceInner',
          params: {
            id: this.curAppCode,
            service: this.service,
            category_id: this.$route.params.category_id,
          },
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.loading = false;
      }
    },
    // 获取应用模块绑定服务时，可能的详情方案
    async getServicePossiblePlans() {
      try {
        const res = await this.$store.dispatch('service/getServicePossiblePlans', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          service: this.service,
        });
        this.serviceConfig = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.app-container {
  padding: 15px 0;
}
</style>
