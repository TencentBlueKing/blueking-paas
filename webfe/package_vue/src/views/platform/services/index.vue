<template>
  <div class="right-main platform-enhanced-services">
    <ServiceConfig v-if="queueActive === 'config'" />
    <ServicePlan v-else />
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
  computed: {
    queueActive() {
      return this.$route.query.active;
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-enhanced-services {
  height: 100%;
}
</style>
