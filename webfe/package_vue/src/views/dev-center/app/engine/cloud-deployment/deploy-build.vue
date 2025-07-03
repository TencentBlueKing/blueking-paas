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
      <!-- 仅镜像 -->
      <template v-if="isCustomImage">
        <image-info :credential-list="credentialList"></image-info>
        <image-credential
          :list="credentialList"
          @reacquire="getCredentialList"
        ></image-credential>
        <!-- 上云版添加源码信息 -->
        <code-source
          v-if="curAppInfo.feature?.IMAGE_APP_BIND_REPO"
          class="custom-image-modle"
          :build-method="buildMethod"
        />
      </template>
      <template v-else>
        <!-- lesscode/smart应用 源码信息 -->
        <packages-view v-if="isLesscodeApp || isSmartApp || isAidevPlugin" />
        <!-- 代码源 -->
        <code-source
          v-else
          :build-method="buildMethod"
        />
        <!-- 镜像信息 -->
        <mirror
          v-if="!isSmartApp"
          @set-build-method="setBuildMethod"
        />
      </template>
    </paas-content-loader>
  </div>
</template>

<script>
import codeSource from './comps/deploy-build/code-source.vue';
import mirror from './comps/deploy-build/mirror.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import packagesView from '@/views/dev-center/app/engine/packages/index.vue';
import imageInfo from './image-info';
import imageCredential from './image-credential';

export default {
  name: 'DeployBuild',
  components: {
    codeSource,
    mirror,
    packagesView,
    imageInfo,
    imageCredential,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      buildMethod: '',
      credentialList: [],
    };
  },
  computed: {
    isCustomImage() {
      return this.curAppModule?.web_config?.runtime_type === 'custom_image';
    },
    // AIDEV 插件
    isAidevPlugin() {
      return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.AIDEV;
    },
  },
  created() {
    if (this.isCustomImage) {
      this.getCredentialList();
    } else {
      setTimeout(() => {
        this.closeContentLoader();
      }, 1000);
    }
  },
  methods: {
    closeContentLoader() {
      this.isLoading = false;
    },

    setBuildMethod(data) {
      this.buildMethod = data;
    },

    // 获取凭证列表
    async getCredentialList() {
      try {
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode: this.appCode });
        this.credentialList = res;
        this.credentialList.forEach((item) => {
          item.password = '';
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.closeContentLoader();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.build-container {
  padding: 0 20px 20px;
  min-height: 200px;
  ::v-deep .custom-image-modle .source-code-info {
    border-bottom: none;
  }

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
