<template>
  <div class="app-success-wrapper">
    <top-bar />
    <!-- github、gitee、tc_git、bare_git、bk_gitlab -->
    <div class="container biz-create-success">
      <div class="success-wrapper">
        <div class="info">
          <p>
            <i class="paasng-icon paasng-check-1 text-success" />
          </p>
          <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
          <p v-if="application.type === 'cloud_native'">
            <bk-button
              :theme="'primary'"
              class="mr10"
              @click="handlePageJump('cloudAppDeployManageStag')"
            >
              {{ $t('部署应用') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handlePageJump('process', 'default')"
            >
              {{ $t('模块配置') }}
            </bk-button>
          </p>
          <p v-else>
            <bk-button
              :theme="'primary'"
              class="mr10"
              @click="handlePageJump('appDeploy')"
            >
              {{ $t('部署应用') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handlePageJump('appSummary')"
            >
              {{ $t('应用概览') }}
            </bk-button>
          </p>
        </div>

        <!-- 平台提供代码仓库，开发指引 -->
        <div
          class="content"
          v-if="isCreatedByPlatform"
        >
          <section>
            <p class="step-title">{{ $t('开发指引') }}</p>
            <StepGuide :steps="platformCodeRepositorySteps" />
          </section>
        </div>
        <div
          class="content"
          v-else
        >
          <div
            v-if="downloadableAddress"
            class="input-wrapper mb-16"
          >
            <div class="title-wrapper">
              <p class="title">{{ $t('应用初始化模板地址：') }}</p>
              <div class="icon-wrapper">
                <a
                  target="_blank"
                  :href="downloadableAddress"
                >
                  <i class="paasng-icon paasng-download" />
                  <span>{{ $t('下载') }}</span>
                </a>
                <a
                  href="javascript: void(0);"
                  :class="['ml10', { disabled: isRefresLoading }]"
                  @click="refreshInitTemplateUrl"
                >
                  <i class="paasng-icon paasng-refresh-line" />
                  {{ $t('刷新') }}
                </a>
              </div>
            </div>
            <div
              class="template-url"
              v-bk-tooltips.top="downloadableAddress"
            >
              {{ downloadableAddress }}
            </div>
          </div>

          <!-- 插件成功指引 -->
          <section v-if="application.is_plugin_app">
            <p class="step-title">{{ $t('插件开发指引') }}</p>
            <StepGuide :steps="pluginSteps" />
          </section>

          <!-- 云原生应用，已有代码仓库开发指引 -->
          <section v-if="isShowGitBash">
            <p class="step-title">{{ $t('使用 Git 命令推送代码到远程仓库') }}</p>
            <StepGuide :steps="gitSteps" />
          </section>
        </div>
        <section
          class="doc-panel"
          v-if="advisedDocLinks.length > 0"
        >
          <template>
            <p class="help-doc">
              {{ $t('帮助文档') }}
            </p>
            <p
              v-for="(link, linkIndex) in advisedDocLinks"
              :key="linkIndex"
              class="doc-item"
            >
              <a
                :href="link.location"
                :title="link.short_description"
                target="_blank"
              >
                {{ link.title }}
              </a>
            </p>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import topBar from './comps/top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import auth from '@/auth';
import StepGuide from './comps/step-guide.vue';
export default {
  components: {
    topBar,
    StepGuide,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      application: {
        code: '',
        config_info: {},
      },
      trunkURL: '',
      advisedDocLinks: [],
      downloadableAddress: '',
      downloadableAddressExpiresIn: 3600,
      isShowTips: false,
      user: {},
      isRuntimeType: false,
      isRefresLoading: false,
      appTemplateInfo: {},
    };
  },
  computed: {
    downloadTips() {
      return [
        `mkdir ${this.application.code}`,
        `curl "${this.downloadableAddress}" > ${this.application.code}.tar.gz`,
        `tar -xf ${this.application.code}.tar.gz -C ${this.application.code}`,
      ].join('\n');
    },
    pluginTips() {
      const { repo_url, source_dir } = this.appTemplateInfo;
      const baseCommand = `cookiecutter ${repo_url}`;
      const fullCommand = !source_dir || source_dir === '.' ? baseCommand : `${baseCommand} --directory ${source_dir}`;
      return `pip install cookiecutter\n${fullCommand}`;
    },
    initTips() {
      return [
        `project_name：${this.application.code}`,
        `app_code：${this.application.code}`,
        'plugin_desc：插件描述',
        `init_admin：${this.user.chineseName || this.user.username}`,
        `init_apigw_maintainer：${this.user.chineseName || this.user.username}`,
      ].join('\n');
    },
    pushTips() {
      return [
        `cd ${this.application.code}`,
        'git init',
        'git add .',
        'git commit -m "init repo"',
        `git remote add origin ${this.trunkURL}`,
        'git push -u origin master',
      ].join('\n');
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    isShowGitBash() {
      const isDockerfile = this.$route.query.method === 'dockerfile';
      // dockerfile构建方式，蓝鲸插件不展示GitBash
      if (!isDockerfile && !this.application.is_plugin_app && this.isShowTips) {
        return true;
      }
      return false;
    },
    isCreatedByPlatform() {
      return this.$route.query.type === 'platform';
    },
    gitSteps() {
      return [
        {
          title: this.$t('下载并解压代码到本地目录'),
          code: this.downloadTips,
        },
        {
          title: this.$t('添加远程仓库地址并完成推送'),
          code: this.pushTips,
        },
      ];
    },
    // 插件成功指引
    pluginSteps() {
      return [
        {
          title: this.$t('初始化插件项目'),
          code: [this.pluginTips, '\n', this.initTips],
          copyText: this.pluginTips,
        },
        {
          title: this.$t('添加远程仓库地址并完成推送'),
          code: this.pushTips,
        },
      ];
    },
    // 平台提供代码仓库，开发指引
    platformCodeRepositorySteps() {
      return [
        {
          title: this.$t('拉取代码到本地'),
          code: `git clone ${this.trunkURL}`,
        },
        {
          title: this.$t('本地开发'),
        },
        {
          title: this.$t('提交代码到代码仓库'),
          code: ['git add .', 'git commit -m "Your modified content"', 'git push'],
          copyText: 'git add .\ngit commit -m "Your modified content"\ngit push',
        },
      ];
    },
  },
  created() {
    this.getCreateAppData();
    this.getDocLinks();
    this.getCurrentUser();
  },
  mounted() {
    const objectKey =
      localStorage.getItem(this.$route.query.objectKey) === 'undefined'
        ? ''
        : localStorage.getItem(this.$route.query.objectKey);
    const extraInfo = JSON.parse(objectKey || '{}');
    this.downloadableAddress = extraInfo.downloadable_address;
    this.downloadableAddressExpiresIn = extraInfo.downloadable_address_expires_in;
  },
  methods: {
    getCurrentUser() {
      auth.requestCurrentUser().then((user) => {
        this.user = user;
      });
    },
    handlePageJump(name, moduleId) {
      const targetRouteName =
        name === 'process' ? (this.isRuntimeType ? 'cloudAppDeployForBuild' : 'cloudAppDeployForProcess') : name;
      this.$router.push({
        name: targetRouteName,
        params: {
          id: this.appCode,
          moduleId,
        },
      });
    },
    hideNotChildElement(el) {
      const { childNodes } = el;

      // 判断子元素是否存在
      const allChildNodes = Array.from(childNodes).filter((node) => node.nodeType !== 8); // 过滤掉注释节点
      if (allChildNodes.length === 0) {
        el.style.display = 'none'; // 隐藏当前元素
      }
    },
    // 刷新初始化模板地址
    async refreshInitTemplateUrl() {
      this.isRefresLoading = true;
      try {
        const res = await this.$store.dispatch('getAppDefaultInitTemplateUrl', {
          appCode: this.appCode,
        });
        this.downloadableAddress = res.downloadable_address;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: resp.detail || this.$t('服务暂不可用，请稍后再试'),
        });
      } finally {
        this.isRefresLoading = false;
      }
    },
    // 获取已创建应用数据
    async getCreateAppData() {
      try {
        const ret = await this.$http.get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`);
        this.application = ret.application;
        const { modules } = this.application;

        if (modules?.length) {
          const [firstModule] = modules;
          this.trunkURL = firstModule.repo?.trunk_url;

          const defaultModule = modules.find((item) => item.name === 'default');
          this.isShowTips = defaultModule?.source_origin === 1;
          this.isRuntimeType = firstModule.web_config?.runtime_type !== 'custom_image';
        }

        // 如果是插件应用，则获取模板信息
        if (this.application.is_plugin_app) {
          this.getAppTemplateInfo();
        }

        this.$nextTick(() => {
          const el = document.querySelector('.content');
          // 没有子元素隐藏当前容器
          this.hideNotChildElement(el);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取文档链接信息
    async getDocLinks() {
      try {
        const res = await this.$store.dispatch('deploy/getAppDocLinks', {
          appCode: this.appCode,
          params: {
            plat_panel: 'app_created',
            limit: 3,
          },
        });
        this.advisedDocLinks = res.links;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取应用模板信息
    async getAppTemplateInfo() {
      this.isSelectLoading = true;
      try {
        const res = await this.$store.dispatch('getAppTemplateInfo', {
          appCode: this.appCode,
          moduleId: 'default',
        });
        this.appTemplateInfo = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import './success-git.scss';
</style>
