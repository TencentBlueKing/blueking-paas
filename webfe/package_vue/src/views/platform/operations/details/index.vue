<template>
  <div
    class="right-main app-details-container"
    :key="tabActive"
  >
    <!-- 基本信息 -->
    <AppOverview v-if="tabActive === 'overview'" />
    <Feature v-else-if="tabActive === 'feature'" />
    <Member v-else />
  </div>
</template>

<script>
import AppOverview from './app-overview';
import Feature from './feature';
import Member from './member';
export default {
  name: 'platformAppDetail',
  components: {
    AppOverview,
    Feature,
    Member,
  },
  data() {
    return {};
  },
  computed: {
    tabActive() {
      return this.$route.query.active;
    },
  },
};
</script>

<style lang="scss" scoped>
.app-details-container {
  padding: 24px;
}
</style>
