<template>
  <div class="build-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="build-config-loading"
      :offset-top="0"
      :offset-left="0"
      :is-transition="false"
      class="middle"
    >
      <!-- 代码源 -->
      <code-source />
      <!-- 镜像信息 -->
      <mirror @close-content-loader="closeContentLoader" />
    </paas-content-loader>
  </div>
</template>

<script>
import codeSource from './comps/deploy-build/code-source.vue';
import mirror from './comps/deploy-build/mirror.vue';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  name: 'DeployBuild',
  components: {
    codeSource,
    mirror,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
    };
  },
  methods: {
    closeContentLoader() {
      this.isLoading = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.build-container {
  padding: 0 20px 20px;
  min-height: 200px;

  :deep(.code-main),
  :deep(.mirror-main) {
    .header-wrapper {
      display: flex;

      .edit-container {
        font-size: 12px;
        color: #3a84ff;
        margin-top: 2px;
        cursor: pointer;
      }
    }
  }
}
</style>
