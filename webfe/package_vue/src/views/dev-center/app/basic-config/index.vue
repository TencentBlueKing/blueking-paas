<template>
  <div>
    <cloud-app-top-bar
      :title="$t('应用配置')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
      @right-config-click="toDeployHistory"
    />
    <div class="router-container m20">
      <router-view :key="routeIndex" :environment="active"></router-view>
    </div>
  </div>
</template>
<script>
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'BasicConfig',
  components: {
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'api',
      routeIndex: 0,
      panels: [
        { name: 'api', label: this.$t('云API权限'), routeName: 'appCloudAPI' },
        { name: 'url', label: this.$t('访问地址'), routeName: 'visitUrl' },
        { name: 'market', label: this.$t('应用市场'), routeName: 'appMarket' },
        { name: 'mobile-market', label: this.$t('应用市场 (移动端)'), routeName: 'appMobileMarket' },
        { name: 'info', label: this.$t('基本信息'), routeName: 'appBasicInfo' },
        { name: 'member', label: this.$t('成员管理'), routeName: 'appMembers' },
      ],
    };
  },
  methods: {
    handleTabChange(name) {
      this.active = name;
      const curEnv = this.panels.find(item => item.name === name);
      this.$router.push({
        name: curEnv.routeName,
        params: {
          id: this.curAppCode,
        },
      });
    },

    /** 部署历史 */
    toDeployHistory() {
      this.$router.push({
        name: 'cloudAppDeployHistory',
      });
    },

    goBack() {
      this.$router.go(-1);
    },
  },
};
</script>
