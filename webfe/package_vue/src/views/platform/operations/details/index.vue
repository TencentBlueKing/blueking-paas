<template>
  <div class="right-main app-details-container">
    <!-- 基本信息 -->
    <AppOverview v-if="tabActive === 'overview'" />
    <span v-else>开发中...</span>
  </div>
</template>

<script>
import AppOverview from './app-overview';
export default {
  name: 'platformAppDetail',
  components: {
    AppOverview,
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
