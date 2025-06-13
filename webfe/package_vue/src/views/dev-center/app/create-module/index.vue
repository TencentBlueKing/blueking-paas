<template lang="html">
  <div class="paas-content white">
    <div
      v-en-class="'en-label'"
      class="wrap"
    >
      <div class="paas-application-tit establish-title mt30">
        <span> {{ $t('创建模块') }} </span>
      </div>
      <div
        v-if="canCreateModule"
        class="establish mt50"
      >
        <form
          id="form-create-app"
          @submit.prevent="createAppModule"
        >
          <div class="create-item">
            <div class="item-title">
              {{ $t('基本信息') }}
            </div>
            <div class="form-group pb0">
              <label class="form-label"> {{ $t('所属应用') }} </label>
              <div class="form-group-flex">
                <p class="app-name">
                  {{ curAppInfo.application.name }}
                </p>
              </div>
            </div>

            <div class="form-group pb0">
              <label class="form-label"> {{ $t('模块名称') }} </label>
              <div class="form-group-flex">
                <p>
                  <input
                    type="text"
                    name="name"
                    data-parsley-required="true"
                    :data-parsley-required-message="$t('该字段是必填项')"
                    data-parsley-maxlength="16"
                    data-parsley-pattern="[a-z][a-z0-9-]+"
                    :data-parsley-pattern-message="$t('格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母')"
                    data-parsley-trigger="input blur"
                    class="ps-form-control"
                    :placeholder="$t('由小写字母和数字以及连接符(-)组成，不能超过 16 个字符')"
                  >
                </p>
              </div>
            </div>
          </div>

          <!-- 镜像管理 -->
          <div
            v-if="structureType === 'mirror'"
            class="create-item"
            data-test-id="createDefault_item_baseInfo"
          >
            <div class="item-title">
              {{ $t('镜像管理') }}
            </div>

            <div
              class="form-group"
              style="margin-top: 7px;"
            >
              <label class="form-label"> {{ $t('镜像类型') }} </label>
              <div
                class="form-group-radio"
                style="margin-top: 5px;"
              >
                <bk-radio-group v-model="mirrorData.type">
                  <bk-radio value="public">
                    {{ $t('公开') }}
                  </bk-radio>
                  <bk-radio
                    value="private"
                    disabled
                  >
                    {{ $t('私有') }}
                  </bk-radio>
                </bk-radio-group>
              </div>
            </div>

            <bk-form
              ref="validate2"
              form-type="inline"
              :model="mirrorData"
              :rules="mirrorRules"
            >
              <bk-form-item
                :required="true"
                :property="'url'"
                error-display-type="normal"
                ext-cls="item-cls"
              >
                <div
                  class="form-group"
                  style="margin-top: 10px;"
                >
                  <label class="form-label"> {{ $t('镜像地址') }} </label>
                  <div class="form-input-flex">
                    <bk-input
                      v-model="mirrorData.url"
                      class="mt10"
                      style="width: 520px;"
                      size="large"
                      clearable
                      :placeholder="$t('请输入镜像地址,不包含版本(tag)信息')"
                    >
                      <template
                        v-if="GLOBAL.CONFIG.MIRROR_PREFIX"
                        slot="prepend"
                      >
                        <div class="group-text">
                          {{ GLOBAL.CONFIG.MIRROR_PREFIX }}
                        </div>
                      </template>
                    </bk-input>
                  </div>
                </div>
              </bk-form-item>
            </bk-form>
          </div>

          <div
            v-if="sourceOrigin !== GLOBAL.APP_TYPES.IMAGE"
            class="create-item"
          >
            <!-- 代码库 -->
            <div class="item-title">
              {{ $t('应用模板') }}
            </div>
            <div class="establish-tab">
              <section class="code-type">
                <label class="form-label template"> {{ $t('模板来源') }} </label>
                <div class="tab-box">
                  <li
                    :class="['tab-item template', { 'active': localSourceOrigin === 1 }]"
                    @click="handleCodeTypeChange(1)"
                  >
                    {{ $t('蓝鲸开发框架') }}
                  </li>
                </div>
              </section>
            </div>

            <div
              v-show="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP"
              class="establish-tab pb0 mb0"
            >
              <section class="deploy-panel deploy-main">
                <ul
                  class="ps-tab"
                  style="position: relative; z-index: 10; padding: 0 10px;"
                >
                  <li
                    v-for="(langItem, langName) in curLanguages"
                    :key="langName"
                    :class="['item', { 'active': language === langName }]"
                    @click="changeLanguage(langName)"
                  >
                    {{ $t(defaultlangName[langName]) }}
                  </li>
                </ul>
              </section>

              <div
                class="form-group establish-main card-container"
                :style="establishStyle"
              >
                <transition
                  v-if="sourceControlType"
                  :name="langTransitionName"
                >
                  <template>
                    <div
                      v-for="(langItem, langName) in curLanguages"
                      v-if="langName === language"
                      :key="langName"
                      class="options-card"
                    >
                      <h2> {{ $t('初始化代码模板：') }} </h2>
                      <ul class="establish-main-list">
                        <li
                          v-for="(item, itemIndex) in langItem"
                          :key="itemIndex"
                        >
                          <label class="pointer">
                            <input
                              v-model="sourceInitTemplate"
                              type="radio"
                              name="q"
                              :value="item.name"
                              class="ps-radio-default"
                              checked
                            >
                            {{ item.display_name }}
                          </label>
                          <p class="f12">
                            {{ item.description }}
                          </p>
                        </li>
                      </ul>
                    </div>
                  </template>
                </transition>
              </div>
            </div>

            <div
              v-show="sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP"
              class="ps-tip-block lesscode-info mt15"
            >
              <i
                style="color: #3A84FF;"
                class="paasng-icon paasng-info-circle"
              />
              {{ $t('默认模块需要在') }} <a
                target="_blank"
                :href="GLOBAL.LINK.LESSCODE_INDEX"
                style="color: #3a84ff"
              > {{ $t('蓝鲸运维开发平台') }} </a> {{ $t('生成源码包部署，您也可以在应用中新增普通模块。') }}
            </div>
            <div
              v-if="sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules"
              class="error-tips pt10"
            >
              {{ $t('蓝鲸运维开发平台的应用 ID 只能由小写字母组成, 所属应用') }} {{ curAppInfo.application.name }} {{ $t('的应用 ID 为') }} {{ curAppInfo.application.code }},
              {{ $t('故无法在当前应用下创建蓝鲸运维开发平台的模块。') }}
            </div>
          </div>

          <div
            v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP"
            class="create-item"
            data-test-id="createDefault_item_appEngine"
          >
            <div class="item-title">
              {{ $t('源码管理') }}
            </div>
            <section class="code-depot">
              <label class="form-label">
                {{ $t('代码源') }}
              </label>
              <div
                v-for="(item, index) in sourceControlTypes"
                :key="index"
                :class="['code-depot-item mr10', { 'on': item.value === sourceControlType }]"
                @click="changeSourceControl(item)"
              >
                <img :src="'/static/images/' + item.imgSrc + '.png'">
                <p class="sourceControlTypeInfo">
                  {{ item.name }}
                </p>
              </div>
            </section>

            <!-- Git 相关额外代码 start -->
            <template v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP">
              <!-- Git 相关额外代码 start -->
              <template v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
                <git-extend
                  :key="sourceControlType"
                  :git-control-type="sourceControlType"
                  :is-auth="gitExtendConfig[sourceControlType].isAuth"
                  :is-loading="gitExtendConfig[sourceControlType].isLoading"
                  :alert-text="gitExtendConfig[sourceControlType].alertText"
                  :auth-address="gitExtendConfig[sourceControlType].authAddress"
                  :auth-docs="gitExtendConfig[sourceControlType].authDocs"
                  :fetch-method="gitExtendConfig[sourceControlType].fetchMethod"
                  :repo-list="gitExtendConfig[sourceControlType].repoList"
                  :selected-repo-url.sync="gitExtendConfig[sourceControlType].selectedRepoUrl"
                />
                <div
                  class="form-group-dir"
                  style="margin-top: 10px;"
                >
                  <label class="form-label mr10">
                    {{ $t('部署目录') }}
                    <i
                      v-bk-tooltips="sourceDirTip"
                      class="paasng-icon paasng-info-circle"
                    />
                  </label>
                  <div class="form-group-flex">
                    <p>
                      <bk-input
                        v-model="sourceDirVal"
                        class="source-dir"
                        :class="sourceDirError ? 'error' : ''"
                        :placeholder="$t('请输入应用所在子目录，不填则默认为根目录')"
                        @blur="validSourceDir"
                      />
                      <ul
                        v-if="sourceDirError"
                        class="parsley-errors-list"
                      >
                        <li class="parsley-pattern">
                          {{ $t('支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头') }}
                        </li>
                      </ul>
                    </p>
                  </div>
                </div>
              </template>
              <!-- Git 相关额外代码 end -->

              <!-- 用户自定义git、svn账号信息 start -->
              <repo-info
                v-if="curSourceControl && curSourceControl.auth_method === 'basic'"
                ref="repoInfo"
                :key="sourceControlType"
                :type="sourceControlType"
              />
              <!-- 用户自定义git、svn账号信息 end -->
            </template>
          </div>

          <div
            v-if="formLoading"
            class="form-loading"
          >
            <img src="/static/images/create-app-loading.svg">
            <p> {{ $t('模块创建中，请稍候') }} </p>
          </div>
          <div
            v-else
            class="form-actions"
          >
            <button
              v-if="canCreateModule"
              class="ps-btn ps-btn-l ps-btn-primary"
              type="submit"
              :class="{ 'ps-btn-isdisabled': sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules }"
              :disabled="sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules"
            >
              {{ $t('创建模块') }}
            </button>
            <div
              v-else
              v-bk-tooltips="$t('非内部版应用目前无法创建其它模块')"
              class="ps-btn-disabled"
              style="text-align: center;"
            >
              {{ $t('创建模块') }}
            </div>
            <button
              class="ps-btn ps-btn-l ps-btn-default"
              @click.stop.prevent="goBack"
            >
              {{ $t('返回') }}
            </button>
          </div>
        </form>
      </div>
      <div
        v-else
        style="padding-top: 100px; text-align: center;"
      >
        {{ $t('非内部版应用 目前无法创建新模块') }}
      </div>
    </div>
  </div>
</template>

<script>
// eslint-disable-next-line
    import { Parsley, ParsleyUI } from 'parsleyjs'
import { APP_LANGUAGES_IMAGE, DEFAULT_APP_SOURCE_CONTROL_TYPES, DEFAULR_LANG_NAME } from '@/common/constants';
import '@/common/parsley_locale';
import _ from 'lodash';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import appPreloadMixin from '@/mixins/app-preload';

export default {
  components: {
    gitExtend,
    repoInfo,
  },
  mixins: [appPreloadMixin],
  data() {
    return {
      formLoading: false,
      globalErrorMessage: '',
      language: 'Python',
      sourceInitTemplate: '',
      sourceControlType: this.GLOBAL.DEFAULT_SOURCE_CONTROL,
      gitExtendConfig: {
        bk_gitlab: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
        tc_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('tc_git'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
        github: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('github'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
        gitee: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('gitee'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
      },
      // For rendering template
      languages: {},
      language_images_map: APP_LANGUAGES_IMAGE,
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES,
      langTransitionName: '',
      allRegionsSpecs: {},
      canCreateModule: true,

      supportPlusValue: true,
      isOpenSupportPlus: 'yes',
      regionsServices: {},

      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      localSourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      curLanguages: {},
      sourceDirVal: '',
      sourceDirError: false,
      sourceDirTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${this.GLOBAL.DOC.DEPLOY_DIR}" style="color: #3a84ff">${this.$t('如何设置部署目录')}</a>`,
        placements: ['right'],
      },
      defaultlangName: DEFAULR_LANG_NAME,
      structureType: 'soundCode',
      mirrorData: {
        type: 'public',
        url: '',
      },
      mirrorRules: {
        url: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              return !val.includes(':');
            },
            message: '镜像地址中不能包含版本(tag)信息',
            trigger: 'blur',
          },
        ],
      },
      lessCodeCorrectRules: false,
    };
  },
  computed: {
    region() {
      return this.curAppInfo.application.region;
    },
    isShowRegionsService() {
      return Object.keys(this.regionsServices).length > 0;
    },
    establishStyle() {
      if (this.curLanguages && this.language && this.curLanguages[this.language]) {
        const len = this.curLanguages[this.language].length;
        const lanItemHeight = 50;
        if (!len) {
          return {
            height: '208px',
          };
        }
        return {
          height: `${(len + 1) * lanItemHeight}px`,
        };
      }
      return {
        height: '208px',
      };
    },
    curUserFeature() {
      return this.$store.state.userFeature;
    },
    curSourceControl() {
      const match = this.sourceControlTypes.find(item => item.value === this.sourceControlType);
      return match;
    },
  },
  watch: {
    sourceInitTemplate() {
      this.fetchRegionsServices();
    },
    structureType(value) {
      if (value === 'mirror') {
        this.sourceOrigin = 4;
      } else if (value === 'soundCode') {
        this.handleCodeTypeChange(1);
      }
    },
    sourceOrigin(value) {
      this.lessCodeCorrectRules = false;
      if (value === 2) {
        this.lessCodeCorrectRules = !/^[a-z]+$/.test(this.curAppInfo.application.code);
      }
    },
  },
  async created() {
    await this.fetchRegion();

    if (!this.canCreateModule) {
      this.loading = false;
      return;
    }
    await this.getLanguageByRegion();
    await this.getCodeTypes();
    this.sourceInitTemplate = this.languages[this.language][0].name;
    this.fetchRegionsServices();
    switch (this.sourceControlType) {
      case 'bk_gitlab':
      case 'tc_git':
        for (const key in this.gitExtendConfig) {
          // 初始化 repo List
          const config = this.gitExtendConfig[key];
          config.fetchMethod();
        }
        break;
      default:
        break;
    }
  },
  mounted() {
    this.form = $('#form-create-app').parsley();
    this.$form = this.form.$element;

    // Auto clearn ServerError message for field
    this.form.on('form:validated', (target) => {
      target.fields.forEach((field) => {
        field.removeError('serverError');
      });
    });
    window.Parsley.on('field:error', function () {
      // 防止出现多条错误提示
      this.$element.parsley().removeError('serverError');
    });
  },
  methods: {
    handleCodeTypeChange(payload) {
      this.localSourceOrigin = payload;
      if (payload === this.GLOBAL.APP_TYPES.NORMAL_APP) {
        this.sourceOrigin = payload;
        this.curLanguages = _.cloneDeep(this.languages);
        this.language = 'Python';
      } else {
        if (payload === 2) {
          this.curLanguages = _.cloneDeep({
            NodeJS: [this.languages.NodeJS[0]],
          });
          this.language = 'NodeJS';
          this.sourceOrigin = payload;
        }
      }
      this.sourceInitTemplate = this.curLanguages[this.language][0].name;
    },

    async fetchRegion() {
      try {
        await this.$store.dispatch('fetchRegionInfo', this.region);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async fetchRegionsServices() {
      try {
        const res = await this.$store.dispatch('createApp/getServicesByTmpl', {
          language: this.sourceInitTemplate,
        });
        this.regionsServices = JSON.parse(JSON.stringify(res.result));
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    /**
             * 获取代码库类型
             */
    async getCodeTypes() {
      try {
        const res = await this.$store.dispatch('module/getCodeTypes');
        this.sourceControlTypes = res.results;

        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });
      } catch (res) {
        this.$paasMessage({
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    /**
             * 根据应用类型获取支持的语言（内部、混合云...）
             * @return {[type]} [description]
             */
    async getLanguageByRegion() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        this.allRegionsSpecs = res;

        if (!_.has(this.allRegionsSpecs, this.region)) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('版本配置未找到，您没有创建模块权限。'),
          });
          return;
        }
        this.languages = this.allRegionsSpecs[this.region].languages;
        this.curLanguages = _.cloneDeep(this.languages);
      } catch (res) {
        this.$paasMessage({
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    /**
             * 根据不同的 sourceControlType 生成对应的 fetchRepoList 方法
             * @param {String} sourceControlType 代码库类型
             */
    generateFetchRepoListMethod(sourceControlType) {
      return async () => {
        const config = this.gitExtendConfig[sourceControlType];
        try {
          config.isLoading = true;
          const resp = await this.$store.dispatch('getRepoList', { sourceControlType });
          config.repoList = resp.results.map((repo, index) => ({ name: repo.fullname, id: repo.http_url_to_repo }));
          config.isAuth = true;
        } catch (e) {
          const resp = e.response;
          config.isAuth = false;
          if (resp.status === 403 && resp.data.result) {
            config.authAddress = resp.data.address;
            config.authDocs = resp.data.auth_docs;
          }
        } finally {
          config.isLoading = false;
        }
      };
    },

    /**
             * 选择开发语言回调
             * @param {String} language 开发语言
             */
    changeLanguage(language) {
      const fromLanguage = this.language;
      this.language = language;
      // Select the first choice of selected language
      this.sourceInitTemplate = this.languages[this.language][0].name;

      // Detect animate direction
      const languageList = [];
      for (const key in this.languages) {
        this.languages[key].forEach((lang) => {
          languageList.push(lang.language);
        });
      }
      if (languageList.indexOf(fromLanguage) > languageList.indexOf(language)) {
        this.langTransitionName = 'lang-card-to-right';
      } else {
        this.langTransitionName = 'lang-card-to-left';
      }
    },

    /**
             * 选择代码库回调
             * @param {String} sourceControlType 代码库
             */
    changeSourceControl(item) {
      this.sourceControlType = item.value;
      this.sourceDirError = false;
      this.sourceDirVal = '';
      // 请求下拉数据
      switch (this.sourceControlType) {
        case 'bk_gitlab':
        case 'tc_git':
          const config = this.gitExtendConfig[this.sourceControlType];
          config.fetchMethod();
          break;
        default:
          break;
      }
    },

    goBack() {
      // this.$router.push({
      //     name: 'appSummary',
      //     params: {
      //         id: this.$route.params.id,
      //         moduleId: this.curModuleId
      //     }
      // })
      window.history.go(-1);
    },
    validSourceDir() {
      const val = this.sourceDirVal || '';
      if (!val) {
        this.sourceDirError = false;
        return;
      }
      this.sourceDirError = !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(val);
    },

    /**
             * 创建应用模块
             */
    async createAppModule() {
      if (!this.canCreateModule) {
        return;
      }
      let sourceRepoUrl = null;
      if (!this.form.isValid()) {
        return;
      }

      if (this.sourceDirError) {
        return;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && ['bare_git', 'bare_svn'].includes(this.sourceControlType)) {
        const validRet = await this.$refs.repoInfo.valid();
        if (!validRet) {
          window.scrollTo(0, 0);
          return;
        }
      }

      if (this.$refs.validate2) {
        try {
          await this.$refs.validate2.validate();
        } catch (e) {
          console.error(e);
          return;
        }
      }

      this.formLoading = true;
      // Remove all serverError error messages
      this.globalErrorMessage = '';
      this.form.reset();

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP) {
        switch (this.sourceControlType) {
          case 'bk_gitlab':
          case 'github':
          case 'gitee':
          case 'tc_git':
            const config = this.gitExtendConfig[this.sourceControlType];
            sourceRepoUrl = config.selectedRepoUrl;
            if (!sourceRepoUrl) {
              this.formLoading = false;
              this.$paasMessage({
                theme: 'error',
                message: config.isAuth ? this.$t('请选择关联的远程仓库') : this.$t('请关联 git 账号'),
              });
              window.scrollTo(0, 0);
              return;
            }
            break;
          case 'bk_svn':
          default:
            sourceRepoUrl = undefined;
            break;
        }
      }

      const params = {
        name: this.name,
        language: this.language,
        source_init_template: this.sourceInitTemplate,
        source_control_type: this.sourceControlType,
        source_repo_url: sourceRepoUrl,
        source_origin: this.sourceOrigin,
        source_dir: this.sourceDirVal || '',
        ...this.$form.serializeObject(),
      };

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && ['bare_git', 'bare_svn'].includes(this.sourceControlType)) {
        const repoData = this.$refs.repoInfo.getData();
        params.source_repo_url = repoData.url;
        params.source_repo_auth_info = {
          username: repoData.account,
          password: repoData.password,
        };
        params.source_dir = repoData.sourceDir;
      }

      if (this.sourceOrigin !== this.GLOBAL.APP_TYPES.NORMAL_APP) {
        delete params.source_repo_url;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.IMAGE) {
        params.type = 'default';
        params.source_control_type = 'tc_docker';
        params.source_repo_url = `${this.GLOBAL.CONFIG.MIRROR_PREFIX}${this.mirrorData.url}`;
        params.source_repo_auth_info = {
          username: '',
          password: '',
        };
      }

      try {
        this.formLoading = true;

        const res = await this.$store.dispatch('module/createAppModule', {
          appCode: this.appCode,
          data: params,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('创建应用模块成功！'),
        });

        this.$store.commit('addAppModule', res.module);
        this.$router.push({
          name: 'appSummary',
          params: {
            id: this.appCode,
            moduleId: res.module.name,
          },
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.formLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
    @import "./index.scss";
</style>
<style lang="scss">
.item-cls {
    .bk-form-content{
        .form-error-tip{
            margin: 5px 0 0 260px;
        }
    }
}
</style>
