<template>
  <div>
    <div class="container biz-create-success">
      <div class="success-wrapper">
        <div class="info">
          <p>
            <i class="paasng-icon paasng-check-circle-shape text-success" />
          </p>
          <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
          <p>
            {{ $t('常用操作：') }}
            <router-link
              :to="{ name: 'appSummary', params: { id: appCode } }"
              class="link"
            >
              {{ $t('查看应用概览') }}
            </router-link>
            <span class="success-dividing-line">|</span>
            <router-link
              :to="{ name: 'appDeploy', params: { id: appCode } }"
              class="link"
            >
              {{ $t('部署应用') }}
            </router-link>
            <span class="success-dividing-line">|</span>
            <router-link
              :to="{ name: 'appRoles', params: { id: appCode } }"
              class="link"
            >
              {{ $t('添加成员') }}
            </router-link>
          </p>
        </div>
        <div class="content">
          <div
            v-if="application.config_info.require_templated_source && downloadableAddress"
            class="input-wrapper"
          >
            <div class="input-item">
              <span class="url-label"> {{ $t('应用初始化模板地址：') }} </span>
              <input
                v-model="downloadableAddress"
                v-bk-tooltips.top="downloadableAddress"
                :class="['ps-form-control', 'svn-input', localLanguage === 'en' ? 'svn-input-en' : '']"
                type="text"
              >
            </div>
            <div class="btn-item">
              <a
                target="_blank"
                class="btn-checkout ps-btn ps-btn-primary"
                :href="downloadableAddress"
              > {{ $t('点击下载') }} </a>
            </div>
          </div>
          <div
            v-if="application.type === 'bk_plugin'"
            class="btn-check-svn spacing-x4"
          >
            <div class="tips-wrapper">
              <div class="tips">
                <code># {{ $t('初始化插件项目') }}
                  <p>{{ pluginTips }}</p>
                </code>
                <i
                  v-copy="pluginTips"
                  :class="['paasng-icon', 'paasng-general-copy', localLanguage === 'en' ? 'copy-icon-en' : 'copy-icon']"
                />
              </div>
              <div class="tips tips-plugin">
                <code>
                  {{ initTips }}
                </code>
              </div>
              <div class="tips">
                <code># {{ $t('添加远程仓库地址并完成推送') }}
                  <p>{{ pushTips }}</p>
                </code>
                <i
                  v-copy="pushTips"
                  :class="['paasng-icon', 'paasng-general-copy', 'copy-icon',
                           localLanguage === 'en' ? 'copy-icon-two' : '']"
                />
              </div>
            </div>
          </div>
          <div
            v-if="application.type !== 'bk_plugin' && isShowTips"
            class="btn-check-svn spacing-x4"
          >
            <p class="log-title">
              {{ $t('使用 Git 命令推送代码到远程仓库') }}
            </p>
            <div class="tips-wrapper">
              <div class="tips">
                <code># {{ $t('下载并解压代码到本地目录') }}
                  <p>{{ downloadTips }}</p>
                </code>
                <i
                  v-copy="downloadTips"
                  :class="['paasng-icon', 'paasng-general-copy', localLanguage === 'en' ? 'copy-icon-en' : 'copy-icon']"
                />
              </div>
              <div class="tips">
                <code># {{ $t('添加远程仓库地址并完成推送') }}
                  <p>{{ pushTips }}</p>
                </code>
                <i
                  v-copy="pushTips"
                  :class="['paasng-icon', 'paasng-general-copy', 'copy-icon',
                           localLanguage === 'en' ? 'copy-icon-two' : '']"
                />
              </div>
            </div>
          </div>
          <template v-if="advisedDocLinks.length > 0">
            <p class="help-doc">
              {{ $t('帮助文档') }}
            </p>
            <p
              v-for="(link, linkIndex) in advisedDocLinks"
              :key="linkIndex"
            >
              <a
                :href="link.location"
                :title="link.short_description"
                target="_blank"
              >{{ link.title }}</a>
            </p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import auth from '@/auth';
export default {
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
      return [
        'pip install cookiecutter',
        'cookiecutter https://github.com/TencentBlueKing/bk-plugin-framework-python/ --directory template',
      ].join('\n');
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
  },
  created() {
    const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
    const linkUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/accessories/advised_documentary_links/?plat_panel=app_created&limit=3`;
    this.$http.get(url).then((response) => {
      const body = response;
      this.application = body.application;
      const { modules } = this.application;

      console.log('response', response);

      if (modules && modules.length) {
        this.trunkURL = modules[0].repo?.trunk_url;
        const defaultModule = modules.find(item => item.name === 'default');
        this.isShowTips = defaultModule.source_origin === 1;
      }
    });
    this.$http.get(linkUrl).then((response) => {
      this.advisedDocLinks = response.links;
    });

    this.getCurrentUser();
  },
  mounted() {
    const objectKey = localStorage.getItem(this.$route.query.objectKey) === 'undefined' ? '' : localStorage.getItem(this.$route.query.objectKey);
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
  },
};
</script>

<style lang="scss" scoped>
    @import './success-git.scss';
</style>
