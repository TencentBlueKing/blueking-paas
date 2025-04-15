<template>
  <div class="right-main platform-user-management">
    <SystemApiUser v-if="queueActive === 'api'" />
    <UserFeature v-else-if="queueActive === 'feature'" />
    <PlatformAdmin v-else />
  </div>
</template>

<script>
import PlatformAdmin from './platform-admin';
import SystemApiUser from './system-api-user';
import UserFeature from './user-feature';
export default {
  name: 'PlatformUserManagement',
  components: {
    PlatformAdmin,
    SystemApiUser,
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
