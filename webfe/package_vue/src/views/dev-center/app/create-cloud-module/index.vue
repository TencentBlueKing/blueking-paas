<template>
  <div class="paas-content created-module-container">
    <div
      v-en-class="'en-label'"
      class="wrap"
    >
      <div class="paas-application-tit establish-title">
        <i
          class="paasng-icon paasng-back"
          @click="goBack"
        ></i>
        <span class="f16 ml5">{{ $t('创建模块') }}</span>
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
              {{ $t('代码来源') }}
            </div>
            <ul class="tab-box mt10">
              <li
                :class="['tab-item', { active: structureType === 'soundCode' }]"
                @click="handleSwitchCodeSource('soundCode')"
              >
                {{ $t('代码仓库') }}
              </li>
              <li
                :class="['tab-item', { active: structureType === 'mirror' }]"
                @click="handleSwitchCodeSource('mirror')"
              >
                {{ $t('镜像仓库') }}
              </li>
            </ul>
          </div>

          <div class="create-item">
            <div class="item-title">
              {{ $t('基本信息') }}
            </div>
            <bk-form
              :model="formData"
              ref="formDataRef"
              :label-width="100"
              class="from-content mt10"
            >
              <bk-form-item
                error-display-type="normal"
                ext-cls="form-item-cls"
                :label="$t('所属应用')"
              >
                <p class="app-name f12 form-input-width">
                  {{ curAppInfo.application.name }}
                </p>
              </bk-form-item>
              <bk-form-item
                :required="true"
                :property="'name'"
                :rules="rules.name"
                error-display-type="normal"
                ext-cls="form-item-cls mt20"
                :label="$t('模块名称')"
              >
                <bk-input
                  v-model="formData.name"
                  :placeholder="$t('由小写字母和数字以及连接符(-)组成，不能超过 16 个字符')"
                  class="form-input-width"
                ></bk-input>
              </bk-form-item>
            </bk-form>
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
              class="from-content mt10"
              ref="validate2"
              :model="mirrorData"
              :rules="mirrorRules"
              :label-width="100"
            >
              <bk-form-item
                :required="true"
                :property="'url'"
                error-display-type="normal"
                ext-cls="form-item-cls"
                :label="$t('镜像仓库')"
              >
                <bk-input
                  v-model="mirrorData.url"
                  class="form-input-width"
                  clearable
                  :placeholder="mirrorExamplePlaceholder"
                ></bk-input>
              </bk-form-item>

              <bk-form-item
                error-display-type="normal"
                ext-cls="form-item-cls mt20"
                :label="$t('镜像凭证')"
              >
                <bk-select
                  v-model="imageCredentialsData.name"
                  :disabled="false"
                  class="form-input-width"
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
            <bk-form
              :label-width="100"
              class="from-content"
            >
              <div class="form-item-title mb10">
                {{ $t('应用模版') }}
              </div>
              <bk-form-item
                error-display-type="normal"
                ext-cls="form-item-cls"
                :label="$t('模板来源')"
              >
                <TemplateSourceTabs
                  :value="activeIndex"
                  @change="handleCodeTypeChange"
                />
              </bk-form-item>
              <!-- 蓝鲸开发框架 -->
              <section v-show="isBkDevOps">
                <bk-form-item
                  error-display-type="normal"
                  ext-cls="form-item-cls mt10"
                >
                  <div class="flex-row justify-content-between">
                    <div class="bk-button-group">
                      <bk-button
                        v-for="(langItem, langName) in curLanguages"
                        :key="langName"
                        :class="language === langName ? 'is-selected' : ''"
                        @click="changeLanguage(langName)"
                      >
                        {{ $t(defaultlangName[langName]) }}
                      </bk-button>
                    </div>
                  </div>
                </bk-form-item>
                <div class="languages-card">
                  <bk-radio-group v-model="sourceInitTemplate">
                    <div
                      v-for="item in curLanguages[language] || []"
                      :key="item.name"
                      class="pb20"
                    >
                      <bk-radio :value="item.name">
                        <div class="languages-name pl5">
                          {{ item.display_name }}
                        </div>
                        <div class="languages-desc pl5">
                          {{ item.description }}
                        </div>
                      </bk-radio>
                    </div>
                  </bk-radio-group>
                </div>
              </section>
              <!-- 空模板 -->
              <div
                v-show="isEmptyTemplate"
                class="empty-template-container"
              >
                <bk-icon type="info-circle" />
                {{ $t('空模版：从零开始创建模块，适合需要完全自定义项目结构的场景。') }}
              </div>
            </bk-form>
          </div>

          <div
            v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP && curStep === 1"
            class="create-item"
            data-test-id="createDefault_item_appEngine"
          >
            <div class="item-title">{{ $t('源码管理') }}</div>

            <bk-form
              :label-width="100"
              class="from-content mt20"
            >
              <template v-if="codeRepositoryConfig.creationRepositories.length">
                <bk-form-item
                  :required="true"
                  :label="$t('仓库类型')"
                  ext-cls="form-item-cls"
                >
                  <bk-radio-group v-model="codeRepositoryConfig.type">
                    <bk-radio :value="'existing'">{{ $t('已有代码仓库') }}</bk-radio>
                    <bk-radio :value="'platform'">
                      {{ $t('新建代码仓库（由平台自动创建）') }}
                    </bk-radio>
                  </bk-radio-group>
                </bk-form-item>

                <!-- 新建代码仓库（由平台自动创建） -->
                <template v-if="isCreatedByPlatform">
                  <bk-form-item
                    :required="true"
                    :label="$t('代码源')"
                    ext-cls="form-item-cls mt20"
                  >
                    <CodeSourceSelector
                      :items="codeRepositoryConfig.creationRepositories"
                      :value="0"
                      selection-type="index"
                      :clickable="false"
                      :auto-select-single="true"
                    />
                  </bk-form-item>

                  <bk-form-item
                    v-if="gitExtendConfig[sourceControlType].isAuth"
                    :required="true"
                    :label="$t('代码仓库')"
                    ext-cls="form-item-cls mt20"
                  >
                    <PlatformCodeRepositoryForm
                      ref="newCodeRepositoryForm"
                      :app-id="curAppInfo.application?.code"
                      :module-name="formData.name"
                      :list="codeRepositoryConfig.creationRepositories"
                      :data="codeRepositoryConfig.formData"
                    ></PlatformCodeRepositoryForm>
                    <p
                      slot="tip"
                      class="g-tip"
                    >
                      {{ $t('将自动创建该私有仓库并完成模板代码初始化，当前用户默认为仓库管理员') }}
                    </p>
                  </bk-form-item>
                  <!-- 未授权提示 -->
                  <UnauthorizedTips
                    v-else
                    class="mt20"
                    :type="sourceControlType"
                    :data="gitExtendConfig[sourceControlType]"
                  />
                </template>
              </template>

              <template v-if="!isCreatedByPlatform">
                <bk-form-item
                  :required="true"
                  :label="$t('代码源')"
                  error-display-type="normal"
                  ext-cls="form-item-cls"
                >
                  <CodeSourceSelector
                    class="mb20"
                    :items="sourceControlTypes"
                    :value="sourceControlType"
                    selection-type="value"
                    @change="changeSourceControl"
                  />
                </bk-form-item>

                <!-- 已有代码仓库-构建方式 -->
                <bk-form-item
                  :required="true"
                  error-display-type="normal"
                  ext-cls="form-item-cls mt20 mb20"
                  :label="$t('构建方式')"
                >
                  <bk-radio-group
                    v-model="formData.buildMethod"
                    @change="handleChangeBuildMethod"
                  >
                    <bk-radio :value="'buildpack'">
                      {{ $t('蓝鲸 Buildpack') }}
                    </bk-radio>
                    <bk-radio
                      :value="'dockerfile'"
                      :disabled="!isDockerfileAllowed"
                      v-bk-tooltips="dockerfileDisabledTips"
                    >
                      Dockerfile
                    </bk-radio>
                  </bk-radio-group>
                </bk-form-item>

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
                    <bk-form-item
                      :label="$t('构建目录')"
                      error-display-type="normal"
                      ext-cls="form-item-cls mt20"
                    >
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
                    </bk-form-item>
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
                  :label-width="100"
                  :model="dockerfileData"
                  ref="dockerfileRef"
                  class="mt20"
                >
                  <bk-form-item
                    :label="$t('Dockerfile 路径')"
                    :rules="absolutePathRule"
                    :property="'dockerfilePath'"
                    error-display-type="normal"
                    ext-cls="form-item-cls"
                  >
                    <bk-input
                      v-model="dockerfileData.dockerfilePath"
                      class="form-input-width"
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
                    :label-width="100"
                    ext-cls="build-params-form"
                  >
                    <bk-form-item
                      :label="$t('构建参数')"
                      ext-cls="form-item-cls"
                    >
                      <div class="form-value-wrapper">
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
                                style="margin-left: 0"
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
                    </bk-form-item>
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
              </template>
            </bk-form>
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
            <img :src="createAppLoading" />
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
import { mapState } from 'vuex';
import { DEFAULT_APP_SOURCE_CONTROL_TYPES, DEFAULR_LANG_NAME } from '@/common/constants';
import { cloneDeep } from 'lodash';
import { encryptString } from '@/common/crypto';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import appPreloadMixin from '@/mixins/app-preload';
import collapseContent from './comps/collapse-content.vue';
import deployProcess from '@/views/dev-center/app/engine/cloud-deployment/deploy-process';
import deployHook from '@/views/dev-center/app/engine/cloud-deployment/deploy-hook';
import { TE_MIRROR_EXAMPLE } from '@/common/constants.js';
import ExamplesDirectory from '@/components/examples-directory';
import PlatformCodeRepositoryForm from '@/views/dev-center/create-app/comps/platform-code-repository-form.vue';
import CodeSourceSelector from '@/views/dev-center/create-app/comps/code-source-selector.vue';
import UnauthorizedTips from '@/views/dev-center/create-app/comps/unauthorized-tips.vue';
import TemplateSourceTabs from '@/views/dev-center/create-app/comps/template-source-tabs.vue';
import { TEMPLATE_SOURCE_TYPES } from '@/views/dev-center/create-app/comps/template-source-types';

export default {
  components: {
    gitExtend,
    repoInfo,
    collapseContent,
    deployProcess,
    deployHook,
    ExamplesDirectory,
    PlatformCodeRepositoryForm,
    CodeSourceSelector,
    UnauthorizedTips,
    TemplateSourceTabs,
  },
  mixins: [appPreloadMixin],
  data() {
    return {
      createAppLoading: require('@static/images/create-app-loading.svg'),
      formLoading: false,
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
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES,
      canCreateModule: true,

      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      activeIndex: TEMPLATE_SOURCE_TYPES.BK_DEVOPS,
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
            regex: /^(?:([a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*(?::\d+)?)\/)?(?:([a-zA-Z0-9_.-]+)\/)*([a-zA-Z0-9_.-]+)$/,
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
      // 仓库类型
      codeRepositoryConfig: {
        type: 'existing',
        creationRepositories: [],
        formData: {},
      },
    };
  },
  computed: {
    ...mapState('tenantConfig', ['encryptConfig']),
    region() {
      return this.curAppInfo.application.region;
    },
    curSourceControl() {
      const match = this.sourceControlTypes.find((item) => item.value === this.sourceControlType);
      return match;
    },
    createCloudAppData() {
      return this.$store.state.cloudApi.cloudAppData;
    },
    isShowAppTemplate() {
      return this.sourceOrigin !== this.GLOBAL.APP_TYPES.CNATIVE_IMAGE && this.curStep === 1;
    },
    isBkDevOps() {
      return this.activeIndex === TEMPLATE_SOURCE_TYPES.BK_DEVOPS;
    },
    isEmptyTemplate() {
      return this.activeIndex === TEMPLATE_SOURCE_TYPES.EMPTY_TEMPLATE;
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
    isCreatedByPlatform() {
      return this.codeRepositoryConfig.type === 'platform';
    },
    // 当前模板支持的构建方式类型
    supportedRuntimeTypes() {
      if (this.isEmptyTemplate) {
        return ['dockerfile'];
      }
      const currentTemplate = this.getCurrentTemplate();
      if (currentTemplate?.supported_runtime_types) {
        return currentTemplate.supported_runtime_types;
      }
      return ['buildpack'];
    },
    // 判断是否允许选择 Dockerfile 构建方式
    isDockerfileAllowed() {
      return this.supportedRuntimeTypes.includes('dockerfile');
    },
    dockerfileDisabledTips() {
      const templateDisplayName = this.getCurrentTemplate()?.display_name || this.$t('当前模板');
      return {
        content: `${templateDisplayName}${this.$t('暂不支持使用 Dockerfile 构建')}`,
        disabled: this.isDockerfileAllowed,
        placement: 'top',
      };
    },
  },
  watch: {
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
    supportedRuntimeTypes: {
      handler(value) {
        this.syncBuildMethodWithSupportedRuntimeTypes(value);
      },
      immediate: true,
    },
  },
  async created() {
    await this.fetchEncryptConfig();
    await this.fetchRegion();
    await this.getLanguageByRegion();
    await this.getCodeTypes();
    this.sourceInitTemplate = this.languages[this.language][0].name;
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
    // 获取加密配置
    async fetchEncryptConfig() {
      await this.$store.dispatch('tenantConfig/getEncryptConfig').catch((e) => this.catchErrorHandler(e));
    },

    handleCodeTypeChange(payload) {
      this.activeIndex = payload;
      if (payload === TEMPLATE_SOURCE_TYPES.EMPTY_TEMPLATE) {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP;
        this.sourceInitTemplate = '';
        this.formData.buildMethod = 'dockerfile';
        return;
      }
      this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP;
      this.curLanguages = cloneDeep(this.languages);
      this.language = 'Python';
      this.sourceInitTemplate = this.curLanguages[this.language]?.[0]?.name || '';
      this.syncBuildMethodWithSupportedRuntimeTypes();
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

    /**
     * 获取代码库类型
     */
    async getCodeTypes() {
      try {
        const { results = [] } = await this.$store.dispatch('module/getCodeTypes');
        this.sourceControlTypes = results;

        // 判断是否提供选择仓库类型
        this.codeRepositoryConfig.creationRepositories = results.filter((item) => item.repo_creation_enabled);

        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    /**
     * 根据应用类型获取支持的语言（内部、混合云...）
     * @return {[type]} [description]
     */
    async getLanguageByRegion() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');

        if (!res?.[this.region]) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('版本配置未找到，您没有创建模块权限。'),
          });
          return;
        }
        this.languages = res[this.region].languages;
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
      this.language = language;
      this.sourceInitTemplate = this.languages[this.language][0].name;
    },

    // 获取当前选中的模板信息
    getCurrentTemplate() {
      if (this.isEmptyTemplate) {
        return null;
      }
      const templates = this.curLanguages?.[this.language] || [];
      return templates.find((item) => item.name === this.sourceInitTemplate);
    },

    // 当前模板不支持已选构建方式时，自动回退到 Buildpack
    syncBuildMethodWithSupportedRuntimeTypes(runtimeTypes = this.supportedRuntimeTypes) {
      if (this.structureType !== 'soundCode') {
        return;
      }
      if (this.isEmptyTemplate) {
        this.formData.buildMethod = 'dockerfile';
        return;
      }
      if (!runtimeTypes.includes(this.formData.buildMethod)) {
        this.formData.buildMethod = 'buildpack';
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

    // 参数区分：已有代码仓库 / 由平台创建代码仓库
    getRepositoryParams(sourceRepoUrl) {
      if (this.isCreatedByPlatform) {
        return {
          auto_create_repo: true,
          write_template_to_repo: true,
          ...this.codeRepositoryConfig.formData,
        };
      }
      return {
        source_repo_url: sourceRepoUrl,
      };
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

      // 授权校验
      if (this.isCreatedByPlatform && !this.gitExtendConfig[this.sourceControlType].isAuth) {
        this.handlePrev();
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请先授权代码源'),
        });
        return;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && !this.isCreatedByPlatform) {
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
          source_origin: this.sourceOrigin,
          source_dir: this.sourceDirVal || '',
          ...this.getRepositoryParams(sourceRepoUrl), // 代码仓库参数
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
        if (!this.isEmptyTemplate) {
          delete params.source_config.source_init_template;
        }
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
          password: encryptString(this.repoData.password, this.encryptConfig),
        };
        params.source_config.source_dir = this.repoData.sourceDir;
      }

      // 由平台创建代码仓库过滤 source_repo_url
      if (this.sourceOrigin !== this.GLOBAL.APP_TYPES.NORMAL_APP || this.isCreatedByPlatform) {
        delete params.source_config.source_repo_url;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.CNATIVE_IMAGE) {
        // 仅镜像
        params.source_config = {
          source_repo_url: this.mirrorData.url,
          source_origin: this.sourceOrigin,
        };
      }

      if (this.isCreatedByPlatform) {
        params.source_config.write_template_to_repo = !!params.source_config?.source_init_template;
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
      // 获取新建代码仓库数据
      if (this.isCreatedByPlatform) {
        this.codeRepositoryConfig.formData = this.$refs.newCodeRepositoryForm?.getFromData();
      }
      // 构建目录
      if (this.sourceDirError) {
        return;
      }
      if (this.isDockerfile) {
        await this.$refs.dockerfileRef?.validate();
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

    handleSwitchCodeSource(type) {
      if (this.structureType === type) {
        return;
      }
      this.formData.buildMethod = 'buildpack';
      this.structureType = type;
    },

    handleChangeBuildMethod(value) {
      if (!this.supportedRuntimeTypes.includes(value)) {
        this.formData.buildMethod = this.supportedRuntimeTypes.includes('buildpack')
          ? 'buildpack'
          : this.supportedRuntimeTypes[0];
      }
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
}
.wrap .establish-title {
  text-align: left;
  padding-left: 24px;
  i {
    color: #3a84ff;
    font-size: 20px;
    transform: translateY(0px);
    cursor: pointer;
  }
}
.module-code-repo {
  /deep/ .bk-form .bk-label {
    padding-right: 18px;
  }
}
.form-item-title {
  color: #313238;
  font-size: 14px;
  font-weight: 600;
}
.from-content {
  padding: 0;
}
.form-item-cls {
  /deep/ .bk-label {
    width: 100px !important;
  }
}
.languages-card {
  background: #fafbfd;
  border-radius: 2px;
  padding: 20px 20px 0 20px;
  margin: 20px 0 0 100px;

  .languages-name {
    color: #63656e;
  }

  .languages-desc {
    color: #979ba5;
    font-size: 12px;
  }
}
.empty-template-container {
  margin-left: 100px;
  padding: 16px;
  border-radius: 2px;
  background: #fafbfd;
  color: #63656e;

  .bk-icon {
    color: #979ba5;
    margin-right: 4px;
  }
}
.tab-box {
  height: 56px;
  list-style: none;
  display: flex;
  padding: 0;

  .tab-item {
    flex: 1;
    margin-right: 16px;
    height: 56px;
    line-height: 56px;
    text-align: center;
    background: #f0f1f5;
    border-radius: 2px;
    font-size: 14px;
    color: #63656e;
    cursor: pointer;
    position: relative;

    &:last-of-type {
      margin-right: 0;
    }

    &.active {
      background: #fff;
      border: 2px solid #3a84ff;
      color: #3a84ff;

      @include border-active-logo;
    }
  }
}

.build-params-item {
  /deep/ .bk-form-content {
    margin-left: 0 !important;
  }
}
</style>
