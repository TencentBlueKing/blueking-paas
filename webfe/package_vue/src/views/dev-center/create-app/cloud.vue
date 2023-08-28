<template>
  <div class="cloud-app-container">
    <bk-alert
      class="mb20 mt20" type="info"
      :title="$t('基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力。')"></bk-alert>
    <bk-form
      ref="formRef"
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
        :rules="rules.name"
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
        :property="'code'"
        :rules="rules.name"
        error-display-type="normal"
        ext-cls="form-item-cls mt20"
        :label="$t('应用名称')"
      >
        <bk-input
          v-model="formData.code"
          :placeholder="$t('由小写英文字母、下划线或数字组成，长度小于16个字符')"
          class="form-input-width"
        >
        </bk-input>
      </bk-form-item>

      <bk-form-item
        :required="true"
        :property="'code'"
        :rules="rules.name"
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

    <bk-form
      ref="formRef"
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
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-width="100"
    >
      <div class="form-item-title mb10 mt10">
        {{ $t('源码管理') }}
      </div>

      <bk-form-item
        :required="true"
        :property="$t('代码源')"
        :rules="rules.name"
        error-display-type="normal"
        ext-cls="form-item-cls mt20"
      >
        <div class="flex-row align-items-center">
          <div
            v-for="(item, index) in sourceControlTypes"
            :key="index"
            :class="['code-depot-item mr10', { 'on': item.value === sourceControlTypeItem }]"
            @click="changeSourceControl(item)"
          >
            <img :src="'/static/images/' + item.imgSrc + '.png'">
            <p
              class="source-control-title"
              :title="item.name"
            >
              {{ item.name }}
            </p>
          </div>
        </div>
      </bk-form-item>
    </bk-form>
  </div>
</template>
<script>
import { DEFAULR_LANG_NAME, DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import _ from 'lodash';
export default {
  data() {
    return {
      formData: {
        name: '',
        code: '',
        sourceOrigin: 'soundCode',
        sourceInitTemplate: '',
      },
      createSteps: [{ title: this.$t('源码信息'), icon: 1 }, { title: this.$t('部署配置'), icon: 2 }],
      curStep: 1,
      buttonActive: '',
      languagesData: {},
      defaultlangName: DEFAULR_LANG_NAME, // 开发框架语言
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES, // 源码代码仓库
      sourceControlTypeItem: '',
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
      },
    };
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

    // 获取代码源仓库信心
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
        for (const key in this.gitExtendConfig) {
          // 初始化 repo List
          const config = this.gitExtendConfig[key];
          if (key === this.sourceControlType && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlType)) {
            config.fetchMethod();
          }
        }
      });
    },


    generateFetchRepoListMethod(sourceControlType) {
      // 根据不同的 sourceControlType 生成对应的 fetchRepoList 方法
      return async () => {
        const config = this.gitExtendConfig[sourceControlType];
        try {
          config.isLoading = true;
          const resp = await this.$store.dispatch('getRepoList', { sourceControlType });
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
      // const curGitConfig = this.gitExtendConfig[this.sourceControlType];
      // if (curGitConfig && curGitConfig.repoList.length < 1 && ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlType)) {
      //   curGitConfig.fetchMethod();
      // }
    },
  },
};
</script>
<style lang="scss" scoped>
 @import "./cloud.scss";
</style>
