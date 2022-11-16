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
      <!-- 去掉 -->
      <!-- <section class="deploy-panel deploy-metadata flex mt20">
                <div class="metadata-wrap">
                    <div class="data-logo">
                        <img src="/static/images/smart.png" v-if="isSmartApp" />
                        <img src="/static/images/docker.png" v-else-if="isDockerApp" />
                        <svg aria-hidden="true" v-else>
                            <use xlink:href="#paasng-gitlab-2" v-if="overview.repo.source_type === 'bk_gitlab'"></use>
                            <use xlink:href="#paasng-git-code" v-if="overview.repo.source_type === 'tc_git'"></use>
                            <use xlink:href="#paasng-svn" v-if="overview.repo.source_type === 'bk_svn'"></use>
                            <use xlink:href="#paasng-svn" v-if="overview.repo.source_type === 'bare_svn'"></use>
                            <use xlink:href="#paasng-git" v-if="overview.repo.source_type === 'bare_git'"></use>
                            <use xlink:href="#paasng-lesscode" v-if="isLesscodeApp"></use>
                        </svg>
                    </div>
                    <div class="metadata">
                        <template v-if="overview.repo.source_type === 'bk_svn'">
                            <div class="data-item">
                                <span class="data-title" v-bk-overflow-tips> {{ $t('仓库：') }} {{overview.repo.display_name}}</span>
                            </div>
                            <div class="data-item">
                                <div class="data-value" v-bk-overflow-tips> {{ $t('地址：') }} {{overview.repo.repo_url}}</div>
                            </div>
                            <a class="mr10" target="_blank" :href="overview.repo.repo_url"> {{ $t('点击访问') }} </a>
                        </template>
                        <template v-else>
                            <template v-if="isLesscodeApp">
                                <div class="data-item">
                                    <span class="data-title mr15"> {{ $t('仓库：蓝鲸可视化开发平台提供源码包') }} </span>
                                </div>
                                <router-link :to="{ name: 'appPackages' }" class="mr10"> {{ $t('查看包版本') }} </router-link>
                                <a :href="GLOBAL.DOC.LESSCODE_START" target="_blank" class="mr10"> {{ $t('开发指引') }} </a>
                                <a v-if="lessCodeFlag && curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP" :target="lessCodeData.address_in_lesscode ? '_blank' : ''" :href="lessCodeData.address_in_lesscode || 'javascript:;'" @click="handleLessCode"> {{ $t('我要开发') }} </a>
                            </template>
                            <template v-else-if="isSmartApp">
                                <div class="data-item">
                                    <span class="data-title mr15"> {{ $t('仓库：蓝鲸 S-mart 源码包') }} </span>
                                </div>
                                <router-link :to="{ name: 'appPackages' }" class="mr10"> {{ $t('查看包版本') }} </router-link>
                            </template>
                            <template v-else>
                                <div class="data-item">
                                    <span class="data-title mr15"> {{ $t('仓库：') }} {{overview.repo.display_name}}</span>
                                    <template v-if="overview.repo.authorized">
                                        <label class="data-label success">
                                            <span class="text"> {{ $t('已授权') }} </span>
                                        </label>
                                    </template>
                                    <template v-else>
                                        <label class="data-label">
                                            <span class="text"> {{ $t('未授权') }} </span>
                                        </label>
                                    </template>
                                </div>
                                <div class="data-item">
                                    <div class="data-value" v-bk-overflow-tips> {{ $t('地址：') }} {{overview.repo.repo_url}}</div>
                                </div>
                                <div class="data-item" v-if="overview.repo.source_dir">
                                    <div class="data-value" v-bk-overflow-tips> {{ $t('部署目录：') }} {{overview.repo.source_dir}}</div>
                                </div>
                                <a class="mr10" target="_blank" v-if="!isDockerApp" :href="overview.repo.repo_url"> {{ $t('点击访问') }} </a>
                                <router-link target="_blank" v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE && !overview.repo.authorized" :to="{ name: 'serviceCode' }"> {{ $t('前往授权') }} </router-link>
                            </template>
                        </template>
                    </div>
                </div>

                <div class="metadata-wrap" v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE">
                    <div class="data-logo">
                        <svg aria-hidden="true">
                            <use xlink:href="#paasng-python" v-if="overview.language === 'Python'"></use>
                            <use xlink:href="#paasng-nodejs-2" v-if="overview.language === 'NodeJS'"></use>
                            <use xlink:href="#paasng-golang" v-if="overview.language === 'Go'"></use>
                        </svg>
                    </div>
                    <div class="metadata">
                        <div class="data-item"> {{ $t('镜像：') }} {{overview.stack || '--'}}</div>
                        <div class="data-item">
                            <div class="data-value" v-bk-overflow-tips> {{ $t('构建工具：') }} {{buildpacks || '--'}}</div>
                        </div>
                        <router-link :to="{ name: 'appEnvVariables', params: { id: appCode, moduleId: curModuleId } }"> {{ $t('查看详情') }} </router-link>
                    </div>
                </div>
            </section> -->

      <section class="deploy-panel deploy-main mt15">
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
            appTopBar
        },
        mixins: [appBaseMixin],
        data () {
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
                        display_name: ''
                    },
                    stack: '',
                    image: '',
                    buildpacks: []
                },
                lessCodeData: {},
                lessCodeFlag: true
            };
        },
        computed: {
            buildpacks () {
                if (this.overview.buildpacks && this.overview.buildpacks.length) {
                    const buildpacks = this.overview.buildpacks.map(item => item.display_name);
                    return buildpacks.join('，');
                }
                return '--';
            },
            deployModule () {
                return this.$route.meta.module || 'stag';
            },
            routeName () {
                return this.$route.name;
            },
            loaderPlaceholder () {
                if (this.routeName === 'appDeployForStag' || this.routeName === 'appDeployForProd') {
                    return 'deploy-loading';
                } else if (this.routeName === 'appDeployForHistory') {
                    return 'deploy-history-loading';
                }
                return 'deploy-top-loading';
            }
        },
        watch: {
            '$route' (newVal, oldVal) {
                if (newVal.params.id !== oldVal.params.id || newVal.params.moduleId !== oldVal.params.moduleId) {
                    console.log('init-overview');
                    this.renderIndex++;
                    this.init();
                }
            },
            curModuleId (val) {
                // this.getLessCode();
            }
        },
        created () {
            this.init();
        },
        methods: {
            async init () {
                this.isLoading = false;
                // 部署 deploy-metadata 不展示
                // this.getModuleRuntimeOverview();
                // this.getLessCode();
            },

            async getModuleRuntimeOverview () {
                try {
                    const appCode = this.appCode;
                    const moduleId = this.curModuleId;
                    const res = await this.$store.dispatch('deploy/getModuleRuntimeOverview', {
                        appCode,
                        moduleId
                    });
                    this.overview = res;
                    if (this.overview.repo === null) {
                        this.overview.repo = {};
                    }
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.isLoading = false;
                }
            },

            handleTimelineSelect (payload) {
                this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation(payload.stage);
            },

            handleGoPage (routeName) {
                this.$router.push({
                    name: routeName
                });
            },

            async getLessCode () {
                try {
                    const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
                        appCode: this.appCode,
                        moduleName: this.curModuleId
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

            handleLessCode () {
                if (this.lessCodeData.address_in_lesscode) {
                    return;
                }
                this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
            }
        }
    };
</script>

<style lang="scss" scoped>
    @import './index.scss'
</style>
