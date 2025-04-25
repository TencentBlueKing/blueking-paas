<template>
  <div class="right-main platform-user-management">
    <AuthorizedApp v-if="queueActive === 'authorized'" />
    <UserFeature v-else-if="queueActive === 'feature'" />
    <PlatformAdmin v-else />
  </div>
</template>

<script>
import PlatformAdmin from './platform-admin';
import AuthorizedApp from './authorized-app';
import UserFeature from './user-feature';
export default {
  name: 'PlatformUserManagement',
  components: {
    PlatformAdmin,
    AuthorizedApp,
    UserFeature,
  },
  computed: {
    queueActive() {
      return this.$route.query.active;
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-user-management {
  padding: 24px;
}
</style>
