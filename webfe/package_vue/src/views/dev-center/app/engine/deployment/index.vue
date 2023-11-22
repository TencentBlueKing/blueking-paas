<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t('部署管理')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <paas-content-loader
      :is-loading="isLoading"
      :placeholder="loaderPlaceholder"
      :offset-top="30"
      class="app-container middle overview"
    >

      <section class="deploy-panel deploy-main">
        <ul
          class="ps-tab"
          style="position: relative; z-index: 10;"
        >
          <li
            :class="['item', { 'active': deployModule === 'stag' }]"
            @click="handleGoPage('appDeployForStag')"
          >
            {{ $t('预发布环境') }}
            <router-link :to="{ name: 'appDeployForStag' }" />
          </li>
          <li
            :class="['item', { 'active': deployModule === 'prod' }]"
            @click="handleGoPage('appDeployForProd')"
          >
            {{ $t('生产环境') }}
          </li>
          <li
            :class="['item', { 'active': deployModule === 'config' }]"
            @click="handleGoPage('appDeployForConfig')"
          >
            {{ $t('部署配置') }}
          </li>
          <li
            :class="['item', { 'active': deployModule === 'history' }]"
            @click="handleGoPage('appDeployForHistory')"
          >
            {{ $t('部署历史') }}
          </li>
        </ul>

        <div class="deploy-content">
          <router-view :key="renderIndex" />
        </div>
      </section>
    </paas-content-loader>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import appTopBar from '@/components/paas-app-bar';

export default {
  components: {
    appTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      renderIndex: 0,
      overview: {
        repo: {
          source_type: '',
          type: '',
          trunk_url: '',
          repo_url: '',
          repo_fullname: '',
          use_external_diff_page: true,
          linked_to_internal_svn: false,
          display_name: '',
        },
        stack: '',
        image: '',
        buildpacks: [],
      },
      lessCodeData: {},
      lessCodeFlag: true,
    };
  },
  computed: {
    buildpacks() {
      if (this.overview.buildpacks && this.overview.buildpacks.length) {
        const buildpacks = this.overview.buildpacks.map(item => item.display_name);
        return buildpacks.join('，');
      }
      return '--';
    },
    deployModule() {
      return this.$route.meta.module || 'stag';
    },
    routeName() {
      return this.$route.name;
    },
    loaderPlaceholder() {
      if (this.routeName === 'appDeployForStag' || this.routeName === 'appDeployForProd') {
        return 'deploy-loading';
      } if (this.routeName === 'appDeployForHistory') {
        return 'deploy-history-loading';
      }
      return 'deploy-top-loading';
    },
  },
  watch: {
    '$route'(newVal, oldVal) {
      if (newVal.params.id !== oldVal.params.id || newVal.params.moduleId !== oldVal.params.moduleId) {
        console.log('init-overview');
        // eslint-disable-next-line no-plusplus
        this.renderIndex++;
        this.init();
      }
    },
    curModuleId() {
      // this.getLessCode();
    },
  },
  created() {
    this.init();
  },
  methods: {
    async init() {
      this.isLoading = false;
      // 部署 deploy-metadata 不展示
      // this.getModuleRuntimeOverview();
      // this.getLessCode();
    },

    async getModuleRuntimeOverview() {
      try {
        const { appCode } = this;
        const moduleId = this.curModuleId;
        const res = await this.$store.dispatch('deploy/getModuleRuntimeOverview', {
          appCode,
          moduleId,
        });
        this.overview = res;
        if (this.overview.repo === null) {
          this.overview.repo = {};
        }
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    handleTimelineSelect(payload) {
      this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation(payload.stage);
    },

    handleGoPage(routeName) {
      this.$router.push({
        name: routeName,
      });
    },

    async getLessCode() {
      try {
        const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
          appCode: this.appCode,
          moduleName: this.curModuleId,
        });
        if (resp.address_in_lesscode === '' && resp.tips === '') {
          this.lessCodeFlag = false;
        }
        this.lessCodeData = resp;
      } catch (errRes) {
        this.lessCodeFlag = false;
        console.error(errRes);
      }
    },

    handleLessCode() {
      if (this.lessCodeData.address_in_lesscode) {
        return;
      }
      this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
    },
  },
};
</script>

<style lang="scss" scoped>
    @import './index.scss'
</style>
