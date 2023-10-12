<template>
  <div class="image-manage">
    <cloud-app-top-bar
      :title="$t('镜像管理')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
    />
    <div class="app-container middle main">
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="image-manage-loading"
        :offset-top="0"
        class="access-user"
      >
        <router-view :key="routeIndex" @hide-loading="isLoading = false"></router-view>
      </paas-content-loader>
    </div>
  </div>
</template>

<script>
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'ClundImageManage',
  components: {
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      active: 'image',
      routeIndex: 0,
      panels: [
        { name: 'image', label: this.$t('镜像管理'), routeName: 'cloudAppImageList' },
        { name: 'history', label: this.$t('构建历史'), routeName: 'cloudAppBuildHistory' },
      ],
      isLoading: true,
    };
  },
  created() {
    this.active = this.panels.find(item => item.routeName === this.$route.name).name || 'image';
  },
  methods: {
    handleTabChange(name) {
      this.isLoading = true;
      this.active = name;
      const curPanel = this.panels.find(item => item.name === name);
      this.$router.push({
        name: curPanel.routeName,
        params: {
          id: this.curAppCode,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.image-manage {
  .main {
    padding-top: 0;
    margin-top: 16px;
    background: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 #1919290d;
  }
}
</style>
