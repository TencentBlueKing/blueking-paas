<template>
  <div class="cloud-app-container">
    <bk-alert
      class="mb20 mt20" type="info"
      :title="$t('基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力。')"></bk-alert>
    <bk-form
      ref="formBaseRef"
      :model="formData"
      :rules="rules"
      :label-width="100"
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
        <p class="input-tips">
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
          :placeholder="$t('由小写英文字母、下划线或数字组成，长度小于16个字符')"
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
            <bk-radio :value="'soundCode'">
              {{ $t('源码&镜像') }}
            </bk-radio>
            <bk-radio :value="'image'">
              {{ $t('仅镜像') }}
            </bk-radio>
          </bk-radio-group>
        </div>
      </bk-form-item>
    </bk-form>

    <bk-steps ext-cls="step-cls" :steps="createSteps" :cur-step.sync="curStep"></bk-steps>


    <section v-if="formData.sourceOrigin === 'soundCode' && curStep === 1">
      <bk-form
        ref="formModuleRef"
        :model="formData"
        :rules="rules"
        :label-width="100"
      >
        <div class="form-item-title mb10 mt10">
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
          :required="true"
          :property="'code'"
          :rules="rules.name"
          error-display-type="normal"
          ext-cls="form-item-cls mt20"
        >
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
      >
        <div class="form-item-title mb10 mt10">
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
                :placeholder="$t('请输入应用所在子目录，并确保 Procfile 文件在该目录下，不填则默认为根目录')"
              />
            </div>
          </bk-form-item>
        </section>

        <section class="" v-if="curSourceControl && curSourceControl.auth_method === 'basic'">
          <repo-info
            ref="repoInfo"
            :key="sourceControlTypeItem"
            :type="sourceControlTypeItem"
          />
        </section>
      </bk-form>
    </section>

    <section v-if="formData.sourceOrigin === 'image' && curStep === 1">

      <!-- 镜像管理 -->
      <bk-form
        ref="formImageRef"
        :model="formData"
        :rules="rules"
        :label-width="100"
      >
        <div class="form-item-title">
          {{ $t('源码管理') }}
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
            style="width: 520px;"
            clearable
            :placeholder="$t('示例镜像：mirrors.tencent.com/bkpaas/django-helloworld')"
          >

            <template slot="append">
              <div
                class="group-text form-text-append"
                @click="handleSetMirrorUrl"
              >应用示例</div>
            </template>
          </bk-input>
          <span class="input-tips">{{ $t('镜像应监听“容器端口“处所指定的端口号，或环境变量值 $PORT 来提供 HTTP服务。') }}</span>
        </bk-form-item>
      </bk-form>
    </section>

    <!-- 源码&镜像 部署配置内容 -->
    <div class="mt20" v-if="formData.sourceOrigin === 'soundCode' && curStep === 2">
      <collapseContent :title="$t('进程配置')">
        <bk-alert
          type="info">
          <div slot="title">
            {{ $t('进程名和启动命令在构建目录下的 bkapp.yaml 文件中定义。') }}
            <a
              target="_blank" :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/bkapp'"
              style="color: #3a84ff">
              {{$t('应用进程介绍')}}
            </a>
          </div>
        </bk-alert>
      </collapseContent>

      <collapseContent :title="$t('钩子命令')" class="mt20">
        <bk-alert
          type="info">
          <div slot="title">
            {{ $t('钩子命令的 bkapp.yaml 文件中定义。') }}
            <a
              target="_blank" :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/bkapp'"
              style="color: #3a84ff">
              {{$t('应用进程介绍')}}
            </a>
          </div>
        </bk-alert>
      </collapseContent>
    </div>


    <div class="mt20" v-if="formData.sourceOrigin === 'image' && curStep === 2">
      <collapseContent :title="$t('进程配置')">
        <deploy-process ref="processRef" :cloud-app-data="cloudAppData" :is-create="isCreate"></deploy-process>
      </collapseContent>

      <collapseContent :title="$t('钩子命令')" class="mt20">
        <deploy-hook :cloud-app-data="cloudAppData" :is-create="isCreate"></deploy-hook>
      </collapseContent>
    </div>


    <div class="form-btn flex-row">
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
          @click="handleCreateApp"
        >
          {{ $t('提交') }}
        </bk-button>
      </div>
      <bk-button @click="handleCancel">
        {{ $t('取消') }}
      </bk-button>
    </div>
  </div>
</template>
<script>import { DEFAULR_LANG_NAME, DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import _ from 'lodash';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import collapseContent from '@/views/dev-center/app/create-module/comps/collapse-content.vue';
import deployProcess from '@/views/dev-center/app/engine/cloud-deployment/deploy-process';
import deployHook from '@/views/dev-center/app/engine/cloud-deployment/deploy-hook';
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
        url: '',
        name: '',
        code: '',
        sourceOrigin: 'soundCode',
        sourceInitTemplate: '',
        buildDir: '',
      },
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
      cloudAppData: {},
      isCreate: true,
      localCloudAppData: {},
      rules: {
        code: [
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
            message: '格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母',
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-z][a-z0-9-]{3,16}$/;
              return reg.test(val);
            },
            message: '请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头',
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
            validator(val) {
              const reg = /^[a-z][a-z0-9-]*$/;
              return reg.test(val);
            },
            message: '格式不正确，只能包含：小写字母、数字、连字符(-)，首字母必须是字母',
            trigger: 'blur',
          },
          {
            validator(val) {
              const reg = /^[a-z][a-z0-9-]{1,16}$/;
              return reg.test(val);
            },
            message: '由小写字母和数字以及连接符(-)组成，不能超过 16 个字符',
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
            message: '支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头',
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    curSourceControl() {
      return this.sourceControlTypes.find(item => item.value === this.sourceControlTypeItem);
    },
  },
  watch: {
    'formData.sourceOrigin'(value) {
      if (value === 'image') {
        this.sourceOrigin = 4;
        this.createSteps = [{ title: this.$t('镜像信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }];
      } else if (value === 'soundCode') {
        this.createSteps = [{ title: this.$t('源码信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }];
      }
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    init() {
      this.fetchLanguageInfo();
      this.fetchSourceControlTypesData();
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
        this.languagesData = res.ieod.languages;
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
        console.log('this.sourceControlTypes', this.sourceControlTypes);
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
        await this.$refs?.repoInfo?.valid();
        this.curStep = 2;
        // if (this.structureType === 'mirror') {
        //   this.getProcessData();
        // }
      } catch (error) {

      }
    },

    // 上一步
    handlePrev() {
      this.curStep = 1;
    },

    // 处理取消
    handleCancel() {
      // this.$refs?.processRef?.handleCancel();
      // this.cloudAppData = _.cloneDeep(this.localCloudAppData);
      // this.$store.commit('cloudApi/updateHookPageEdit', false);
      // this.$store.commit('cloudApi/updateProcessPageEdit', false);
    },


    // 创建应用
    handleCreateApp() {
      console.log(1);
    },


    // 处理应用示例填充
    handleSetMirrorUrl() {
      this.formData.url = 'mirrors.tencent.com/bkpaas/django-helloworld';
      this.$refs.formImageRef.clearError();
    },
  },
};
</script>
<style lang="scss" scoped>
 @import "./cloud.scss";
</style>
