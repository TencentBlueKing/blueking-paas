<template>
  <div class="cloud-overview-container mt-16">
    <!-- 访问统计 -->
    <AccessStatistics v-if="userFeature.ANALYTICS" />
    <!-- 增强服务 -->
    <EnhancedService class="mt-16" />
  </div>
</template>

<script>
import { mapState } from 'vuex';
import AccessStatistics from './comps/access-statistics.vue';
import EnhancedService from './comps/enhanced-service.vue';

export default {
  name: 'CloudOverviewMain',
  components: {
    AccessStatistics,
    EnhancedService,
  },
  computed: {
    ...mapState(['userFeature']),
  },
};
</script>

<style lang="scss" scoped>
.cloud-overview-container {
  min-width: 0;
  flex: 1;
}
</style>
