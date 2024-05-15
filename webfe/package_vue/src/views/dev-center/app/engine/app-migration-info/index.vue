<template>
  <div class="right-main app-migration-info">
    <cloud-app-top-bar
      :title="$t('迁移信息')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
    />
    <section class="migration-info-main">
      <!-- 进程管理 -->
      <migration-process-management v-if="active === 'migrationProcessManagement'" />
      <!-- 访问地址 -->
      <section v-else class="addressp-config-wrapper">
        <visit-config />
      </section>
    </section>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import migrationProcessManagement from './comps/migration-process-management.vue';
import visitConfig from '@/views/dev-center/app/engine/entry-config/comps/visit-config.vue';

export default {
  name: 'AppMigrationInfo',
  components: {
    cloudAppTopBar,
    migrationProcessManagement,
    visitConfig,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'migrationProcessManagement',
      panels: [
        { name: 'migrationProcessManagement', label: this.$t('进程管理') },
        { name: 'moduleAddress', label: this.$t('访问地址') },
      ],
    };
  },
  created() {
    this.checkTab();
  },
  methods: {
    handleTabChange(name, updateRoute = true) {
      this.active = name;
      if (updateRoute) {
        this.$router.replace({ query: { ...this.$route.query, tab: name } });
      }
    },
    checkTab() {
      const tabQuery = this.$route.query.tab;
      const validTab = this.panels.some(panel => panel.name === tabQuery);
      if (validTab) {
        this.active = tabQuery;
      } else {
        this.handleTabChange(this.panels[0].name, false);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.addressp-config-wrapper {
  padding: 24px;
}
</style>
