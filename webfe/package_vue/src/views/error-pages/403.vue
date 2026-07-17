<template lang="html">
  <div class="right-main">
    <div
      v-if="errorDetail.code === 1302403"
      class="no-app-permissions"
    >
      <bk-exception
        class="exception-wrap-item"
        type="403"
      >
        <span>{{ $t('无该应用访问权限') }}</span>
        <div class="text-subtitle">{{ errorDetail.detail }}</div>
      </bk-exception>
    </div>
    <div
      v-else
      class="log-middle"
      style="width: 1180px; margin: 0 auto; padding-bottom: 0"
    >
      <div
        class="nofound"
        style="width: 1180px; margin: 0 auto"
      >
        <img :src="permissionsImg" />
        <p>{{ $t('您没有访问当前应用该功能的权限') }}</p>
        <bk-button
          v-if="applyUrl"
          :theme="'primary'"
          :title="$t('申请成为开发者')"
          class="mr10"
          @click="toApplication(applyUrl)"
        >
          {{ $t('申请成为开发者') }}
        </bk-button>
        <bk-button
          v-if="adminApplyUrl"
          :theme="'primary'"
          @click="toApplication(adminApplyUrl)"
        >
          {{ $t('申请成为管理员') }}
        </bk-button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  data() {
    return {
      permissionsImg: require('@static/images/permissions.png'),
    };
  },
  computed: {
    ...mapState(['applyUrls', 'errorDetail']),
    ...mapState('plugin', ['pluginApplyUrl']),
    isPlugin() {
      return this.$route.meta.plugin;
    },
    applyUrl() {
      if (this.isPlugin) {
        return this.pluginApplyUrl;
      }
      return this.applyUrls?.apply_url_for_dev;
    },
    adminApplyUrl() {
      if (this.isPlugin) {
        return '';
      }
      return this.applyUrls?.apply_url_for_admin;
    },
    id() {
      return this.$route.params.id;
    },
    pluginTypeId() {
      return this.$route.params.pluginTypeId;
    },
  },
  async created() {
    let appInfo = {};
    if (this.isPlugin) {
      appInfo = await this.$store.dispatch('plugin/getPluginInfo', {
        pluginId: this.id,
        pluginTypeId: this.pluginTypeId,
      });
    } else {
      appInfo = await this.$store.dispatch('getAppInfo', { appCode: this.id });
    }
    this.isPermission(appInfo);
  },
  methods: {
    toApplication(url) {
      window.open(url, '_blank');
    },
    // 应用是否有权限
    isPermission(data) {
      // 403 无权限
      if (data.status === 403 || data.response?.status === 403) {
        return;
      }
      if (this.isPlugin) {
        this.$router.push({
          name: 'pluginSummary',
          params: {
            id: this.id,
            pluginTypeId: this.pluginTypeId,
          },
        });
      } else {
        // 跳转概览/默认模块
        this.$router.push({
          name: 'appSummary',
          params: {
            id: this.id,
          },
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.nofound {
  width: 939px;
  padding-top: 150px;
  text-align: center;
}

.nofound p {
  font-size: 20px;
  color: #979797;
  line-height: 80px;
}

.no-app-permissions {
  margin-top: 150px;

  .text-subtitle {
    color: #979ba5;
    font-size: 14px;
    text-align: center;
    margin-top: 14px;
  }
}
</style>
