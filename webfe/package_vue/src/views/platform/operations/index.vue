<template>
  <div class="right-main platform-operations-container">
    <!-- 应用列表 -->
    <AppList :tenants="tenants" />
  </div>
</template>

<script>
import AppList from './app-list';
export default {
  name: 'PlatformAppList',
  components: {
    AppList,
  },
  data() {
    return {
      tenants: [],
    };
  },
  created() {
    this.getTenants();
  },
  methods: {
    async getTenants() {
      try {
        const res = await this.$store.dispatch('tenant/getTenants');
        this.tenants = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-operations-container {
  padding: 24px;
}
</style>
