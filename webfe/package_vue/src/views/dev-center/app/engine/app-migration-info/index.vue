<template>
  <div class="right-main app-migration-info">
    <cloud-app-top-bar
      :title="$t('迁移信息')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      :is-migration-progress="true"
      @change="handleTabChange"
      @migration-dialog="handleMigrationDialog"
    >
      <div slot="right">
        <bk-button
          :theme="'default'"
          type="submit"
          @click="handleRollbackApp">
          {{ $t('回退应用') }}
        </bk-button>
      </div>
    </cloud-app-top-bar>
    <section class="migration-info-main">
      <!-- 进程管理 -->
      <migration-process-management v-if="active === 'migrationProcessManagement'" />
      <!-- 访问地址 -->
      <section v-else class="addressp-config-wrapper">
        <visit-config :is-operation-shown="false" />
      </section>
    </section>

    <!-- 普通应用迁移至云原生应用弹窗 -->
    <app-migration-dialog
      v-model="appMigrationDialogConfig.visible"
      :data="appMigrationDialogConfig.data"
    />

    <!-- 回退应用弹窗 -->
    <rollback-app-dialog
      v-model="rollbackAppDialogConfig.visible"
      :app-code="appCode"
    />
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import migrationProcessManagement from './comps/migration-process-management.vue';
import visitConfig from '@/views/dev-center/app/engine/entry-config/comps/visit-config.vue';
import appMigrationDialog from '@/components/app-migration-dialog';
import rollbackAppDialog from './comps/rollback-app-dialog.vue';

export default {
  name: 'AppMigrationInfo',
  components: {
    cloudAppTopBar,
    migrationProcessManagement,
    visitConfig,
    appMigrationDialog,
    rollbackAppDialog,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'migrationProcessManagement',
      panels: [
        { name: 'migrationProcessManagement', label: this.$t('进程管理') },
        { name: 'moduleAddress', label: this.$t('访问地址') },
      ],
      appMigrationDialogConfig: {
        visible: false,
        data: {},
      },
      rollbackAppDialogConfig: {
        visible: false,
      },
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
    handleMigrationDialog(visible) {
      this.appMigrationDialogConfig.visible = visible;
      this.appMigrationDialogConfig.data = this.curAppInfo.application;
    },
    // 回退应用
    handleRollbackApp() {
      this.rollbackAppDialogConfig.visible = true;
    },
  },
};
</script>

<style lang="scss" scoped>
.addressp-config-wrapper {
  padding: 24px;
}
</style>
