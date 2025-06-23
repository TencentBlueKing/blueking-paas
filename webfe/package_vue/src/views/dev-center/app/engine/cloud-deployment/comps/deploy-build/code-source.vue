<template>
  <div class="code-main">
    <section class="source-code-info code-source">
      <div class="header-wrapper mb20">
        <span :class="['build-title', { edit: isCodeSourceEdit }]">{{ $t('源码信息') }}</span>
        <div
          class="edit-container"
          v-if="isShowEdit"
          @click="handleEdit"
        >
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>
      </div>

      <template v-if="isEmptyData">
        <!-- 查看态 -->
        <div
          class="content"
          v-if="!isCodeSourceEdit"
        >
          <div
            v-if="isCodeQuality"
            :class="['code-quality', { entry: codeDetails.rdIndicatorsScore }]"
            :style="isInitTemplate ? { height: '158px' } : ''"
            @click="handleToggleSideslider"
          >
            <div class="box">
              <p>
                <span class="fraction">{{ codeDetails.rdIndicatorsScore ?? '--' }}</span>
                {{ $t('分') }}
              </p>
              <p class="desc">{{ $t('代码质量') }}</p>
            </div>
            <div
              v-if="codeDetails.rdIndicatorsScore"
              class="code-inspection-entry"
            >
              {{ $t('代码检查') }}
              <i class="paasng-icon paasng-back"></i>
            </div>
          </div>
          <div class="code-detail form-edit">
            <bk-form :model="sourceCodeData">
              <bk-form-item :label="`${$t('代码源')}：`">
                <span class="form-text">{{ curAppModule.repo?.display_name || '--' }}</span>
                <a
                  v-if="sourceControlType === 'tc_git'"
                  :href="tcgitCopilotUrl"
                  target="_blank"
                  class="copilot-link"
                >
                  {{ `${$t('体验')}${$t('工蜂 Copilot')}` }}
                  <i class="paasng-icon paasng-jump-link"></i>
                </a>
              </bk-form-item>
              <bk-form-item :label="`${$t('代码仓库')}：`">
                <a
                  v-if="curAppModule.repo?.repo_url"
                  class="form-text code-link"
                  :href="curAppModule.repo?.repo_url"
                  target="_blank"
                >
                  {{ curAppModule.repo?.repo_url }}
                </a>
                <template v-else>--</template>
              </bk-form-item>
              <bk-form-item :label="`${$t('构建目录')}：`">
                <span class="form-text">{{ curAppModule.repo?.source_dir || '--' }}</span>
              </bk-form-item>
              <bk-form-item
                :label="`${$t('初始化模板')}：`"
                v-if="isInitTemplate"
              >
                <span class="form-text">{{ curAppModule.template_display_name || '--' }}</span>
                <a
                  v-if="!curAppModule.repo?.linked_to_internal_svn && initTemplateDesc !== '--'"
                  class="download"
                  href="javascript: void(0);"
                  @click="handleDownloadTemplate"
                >
                  <i class="paasng-icon paasng-download"></i>
                  {{ $t('下载') }}
                </a>
              </bk-form-item>
            </bk-form>
          </div>
        </div>

        <!-- 编辑态 -->
        <div
          class="content no-border"
          v-else
        >
          <section class="code-depot">
            <label class="form-label">
              {{ $t('代码源') }}
            </label>
            <div
              v-for="(item, index) in sourceControlTypes"
              :key="index"
              :class="[
                'code-depot-item mr10',
                { on: item.value === sourceControlType },
                { disabled: sourceControlDisabled && item.value === 'bk_svn' },
              ]"
              @click="changeSourceControl(item.value)"
            >
              <img :src="'/static/images/' + item.imgSrc + '.png'" />
              <p
                class="source-control-title"
                :title="item.name"
              >
                {{ item.name }}
              </p>
            </div>
          </section>

          <!-- Git 相关额外代码 start -->
          <template v-if="sourceOrigin === GLOBAL.APP_TYPES.NORMAL_APP">
            <div v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
              <!-- 代码仓库 -->
              <git-extend
                :key="sourceControlType"
                :label-width="150"
                :git-control-type="sourceControlType"
                :is-auth="gitExtendConfig[sourceControlType].isAuth"
                :is-loading="gitExtendConfig[sourceControlType].isLoading"
                :auth-docs="gitExtendConfig[sourceControlType].authDocs"
                :alert-text="gitExtendConfig[sourceControlType].alertText"
                :auth-address="gitExtendConfig[sourceControlType].authAddress"
                :fetch-method="gitExtendConfig[sourceControlType].fetchMethod"
                :repo-list="gitExtendConfig[sourceControlType].repoList"
                :selected-repo-url.sync="gitExtendConfig[sourceControlType].selectedRepoUrl"
                @change="changeSelectedRepoUrl"
              />
              <!-- 构建目录 -->
              <div
                class="form-group-dir"
                style="margin-top: 10px"
              >
                <label class="form-label optional">
                  {{ $t('构建目录') }}
                </label>
                <div class="form-group-flex">
                  <div>
                    <bk-input
                      v-model="sourceControlChangeForm.sourceDir"
                      class="source-dir"
                      :class="isSourceDirInvalid ? 'error' : ''"
                      :placeholder="$t('请输入应用所在子目录，并确保 app_desc.yaml 文件在该目录下，不填则默认为根目录')"
                    />
                    <ul
                      v-if="isSourceDirInvalid"
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
            </div>
            <repo-info
              v-if="curSourceControl && curSourceControl.auth_method === 'basic'"
              ref="repoInfo"
              :key="sourceControlType"
              :type="sourceControlType"
              :default-url="curAppModule.repo?.trunk_url"
              :default-account="curAppModule.repo_auth_info?.username"
              :default-dir="curAppModule.repo?.source_dir"
              :deployment-is-show="true"
              :source-dir-label="'构建目录'"
              :is-cloud-created="true"
              @change="handleRepoInfoChange"
            />
          </template>

          <div class="footer-operate">
            <bk-button
              :theme="'primary'"
              class="mr10"
              :loading="switchLoading"
              @click="sureSwitch"
            >
              {{ $t('保存') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handleCancel"
              class="mr10"
            >
              {{ $t('取消') }}
            </bk-button>
          </div>
        </div>
      </template>

      <!-- 空数据状态 -->
      <bk-exception
        v-if="!isCodeSourceEdit && !curAppModule.repo?.repo_url"
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        <p
          class="mt10"
          style="color: #63656e; font-size: 14px"
        >
          {{ $t('暂未绑定源码信息') }}
        </p>
        <p
          class="mt10"
          style="color: #979ba5; font-size: 12px"
        >
          {{ $t('源码仓库仅用于 Homepage 运维开发分数统计，请瑞雪填写') }}
        </p>
        <p
          class="guide-link mt15"
          @click="handleEdit"
        >
          {{ $t('立即绑定') }}
        </p>
      </bk-exception>
    </section>

    <!-- 代码检查 -->
    <bk-sideslider
      :is-show.sync="defaultSettings.isShow"
      :width="960"
      :quick-close="true"
    >
      <div slot="header">{{ defaultSettings.title }}</div>
      <div
        class="p20 sideslider-content"
        slot="content"
      >
        <bk-alert
          type="info"
          v-if="!isDeploy"
        >
          <div slot="title">
            {{ $t('该模块未部署，没有执行过代码检查。') }}
          </div>
        </bk-alert>
        <code-inspection :code-details="codeDetails" />
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import gitExtend from '@/components/ui/git-extend';
import repoInfo from '@/components/ui/repo-info.vue';
import codeInspection from './code-inspection.vue';
import { DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import { fileDownload } from '@/common/utils';
import appBaseMixin from '@/mixins/app-base-mixin';
import dayjs from 'dayjs';

export default {
  components: {
    codeInspection,
    gitExtend,
    repoInfo,
  },
  mixins: [appBaseMixin],
  props: {
    buildMethod: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      isCodeSourceEdit: false,
      sourceCodeData: {},
      defaultSettings: {
        isShow: false,
        title: this.$t('代码检查'),
      },
      // 代码检查
      codeDetails: {},
      switchLoading: false,
      // 编辑态数据
      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      // 当前代码源
      sourceControlType: this.GLOBAL.DEFAULT_SOURCE_CONTROL,
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES,
      sourceDirVal: '',
      sourceDirError: false,
      // 配置
      sourceControlChangeForm: {
        sourceRepoUrl: '',
        // 部署目录
        sourceDir: '',
      },
      initTemplateDesc: '',
      initTemplateType: '',
      gitExtendConfig: {
        // 蓝鲸 gitlab
        bk_gitlab: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // 工蜂
        tc_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('tc_git'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // github
        github: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('github'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // gitee
        gitee: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('gitee'),
          repoList: [],
          selectedRepoUrl: '',
          sourceDir: '',
          authDocs: '',
        },
        // SVN 代码库
        bare_svn: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
        // Git 代码库
        bare_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          selectedRepoUrl: '',
          authInfo: {
            account: '',
            password: '',
          },
          sourceDir: '',
        },
      },
    };
  },

  computed: {
    curSourceControl() {
      const match = this.sourceControlTypes.find((item) => item.value === this.sourceControlType);
      return match;
    },
    // 部署目录校验
    isSourceDirInvalid() {
      if (this.sourceControlChangeForm.sourceDir === '') {
        return false;
      }
      return !/^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/.test(this.sourceControlChangeForm.sourceDir);
    },
    sourceControlDisabled() {
      return this.curAppModule.repo && this.curAppModule.repo.type !== 'bk_svn';
    },
    // 代码检查无数据为未部署
    isDeploy() {
      return Object.keys(this.codeDetails).length;
    },
    isInitTemplate() {
      return this.buildMethod === 'buildpack';
    },
    isCodeQuality() {
      return this.curAppInfo.feature?.CODE_CHECK;
    },
    isEmptyData() {
      return this.isCodeSourceEdit ? this.isCodeSourceEdit : this.curAppModule.repo?.repo_url;
    },
    isShowEdit() {
      return !this.isCodeSourceEdit ? this.isEmptyData : false;
    },
    tcgitCopilotUrl() {
      return window.BK_TCGIT_COPILOT_URL;
    },
  },

  created() {
    this.init();
  },

  methods: {
    async init() {
      // 获取模块基本信息
      await Promise.all([this.fetchModuleInfo(), this.fetchAccountAllowSourceControlType()]);
      await this.fetchLanguageInfo();
      // 获取代码检查详情
      this.getCodeInspection();

      const sourceControlTypes = this.sourceControlTypes.map((e) => e.value);
      // 初始化 repo List
      for (const key in this.gitExtendConfig) {
        const config = this.gitExtendConfig[key];
        sourceControlTypes.includes(key) && config.fetchMethod && config.fetchMethod();
        // 设置默认值
        if (this.curAppModule.repo?.type === key) {
          this.changeSourceControl(key);
        }
      }
      this.$nextTick(() => {
        this.$emit('close-content-loader');
      });
    },

    // 获取代码源列表
    async fetchAccountAllowSourceControlType() {
      try {
        const sourceControlTypes = await this.$store.dispatch('fetchAccountAllowSourceControlType', {});
        // 代码源列表
        this.sourceControlTypes = sourceControlTypes;
        // bare_svn 单独处理
        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 代码检查
    async getCodeInspection() {
      try {
        const details = await this.$store.dispatch('deploy/getCodeInspection', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        if (Object.keys(details).length) {
          details.lastAnalysisTime = dayjs(details.lastAnalysisTime).format('YYYY-MM-DD HH:mm:ss');
          for (const key in details) {
            if (key.endsWith('Score') && !Number.isInteger(details[key])) {
              // 保留两位小数
              details[key] = details[key]?.toFixed(2);
            }
          }
          this.codeDetails = details;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取对应的RepoList
    generateFetchRepoListMethod(sourceControlType) {
      // 根据不同的 sourceControlType 生成对应的 fetchRepoList 方法
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

    // 切换代码源
    changeSourceControl(sourceControlType) {
      // bk svn禁止切换
      if (sourceControlType === 'bk_svn' && this.sourceControlDisabled) {
        return;
      }
      // 高亮切换
      this.sourceControlType = sourceControlType;
      // 当前代码源配置
      const config = this.gitExtendConfig[sourceControlType];

      if (!this.curAppModule.repo) {
        this.sourceControlChangeForm.sourceRepoUrl = '';
        this.sourceControlChangeForm.sourceDir = '';
      } else {
        if (sourceControlType === this.curAppModule.repo.type) {
          if (config) {
            // 设置 selectedRepoUrl 仓库地址
            config.selectedRepoUrl = this.curAppModule.repo.trunk_url;
          }
          this.sourceControlChangeForm.sourceRepoUrl = this.curAppModule.repo.trunk_url;
          this.sourceControlChangeForm.sourceDir = this.curAppModule.repo.source_dir;
        } else {
          this.sourceControlChangeForm.sourceRepoUrl = this.gitExtendConfig[sourceControlType].sourceDir;
          this.sourceControlChangeForm.sourceDir = '';
        }
      }
    },

    // 取消重置
    resetSourceType() {
      // repo 为空重置当前状态
      if (!this.curAppModule.repo) {
        this.sourceControlType = this.GLOBAL.DEFAULT_SOURCE_CONTROL;
        this.gitExtendConfig[this.sourceControlType].selectedRepoUrl = '';
        this.sourceControlChangeForm.sourceRepoUrl = '';
        this.sourceControlChangeForm.sourceDir = '';
        return;
      }
      if (
        this.curAppModule?.source_origin === 1 ||
        this.curAppModule?.source_origin === this.GLOBAL.APP_TYPES.SCENE_APP
      ) {
        this.sourceControlType = this.curAppModule.repo.type;
        this.sourceControlChangeForm.sourceRepoUrl = this.curAppModule.repo.trunk_url;
        this.sourceControlChangeForm.sourceDir = this.curAppModule.repo.source_dir;

        if (this.curAppModule.repo.type !== 'bk_svn') {
          const match = this.gitExtendConfig[this.sourceControlType];
          match.selectedRepoUrl = this.curAppModule.repo.trunk_url || '';
          match.sourceDir = this.curAppModule.repo.source_dir || '';
          if (match.authInfo) {
            match.authInfo.account = this.curAppModule.repo_auth_info.username;
            match.authInfo.password = '';
          }
        }
      }
    },

    handleRepoInfoChange(data) {
      const match = this.gitExtendConfig[this.sourceControlType];

      this.sourceControlChangeForm.sourceRepoUrl = data.url;
      this.sourceControlChangeForm.sourceDir = data.sourceDir;

      match.selectedRepoUrl = data.url;
      match.authInfo = {
        account: data.account,
        password: data.password,
      };
      match.sourceDir = data.sourceDir;
    },

    changeSelectedRepoUrl(url) {
      this.sourceControlChangeForm.sourceRepoUrl = url;
    },

    sureSwitch() {
      const config = this.gitExtendConfig[this.sourceControlType];
      let sourceRepoUrl = config.selectedRepoUrl;
      switch (this.sourceControlType) {
        case 'bk_gitlab':
        case 'github':
        case 'gitee':
        case 'tc_git':
          if (!sourceRepoUrl) {
            this.$paasMessage({
              theme: 'error',
              message: config.isAuth ? this.$t('请选择关联的远程仓库') : this.$t('请关联 git 账号'),
            });
            return;
          }
          break;
        case 'bare_svn':
        case 'bare_git':
          // eslint-disable-next-line no-case-declarations
          const repoData = this.$refs.repoInfo.getData();
          if (!repoData.url) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入源代码地址'),
            });
            return;
          }
          if (!repoData.account) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入账号'),
            });
            return;
          }
          if (!repoData.password) {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请输入密码'),
            });
            return;
          }

          break;
        case 'bk_svn':
        default:
          sourceRepoUrl = undefined;
          break;
      }
      // 发送请求
      this.sureSwitchRepo();
    },

    // 切换代码源仓库
    async sureSwitchRepo() {
      if (this.switchLoading) {
        return false;
      }

      const config = this.gitExtendConfig[this.sourceControlType];

      try {
        this.switchLoading = true;
        const params = {
          appCode: this.appCode,
          modelName: this.curModuleId,
          data: {
            source_control_type: this.sourceControlType,
            source_repo_url: this.sourceControlChangeForm.sourceRepoUrl || config.selectedRepoUrl,
            source_dir: this.sourceControlChangeForm.sourceDir,
          },
        };

        if (config && config.authInfo) {
          params.data.source_repo_auth_info = {
            username: config.authInfo.account,
            password: config.authInfo.password,
          };
        }

        if (this.curAppModule?.source_origin === this.GLOBAL.APP_TYPES.IMAGE) {
          params.data.source_control_type = 'tc_docker';
          params.data.source_repo_url = `${this.GLOBAL.CONFIG.MIRROR_PREFIX}${this.mirrorData.url}`;
          params.data.source_repo_auth_info = {
            username: '',
            password: '',
          };
        }

        const res = await this.$store.dispatch('module/switchRepo', params);
        if (res.repo_type === 'tc_docker') {
          this.$paasMessage({
            theme: 'success',
            message: res.message,
          });
        } else {
          if (this.sourceControlType === 'bk_svn') {
            ['bare_git', 'tc_git'].forEach((item) => {
              this.gitExtendConfig[item].selectedRepoUrl = '';
            });
          } else {
            if (this.sourceControlType === 'bk_gitlab') {
              this.gitExtendConfig.tc_git.selectedRepoUrl = '';
            } else {
              this.gitExtendConfig.bk_gitlab.selectedRepoUrl = '';
            }
          }
          this.$paasMessage({
            theme: 'success',
            message: this.$t('修改源码信息成功'),
          });
        }
        await this.fetchModuleInfo();
        this.isCodeSourceEdit = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.switchLoading = false;
      }
    },

    // 获取当前应用基本信息
    async fetchModuleInfo() {
      try {
        await this.$store.dispatch('getAppInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.initTemplateType = this.curAppModule.template_display_name;

        if (
          this.curAppModule?.source_origin === 1 ||
          this.curAppModule?.source_origin === this.GLOBAL.APP_TYPES.SCENE_APP
        ) {
          const { repo } = this.curAppModule;
          if (repo) {
            this.sourceControlType = repo.type;
            this.sourceControlChangeForm.sourceRepoUrl = repo.trunk_url;
            this.sourceControlChangeForm.sourceDir = repo.source_dir;
            if (repo.type !== 'bk_svn' && this.gitExtendConfig[repo.type]) {
              this.gitExtendConfig[repo.type].selectedRepoUrl = repo.trunk_url;
              this.gitExtendConfig[repo.type].sourceDir = repo.source_dir || '';
            }
            if (['bare_svn', 'bare_git'].includes(repo.type)) {
              this.gitExtendConfig[repo.type].authInfo.account = this.curAppModule.repo_auth_info.username;
              this.gitExtendConfig[repo.type].authInfo.password = '';
              this.gitExtendConfig[repo.type].sourceDir = repo.source_dir || '';
            }
          }
        }
      } catch (res) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async fetchLanguageInfo() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        const { region } = this.curAppModule;

        this.initTemplateDesc = '';
        const initLanguage = this.curAppModule?.language;
        if (res[region] && res[region].languages) {
          const languages = res[region].languages[initLanguage] || [];
          const lanObj = languages.find((item) => item.display_name === this.initTemplateType) || {};
          this.initTemplateDesc = lanObj.description || '--';
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.detail || res.message || this.$t('接口异常'),
        });
      }
    },

    handleEdit() {
      this.isCodeSourceEdit = true;
    },

    // 重置
    handleCancel() {
      this.resetSourceType();
      this.isCodeSourceEdit = false;
    },

    handleToggleSideslider() {
      this.defaultSettings.isShow = true;
    },

    // 下载初始化模板
    async handleDownloadTemplate() {
      try {
        const res = await this.$store.dispatch('getAppInitTemplateUrl', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        fileDownload(res.downloadable_address);
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: resp.detail || this.$t('服务暂不可用，请稍后再试'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/border-active-logo.scss';

.code-main {
  position: relative;

  & > section {
    padding-bottom: 24px;
    border-bottom: 1px solid #eaebf0;
    margin-bottom: 24px;
  }

  :deep(.bk-label-text) {
    color: #63656e;
  }

  :deep(.bk-form-content) {
    color: #313238;
  }

  :deep(.bk-sideslider-content) {
    background: #f5f7fa;
  }

  :deep(.bk-alert) {
    margin-bottom: 16px;
  }

  .button-edit {
    position: absolute;
    right: 0;
    top: 0;
  }

  .form-group {
    display: flex;
  }

  .code-detail {
    .code-link {
      color: #3a84ff;
    }
    .copilot-link {
      margin-left: 10px;
      i {
        font-size: 16px;
      }
    }
  }

  .form-group-dir {
    display: flex;
    align-items: center;

    .form-label {
      transform: translateY(5px);
    }
  }
}

.source-code-info.code-source {
  width: 100%;
}

.source-code-info .content {
  display: flex;

  :deep(.bk-form-item + .bk-form-item) {
    margin-top: 10px;
  }

  :deep(.code-repo) {
    .bk-label {
      width: 150px !important;
    }
    .bk-form-content {
      margin-left: 150px !important;
    }
  }
}

.content.no-border {
  display: block;

  :deep(.form-label) {
    width: 150px;
  }
}

:deep(.establish-tab) #shorter-loading-animate .form-label {
  width: 130px !important;
  margin-right: 20px;
}

.mirror-info {
  :deep(.bk-form-item + .bk-form-item) {
    margin-top: 10px;
  }
}

.build-title {
  position: relative;
  font-weight: 700;
  font-size: 14px;
  color: #313238;
  &.edit::after {
    content: '*';
    height: 8px;
    line-height: 1;
    color: #ea3636;
    font-size: 12px;
    position: absolute;
    display: inline-block;
    vertical-align: middle;
    top: 50%;
    transform: translate(3px, -50%);
  }
}

.code-quality {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 190px;
  background: #f5f7fa;
  border-radius: 2px;
  text-align: center;
  cursor: pointer;

  &.entry:hover {
    background: #f0f1f5;
  }

  .fraction {
    font-size: 30px;
    color: #313238;
  }

  .desc {
    margin-top: 8px;
    font-size: 14px;
    color: #00000099;
  }

  .box {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .code-inspection-entry {
    width: 100%;
    height: 32px;
    line-height: 32px;
    font-size: 12px;
    color: #3a84ff;
    background: #e1ecff;
    border-radius: 0 0 2px 2px;
    i {
      color: #3a84ff;
      transform: rotate(180deg) translateY(1px);
    }
  }
}

.sideslider-content {
  :deep(.bk-alert-wraper) {
    align-items: center;
  }
}

/* 代码源 */
.code-source {
  position: relative;
  width: 1160px;

  .form-label {
    width: 150px;
    min-height: 32px;
    text-align: right;
    vertical-align: middle;
    line-height: 32px;
    float: left;
    font-size: 14px;
    font-weight: 400;
    color: #63656e;
    padding: 0 24px 0 0;
    box-sizing: border-box;
  }

  .code-depot {
    display: flex;
    margin: 20px 0;

    &-item {
      width: 134px;
      height: 88px;
      background: #f0f1f5;
      border-radius: 2px;
      text-align: center;
      position: relative;
      cursor: pointer;

      img {
        width: 40px;
        height: 36px;
        margin: 12px 0 6px 0;
      }
    }

    .on {
      border: solid 2px #3a84ff;
      background-color: #fff;
      color: #3a84ff;
      @include border-active-logo;
    }

    .disabled {
      color: #c4c6cc;
      cursor: not-allowed;

      span {
        color: #c4c6cc;
      }
    }
  }
}

.form-group {
  display: flex;

  &-flex {
    width: 520px;
    margin-top: 10px;
  }

  &-radio {
    display: flex;
    align-items: center;
    margin-top: 3px;
  }
}

.footer-operate {
  margin-top: 24px;
  margin-left: 150px;
}

.download {
  cursor: pointer;
  color: #3a84ff;
  margin-left: 10px;
  i {
    font-size: 16px;
  }
}
</style>
<style lang="scss">
.form-group-flex .source-dir.error .bk-input-text {
  input {
    border-color: #ff3737 !important;
  }
}
</style>
