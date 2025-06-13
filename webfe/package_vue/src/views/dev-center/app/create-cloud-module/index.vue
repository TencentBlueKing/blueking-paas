<template>
  <div class="paas-content created-module-container">
    <div
      v-en-class="'en-label'"
      class="wrap"
    >
      <div
        class="paas-application-tit establish-title"
        @click="goBack"
      >
        <i class="paasng-icon paasng-back"></i>
        <span>{{ $t('创建模块') }}</span>
      </div>
      <div
        v-if="canCreateModule"
        class="establish"
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
              <label class="form-label">{{ $t('所属应用') }}</label>
              <div class="form-group-flex form-input-width">
                <p class="app-name">
                  {{ curAppInfo.application.name }}
                </p>
              </div>
            </div>

            <bk-form
              form-type="inline"
              :model="formData"
              ref="formDataRef"
            >
              <bk-form-item
                :required="true"
                :property="'name'"
                :rules="rules.name"
                error-display-type="normal"
                ext-cls="module-item-cls"
              >
                <div class="form-group mt10">
                  <label class="form-label">{{ $t('模块名称') }}</label>
                  <div class="form-input-flex">
                    <bk-input
                      v-model="formData.name"
                      :placeholder="$t('由小写字母和数字以及连接符(-)组成，不能超过 16 个字符')"
                      class="mr10 mt10 form-input-width"
                    ></bk-input>
                  </div>
                </div>
              </bk-form-item>
            </bk-form>

            <!-- 构建方式 -->
            <div class="form-group mt10 align-items-center mt10">
              <label class="form-label mr10">
                {{ $t('构建方式') }}
              </label>
              <div class="form-group-flex">
                <bk-radio-group
                  v-model="formData.buildMethod"
                  class="construction-manner"
                  @change="handleChangeBuildMethod"
                >
                  <bk-radio :value="'buildpack'">
                    {{ $t('蓝鲸 Buildpack') }}
                  </bk-radio>
                  <bk-radio :value="'dockerfile'">Dockerfile</bk-radio>
                  <bk-radio :value="'mirror'">
                    {{ $t('仅镜像') }}
                  </bk-radio>
                </bk-radio-group>
              </div>
            </div>
          </div>

          <bk-steps
            ext-cls="step-cls"
            :steps="createSteps"
            :cur-step.sync="curStep"
          ></bk-steps>

          <!-- 镜像管理 -->
          <div
            v-if="structureType === 'mirror' && curStep === 1"
            class="create-item"
            data-test-id="createDefault_item_baseInfo"
          >
            <div class="item-title">
              {{ $t('镜像管理') }}
            </div>

            <bk-form
              class="mt10 image-manage-cls"
              ref="validate2"
              :model="mirrorData"
              :rules="mirrorRules"
              :label-width="100"
            >
              <bk-form-item
                :required="true"
                :property="'url'"
                error-display-type="normal"
                ext-cls="item-cls image-item"
                :label="$t('镜像仓库')"
              >
                <div class="form-input-flex">
                  <bk-input
                    v-model="mirrorData.url"
                    style="width: 650px"
                    clearable
                    :placeholder="mirrorExamplePlaceholder"
                  ></bk-input>
                </div>
              </bk-form-item>

              <bk-form-item
                error-display-type="normal"
                ext-cls="item-cls"
                :label="$t('镜像凭证')"
              >
                <bk-select
                  v-model="imageCredentialsData.name"
                  :disabled="false"
                  style="width: 650px"
                  ext-cls="select-custom"
                  ext-popover-cls="select-popover-custom"
                  searchable
                >
                  <bk-option
                    v-for="option in imageCredentialList"
                    :id="option.name"
                    :key="option.name"
                    :name="option.name"
                  />
                  <!-- <div
                    slot="extension"
                    style="cursor: pointer;"
                    @click="handlerCreateImageCredential"
                  >
                    <i class="bk-icon icon-plus-circle mr5" />{{ $t('新建凭证') }}
                  </div> -->
                </bk-select>
                <span
                  slot="tip"
                  class="input-tips"
                >
                  {{ $t('请选择镜像凭证以拉取私有镜像，也可在创建模块后在 "模块配置 - 构建配置“ 页面中添加') }}
                </span>
              </bk-form-item>
            </bk-form>
          </div>

          <div
            v-if="isShowAppTemplate"
            class="create-item"
          >
            <!-- 代码库 -->
            <div class="item-title">
              {{ $t('应用模板') }}
            </div>
            <div class="establish-tab mt10">
              <section class="code-type">
                <span class="pl20">{{ $t('模板来源') }}：</span>
                <span class="pl10 module-name">{{ $t('蓝鲸开发框架') }}</span>
              </section>
            </div>

            <div
              v-show="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP"
              class="establish-tab pb0 mb0"
            >
              <section class="deploy-panel deploy-main">
                <ul
                  class="ps-tab"
                  style="position: relative; z-index: 10; padding: 0 10px"
                >
                  <li
                    v-for="(langItem, langName) in curLanguages"
                    :key="langName"
                    :class="['item', { active: language === langName }]"
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
                      <h2>{{ $t('初始化代码模板：') }}</h2>
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
                            />
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
                style="color: #3a84ff"
                class="paasng-icon paasng-info-circle"
              />
              {{ $t('默认模块需要在') }}
              <a
                target="_blank"
                :href="GLOBAL.LINK.LESSCODE_INDEX"
                style="color: #3a84ff"
              >
                {{ $t('蓝鲸运维开发平台') }}
              </a>
              {{ $t('生成源码包部署，您也可以在应用中新增普通模块。') }}
            </div>
            <div
              v-if="sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules"
              class="error-tips pt10"
            >
              {{ $t('蓝鲸运维开发平台的应用 ID 只能由小写字母组成, 所属应用') }}
              {{ curAppInfo.application.name }} {{ $t('的应用 ID 为') }} {{ curAppInfo.application.code }},
              {{ $t('故无法在当前应用下创建蓝鲸运维开发平台的模块。') }}
            </div>
          </div>

          <div
            v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP && curStep === 1"
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
                :class="['code-depot-item mr10', { on: item.value === sourceControlType }]"
                @click="changeSourceControl(item)"
              >
                <img :src="'/static/images/' + item.imgSrc + '.png'" />
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
                  class="module-code-repo"
                  ref="extend"
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
                  style="margin-top: 10px"
                >
                  <label class="form-label mr10 pr8">
                    {{ $t('构建目录') }}
                  </label>
                  <div class="form-group-flex">
                    <div>
                      <bk-input
                        v-model="sourceDirVal"
                        class="source-dir form-input-width"
                        :class="sourceDirError ? 'error' : ''"
                        :placeholder="$t('请输入应用所在子目录，不填则默认为根目录')"
                        @blur="validSourceDir"
                      />
                      <ul
                        v-if="sourceDirError"
                        class="parsley-errors-list"
                      >
                        <li class="parsley-pattern">
                          {{
                            $t(
                              '支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头'
                            )
                          }}
                        </li>
                      </ul>
                    </div>
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
                :source-dir-label="'构建目录'"
                :is-cloud-created="true"
                :default-url="repoData.url"
                :default-account="repoData.account"
                :default-password="repoData.password"
                :default-dir="repoData.sourceDir"
                @dir-change="($event) => (curRepoDir = $event)"
              />
              <!-- 用户自定义git、svn账号信息 end -->
            </template>

            <!-- Dockerfile 构建 -->
            <bk-form
              v-if="isDockerfile"
              :label-width="119"
              :model="dockerfileData"
              ref="dockerfileRef"
              class="mt20"
            >
              <bk-form-item
                :label="$t('Dockerfile 路径')"
                :rules="absolutePathRule"
                :property="'dockerfilePath'"
                error-display-type="normal"
                ext-cls="form-dockerfile-cls"
              >
                <bk-input
                  style="width: 650px"
                  v-model="dockerfileData.dockerfilePath"
                  :placeholder="$t('相对于构建目录的路径，若留空，默认为构建目录下名为 “Dockerfile” 的文件')"
                ></bk-input>
              </bk-form-item>
            </bk-form>

            <!-- 文件示例目录 -->
            <ExamplesDirectory
              style="margin-left: 100px"
              :root-path="rootPath"
              :append-path="appendPath"
              :default-files="defaultFiles"
              :is-dockerfile="isDockerfile"
              :show-root="false"
              :type="'string'"
            />

            <!-- 构建参数 -->
            <template v-if="isDockerfile">
              <bk-form
                :model="dockerfileData"
                form-type="vertical"
                ext-cls="build-params-form"
              >
                <div
                  class="form-label pr8"
                  :class="{ 'params-dockerfile': curSourceControl && curSourceControl.auth_method === 'basic' }"
                >
                  {{ $t('构建参数') }}
                </div>
                <div class="form-value-wrapper mt10">
                  <bk-button
                    v-if="!dockerfileData.buildParams.length"
                    :text="true"
                    title="primary"
                    @click="addBuildParams"
                  >
                    <i class="paasng-icon paasng-plus-thick" />
                    {{ $t('新建构建参数') }}
                  </bk-button>
                  <template v-if="dockerfileData.buildParams.length">
                    <div class="build-params-header">
                      <div class="name">{{ $t('参数名') }}</div>
                      <div class="value">{{ $t('参数值') }}</div>
                    </div>
                    <div
                      v-for="(item, index) in dockerfileData.buildParams"
                      class="build-params-item"
                      :key="index"
                    >
                      <bk-form
                        :ref="`name-${index}`"
                        :model="item"
                      >
                        <bk-form-item
                          :rules="rules.buildParams"
                          :property="'name'"
                        >
                          <bk-input
                            v-model="item.name"
                            :placeholder="$t('参数名')"
                          ></bk-input>
                        </bk-form-item>
                      </bk-form>
                      <span class="equal">=</span>
                      <bk-form
                        :ref="`value-${index}`"
                        :model="item"
                      >
                        <bk-form-item
                          :rules="rules.buildParams"
                          :property="'value'"
                        >
                          <bk-input v-model="item.value"></bk-input>
                        </bk-form-item>
                      </bk-form>
                      <i
                        class="paasng-icon paasng-minus-circle-shape"
                        @click="removeBuildParams(index)"
                      ></i>
                    </div>
                  </template>
                </div>
              </bk-form>
              <bk-button
                v-if="dockerfileData.buildParams.length"
                ext-cls="add-build-params"
                :text="true"
                title="primary"
                @click="addBuildParams"
              >
                <i class="paasng-icon paasng-plus-thick" />
                {{ $t('新建构建参数') }}
              </bk-button>
            </template>
          </div>

          <!-- 源码&镜像 部署配置内容 -->
          <div
            class="mt20"
            v-if="structureType === 'soundCode' && curStep === 2"
          >
            <collapseContent
              :title="$t('进程配置')"
              collapse-item-name="process-config"
              active-name="process-config"
            >
              <bk-alert type="info">
                <div slot="title">
                  {{ $t('进程配置、钩子命令在 app_desc.yaml 文件中定义。') }}
                  <a
                    target="_blank"
                    :href="GLOBAL.DOC.APP_DESC_DOC"
                    style="color: #3a84ff"
                  >
                    {{ $t('应用描述文件') }}
                  </a>
                </div>
              </bk-alert>
            </collapseContent>
          </div>

          <!-- 仅镜像，默认编辑态 -->
          <div
            class="mt20"
            v-if="structureType === 'mirror' && curStep === 2"
          >
            <collapseContent
              active-name="process"
              collapse-item-name="process"
              :title="$t('进程配置')"
            >
              <deploy-process
                ref="processRef"
                :cloud-form-data="{ url: mirrorData.url, imageCredentialName: imageCredentialsData.name }"
                :is-create="isCreate"
              ></deploy-process>
            </collapseContent>

            <collapseContent
              active-name="hook"
              collapse-item-name="hook"
              :title="$t('部署前置命令')"
              class="mt20"
            >
              <deploy-hook
                ref="hookRef"
                :is-create="isCreate"
              ></deploy-hook>
            </collapseContent>
          </div>

          <div
            v-if="formLoading"
            class="form-loading"
          >
            <img src="/static/images/create-app-loading.svg" />
            <p>{{ $t('模块创建中，请稍候') }}</p>
          </div>
          <div
            v-else
            class="form-actions flex-row"
          >
            <!-- :disabled="" -->
            <div v-if="curStep === 1">
              <bk-button
                theme="primary"
                @click="handleNext"
              >
                {{ $t('下一步') }}
              </bk-button>
            </div>
            <div v-if="curStep === 2">
              <bk-button @click="handlePrev">
                {{ $t('上一步') }}
              </bk-button>
              <bk-button
                theme="primary"
                v-if="canCreateModule"
                :class="{ 'ps-btn-isdisabled': sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules }"
                :disabled="sourceOrigin !== GLOBAL.APP_TYPES.NORMAL_APP && lessCodeCorrectRules"
                @click="createAppModule"
              >
                {{ $t('创建模块') }}
              </bk-button>
              <div
                v-else
                v-bk-tooltips="$t('非内部版应用目前无法创建其它模块')"
                class="ps-btn-disabled"
                style="text-align: center"
              >
                {{ $t('提交') }}
              </div>
            </div>
            <bk-button @click="handleCancel">
              {{ $t('取消') }}
            </bk-button>
          </div>
        </form>
      </div>
      <div
        v-else
        style="padding-top: 100px; text-align: center"
      >
        {{ $t('非内部版应用 目前无法创建新模块') }}
      </div>
    </div>
  </div>
</template>

<script>
import { APP_LANGUAGES_IMAGE, DEFAULT_APP_SOURCE_CONTROL_TYPES, DEFAULR_LANG_NAME } from '@/common/constants';
import { cloneDeep, has } from 'lodash';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import appPreloadMixin from '@/mixins/app-preload';
import collapseContent from './comps/collapse-content.vue';
import deployProcess from '@/views/dev-center/app/engine/cloud-deployment/deploy-process';
import deployHook from '@/views/dev-center/app/engine/cloud-deployment/deploy-hook';
import { TE_MIRROR_EXAMPLE } from '@/common/constants.js';
import ExamplesDirectory from '@/components/examples-directory';

export default {
  components: {
    gitExtend,
    repoInfo,
    collapseContent,
    deployProcess,
    deployHook,
    ExamplesDirectory,
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
      defaultlangName: DEFAULR_LANG_NAME,
      structureType: 'soundCode',
      imageCredentialsData: {
        name: '',
        username: '',
        password: '',
      },
      imageCredentialList: [],
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
            regex: /^(?:([a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*(?::\d+)?)\/)?(?:([a-zA-Z0-9_-]+)\/)*([a-zA-Z0-9_.-]+)$/,
            message: this.$t('请输入不包含标签(tag)的镜像仓库地址'),
            trigger: 'blur',
          },
        ],
      },
      rules: {
        name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-z][a-z0-9-]*$/;
              return reg.test(val);
            },
            message: this.$t('格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-z][a-z0-9-]{1,16}$/;
              return reg.test(val);
            },
            message: this.$t('由小写字母和数字以及连接符(-)组成，不能超过 16 个字符'),
            trigger: 'blur',
          },
        ],
        buildParams: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
      lessCodeCorrectRules: false,
      createSteps: [
        { title: this.$t('源码信息'), icon: 1 },
        { title: this.$t('部署配置'), icon: 2 },
      ],
      curStep: 1,
      formData: {
        name: '',
        buildMethod: 'buildpack', // 构建方式
      },
      cloudAppData: {},
      isCreate: true,
      localCloudAppData: {},
      repoData: {},
      initCloudAppData: {},
      dockerfileData: {
        dockerfilePath: '', // Dockerfile 路径
        buildParams: [], // 构建参数
      },
      curRepoDir: '',
      absolutePathRule: [
        {
          regex: /^(?!.*(^|\/|\\|)\.{1,2}($|\/|\\|)).*$/,
          message: this.$t('不支持填写相对路径'),
          trigger: 'blur',
        },
      ],
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
      const match = this.sourceControlTypes.find((item) => item.value === this.sourceControlType);
      return match;
    },
    createCloudAppData() {
      return this.$store.state.cloudApi.cloudAppData;
    },
    isShowAppTemplate() {
      return (
        this.sourceOrigin !== this.GLOBAL.APP_TYPES.CNATIVE_IMAGE &&
        this.curStep === 1 &&
        this.formData.buildMethod === 'buildpack'
      );
    },
    // 示例镜像 placeholder
    mirrorExamplePlaceholder() {
      return `${this.$t('请输入镜像仓库，如')}：${
        this.GLOBAL.CONFIG.MIRROR_EXAMPLE === 'nginx' ? this.GLOBAL.CONFIG.MIRROR_EXAMPLE : TE_MIRROR_EXAMPLE
      }`;
    },
    isDockerfile() {
      return this.formData.buildMethod === 'dockerfile';
    },
    // 根目录
    rootPath() {
      const { auth_method } = this.curSourceControl || {};
      const authPathMap = {
        oauth: this.sourceDirVal,
        basic: this.curRepoDir,
      };
      return authPathMap[auth_method] || '';
    },
    appendPath() {
      return this.isDockerfile ? this.dockerfileData.dockerfilePath : '';
    },
    // 默认文件
    defaultFiles() {
      const languageFileMap = {
        Python: 'requirements.txt',
        NodeJS: 'package.json',
        Go: 'go.mod',
      };
      const file = languageFileMap[this.language || 'Python'];
      return [{ name: file }];
    },
  },
  watch: {
    sourceInitTemplate() {
      this.fetchRegionsServices();
    },
    structureType(value) {
      this.curStep = 1;
      if (value === 'mirror') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.CNATIVE_IMAGE; // 仅镜像的云原生
        this.createSteps = [
          { title: this.$t('镜像信息'), icon: 1 },
          { title: this.$t('部署配置'), icon: 2 },
        ];
        this.getImageCredentialList(); // 获取镜像凭证
      } else if (value === 'soundCode') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP;
        this.createSteps = [
          { title: this.$t('源码信息'), icon: 1 },
          { title: this.$t('部署配置'), icon: 2 },
        ];
        this.handleCodeTypeChange(1);
      }
    },
    sourceOrigin(value) {
      this.lessCodeCorrectRules = false;
      if (value === 2) {
        this.lessCodeCorrectRules = !/^[a-z]+$/.test(this.curAppInfo.application.code);
      }
    },
    createCloudAppData: {
      handler(value) {
        // 如果vuex变量cloudAppData变动了则需要将值赋值给this.cloudAppData
        if (JSON.stringify(value?.spec?.processes) !== JSON.stringify(this.cloudAppData?.spec?.processes)) {
          this.cloudAppData = value;
        }
      },
      deep: true,
    },
    'formData.name'(value) {
      if (Object.keys(this.createCloudAppData).length) {
        this.localCloudAppData = cloneDeep(this.createCloudAppData);
        this.localCloudAppData.metadata.name = `${this.appCode}-m-${value}`;

        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
      }
    },
    sourceDirVal(newVal) {
      if (newVal === '') {
        this.sourceDirError = false;
      }
    },
  },
  async created() {
    await this.fetchRegion();
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
  methods: {
    handleCodeTypeChange(payload) {
      this.localSourceOrigin = payload;
      if (payload === this.GLOBAL.APP_TYPES.NORMAL_APP) {
        this.sourceOrigin = payload;
        this.curLanguages = cloneDeep(this.languages);
        this.language = 'Python';
      } else {
        if (payload === 2) {
          this.curLanguages = cloneDeep({
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

        if (!has(this.allRegionsSpecs, this.region)) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('版本配置未找到，您没有创建模块权限。'),
          });
          return;
        }
        this.languages = this.allRegionsSpecs[this.region].languages;
        this.curLanguages = cloneDeep(this.languages);
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
          config.repoList = resp.results.map((repo) => ({ name: repo.fullname, id: repo.http_url_to_repo }));
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
          // eslint-disable-next-line no-case-declarations
          const config = this.gitExtendConfig[this.sourceControlType];
          config.fetchMethod();
          break;
        default:
          break;
      }
    },
    validSourceDir() {
      const val = this.sourceDirVal || '';
      if (!val) {
        this.sourceDirError = false;
        return;
      }
      this.sourceDirError = !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(val);
    },

    // 钩子命令校验
    async handleHookValidator() {
      if (this.$refs.hookRef) {
        return await this.$refs.hookRef?.handleValidator();
      }
      return true;
    },

    /**
     * 创建应用模块
     */
    async createAppModule() {
      let sourceRepoUrl = null;

      // 启动命令校验
      if (this.createCloudAppData.spec?.hooks) {
        const isVerificationPassed = await this.handleHookValidator();
        if (!isVerificationPassed) {
          return;
        }
      }

      // Remove all serverError error messages
      this.globalErrorMessage = '';

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP) {
        switch (this.sourceControlType) {
          case 'bk_gitlab':
          case 'github':
          case 'gitee':
          case 'tc_git':
            // eslint-disable-next-line no-case-declarations
            const config = this.gitExtendConfig[this.sourceControlType];
            sourceRepoUrl = config.selectedRepoUrl;
            if (!sourceRepoUrl) {
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
        name: this.formData.name,
        source_config: {
          source_init_template: this.sourceInitTemplate,
          source_control_type: this.sourceControlType,
          source_repo_url: sourceRepoUrl,
          source_origin: this.sourceOrigin,
          source_dir: this.sourceDirVal || '',
        },
        bkapp_spec: {
          // 构建方式
          build_config: {
            build_method: this.formData.buildMethod,
          },
        },
      };

      // dockerfile 构建方式
      if (this.isDockerfile) {
        // 构建参数
        const dockerBuild = {};
        this.dockerfileData.buildParams.forEach((item) => {
          dockerBuild[item.name] = item.value;
        });
        if (this.dockerfileData.dockerfilePath === '') {
          this.dockerfileData.dockerfilePath = null;
        }
        params.bkapp_spec.build_config = {
          build_method: 'dockerfile',
          dockerfile_path: this.dockerfileData.dockerfilePath,
          docker_build_args: dockerBuild,
        };
        delete params.source_config.source_init_template;
      }

      // 仅镜像
      if (this.structureType === 'mirror') {
        params.bkapp_spec.build_config = {
          build_method: 'custom_image',
          image_repository: this.mirrorData.url,
        };
        // 镜像凭证
        if (this.imageCredentialsData.name) {
          if (!params.bkapp_spec.build_config.image_credential) {
            params.bkapp_spec.build_config.image_credential = {};
          }
          params.bkapp_spec.build_config.image_credential.name = this.imageCredentialsData.name;
        }
        const processData = await this.$refs?.processRef?.handleSave();
        const hookData = await this.$refs?.hookRef?.handleSave();
        if (!processData || !hookData) return;
        hookData.type = 'pre-release-hook';
        params.bkapp_spec.processes = processData;
        if (hookData.enabled) {
          params.bkapp_spec.hook = hookData;
        }
      }

      if (
        this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP &&
        ['bare_git', 'bare_svn'].includes(this.sourceControlType)
      ) {
        params.source_config.source_repo_url = this.repoData.url;
        params.source_config.source_repo_auth_info = {
          username: this.repoData.account,
          password: this.repoData.password,
        };
        params.source_config.source_dir = this.repoData.sourceDir;
      }

      if (this.sourceOrigin !== this.GLOBAL.APP_TYPES.NORMAL_APP) {
        delete params.source_config.source_repo_url;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.CNATIVE_IMAGE) {
        // 仅镜像
        params.source_config = {
          source_repo_url: this.mirrorData.url,
          source_origin: this.sourceOrigin,
        };
        // params.manifest = { ...this.createCloudAppData };
      }

      try {
        this.formLoading = true;

        const res = await this.$store.dispatch('module/createCloudModules', {
          appCode: this.appCode,
          data: params,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('创建应用模块成功！'),
        });

        this.$store.commit('addAppModule', res.module);
        this.$router.push({
          name: 'cloudAppDeployForBuild',
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

    // 下一步按钮
    async handleNext() {
      await this.$refs.formDataRef.validate(); // 基本信息检验
      // 构建目录
      if (this.sourceDirError) {
        return;
      }
      if (this.isDockerfile) {
        await this.$refs.dockerfileRef.validate();
      }
      if (this.structureType === 'mirror') {
        // 仅镜像
        await this.$refs.validate2?.validate();
      } else {
        // 源码&镜像
        await this.$refs?.extend?.valid(); // 代码仓库检验
        // 构建参数校验
        const flag = await this.buildParamsValidate();
        if (!flag) {
          return;
        }
        if (['bare_git', 'bare_svn'].includes(this.sourceControlType)) {
          const validRet = await this.$refs?.repoInfo?.valid();
          if (!validRet) {
            window.scrollTo(0, 0);
            return;
          }

          this.repoData = this.$refs?.repoInfo?.getData();
        }
      }
      this.curStep = 2;
      this.$nextTick(() => {
        // 默认编辑态
        this.$refs.processRef?.handleEditClick();
        this.$refs.hookRef?.handleEditClick();
      });
    },

    // 上一步
    handlePrev() {
      this.curStep = 1;
    },

    // 初始化部署配置数据
    initCloudAppDataFunc() {
      this.initCloudAppData = {
        apiVersion: 'paas.bk.tencent.com/v1alpha2',
        kind: 'BkApp',
        metadata: { name: `${this.appCode}-m-${this.formData.name}` },
        spec: {
          build: {
            image: this.mirrorData.url, // 镜像信息-镜像仓库
            imageCredentialsName: this.imageCredentialsData.name, // 镜像信息-镜像凭证-名称
          },
          processes: [
            {
              image: '',
              name: 'web',
              command: [],
              args: [],
              memory: '256Mi',
              cpu: '500m',
              targetPort: 5000,
            },
          ],
        },
      };
      this.localCloudAppData = cloneDeep(this.initCloudAppData);
      this.$store.commit('cloudApi/updateCloudAppData', this.initCloudAppData);
    },

    // 处理取消
    handleCancel() {
      if (this.curStep === 1) {
        this.$router.go(-1);
      } else {
        this.$refs?.processRef?.handleCancel();
        this.cloudAppData = cloneDeep(this.localCloudAppData);
        this.$store.commit('cloudApi/updateHookPageEdit', false);
        this.$store.commit('cloudApi/updateProcessPageEdit', false);
        // 返回模块配置
        this.$router.push({
          name: 'cloudAppDeployForProcess',
          params: {
            moduleId: this.curModuleId,
            id: this.appCode,
          },
        });
      }
    },

    // 获取凭证列表
    async getImageCredentialList() {
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode });
        this.imageCredentialList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    // 前往创建镜像凭证页面
    handlerCreateImageCredential() {
      this.$router.push({ name: 'imageCredential' });
    },

    goBack() {
      this.$router.go(-1);
    },

    // 构建参数校验
    async buildParamsValidate() {
      let flag = true;
      if (!this.dockerfileData.buildParams.length) {
        return flag;
      }
      for (const index in this.dockerfileData.buildParams) {
        try {
          await this.$refs[`name-${index}`][0]?.validate().finally(async () => {
            await this.$refs[`value-${index}`][0]?.validate();
          });
        } catch (error) {
          flag = false;
        }
      }
      return flag;
    },

    // 新建构建参数
    addBuildParams() {
      this.dockerfileData.buildParams.push({
        name: '',
        value: '',
      });
    },

    removeBuildParams(index) {
      this.dockerfileData.buildParams.splice(index, 1);
    },

    handleChangeBuildMethod(value) {
      this.structureType = value === 'mirror' ? 'mirror' : 'soundCode';
    },
  },
};
</script>

<style lang="scss" scoped>
@import './index.scss';
.created-module-container {
  background: #f5f7fa;
  .form-actions {
    button:first-child {
      margin-left: 0;
    }
  }
  .form-dockerfile-cls {
    transform: translateX(-19px);
  }
}
.item-cls {
  /deep/ .bk-form-control .group-text {
    color: #3a84ff !important;
    background: #fafbfd;
    line-height: 30px;
    cursor: pointer;
  }
}
.wrap .establish-title {
  text-align: left;
  padding-left: 24px;
  cursor: pointer;
  i {
    color: #3a84ff;
    font-size: 18px;
    transform: translateY(0px);
  }
}
.module-code-repo {
  /deep/ .bk-form .bk-label {
    padding-right: 18px;
  }
}
.dockerfile-cls {
  transform: translateX(-15px);
  .form-label {
    width: 105px;
  }
  &.repo-dockerfile label {
    transform: translateX(-6px);
  }
}
.params-dockerfile {
  transform: translateX(-6px);
}
.pr8 {
  padding-right: 8px;
}
.image-manage-cls {
  /deep/ .bk-label {
    padding-right: 18px !important;
  }
}
</style>
<style lang="scss">
.module-item-cls {
  .bk-form-content {
    .form-error-tip {
      margin: 5px 0 0 100px;
    }
  }
}
.item-cls.image-item .bk-form-content .form-error-tip {
  margin: 0;
}
</style>
