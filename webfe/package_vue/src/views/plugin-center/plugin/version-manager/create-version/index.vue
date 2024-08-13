<template>
  <div>
    <paas-plugin-title :name="isVersionRelease ? $t('新建版本发布') : $t('新建测试')" />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="plugin-new-version-loading"
      class="app-container middle"
    >
      <!-- 防止高度塌陷 -->
      <div class="version-loading-placeholder" v-if="!Object.keys(scheme).length"></div>
      <template v-else>
        <!-- 新版ui -->
        <new-version
          v-if="scheme.version_type === 'tested_version' && isVersionRelease"
          :scheme="scheme"
          :version-data="versionData"
        />
        <!-- 新建版本 -->
        <editor-version
          v-else
          :scheme="scheme"
          :version-data="versionData"
          :loading="schemeLoading"
          @refresh="getNewVersionFormat"
        />
      </template>
    </paas-content-loader>
  </div>
</template>

<script>
import paasPluginTitle from '@/components/pass-plugin-title';
import editorVersion from './editor-version.vue';
import newVersion from './new-version/index.vue';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';

export default {
  components: {
    paasPluginTitle,
    editorVersion,
    newVersion,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      isLoading: true,
      scheme: {},
      schemeLoading: false,
      versionData: {},
    };
  },
  computed: {
    isVersionRelease() {
      return this.$route.query.type === 'prod';
    },
    versionId() {
      return this.$route.query.versionId;
    },
  },
  async created() {
    if (this.versionId) {
      await this.getReleaseDetail();
    }
    this.getNewVersionFormat();
  },
  methods: {
    // 获取新建版本表单格式 - 是否需要请求
    async getNewVersionFormat() {
      this.schemeLoading = true;
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        type: 'prod',
      };
      try {
        // 多次请求？
        const res = await this.$store.dispatch('plugin/getNewVersionFormat', params);
        this.scheme = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
          this.schemeLoading = false;
        }, 200);
      }
    },
    // 获取版本详情
    async getReleaseDetail() {
      try {
        const res = await this.$store.dispatch('plugin/getReleaseDetail', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          releaseId: this.versionId,
        });
        this.versionData = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.version-loading-placeholder {
    height: 500px;
}
</style>
