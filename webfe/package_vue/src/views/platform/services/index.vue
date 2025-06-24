<template>
  <div class="right-main platform-enhanced-services">
    <ServiceConfig
      v-if="queueActive === 'config'"
      :tenants="tenants"
      :is-init="isInit"
    />
    <ServicePlan
      v-else
      :tenants="tenants"
    />
  </div>
</template>

<script>
import ServiceConfig from './service-config';
import ServicePlan from './service-plan';
export default {
  name: 'PlatformEnhancedServices',
  components: {
    ServiceConfig,
    ServicePlan,
  },
  data() {
    return {
      tenants: [],
      isLoading: false,
      isInit: false,
    };
  },
  computed: {
    queueActive() {
      return this.$route.query.active;
    },
  },
  created() {
    this.getTenants();
  },
  methods: {
    async getTenants() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getTenants');
        this.tenants = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.isInit = true;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-enhanced-services {
  height: 100%;
  /deep/ .vjs-tree {
    font-size: 12px;
  }
}
</style>
