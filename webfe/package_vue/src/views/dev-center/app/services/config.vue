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
      <config-edit
        :list="definitions"
        :guide="serviceMarkdown"
        :value="values"
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
      categoryId: 0,
      definitions: [],
      values: [],
      loading: false,
      serviceMarkdown: `## ${this.$t('暂无使用说明')}`,
    };
  },
  computed: {
    region() {
      return this.curAppInfo.application.region;
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
  },
  created() {
    this.init();
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

        console.log('this.servicePaths', this.servicePaths);
        if (resData.instance_tutorial && resData.instance_tutorial.length > 0) {
          this.serviceMarkdown = resData.instance_tutorial;
        }
        this.categoryId = resData.category.id;
      });
      this.fetchServicesSpecsDetail();
    },
    async handleConfigChange(action, payload) {
      this.loading = true;
      const params = {
        specs: payload,
        service_id: this.service,
        module_name: this.curModuleId,
        code: this.curAppCode,
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
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      } finally {
        this.loading = false;
      }
    },
    async fetchServicesSpecsDetail() {
      try {
        const res = await this.$store.dispatch('service/getServicesSpecsDetail', {
          id: this.service,
          region: this.region,
        })
                    ;(res.definitions || []).forEach((item, index) => {
          let values = [];
          res.values.forEach((val) => {
            values.push(val[index]);
          });
          values = [...new Set(values)].filter(Boolean);
          this.$set(item, 'children', values);
          this.$set(item, 'active', res.recommended_values[index]);
          this.$set(item, 'showError', false);
        });
        this.definitions = [...res.definitions];
        this.values = [...res.values];
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
        this.$router.push({
          name: 'appService',
          params: {
            id: this.curAppCode,
            moduleId: this.curModuleId,
          },
        });
      } finally {
        this.isLoading = false;
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
