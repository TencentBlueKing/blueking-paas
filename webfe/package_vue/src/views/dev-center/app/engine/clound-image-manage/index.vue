<template>
  <div class="image-manage">
    <!-- 部署历史 -->
    <div
      class="ps-top-bar"
      v-if="isDeployHistory"
    >
      <div class="top-title flex-row align-items-center">
        <i
          class="paasng-icon paasng-arrows-left icon-cls-back mr5"
          @click="goBack"
        />
        <h3>{{ $t('构建历史') }}</h3>
      </div>
    </div>
    <cloud-app-top-bar
      v-else
      :title="$t('镜像管理')"
      :active="active"
      :module-id="curModuleId"
    />
    <div class="app-container middle main">
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="image-manage-loading"
        :offset-top="0"
        class="access-user"
      >
        <router-view
          :key="routeIndex"
          @hide-loading="isLoading = false"
          @top-change="handleChangeTopActive"
        ></router-view>
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
      isLoading: true,
      isDeployHistory: false,
    };
  },
  watch: {
    $route(route) {
      this.isDeployHistory = !!route.meta.history;
    },
  },
  created() {
    this.isDeployHistory = !!this.$route.history;
  },
  methods: {
    goBack() {
      this.$router.push({
        name: 'cloudAppImageList',
        params: {
          id: this.curAppCode,
        },
      });
    },
    handleChangeTopActive() {
      this.isDeployHistory = true;
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

  .top-title {
    padding-left: 20px;
    h3 {
      font-size: 16px;
      color: #313238;
      font-weight: 400;
      margin-left: 4px;
    }
    .icon-cls-back {
      color: #3a84ff;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
  }
}
</style>
