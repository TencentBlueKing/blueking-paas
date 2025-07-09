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
        <div class="content">
          <div
            v-if="downloadableAddress"
            class="input-wrapper"
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
          <div
            v-if="application.is_plugin_app"
            class="btn-check-svn spacing-x4"
          >
            <div class="tips-wrapper">
              <div class="title">
                {{ $t('初始化插件项目') }}
                <div
                  class="icon-wrapper"
                  v-copy="pluginTips"
                >
                  <i
                    :class="[
                      'paasng-icon',
                      'paasng-general-copy',
                      localLanguage === 'en' ? 'copy-icon-en' : 'copy-icon',
                    ]"
                  />
                  {{ $t('复制') }}
                </div>
              </div>
              <div class="tips line">
                <code>
                  <p>{{ pluginTips }}</p>
                </code>
              </div>
              <div class="tips tips-plugin line">
                <code>
                  {{ initTips }}
                </code>
              </div>
              <div class="title">
                {{ $t('添加远程仓库地址并完成推送') }}
                <div
                  class="icon-wrapper"
                  v-copy="pushTips"
                >
                  <i
                    :class="[
                      'paasng-icon',
                      'paasng-general-copy',
                      'copy-icon',
                      localLanguage === 'en' ? 'copy-icon-two' : '',
                    ]"
                  />
                  {{ $t('复制') }}
                </div>
              </div>
              <div class="tips">
                <code>
                  <p>{{ pushTips }}</p>
                </code>
              </div>
            </div>
          </div>
          <div
            v-if="isShowGitBash"
            class="btn-check-svn spacing-x4"
          >
            <p class="log-title">
              {{ $t('使用 Git 命令推送代码到远程仓库') }}
            </p>
            <div class="tips-wrapper">
              <div class="title">
                {{ $t('下载并解压代码到本地目录') }}
                <div
                  class="icon-wrapper"
                  v-copy="downloadTips"
                >
                  <i
                    :class="[
                      'paasng-icon',
                      'paasng-general-copy',
                      localLanguage === 'en' ? 'copy-icon-en' : 'copy-icon',
                    ]"
                  />
                  {{ $t('复制') }}
                </div>
              </div>
              <div class="tips line">
                <code>
                  <p>{{ downloadTips }}</p>
                </code>
              </div>
              <div class="title mt10">
                {{ $t('添加远程仓库地址并完成推送') }}
                <div
                  class="icon-wrapper"
                  v-copy="pushTips"
                >
                  <i
                    :class="[
                      'paasng-icon',
                      'paasng-general-copy',
                      'copy-icon',
                      localLanguage === 'en' ? 'copy-icon-two' : '',
                    ]"
                  />
                  {{ $t('复制') }}
                </div>
              </div>
              <div class="tips">
                <code>
                  <p>{{ pushTips }}</p>
                </code>
              </div>
            </div>
          </div>
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
export default {
  components: {
    topBar,
  },
  mixins: [appBaseMixin],
  data() {
    // const appCode = this.$route.params.id
    return {
      // appCode: appCode,
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
      if (name === 'process') {
        name = this.isRuntimeType ? 'cloudAppDeployForBuild' : 'cloudAppDeployForProcess';
      }
      this.$router.push({
        name,
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
