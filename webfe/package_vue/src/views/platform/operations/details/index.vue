<template>
  <div class="right-main app-details-container">
    <!-- 基本信息 -->
    <AppOverview v-if="tabActive === 'overview'" />
    <Feature v-else></Feature>
  </div>
</template>

<script>
import AppOverview from './app-overview';
import Feature from './feature';
export default {
  name: 'platformAppDetail',
  components: {
    AppOverview,
    Feature,
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
