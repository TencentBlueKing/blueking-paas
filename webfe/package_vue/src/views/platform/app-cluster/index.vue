<template>
  <div class="right-main platform-cluster">
    <Config v-if="tabActive === 'config'" />
    <List v-else />
  </div>
</template>

<script>
import Config from './config.vue';
import List from './list.vue';
export default {
  name: 'PlatformOverview',
  props: {
    tabActive: {
      type: String,
      default: '',
    },
  },
  components: {
    Config,
    List,
  },
  beforeRouteEnter(to, from, next) {
    if (!to.query.active) {
      next((vm) => {
        vm.$router.replace({
          path: to.path,
          query: { ...to.query, active: 'config' },
        });
      });
    } else {
      next();
    }
  },
};
</script>

<style lang="scss" scoped>
.platform-cluster {
  padding: 24px;
  min-width: 0;
}
</style>
