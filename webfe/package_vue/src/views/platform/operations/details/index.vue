<template>
  <div class="right-main app-details-container">
    <!-- 动态组件，根据当前激活的标签页显示对应组件 -->
    <component :is="currentComponent" />
  </div>
</template>

<script>
import AppOverview from './app-overview';
import Feature from './feature';
import Services from './services';
import Member from './member';

// 组件映射表
const componentMap = {
  overview: AppOverview,
  feature: Feature,
  services: Services,
  member: Member,
};

export default {
  name: 'PlatformAppDetail',
  components: {
    AppOverview,
    Feature,
    Services,
    Member,
  },
  computed: {
    // 当前激活的标签页
    tabActive() {
      return this.$route.query.active || 'overview';
    },
    // 根据当前激活的标签页返回对应的组件
    currentComponent() {
      return componentMap[this.tabActive] || AppOverview;
    },
  },
};
</script>

<style lang="scss" scoped>
.app-details-container {
  padding: 24px;
}
</style>
