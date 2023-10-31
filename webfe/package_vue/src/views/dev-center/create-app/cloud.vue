<template>
  <div class="cloud-app-container" v-bkloading="{ isLoading: formLoading, opacity: 1 }">
    <bk-alert
      class="mb20 mt20" type="info"
      :title="$t('基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力')"></bk-alert>
    <bk-form
      ref="formBaseRef"
      :model="formData"
      :rules="rules"
      :label-width="100"
      class="from-content"
    >
      <div class="form-item-title mb10">
        {{ $t('基本信息') }}
      </div>
      <bk-form-item
        :required="true"
        :property="'code'"
        :rules="rules.code"
        error-display-type="normal"
        ext-cls="form-item-cls"
        :label="$t('应用 ID')"
      >
        <bk-input
          v-model="formData.code"
          :placeholder="$t('由小写字母、数字、连字符（-）组成，首字母必须是字母，长度小于16个字符')"
          class="form-input-width"
        >
        </bk-input>
        <p slot="tip" class="input-tips">
          {{ $t('应用的唯一标识，创建后不可修改') }}
        </p>
      </bk-form-item>
      <bk-form-item
        :required="true"
        :property="'name'"
        :rules="rules.name"
        error-display-type="normal"
        ext-cls="form-item-cls mt20"
        :label="$t('应用名称')"
      >
        <bk-input
          v-model="formData.name"
          :placeholder="$t('由汉字、英文字母、数字组成，长度小于 20 个字符')"
          class="form-input-width"
        >
        </bk-input>
      </bk-form-item>

      <bk-form-item
        :required="true"
        error-display-type="normal"
        ext-cls="form-item-cls mt20"
        :label="$t('托管方式')"
      >
        <div class="mt5">
          <bk-radio-group
            v-model="formData.sourceOrigin"
            class="construction-manner"
          >
            <bk-radio :value="'soundCode'" v-if="userFeature.ENABLE_DEPLOY_CNATIVE_APP_FROM_CODE">
              {{ $t('源代码') }}
            </bk-radio>
            <bk-radio :value="'image'">
              {{ $t('仅镜像') }}
            </bk-radio>
          </bk-radio-group>
        </div>
      </bk-form-item>

      <!-- 构建方式 -->
      <bk-form-item
        v-if="formData.sourceOrigin === 'soundCode'"
        :required="true"
        error-display-type="normal"
        ext-cls="form-item-cls mt20"
        :label="$t('构建方式')"
      >
        <div class="mt5">
          <bk-radio-group
            v-model="formData.buildMethod"
            class="construction-manner"
          >
            <bk-radio :value="'buildpack'">
              {{ $t('蓝鲸 Buildpack') }}
            </bk-radio>
            <!-- <bk-radio :value="'dockerfile'">
              {{ $t('Dockerfile 构建') }}
            </bk-radio> -->
          </bk-radio-group>
        </div>
      </bk-form-item>
    </bk-form>

    <bk-steps ext-cls="step-cls" :steps="createSteps" :cur-step.sync="curStep"></bk-steps>

    <section v-if="formData.sourceOrigin === 'image' && curStep === 1">
      <!-- 镜像管理 -->
      <bk-form
        ref="formImageRef"
        :model="formData"
        :rules="rules"
        :label-width="100"
        class="from-content mt20"
      >
        <div class="form-item-title mb10">
          {{ $t('镜像信息') }}
        </div>
        <bk-form-item
          :required="true"
          :property="'url'"
          error-display-type="normal"
          ext-cls="form-item-cls"
          :label="$t('镜像仓库')"
        >
          <bk-input
            v-model="formData.url"
            class="form-input-width"
            clearable
            :placeholder="$t('示例镜像：mirrors.tencent.com/bkpaas/django-helloworld')"
          >

            <template slot="append">
              <div
                class="group-text form-text-append"
                @click="handleSetMirrorUrl"
              >{{$t('使用示例镜像')}}</div>
            </template>
          </bk-input>
          <span slot="tip" class="input-tips">{{ $t('镜像应监听“容器端口“处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>
        </bk-form-item>
        <bk-form-item
          error-display-type="normal"
          ext-cls="form-item-cls"
          :label="$t('镜像凭证')"
        >
          <div class="flex-row form-input-width">
            <bk-input
              class="mr10"
              v-model="formData.imageCredentialName"
              clearable
              :placeholder="$t('请输入名称，如 default')"
            >
            </bk-input>
            <bk-input
              class="mr10"
              v-model="formData.imageCredentialUserName"
              clearable
              :placeholder="$t('请输入账号')"
            >
            </bk-input>
            <bk-input
              type="password"
              v-model="formData.imageCredentialPassWord"
              clearable
              :placeholder="$t('请输入密码')"
            >
            </bk-input>
          </div>
          <p slot="tip" class="input-tips">{{ $t('私有镜像需要填写镜像凭证才能拉取镜像') }}</p>
        </bk-form-item>
      </bk-form>
    </section>

    <section v-if="curStep === 1">
      <template v-if="formData.sourceOrigin === 'soundCode'">
        <bk-form
          v-if="formData.buildMethod === 'buildpack'"
          ref="formModuleRef"
          :model="formData"
          :rules="rules"
          :label-width="100"
          class="from-content mt20"
        >
          <div class="form-item-title mb10">
            {{ $t('应用模版') }}
          </div>
          <bk-form-item
            error-display-type="normal"
            ext-cls="form-item-cls"
            :label="$t('模版来源')"
          >
            <div>{{ $t('蓝鲸开发框架') }}</div>
          </bk-form-item>
          <bk-form-item
            error-display-type="normal"
            ext-cls="form-item-cls mt10"
          >
            <div class="flex-row justify-content-between">
              <div class="bk-button-group">
                <bk-button
                  v-for="(item, key) in languagesData"
                  :key="key"
                  :class="buttonActive === key ? 'is-selected' : ''"
                  @click="handleSelected(item, key)"
                >
                  {{ $t(defaultlangName[key]) }}
                </bk-button>
              </div>
              <div class="build-info" @click="showBuildDialog">
                <i class="row-icon paasng-icon paasng-page-fill"></i>
                {{ $t('构建信息') }}
              </div>
            </div>
          </bk-form-item>
          <div class="languages-card">
            <bk-radio-group v-model="formData.sourceInitTemplate">
              <div v-for="(item) in languagesList" :key="item.name" class="pb20">
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
        </bk-form>


        <bk-form
          ref="formSourceRef"
          :model="formData"
          :rules="rules"
          :label-width="100"
          class="from-content mt20"
        >
          <div class="form-item-title mb10">
            {{ $t('源码管理') }}
          </div>

          <bk-form-item
            :required="true"
            :label="$t('代码源')"
            :rules="rules.name"
            error-display-type="normal"
            ext-cls="form-item-cls mt20"
          >
            <div class="flex-row align-items-center code-depot mb20">
              <div
                v-for="(item, index) in sourceControlTypes"
                :key="index"
                :class="['code-depot-item mr10', { 'on': item.value === sourceControlTypeItem }]"
                @click="changeSourceControl(item)"
              >
                <img :src="'/static/images/' + item.imgSrc + '.png'">
                <div
                  class="source-control-title"
                  :title="item.name"
                >
                  {{ item.name }}
                </div>
              </div>
            </div>
          </bk-form-item>
          <section v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
            <git-extend
              ref="extend"
              :key="sourceControlTypeItem"
              :git-control-type="sourceControlTypeItem"
              :is-auth="gitExtendConfig[sourceControlTypeItem].isAuth"
              :is-loading="gitExtendConfig[sourceControlTypeItem].isLoading"
              :alert-text="gitExtendConfig[sourceControlTypeItem].alertText"
              :auth-address="gitExtendConfig[sourceControlTypeItem].authAddress"
              :auth-docs="gitExtendConfig[sourceControlTypeItem].authDocs"
              :fetch-method="gitExtendConfig[sourceControlTypeItem].fetchMethod"
              :repo-list="gitExtendConfig[sourceControlTypeItem].repoList"
              :selected-repo-url.sync="gitExtendConfig[sourceControlTypeItem].selectedRepoUrl"
            />

            <bk-form-item
              :label="$t('构建目录')"
              error-display-type="normal"
              ext-cls="form-item-cls mt20"
            >
              <div class="flex-row align-items-center code-depot">
                <bk-input
                  v-model="formData.buildDir"
                  class="form-input-width"
                  :placeholder="$t('请输入应用所在子目录，并确保 app_desc.yaml 文件在该目录下，不填则默认为根目录')"
                />
              </div>
            </bk-form-item>
          </section>

          <section v-if="curSourceControl && curSourceControl.auth_method === 'basic'">
            <repo-info
              ref="repoInfo"
              :key="sourceControlTypeItem"
              :type="sourceControlTypeItem"
              :source-dir-label="'构建目录'"
              :is-cloud-created="true"
            />
          </section>

          <!-- Dockerfile 构建 -->
          <template v-if="formData.buildMethod === 'dockerfile'">
            <bk-form-item
              :label="$t('Dockerfile 路径')"
              :property="'dockerfile_path'"
              error-display-type="normal"
              ext-cls="form-dockerfile-cls mt20"
            >
              <div class="flex-row align-items-center code-depot">
                <bk-input
                  v-model="dockerfileData.dockerfilePath"
                  class="form-input-width"
                  :placeholder="$t('相对于构建目录的路径，若留空，默认为构建目录下名为 “Dockerfile” 的文件')"
                />
              </div>
            </bk-form-item>

            <bk-form
              :model="dockerfileData"
              form-type="vertical"
              ext-cls="build-params-form">
              <div class="form-label">
                {{$t('构建参数')}}
              </div>
              <div class="form-value-wrapper">
                <bk-button
                  v-if="!dockerfileData.buildParams.length"
                  :text="true"
                  title="primary"
                  @click="addBuildParams">
                  <i class="paasng-icon paasng-plus-thick" />
                  {{ $t('新建构建参数') }}
                </bk-button>
                <template v-if="dockerfileData.buildParams.length">
                  <div class="build-params-header">
                    <div class="name">{{$t('参数名')}}</div>
                    <div class="value">{{$t('参数值')}}</div>
                  </div>
                  <div
                    v-for="(item, index) in dockerfileData.buildParams"
                    class="build-params-item"
                    :key="index">
                    <bk-form :ref="`name-${index}`" :model="item">
                      <bk-form-item :rules="rules.buildParams" :property="'name'">
                        <bk-input v-model="item.name" :placeholder="$t('参数名')"></bk-input>
                      </bk-form-item>
                    </bk-form>
                    <span class="equal">=</span>
                    <bk-form :ref="`value-${index}`" :model="item">
                      <bk-form-item :rules="rules.buildParams" :property="'value'">
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
              @click="addBuildParams">
              <i class="paasng-icon paasng-plus-thick" />
              {{ $t('新建构建参数') }}
            </bk-button>
          </template>
        </bk-form>
      </template>

      <bk-form
        v-if="isAdvancedOptions"
        ref="formSourceRef"
        :model="formData"
        :rules="rules"
        :label-width="100"
        class="from-content mt20"
      >
        <div class="form-item-title">
          {{ $t('高级选项') }}
        </div>

        <bk-form-item
          :label="$t('选择集群')"
          error-display-type="normal"
          ext-cls="form-item-cls mt20"
        >
          <bk-select
            v-model="formData.clusterName"
            class="form-input-width"
            searchable
          >
            <bk-option
              v-for="option in clusterList"
              :id="option"
              :key="option"
              :name="option"
            />
          </bk-select>
        </bk-form-item>
      </bk-form>
    </section>

    <!-- 源码&镜像 部署配置内容 -->
    <div class="mt20" v-if="formData.sourceOrigin === 'soundCode' && curStep === 2">
      <collapseContent :title="$t('进程配置')" collapse-item-name="process" active-name="process">
        <bk-alert
          type="info">
          <div slot="title">
            {{ $t('进程名和启动命令在构建目录下的 app_desc.yaml 文件中定义。') }}
            <a
              target="_blank"
              :href="GLOBAL.DOC.APP_PROCESS_INTRODUCTION"
              style="color: #3a84ff">
              {{$t('应用进程介绍')}}
            </a>
          </div>
        </bk-alert>
      </collapseContent>

      <collapseContent :title="$t('钩子命令')" class="mt20" :fold="false">
        <bk-alert
          type="info">
          <div slot="title">
            {{ $t('钩子命令在构建目录下的 app_desc.yaml 文件中定义。') }}
            <a
              target="_blank"
              :href="GLOBAL.DOC.BUILD_PHASE_HOOK"
              style="color: #3a84ff">
              {{$t('部署阶段钩子')}}
            </a>
          </div>
        </bk-alert>
      </collapseContent>
    </div>


    <div class="mt20" v-if="formData.sourceOrigin === 'image' && curStep === 2">
      <!-- 默认展开为编辑态 -->
      <collapseContent
        active-name="process"
        collapse-item-name="process"
        :title="$t('进程配置')"
      >
        <deploy-process ref="processRef" :cloud-app-data="initCloudAppData" :is-create="isCreate"></deploy-process>
      </collapseContent>

      <collapseContent
        active-name="hook"
        collapse-item-name="hook"
        :title="$t('钩子命令')"
        class="mt20"
      >
        <deploy-hook ref="hookRef" :cloud-app-data="cloudAppData" :is-create="isCreate"></deploy-hook>
      </collapseContent>
    </div>


    <div class="mt20 flex-row">
      <!-- :disabled="" -->
      <div class="mr20" v-if="curStep === 1">
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
          class="ml20 mr20"
          :loading="formLoading"
          @click="handleCreateApp"
        >
          {{ $t('创建应用') }}
        </bk-button>
      </div>
      <bk-button @click="handleCancel">
        {{ $t('取消') }}
      </bk-button>
    </div>

    <!-- 构建信息弹窗 -->
    <bk-dialog
      v-model="buildDialog.visiable"
      width="720"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="true"
      :show-footer="false"
      :title="buildDialog.title"
    >
      <bk-form
        :model="buildDialog.formData"
        :label-width="130">
        <bk-form-item :label="$t('镜像仓库：')">
          <span class="build-text">
            {{ imageRepositoryTemplate }}
          </span>
        </bk-form-item>
        <bk-form-item :label="$t('镜像 tag 规则：')">
          {{ mirrorTag }}
        </bk-form-item>
        <bk-form-item :label="$t('构建方式：')">
          {{ buildDialog.formData.buildMethod }}
        </bk-form-item>
        <bk-form-item :label="$t('基础镜像：')">
          {{ buildDialog.formData.imageName }}
        </bk-form-item>
        <bk-form-item :label="$t('构建工具：')">
          <p
            class="config-item" v-for="item in buildDialog.formData.buildConfig"
            :key="item.id"
            v-bk-tooltips="`${item.display_name}${item.description ? (item.description) : ''}`">
            {{ item.display_name }} {{ item.description ? (item.description) : '' }}
          </p>
        </bk-form-item>
      </bk-form>
    </bk-dialog>
  </div>
</template>
<script>import { DEFAULR_LANG_NAME, DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import _ from 'lodash';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import collapseContent from '@/views/dev-center/app/create-cloud-module/comps/collapse-content.vue';
import deployProcess from '@/views/dev-center/app/engine/cloud-deployment/deploy-process-creat';
import deployHook from '@/views/dev-center/app/engine/cloud-deployment/deploy-hook-creat';
import { TAG_MAP } from '@/common/constants.js';
export default {
  components: {
    gitExtend,
    repoInfo,
    collapseContent,
    deployProcess,
    deployHook,
  },
  data() {
    return {
      formData: {
        name: '',   // 应用名称
        code: '',   // 应用ID
        url: '',    // 镜像仓库
        clusterName: '', // 集群名称
        sourceOrigin: 'soundCode',  // 托管方式
        sourceInitTemplate: '', // 模版来源
        buildDir: '',   // 构建目录
        sourceRepoUrl: '',   // 代码仓库
        imageCredentialName: '', // 镜像名称
        imageCredentialUserName: '', // 镜像账号
        imageCredentialPassWord: '', // 镜像密码
        buildMethod: 'buildpack', // 构建方式
      },
      dockerfileData: {
        dockerfilePath: '', // Dockerfile 路径
        buildParams: [], // 构建参数
      },
      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      createSteps: [{ title: this.$t('源码信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }],
      curStep: 1,
      buttonActive: '',
      languagesData: {},
      defaultlangName: DEFAULR_LANG_NAME, // 开发框架语言
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES, // 源码代码仓库
      sourceControlTypeItem: this.GLOBAL.DEFAULT_SOURCE_CONTROL,
      languagesList: [],
      sourceDirData: {
        error: '',
        value: '',
      },
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
      isCreate: true,
      localCloudAppData: {},
      repoData: {}, // svn代码库
      cloudAppProcessData: {
        image: '',
        name: 'web',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        targetPort: 5000,
      },
      initCloudAppData: {},
      formLoading: false,
      advancedOptionsObj: {},
      regionChoose: 'ieod',
      bkPluginConfig: {},
      rules: {
        code: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 16,
            message: this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
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
              const reg = /^[a-z][a-z0-9-]{3,16}$/;
              return reg.test(val);
            },
            message: this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
        ],
        name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 20,
            message: this.$t('请输入 1-20 字符的字母、数字、汉字'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-zA-Z\d\u4e00-\u9fa5]*$/;
              return reg.test(val);
            },
            message: this.$t('格式不正确，只能包含：汉字、英文字母、数字，长度小于 20 个字符'),
            trigger: 'blur',
          },
        ],
        buildDir: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/;
              return reg.test(val);
            },
            message: this.$t('支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头'),
            trigger: 'blur',
          },
        ],
        url: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*\/)*[a-z0-9]+(?:[._-][a-z0-9]+)*$/,
            message: this.$t('请输入不包含标签(tag)的镜像仓库地址'),
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
      buildDialog: {
        visiable: false,
        title: this.$t('构建信息'),
        formData: {},
      },
    };
  },
  computed: {
    curSourceControl() {
      return this.sourceControlTypes.find(item => item.value === this.sourceControlTypeItem);
    },
    cloudAppData() {
      return this.$store.state.cloudApi.cloudAppData;
    },
    clusterList() {
      return this.advancedOptionsObj[this.regionChoose] || [];
    },
    imageRepositoryTemplate() {
      if (!this.buildDialog.formData.imageRepositoryTemplate) return '';
      let imageRepositoryTemplate = this.buildDialog.formData.imageRepositoryTemplate
        .replace('{app_code}', this.formData.code);
      if (imageRepositoryTemplate.includes('//')) {
        imageRepositoryTemplate = imageRepositoryTemplate.replace('//', '/');
      }
      return imageRepositoryTemplate.replace('{module_name}', 'default');
    },
    mirrorTag() {
      const tagOptions = this.buildDialog.formData?.tagOptions || {};
      const tagStrList = [];
      for (const key in tagOptions) {
        console.log('tagOptions[key]', tagOptions[key]);
        if (tagOptions[key] && key !== 'prefix') {
          tagStrList.push(TAG_MAP[key]);
        }
      }
      if (tagOptions.prefix) {
        tagStrList.unshift(tagOptions.prefix);
      }
      return tagStrList.join('-');
    },
    userFeature() {
      return this.$store.state.userFeature;
    },
    isAdvancedOptions() {
      return this.$store.state.createApp.isAdvancedOptions;
    },
  },
  watch: {
    'formData.sourceOrigin'(value) {
      this.curStep = 1;
      if (value === 'image') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.CNATIVE_IMAGE; // 6 仅镜像的云原生应用
        this.createSteps = [{ title: this.$t('镜像信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }];
      } else if (value === 'soundCode') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP; // 1
        this.createSteps = [{ title: this.$t('源码信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }];
      }
      this.$refs.formImageRef?.clearError();
    },

    cloudAppData: {
      handler(value) {
        if (!Object.keys(value).length) {  // 没有应用编排数据
          this.initCloudAppDataFunc();
        }
      },
      immediate: true,
    },

    'formData.code'(value) {
      if (!this.initCloudAppData.metadata) {
        this.initCloudAppData.metadata = {};
      }
      // 如果有cloudAppData 则将cloudAppData赋值给initCloudAppData
      if (Object.keys(this.cloudAppData).length) {
        this.initCloudAppData = _.cloneDeep(this.cloudAppData);
      }
      this.initCloudAppData.metadata.name = value;
      this.localCloudAppData = _.cloneDeep(this.initCloudAppData);

      this.$store.commit('cloudApi/updateCloudAppData', this.initCloudAppData);
    },
  },
  mounted() {
    this.formData.sourceOrigin = this.userFeature.ENABLE_DEPLOY_CNATIVE_APP_FROM_CODE ? 'soundCode' : 'image';
    this.init();
  },
  methods: {
    init() {
      this.fetchLanguageInfo();
      this.fetchSourceControlTypesData();
      this.fetchAdvancedOptions();
    },
    handleSelected(item, key) {
      this.buttonActive = key;
      this.languagesList = item;
      this.formData.sourceInitTemplate = this.languagesList[0].name;
    },

    // 获取模版来源
    async fetchLanguageInfo() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        const regionChoose = Object.keys(res) || [];
        this.regionChoose = regionChoose[0] || 'ieod';
        this.languagesData = res[this.regionChoose].languages;
        const languagesKeysData = Object.keys(this.languagesData) || [];
        this.buttonActive = languagesKeysData[0] || 'Python';
        this.languagesList = this.languagesData[this.buttonActive];
        this.formData.sourceInitTemplate = this.languagesList[0].name;
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      } finally {
        this.isLoading = false;
      }
    },

    // 获取代码源仓库信息
    fetchSourceControlTypesData() {
      this.$store.dispatch('fetchAccountAllowSourceControlType', {}).then((res) => {
        this.sourceControlTypes = res;
        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });
        const sourceControlTypeValues = this.sourceControlTypes.map(item => item.value);
        sourceControlTypeValues.forEach((item) => {
          if (!Object.keys(this.gitExtendConfig).includes(item)) {
            this.$set(this.gitExtendConfig, item, _.cloneDeep({
              isAuth: true,
              isLoading: false,
              alertText: '',
              authAddress: undefined,
              fetchMethod: this.generateFetchRepoListMethod(item),
              repoList: [],
              selectedRepoUrl: '',
            }));
          }
        });
        // 在这几种类型里面需要请求
        Object.keys(this.gitExtendConfig).forEach((key) => {
          const config = this.gitExtendConfig[key];
          if (key === this.sourceControlTypeItem && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlTypeItem)) {
            config.fetchMethod();
          }
        });
      });
    },

    // 获取高级选项 集群列表
    async fetchAdvancedOptions() {
      let res;
      try {
        res = await this.$store.dispatch('createApp/getOptions');
      } catch (e) {
        // 请求接口报错时则不显示高级选项
        this.isShowAdvancedOptions = false;
        return;
      }

      // 初始化蓝鲸插件相关配置
      (res.bk_plugin_configs || []).forEach((c) => {
        this.bkPluginConfig[c.region] = c;
      });

      // 如果返回当前用户不支持“高级选项”，停止后续处理
      if (!res.allow_adv_options) {
        this.isShowAdvancedOptions = false;
        return;
      }

      // 高级选项：解析分 Region 的集群信息
      this.isShowAdvancedOptions = true;
      const advancedRegionClusters = res.adv_region_clusters || [];
      advancedRegionClusters.forEach((item) => {
        // eslint-disable-next-line no-prototype-builtins
        if (!this.advancedOptionsObj.hasOwnProperty(item.region)) {
          this.$set(this.advancedOptionsObj, item.region, item.cluster_names);
        }
      });
    },


    generateFetchRepoListMethod(sourceControlTypeItem) {
      // 根据不同的 sourceControlTypeItem 生成对应的 fetchRepoList 方法
      return async () => {
        const config = this.gitExtendConfig[sourceControlTypeItem];
        try {
          config.isLoading = true;
          const resp = await this.$store.dispatch('getRepoList', { sourceControlType: sourceControlTypeItem });
          config.repoList = resp.results.map(repo => ({ name: repo.fullname, id: repo.http_url_to_repo }));
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

    // 点击源码仓库
    changeSourceControl(item) {
      this.sourceDirData.error = false;
      this.sourceDirData.value = '';
      this.sourceControlTypeItem = item.value;
      console.log('this.sourceControlTypeItem', this.sourceControlTypeItem);
      const curGitConfig = this.gitExtendConfig[this.sourceControlTypeItem];
      if (curGitConfig && curGitConfig.repoList.length < 1 && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlTypeItem)) {
        curGitConfig.fetchMethod();
      }
    },

    // 下一步按钮
    async handleNext() {
      try {
        await this.$refs.formBaseRef.validate();
        await this.$refs?.formImageRef?.validate();
        await this.$refs?.repoInfo?.valid();
        // 构建参数校验
        const flag = await this.buildParamsValidate();
        if (!flag) {
          return;
        }
        if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP) {  // 普通应用
          await this.$refs?.extend?.valid();    // 代码仓库
          this.formData.sourceRepoUrl = null;
          switch (this.sourceControlTypeItem) {
            case 'bk_gitlab':
            case 'github':
            case 'gitee':
            case 'tc_git':
              // eslint-disable-next-line no-case-declarations
              const config = this.gitExtendConfig[this.sourceControlTypeItem];
              this.formData.sourceRepoUrl = config.selectedRepoUrl;

              break;
            case 'bk_svn':
            default:
              this.formData.sourceRepoUrl = undefined;
              break;
          }
        }
        this.repoData = this.$refs?.repoInfo?.getData();
        this.initCloudAppDataFunc();   // 初始化应用编排数据
        this.curStep = 2;
        this.$nextTick(() => {
          // 默认编辑态
          this.$refs.processRef?.handleEditClick();
          this.$refs.hookRef?.handleEditClick();
        });
        // if (this.structureType === 'mirror') {
        //   this.getProcessData();
        // }
      } catch (error) {
        console.log(error);
      }
    },

    // 上一步
    handlePrev() {
      this.curStep = 1;
    },

    // 处理取消
    handleCancel() {
      this.$refs?.processRef?.handleCancel();
      this.initCloudAppData = _.cloneDeep(this.localCloudAppData);
      this.$store.commit('cloudApi/updateHookPageEdit', false);
      this.$store.commit('cloudApi/updateProcessPageEdit', false);
      this.$router.push({
        name: 'myApplications',
      });
    },

    // 钩子命令校验
    async handleHookValidator() {
      if (this.$refs.hookRef) {
        return await this.$refs.hookRef?.handleValidator();
      }
      return true;
    },

    // 创建应用
    async handleCreateApp() {
      if (this.cloudAppData.spec?.hooks) {
        const isVerificationPassed = await this.handleHookValidator();
        if (!isVerificationPassed) {
          return;
        }
      }

      this.formLoading = true;
      const params = {
        region: this.regionChoose,
        code: this.formData.code,
        name: this.formData.name,
        source_config: {
          source_init_template: this.formData.sourceInitTemplate,
          source_control_type: this.sourceControlTypeItem,
          source_repo_url: this.formData.sourceRepoUrl,
          source_origin: this.sourceOrigin,
          source_dir: this.formData.buildDir || '',
        },
        // 构建方式
        build_config: {
          build_method: this.formData.buildMethod,
        },
      };

      // dockerfile 构建方式
      if (this.formData.buildMethod === 'dockerfile') {
        // 构建参数
        const dockerBuild = {};
        this.dockerfileData.buildParams.forEach((item) => {
          dockerBuild[item.name] = item.value;
        });
        if (this.dockerfileData.dockerfilePath === '') {
          this.dockerfileData.dockerfilePath = null;
        }
        params.build_config = {
          build_method: 'dockerfile',
          dockerfile_path: this.dockerfileData.dockerfilePath,
          docker_build_args: dockerBuild,
        };
      }

      // 仅镜像
      if (this.formData.sourceOrigin === 'image') {
        params.build_config = {
          build_method: 'custom_image',
        };
      }

      // 集群名称
      if (this.formData.clusterName) {
        params.advanced_options = {
          cluster_name: this.formData.clusterName,
        };
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP && ['bare_git', 'bare_svn'].includes(this.sourceControlTypeItem)) {
        params.source_config.source_repo_url = this.repoData.url;
        params.source_config.source_repo_auth_info = {
          username: this.repoData.account,
          password: this.repoData.password,
        };
        params.source_config.source_dir = this.repoData.sourceDir;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.CNATIVE_IMAGE) {  // 仅镜像
        params.source_config = {
          source_origin: this.sourceOrigin,
        };
        // 镜像凭证任意有一个值都需要image_credentials字段，如果都没有这不需要此字段
        if (this.formData.imageCredentialName || this.formData.imageCredentialUserName
        || this.formData.imageCredentialPassWord) {
          params.image_credentials = {};
        }
        // 仅镜像需要镜像凭证信息
        if (this.formData.imageCredentialName) {
          params.image_credentials.name = this.formData.imageCredentialName;
        }
        if (this.formData.imageCredentialUserName) {
          params.image_credentials.username = this.formData.imageCredentialUserName;
        }
        if (this.formData.imageCredentialPassWord) {
          params.image_credentials.password = this.formData.imageCredentialPassWord;
        }
        params.manifest = {
          ...this.cloudAppData,
        };
        params.source_config.source_repo_url = this.formData.url;   // 镜像
      }

      // 过滤空值容器端口
      if (params.manifest?.spec) {
        params.manifest.spec.processes = params.manifest.spec.processes.map((process) => {
          const { targetPort, ...processValue } = process;
          return (targetPort === '' || targetPort === null) ? processValue : process;
        });
      }

      try {
        const res = await this.$store.dispatch('cloudApi/createCloudApp', {
          appCode: this.appCode,
          data: params,
        });

        const objectKey = `CloundSourceInitResult${Math.random().toString(36)}`;
        if (res.source_init_result) {
          localStorage.setItem(objectKey, JSON.stringify(res.source_init_result.extra_info));
        }

        const path = `/developer-center/apps/${res.application.code}/create/${this.sourceControlTypeItem}/success`;
        this.$router.push({
          path,
          query: {
            objectKey,
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


    // 处理应用示例填充
    handleSetMirrorUrl() {
      this.formData.url = 'mirrors.tencent.com/bkpaas/django-helloworld';
      this.$refs.formImageRef.clearError();
    },

    // 初始化应用编排数据
    initCloudAppDataFunc() {
      this.initCloudAppData = {
        apiVersion: 'paas.bk.tencent.com/v1alpha2',
        kind: 'BkApp',
        metadata: { name: this.formData.code },
        spec: {
          build: {
            image: this.formData.url.trim(),  // 镜像信息-镜像仓库
            imageCredentialsName: this.formData.imageCredentialName, // 镜像信息-镜像凭证-名称
          },
          processes: [this.cloudAppProcessData],
        },
      };
      this.localCloudAppData = _.cloneDeep(this.initCloudAppData);
      this.$store.commit('cloudApi/updateCloudAppData', this.initCloudAppData);
    },

    // 获取构建信息
    async showBuildDialog() {
      try {
        const res = await this.$store.dispatch('cloudApi/getBuildDataInfo', {
          appCode: this.appCode,
          tplTyp: 'normal',
          region: this.regionChoose,
          tplName: this.formData.sourceInitTemplate,
        });
        this.buildDialog.visiable = true;
        this.buildDialog.formData = {
          imageRepositoryTemplate: res.build_config.image_repository_template,    // 镜像仓库
          tagOptions: res.build_config.tag_options,   // tag规则
          buildMethod: res.build_config.build_method,  // 构建方式
          imageName: `${res.slugbuilder.display_name}（${res.slugbuilder.description}）`,
          buildConfig: res.build_config.buildpacks,
        };
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 构建参数校验
    async buildParamsValidate() {
      let flag = true;
      if (!this.dockerfileData.buildParams.length) {
        return flag;
      }
      for (const index in this.dockerfileData.buildParams) {
        try {
          await this.$refs[`name-${index}`][0]?.validate()
            .finally(async () => {
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
  },
};
</script>
<style lang="scss" scoped>
@import "./cloud.scss";
</style>
