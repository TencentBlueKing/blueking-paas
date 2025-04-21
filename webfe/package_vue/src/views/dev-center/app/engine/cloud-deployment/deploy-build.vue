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
        <image-info
          v-if="!allowMultipleImage"
          :credential-list="credentialList"
          @close-content-loader="closeContentLoader"
        ></image-info>
        <image-credential
          :list="credentialList"
          @reacquire="getCredentialList"
        ></image-credential>
        <!-- 上云版添加源码信息 -->
        <code-source
          v-if="curAppInfo.feature?.IMAGE_APP_BIND_REPO"
          class="custom-image-modle"
          :build-method="buildMethod"
          @close-content-loader="closeContentLoader"
        />
      </template>
      <template v-else>
        <!-- lesscode/smart应用 源码信息 -->
        <packages-view
          v-if="isLesscodeApp || isSmartApp || isAidevPlugin"
          @close-content-loader="closeContentLoader"
        />
        <!-- 代码源 -->
        <code-source
          v-else
          :build-method="buildMethod"
          @close-content-loader="closeContentLoader"
        />
        <!-- 镜像信息 -->
        <mirror
          v-if="!isSmartApp"
          @close-content-loader="closeContentLoader"
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
      allowMultipleImage: false,
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
  async created() {
    if (this.isCustomImage) {
      await this.getCredentialList();
      this.getProcessInfo();
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
      // loading处理
      try {
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode: this.appCode });
        this.credentialList = res;
        this.credentialList.forEach((item) => {
          item.password = '';
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    async getProcessInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getAppProcessInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.allowMultipleImage = res.metadata.allow_multiple_image; // 是否允许多条镜像
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
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
