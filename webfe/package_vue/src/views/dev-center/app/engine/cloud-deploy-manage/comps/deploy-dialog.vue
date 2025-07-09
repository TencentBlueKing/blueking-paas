<template>
  <div class="deploy-dialog-container">
    <bk-dialog
      v-model="deployAppDialog.visiable"
      width="520"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :auto-close="false"
      @after-leave="handleAfterLeave"
    >
      <template #header>
        <div class="dialog-header-wrapper">
          {{ $t('模块部署') }}
          <div class="module-name-tag">{{ curAppModule.name || '--' }}</div>
        </div>
      </template>

      <template #footer>
        <div class="dialog-footer-wrapper">
          <span v-bk-tooltips="{ content: $t('部署前置条件检查中'), disabled: deployButtonTipsDisable }">
            <bk-button
              :theme="'primary'"
              :loading="deployAppDialog.isLoading"
              :disabled="deployAppDialog.disabled || deploybuttonDisabled"
              @click="handleConfirmValidate"
              class="mr10"
            >
              {{ `${$t('部署至')}${environment === 'stag' ? $t('预发布环境') : $t('生产环境')}` }}
            </bk-button>
          </span>
          <bk-button
            :theme="'default'"
            @click="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </template>

      <!-- 部署限制 -->
      <section
        v-if="isShowErrorAlert.deploy"
        class="customize-alert-wrapper mb12"
      >
        <p class="text">
          <i class="paasng-icon paasng-remind exclamation-cls"></i>
          <span>{{ deployErrorData?.message }}</span>
        </p>
        <div class="right-link">
          <bk-button
            class="link-text"
            :text="true"
            @click="handleFixPreparation(deployErrorData)"
          >
            {{ $t('立即处理') }}
            <i class="paasng-icon paasng-jump-link" />
          </bk-button>
          <div class="line"></div>
          <bk-button
            class="link-text"
            :text="true"
            @click="getDeployPreparations('deploy')"
          >
            {{ $t('刷新') }}
            <i
              class="paasng-icon paasng-refresh-line"
              v-if="!deployRefreshLoading"
            />
            <round-loading
              class="round-loading-cls"
              v-else
            />
          </bk-button>
        </div>
      </section>

      <!-- 镜像逻辑，排除smart应用 -->
      <div v-if="deploymentInfoBackUp?.build_method === 'custom_image' && !isSmartApp">
        <!-- allowMultipleImage 为false 代表可以需要自己选择一条tag -->
        <div v-if="!allowMultipleImage">
          <div
            class="code-depot mb15"
            v-bk-overflow-tips="{ content: deploymentInfoBackUp.repo_url }"
          >
            <span>{{ $t('镜像仓库') }}：</span>
            {{ deploymentInfoBackUp.repo_url }}
          </div>
          <div>
            <bk-form
              :model="tagData"
              ref="imageFormRef"
              form-type="vertical"
            >
              <bk-form-item
                :label="$t('镜像Tag')"
                :rules="rules.tag"
                :required="true"
                :property="'tagValue'"
                :error-display-type="'normal'"
                ext-cls="image-tag-cls"
              >
                <div
                  v-if="tagUrl"
                  class="image-list version-code"
                  @click="handleOpenUrl(tagUrl)"
                >
                  {{ $t('查看镜像Tag列表') }}
                </div>
                <bk-input
                  v-if="tagUrl"
                  v-model="tagData.tagValue"
                  :placeholder="$t('请输入镜像Tag，如 latest')"
                  clearable
                />
                <bk-select
                  v-else
                  v-model="tagData.tagValue"
                  :placeholder="$t('请选择下拉数据或手动填写')"
                  style="width: 470px; display: inline-block; vertical-align: middle"
                  :popover-min-width="420"
                  :clearable="false"
                  searchable
                  :search-placeholder="$t('请输入关键字搜索或在上面输入框中手动填写')"
                  :disabled="!!errorTips"
                  :loading="isTagLoading"
                  allow-create
                >
                  <bk-option
                    v-for="option in customImageTagList"
                    :id="option.name"
                    :key="option.name"
                    :name="option.name"
                  />
                </bk-select>
                <span
                  v-if="errorTips"
                  class="error-text"
                >
                  {{ errorTips }}
                </span>
              </bk-form-item>
            </bk-form>
          </div>
        </div>
        <div v-else>
          <div>{{ $t('请确认模块下进程对应的镜像地址') }}</div>
          <div
            class="mt10"
            v-for="item in processesData"
            :key="item.name"
          >
            <span class="name">{{ item.name }}：</span>
            <span class="value">{{ item.image }}</span>
          </div>
        </div>
      </div>

      <!-- 源码逻辑 && smartApp -->
      <div v-else>
        <template v-if="!isSmartApp">
          <div
            v-if="deploymentInfoBackUp.repo_url"
            class="code-depot mb10"
            v-bk-overflow-tips="{ content: deploymentInfoBackUp.repo_url }"
          >
            <span>{{ $t('代码仓库') }}：</span>
            {{ deploymentInfoBackUp.repo_url }}
          </div>
          <div class="image-source">
            <div class="mb10">
              <div>
                {{ $t('镜像来源') }}
              </div>
            </div>
            <div class="bk-button-group btn-container">
              <bk-button
                v-for="item in imageSourceData"
                :key="item.value"
                class="btn-item"
                :class="buttonActive === item.value ? 'is-selected' : ''"
                @click="handleSelected(item)"
              >
                {{ $t(item.label) }}
              </bk-button>
            </div>
            <p
              class="tips"
              v-if="deploymentInfoBackUp?.activeImageSource"
            >
              <i class="paasng-icon paasng-info-line"></i>
              {{ $t('将跳过代码构建阶段，仅发布环境变量等应用配置的变更') }}
            </p>
          </div>
        </template>
        <div
          v-if="buttonActive === 'branch' || isSmartApp"
          :class="['image-source', { mt20: !isSmartApp }]"
        >
          <div class="mb10 flex-row justify-content-between">
            <div>{{ isSmartApp ? $t('版本') : $t('代码分支选择') }}</div>
            <!-- smartAPP 不展示，代码版本差异 -->
            <bk-button
              v-if="isShowCodeDifferences"
              style="font-size: 12px"
              theme="primary"
              text
              :disabled="isVersionDifferenceDisabled"
              @click="handleShowCommits"
            >
              {{ $t('查看代码版本差异') }}
            </bk-button>
          </div>
          <!-- 代码分支禁用 -->
          <bk-select
            v-model="branchValue"
            :placeholder="$t('请选择')"
            style="width: 470px; display: inline-block; vertical-align: middle"
            :popover-min-width="420"
            :clearable="false"
            :searchable="true"
            :disabled="isShowCodeAlert"
            @change="handleChangeBranch"
            :loading="isBranchesLoading"
            :empty-text="branchEmptyText"
          >
            <bk-option-group
              v-for="(branch, index) in branchList"
              :key="index"
              class="option-group"
              :name="branch.displayName"
            >
              <bk-button
                ext-cls="paas-branch-btn"
                theme="primary"
                text
                @click="getModuleBranches"
              >
                {{ $t('刷新') }}
              </bk-button>
              <bk-option
                v-for="option in branch.children"
                :id="option.id"
                :key="option.id"
                :name="option.text"
              />
            </bk-option-group>
          </bk-select>
          <!-- 删除 -->
          <!-- <p
            class="error-text mt5"
            v-if="branchErrorTips"
          >
            {{ branchErrorTips }}
          </p> -->
        </div>

        <div
          class="image-source mt20"
          v-if="buttonActive === 'image'"
        >
          <div class="mb10 mt10 flex-row justify-content-between">
            <div>{{ $t('镜像Tag') }}</div>
          </div>
          <bk-select
            v-model="tagData.tagValue"
            :placeholder="$t('请选择')"
            style="width: 470px; display: inline-block; vertical-align: middle"
            :popover-min-width="420"
            :clearable="false"
            :searchable="true"
            @change="handleChangeTags"
            :loading="isTagLoading"
            enable-scroll-load
            :scroll-loading="scrollLoadingOptions"
            @scroll-end="handleScrollToBottom"
          >
            <bk-option
              v-for="option in imageTagList"
              :id="option.id"
              :key="option.id"
              :name="option.tag"
            />
          </bk-select>
        </div>
      </div>

      <div
        class="v1-container"
        v-if="isShowImagePullStrategy || isSmartApp"
      >
        <div
          class="image-pull-strategy"
          :class="isSourceCodeBuild || !allowMultipleImage ? '' : 'flex-row'"
        >
          <div class="label">
            {{ $t('镜像拉取策略') }}
            <span v-if="!isSourceCodeBuild && allowMultipleImage">：</span>
          </div>
          <bk-radio-group v-model="imagePullStrategy">
            <bk-radio :value="'IfNotPresent'">
              IfNotPresent
              <span
                class="last-selected"
                v-if="lastSelectedImagePullStrategy === 'IfNotPresent'"
              >
                ({{ $t('上次选择') }})
              </span>
            </bk-radio>
            <p class="tip mb10">{{ $t('当本地不存在镜像时从远程仓库拉取') }}</p>
            <bk-radio :value="'Always'">
              Always
              <span
                class="last-selected"
                v-if="lastSelectedImagePullStrategy === 'Always'"
              >
                ({{ $t('上次选择') }})
              </span>
            </bk-radio>
            <p class="tip">{{ $t('总在容器启动时拉取最新的镜像') }}</p>
          </bk-radio-group>
        </div>
      </div>

      <section
        v-if="isShowCodeAlert"
        class="customize-alert-wrapper mt10"
      >
        <p class="text">
          <i class="paasng-icon paasng-remind exclamation-cls"></i>
          <span>{{ codeRepositoryErrorData?.message }}</span>
        </p>
        <div class="right-link">
          <bk-button
            v-if="codeRepositoryErrorData.action_name === 'NEED_TO_BIND_OAUTH_INFO'"
            class="link-text"
            :text="true"
            @click="hanndleToAuthorize()"
          >
            {{ $t('去授权') }}
            <i class="paasng-icon paasng-jump-link" />
          </bk-button>
          <bk-button
            v-else
            class="link-text"
            :text="true"
            @click="handleFixPreparation(codeRepositoryErrorData)"
          >
            {{ $t('立即处理') }}
            <i class="paasng-icon paasng-jump-link" />
          </bk-button>
          <div class="line"></div>
          <!-- 刷新代码分支 -->
          <bk-button
            class="link-text"
            :text="true"
            @click="handleRefresh"
          >
            {{ $t('刷新') }}
            <i
              class="paasng-icon paasng-refresh-line"
              v-if="!codeRefreshLoading"
            />
            <round-loading
              class="round-loading-cls"
              v-else
            />
          </bk-button>
        </div>
      </section>
    </bk-dialog>
    <bk-sideslider
      :is-show.sync="isShowSideslider"
      :title="$t('部署日志')"
      :width="920"
      :quick-close="true"
      :before-close="handleCloseProcessWatch"
    >
      <div slot="content">
        <deploy-status-detail
          ref="deployStatusRef"
          :environment="environment"
          :deployment-id="deploymentId"
          :deployment-info="deploymentInfoBackUp"
          :rv-data="rvData"
          @close="handleCloseSideslider"
        ></deploy-status-detail>
      </div>
    </bk-sideslider>

    <bk-dialog
      v-model="commitDialog.visiable"
      width="740"
      :title="$t('查看版本差异')"
      :theme="'primary'"
      :mask-close="true"
      :show-footer="false"
    >
      <div class="result">
        <!-- commitsList 根据 显示 -->
        <paas-loading :loading="commitDialog.isLoading">
          <div
            v-if="!commitDialog.isLoading"
            slot="loadingContent"
          >
            <!-- 改为部署内容 -->
            <form
              v-if="moduleReleaseInfo"
              class="ps-form ps-form-horizontal"
            >
              <div class="middle-list mb15">
                <span class="">
                  {{ $t('已选中分支：') }}
                  <strong>{{ branchValue.split(':')[1] || '--' }}</strong>
                </span>
                <span class="revision-diff-sep ml25 mr25">&lt; &gt;</span>
                <span class="">
                  {{ $t('已部署分支：') }}
                  <strong>
                    {{ moduleReleaseInfo.repo.name }}
                    （{{ $t('版本号') }}: {{ moduleReleaseInfo.repo.version }} ）
                  </strong>
                </span>
              </div>
            </form>
            <table class="ps-table ps-table-default ps-table-outline">
              <colgroup>
                <col style="width: 150px" />
                <col style="width: 150px" />
                <col style="width: 170px" />
                <col style="width: 250px" />
              </colgroup>
              <tr class="ps-table-environment-header">
                <th>{{ $t('版本号') }}</th>
                <th>{{ $t('提交人') }}</th>
                <th>{{ $t('提交时间') }}</th>
                <th>{{ $t('注释') }}</th>
              </tr>
              <tr
                v-if="!commitsList.length"
                class="ps-table-slide-up"
              >
                <td colspan="4">
                  <div class="ps-no-result">
                    <div class="text">
                      <p><i class="paasng-icon paasng-empty no-data" /></p>
                      <p>{{ $t('暂无版本差异记录') }}</p>
                    </div>
                  </div>
                </td>
              </tr>
              <tbody
                v-for="(cItem, index) in commitsList"
                v-else
                :key="index"
                :class="['ps-table-template', { open: commitDialog.curCommitsIndex === index }]"
              >
                <tr
                  class="ps-table-slide-up"
                  @click.stop.prevent="handleToggleCommitsDetail(index)"
                >
                  <td class="pl50">
                    <i class="icon" />
                    <a>{{ cItem.revision }}</a>
                  </td>
                  <td>{{ cItem.author }}</td>
                  <td>{{ cItem.date }}</td>
                  <td>{{ cItem.message }}</td>
                </tr>
                <tr class="ps-table-slide-down">
                  <td colspan="4">
                    <pre>
                      <p
                        v-for="(chagnItem, chagnItemIndex) in cItem.changelist"
                        :key="chagnItemIndex"
                      >{{ chagnItem[0] }} {{ chagnItem[1] }}</p>
                    </pre>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </paas-loading>
      </div>
    </bk-dialog>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployStatusDetail from './deploy-status-detail';
import { cloneDeep } from 'lodash';

// 当前状态，禁用部署按钮
const DEPLOY_ERROR_STATES = ['FILL_PRODUCT_INFO', 'CHECK_ENV_PROTECTION', 'FILL_PLUGIN_TAG_INFO', 'FILL_EXTRA_INFO'];

// 从源码构建，且为当前错误状态，禁用部署按钮
const CODE_REPOSITORY_ERROR_STATES = [
  'NEED_TO_BIND_OAUTH_INFO',
  'DONT_HAVE_ENOUGH_PERMISSIONS',
  'NEED_TO_CORRECT_REPO_INFO',
  'NEED_TO_COMPLETE_PROCFILE',
  'CHECK_CI_GIT_TOKEN',
];

export default {
  components: {
    deployStatusDetail,
  },
  mixins: [appBaseMixin],
  props: {
    show: {
      type: Boolean,
      default: () => false,
    },
    environment: {
      type: String,
      default: () => 'stag',
    },
    deploymentInfo: {
      type: Object,
      default: () => {},
    },
    rvData: {
      type: Object,
      default: () => ({}),
    },
  },

  data() {
    return {
      deployAppDialog: {
        visiable: false,
        isLoading: false,
        disabled: true,
      },
      imageSourceData: [
        { value: 'branch', label: this.$t('从源码构建') },
        { value: 'image', label: this.$t('已构建镜像') },
      ],
      buttonActive: 'branch',
      branchList: [],
      branchesData: [],
      branchValue: '',
      overview: {},
      isBranchesLoading: false,
      branchesMap: {},
      curSelectData: {},
      isShowSideslider: false,
      deploymentId: '',
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      imageTagList: [],
      isTagLoading: false,
      tagData: {
        tagValue: '',
      },
      deploymentInfoBackUp: {}, // 模块信息备份
      imageTagListCount: 0,
      rules: {
        tag: [
          {
            required: true,
            message: this.$t('请输入镜像Tag'),
            trigger: 'blur',
          },
        ],
      },
      tagUrl: '',
      customImageTagList: [],
      errorTips: '',
      branchErrorTips: '',
      imagePullStrategy: 'IfNotPresent',
      processesData: [],
      allowMultipleImage: false,
      curModulemirrorTag: '',
      deployPreparations: {},
      isShowErrorAlert: {
        deploy: false,
        code: false,
      },
      deployRefreshLoading: false,
      codeRefreshLoading: false,
      commitDialog: {
        visiable: false,
        isLoading: false,
        curCommitsIndex: -1,
      },
      commitsList: [],
      moduleReleaseInfo: null,
      scrollLoadingOptions: {
        size: 'mini',
        isLoading: false,
      },
    };
  },
  computed: {
    curAppModule() {
      return this.curAppModuleList.find((e) => e.name === (this.deploymentInfoBackUp.module_name || 'default'));
    },
    branchEmptyText() {
      const sourceType = this.overview.repo && this.overview.repo.source_type;
      if (['bare_svn', 'bare_git'].includes(sourceType)) {
        if (this.branchList.length === 0) {
          return sourceType === 'bare_svn' ? this.$t('请检查SVN账号是否正确') : this.$t('请检查Git账号是否正确');
        }
        return this.$t('暂无选项');
      }
      return this.$t('暂无选项');
    },

    curModuleId() {
      // 当前模块的名称
      return this.deploymentInfoBackUp.module_name;
    },

    // 是否是smartApp
    isSmartApp() {
      return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SMART_APP;
    },

    availableBranch() {
      if (this.$store.state.deploy.availableBranch) {
        return `${this.$store.state.deploy.availableType}:${this.$store.state.deploy.availableBranch}`;
      }
      return '';
    },

    // 为源码构建
    isSourceCodeBuild() {
      return this.deploymentInfoBackUp.build_method !== 'custom_image';
    },

    isShowNext() {
      return this.imageTagListCount > 10;
    },

    // 是否展示镜像拉取策略
    isShowImagePullStrategy() {
      // 镜像来源展示时, 选择以构建镜像才展示
      if (this.isSourceCodeBuild) {
        return this.buttonActive === 'image';
      }
      return !this.allowMultipleImage;
    },

    // 上一次选择的镜像拉取策略
    lastSelectedImagePullStrategy() {
      return this.deploymentInfoBackUp.state?.deployment.latest?.advanced_options?.image_pull_policy || '';
    },

    // 是否显示代码差异
    isShowCodeDifferences() {
      if (!this.isSmartApp && !this.isLesscodeApp && this.overview?.repo?.diff_feature?.enabled) {
        return true;
      }
      return false;
    },

    // 是否展示代码仓库相关错误信息
    isShowCodeAlert() {
      if (this.isShowErrorAlert.code && this.isSourceCodeBuild) {
        if (this.buttonActive === 'branch' || this.isSmartApp) {
          return true;
        }
      }
      return false;
    },

    // 部署相关错误信息
    deployErrorData() {
      return this.getFirstErrorData(DEPLOY_ERROR_STATES);
    },

    // 代码仓库相关错误信息
    codeRepositoryErrorData() {
      return this.getFirstErrorData(CODE_REPOSITORY_ERROR_STATES);
    },

    // 部署按钮禁用状态
    deploybuttonDisabled() {
      if (this.deployPreparations.all_conditions_matched) {
        return false;
      }
      // 部署限制相关的/代码仓库相关
      if (this.isShowErrorAlert.deploy || this.isShowCodeAlert) {
        return true;
      }
      return false;
    },

    // 部署按钮提示禁用
    deployButtonTipsDisable() {
      if (this.deployAppDialog.disabled || this.deploybuttonDisabled) {
        return false;
      }
      return true;
    },

    // svn查看代码版本差异
    isVersionDifferenceDisabled() {
      return this.curAppModule.repo.diff_feature.method !== 'external' && this.moduleReleaseInfo === null;
    },
  },
  watch: {
    show: {
      handler(value) {
        if (!value) return;
        // 镜像来源、镜像拉取策略默认值
        const { activeImageSource, activeImagePullPolicy } = this.deploymentInfoBackUp;
        this.deployAppDialog.visiable = !!value;
        this.buttonActive = activeImageSource || 'branch';
        this.tagData.tagValue = '';
        // 初始化镜像taglist
        this.pagination.limit = 10;
        this.imageTagListCount = 0;
        this.getDeployPreparations();
        // 仅镜像部署不需要获取分支数据
        if (this.deploymentInfoBackUp.build_method !== 'custom_image') {
          this.getModuleBranches(); // 获取分支数据
        } else {
          this.getAppProcessData(); // 获取镜像地址
        }

        this.setCurData();
        this.getModuleRuntimeOverview();
        // 获取当前模块部署信息
        this.getModuleReleaseInfo();
        // 外界传递镜像拉取策略，上次选择的镜像拉取策略，否则为默认值
        this.imagePullStrategy = activeImagePullPolicy || this.lastSelectedImagePullStrategy || 'IfNotPresent';
        // 已构建镜像，获取下拉列表
        if (activeImageSource) {
          this.handleSelected({ value: 'image', label: this.$t('已构建镜像') });
        }
      },
      immediate: true,
    },
    deploymentInfo(v) {
      this.deploymentInfoBackUp = cloneDeep(v);
      const versionInfo = this.deploymentInfoBackUp.state.deployment.latest_succeeded?.version_info || {};
      if (!Object.keys(versionInfo).length) return; // 没有数据就不处理
      this.curModulemirrorTag = versionInfo?.version_name;
      // smartApp下, 代码差异
      if (this.isSmartApp) {
        this.branchValue = `${versionInfo?.version_type}:${versionInfo?.version_name}`;
        this.curSelectData = {
          revision: versionInfo?.revision,
          name: versionInfo?.version_name,
          type: versionInfo?.version_type,
        };
      }
    },
  },
  methods: {
    // 获取第一个匹配的错误数据
    getFirstErrorData(errorStates) {
      const failedConditions = this.deployPreparations.failed_conditions || [];
      const errorList = failedConditions.find((v) => errorStates.includes(v.action_name));
      return errorList || {};
    },
    setCurData() {
      const versionInfo = this.deploymentInfoBackUp.state.deployment.latest_succeeded?.version_info || {};
      if (!Object.keys(versionInfo).length) return; // 没有数据就不处理
      this.curModulemirrorTag = versionInfo?.version_name;
      // smartApp下, 代码差异
      if (this.isSmartApp) {
        this.branchValue = `${versionInfo?.version_type}:${versionInfo?.version_name}`;
        this.curSelectData = {
          revision: versionInfo?.revision,
          name: versionInfo?.version_name,
          type: versionInfo?.version_type,
        };
      }
    },
    async getAppProcessData() {
      try {
        const res = await this.$store.dispatch('deploy/getAppProcessInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.processesData = res.proc_specs;
        this.getCustomImageTagList(); // 获取仅镜像下镜像tag
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
      }
    },
    // 排序
    sortingRules(a, b) {
      return new Date(b.last_update).getTime() - new Date(a.last_update).getTime();
    },
    async getModuleBranches(favBranchName) {
      this.isBranchesLoading = true;
      this.branchErrorTips = '';
      try {
        // 获取上次部署staging环境的分支
        const availableBranch = await this.$store.dispatch('deploy/refreshAvailableBranch', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        const res = await this.$store.dispatch('deploy/getModuleBranches', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });

        // last_update有值，根据时间排序
        if (res.results[0]?.last_update) {
          res.results.sort(this.sortingRules);
        }

        //  Smart 应用(预发布/生产)显示最新分支
        if (this.isSmartApp) {
          this.branchValue = res.results.length ? `${res.results[0]?.type}:${res.results[0]?.name}` : '';
        }
        this.branchesData = res.results;
        const branchesList = [];
        this.branchesData.forEach((branch) => {
          const branchId = `${branch.type}:${branch.name}`;
          let branchName = branch.name;

          if (this.environment === 'prod' && branchId === availableBranch) {
            branchName = `${branch.name}${this.$t('（已在预发布环境成功部署）')}`;
          }

          const obj = {
            id: branchId,
            text: branchName,
            type: branch.type,
          };

          // 组装数据，实现分组
          if (!branchesList.map((item) => item.id).includes(branch.type)) {
            branchesList.push({
              id: branch.type,
              name: branch.type,
              displayName: branch.display_type,
              children: [obj],
            });
          } else {
            const curData = branchesList.find((item) => item.id === branch.type);
            curData.children.push(obj);
          }

          this.branchesMap[branchId] = branch;
        });
        this.branchList = branchesList;
        this.initBranchSelection(favBranchName);
      } catch (e) {
        this.branchList = [];
        this.branchErrorTips = e.detail;
        if (!e.code === 'APP_NOT_RELEASED') {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      } finally {
        this.isBranchesLoading = false;
      }
    },

    initBranchSelection(favBranchName) {
      // 如果是刚刚创建新分支，默认选中新建的分支
      // 如果相应环境上次部署过，默认选中上次部署的分支
      // 如果正式环境没有部署过，默认选中预发布环境部署过的分支

      // eslint-disable-next-line no-prototype-builtins
      if (favBranchName && this.branchesMap.hasOwnProperty(favBranchName)) {
        this.branchValue = favBranchName;
        return;
      }

      if (this.branchList.length && !this.branchValue) {
        if (this.environment === 'prod') {
          if (this.availableBranch) {
            this.branchValue = this.availableBranch;
          } else {
            this.branchValue = this.branchList[0].children[0].id;
          }
        } else {
          // 默认选中第一个
          this.branchValue = this.branchList[0].children[0].id;
        }
      }
    },

    async getModuleRuntimeOverview() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleRuntimeOverview', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.overview = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    handleAfterLeave() {
      this.branchValue = '';
      this.isShowErrorAlert = {
        deploy: false,
        code: false,
      };
      this.isShowErrorAlert.code = false;
      this.deployAppDialog.disabled = true;
      this.$emit('update:show', false);
    },

    // 查看代码差异
    async handleShowCommits() {
      if (this.curAppModule.repo.diff_feature.method === 'external') {
        this.showCompare();
      } else {
        // svn
        this.showCommits();
      }
    },

    // 查看代码对比
    async showCompare() {
      if (!this.branchValue) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择部署分支'),
        });
        return false;
      }

      const fromVersion = this.deploymentInfoBackUp?.version_info?.revision;
      const toVersion = this.branchValue;
      const res = await this.$store.dispatch('deploy/getGitCompareUrl', {
        appCode: this.appCode,
        moduleId: this.curModuleId,
        fromVersion,
        toVersion,
      });
      window.open(res.result, '_blank');
    },

    /**
     * 查看代码提交记录
     */
    async showCommits() {
      if (!this.branchValue) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择部署分支'),
        });
        return false;
      }

      this.commitDialog.visiable = true;
      this.commitDialog.isLoading = true;

      try {
        const fromVersion = this.moduleReleaseInfo.repo?.revision;
        const toVersion = this.branchValue;

        // 根据用户选择的分支获取提交记录
        const res = await this.$store.dispatch('deploy/getSvnCommits', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          fromVersion,
          toVersion,
        });
        this.commitsList = res.results;
      } catch (e) {
        this.commitsList = [];
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.commitDialog.isLoading = false;
      }
    },

    // 获取模块发布信息
    async getModuleReleaseInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleReleaseInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });

        if (!res.code) {
          // 已下架
          if (res.is_offlined) {
            res.offline.repo.version = this.formatRevision(res.offline.repo.revision);
            this.moduleReleaseInfo = res.offline;
          } else if (res.deployment) {
            res.deployment.repo.version = this.formatRevision(res.deployment.repo.revision);
            this.moduleReleaseInfo = res.deployment;
          } else {
            this.moduleReleaseInfo = {
              repo: {},
            };
          }
        }
      } catch (e) {
        this.moduleReleaseInfo = null;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    formatRevision(revision) {
      // 修改后端返回的 repo 数据，增加额外字段
      // 追加 version 字段
      // 为 Git 类型版本号取前 8 位
      const reg = RegExp('^[a-z0-9]{40}$');
      let version = '';
      if (reg.test(revision)) {
        version = revision.substring(0, 8);
      } else {
        version = revision;
      }
      return version;
    },

    handleToggleCommitsDetail(index) {
      if (this.commitDialog.curCommitsIndex === index) {
        this.commitDialog.curCommitsIndex = -1;
      } else {
        this.commitDialog.curCommitsIndex = index;
      }
    },

    async handleConfirmValidate() {
      try {
        if (this.$refs?.imageFormRef) {
          await this.$refs.imageFormRef?.validate();
        }
        if (this.buttonActive === 'image' && !this.tagData.tagValue) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('请选择镜像Tag'),
          });
          return;
        }
        this.handleConfirm();
      } catch (error) {
        console.error(error);
      }
    },

    // 弹窗确认
    async handleConfirm() {
      try {
        if (!this.deploymentInfoBackUp.version_info) {
          this.deploymentInfoBackUp.version_info = {};
        }
        this.deployAppDialog.isLoading = true;
        let params = {};
        // V1alpha1与V1alpha2都添加镜像拉取策略
        const advancedOptions = {
          image_pull_policy: this.imagePullStrategy,
        };
        // 源码构建
        if (this.isSourceCodeBuild) {
          // 如果是镜像则需要传构建产物ID, 镜像列表接口里的 `id` 字段
          if (this.buttonActive === 'image') {
            advancedOptions.build_id = this.tagData.tagValue;
          }
          params = {
            revision: this.curSelectData.revision,
            version_type: this.curSelectData.type,
            version_name: this.curSelectData.name,
            advanced_options: advancedOptions,
          };
          // 部署的分支或tag需要修改为选中的分支或者tag
          this.deploymentInfoBackUp.version_info.version_name = this.curSelectData.name;
          this.deploymentInfoBackUp.version_info.version_type = this.buttonActive;
        } else {
          // 可以自己编辑选择镜像
          if (!this.allowMultipleImage) {
            params = {
              version_type: 'tag',
              version_name: this.tagData.tagValue,
              advanced_options: advancedOptions,
            };
            this.deploymentInfoBackUp.version_info.version_name = this.tagData.tagValue;
          } else {
            params = {
              version_type: 'tag',
              version_name: 'manifest',
              advanced_options: advancedOptions,
            };
          }
        }

        const res = await this.$store.dispatch('deploy/cloudDeployments', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: params,
        });
        this.deployAppDialog.visiable = false;
        this.deploymentId = res.deployment_id;
        this.handleAfterLeave(); // 关闭弹窗
        this.isShowSideslider = true; // 打开侧边栏
        this.$emit('showSideslider');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.deployAppDialog.isLoading = false;
      }
    },

    // 获取镜像tag列表
    async getImageTagList() {
      try {
        this.isTagLoading = true;
        this.scrollLoadingOptions.isLoading = true;
        const res = await this.$store.dispatch('deploy/getImageTagData', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: {
            limit: this.pagination.limit,
            offset: 0,
          },
        });
        this.imageTagList.splice(0, this.imageTagList.length, ...(res.results || []));
        this.imageTagListCount = res.count;
        // 默认选中已部署成功的 Tag, 否则选中第一个
        this.tagData.tagValue = this.curModulemirrorTag || this.imageTagList[0]?.id || '';
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTagLoading = false;
        this.scrollLoadingOptions.isLoading = false;
      }
    },

    // 获取仅镜像镜像tag列表
    async getCustomImageTagList() {
      try {
        this.isTagLoading = true;
        this.tagUrl = '';
        this.errorTips = '';
        const res = await this.$store.dispatch('deploy/getCustomImageTagData', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.customImageTagList.splice(0, this.customImageTagList.length, ...(res || []));
        // 默认选中已部署成功的 Tag, 否则选中第一个
        this.tagData.tagValue = this.curModulemirrorTag || this.customImageTagList[0]?.name || '';
      } catch (e) {
        this.tagUrl = e?.data?.url;
        this.errorTips = e.message;
      } finally {
        this.isTagLoading = false;
      }
    },

    // 选择分支
    handleChangeBranch() {
      if (!this.branchesData.length) return;
      const branchName = this.branchValue.split(':')[1] || this.branchValue;
      this.curSelectData = this.branchesData.find((e) => {
        if (branchName === e.name) {
          return e;
        }
      });
    },

    // 选择tag
    handleChangeTags() {
      this.curSelectData = this.imageTagList.find((e) => {
        if (e.id === this.tagData.tagValue) {
          e.revision = e.digest;
          (e.type = 'image'), (e.name = e.tag);
          return e;
        }
      });
    },
    handleCancel() {
      this.$refs.imageFormRef?.clearError();
      this.deployAppDialog.visiable = false;
    },
    // 点击镜像来源
    handleSelected(item) {
      this.buttonActive = item.value;
      if (this.buttonActive !== 'branch') {
        this.getImageTagList();
      }
      this.pagination.limit = 10;
      this.imageTagListCount = 0;
    },

    // 关闭进程的事件流
    handleCloseProcessWatch() {
      this.$refs.deployStatusRef.closeServerPush();
      this.isShowSideslider = false;
      this.$emit('refresh');
    },

    handleCloseSideslider() {
      this.handleCloseProcessWatch();
    },

    handleScrollToBottom() {
      if (this.pagination.limit >= this.imageTagListCount || this.isTagLoading) return;
      this.pagination.limit += 10;
      this.getImageTagList();
    },

    handleOpenUrl(url) {
      window.open(url, '_blank');
    },

    // 获取部署准备信息
    async getDeployPreparations(type) {
      // 刷新
      if (type) {
        type === 'deploy' ? (this.deployRefreshLoading = true) : (this.codeRefreshLoading = true);
      }
      try {
        const ret = await this.$store.dispatch('deploy/getDeployPreparations', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        this.deployPreparations = ret;

        // 将错误数据进行分类
        if (ret.failed_conditions?.length) {
          // 标识错误类型并更新状态
          const errorTypes = {
            deploy: DEPLOY_ERROR_STATES,
            code: CODE_REPOSITORY_ERROR_STATES,
          };

          Object.keys(errorTypes).forEach((type) => {
            const errorList = ret.failed_conditions.filter((v) => errorTypes[type].includes(v.action_name));
            this.isShowErrorAlert[type] = errorList.length > 0;
          });
        } else {
          // 没有错误，隐藏错误提示alert
          this.isShowErrorAlert = {
            deploy: false,
            code: false,
          };
        }
        this.deployAppDialog.disabled = false;
      } catch (e) {
        this.catchErrorHandler(e);
        this.deployAppDialog.disabled = false;
      } finally {
        type === 'deploy' ? (this.deployRefreshLoading = false) : (this.codeRefreshLoading = false);
      }
    },

    // 刷新
    handleRefresh() {
      this.getDeployPreparations('code');
      // 代码分支
      this.getModuleBranches();
    },

    // 去授权
    hanndleToAuthorize() {
      const route = this.$router.resolve({ name: 'serviceCode' });
      window.open(route.href, '_blank');
    },

    /**
     * 处理部署前准备工作项
     * @param {Object} preparation 错误对象
     */
    handleFixPreparation(preparation) {
      const { action_name: actionName } = preparation;

      if (actionName === 'CHECK_ENV_PROTECTION') {
        this.$paasMessage({
          message: this.$t('请联系应用管理员'),
        });
        return;
      }

      // 路由映射配置
      const routeMap = {
        // 代码仓库没有授权
        NEED_TO_BIND_OAUTH_INFO: {
          name: 'serviceCode',
        },
        // 没有访问源码仓库的权限
        DONT_HAVE_ENOUGH_PERMISSIONS: {
          name: 'serviceCode',
        },
        // 蓝盾没有授权
        CHECK_CI_GIT_TOKEN: {
          name: 'serviceCi',
        },
        // 完善市场信息
        FILL_PRODUCT_INFO: {
          name: 'appMarket',
          params: { id: this.appCode },
          query: { focus: 'baseInfo' },
        },
        // 自定义仓库源配置不正确
        NEED_TO_CORRECT_REPO_INFO: {
          name: 'cloudAppDeployForBuild',
          params: { id: this.appCode, moduleId: this.curModuleId },
        },
        // 未完善进程启动命令
        NEED_TO_COMPLETE_PROCFILE: {
          name: 'cloudAppDeployForProcess',
          params: { id: this.appCode, moduleId: this.curModuleId },
        },
        // 未设置插件分类
        FILL_PLUGIN_TAG_INFO: {
          name: 'appBasicInfo',
          params: { id: this.appCode, moduleId: this.curModuleId },
        },
        // 完善应用基本信息
        FILL_EXTRA_INFO: {
          name: 'appBasicInfo',
          params: { id: this.appCode, moduleId: this.curModuleId },
          query: {
            editMode: true,
          },
        },
      };

      // 获取路由配置
      const routeConfig = routeMap[actionName];
      if (!routeConfig) return;

      const routeData = this.$router.resolve(routeConfig);
      window.open(routeData.href, '_blank');
    },
  },
};
</script>
<style lang="scss" scoped>
.image-source {
  .tips {
    font-size: 12px;
    color: #979ba5;
    margin-top: 4px;
  }
}
.version-code {
  cursor: pointer;
  color: #3a84ff;
  font-size: 12px;
}
.option-group {
  position: relative;
}
.paas-branch-btn {
  position: absolute;
  right: 30px;
  top: 0px;
  font-size: 12px;
}
.btn-container {
  display: flex;
  .btn-item {
    flex: 1;
  }
}
.v1-container {
  .name {
    color: #76787f;
  }
  .value {
    color: #313238;
  }
}
.image-list {
  position: absolute;
  top: -30px;
  right: 0;
}
.error-text {
  font-size: 12px;
  color: #ea3636;
}
.image-pull-strategy {
  margin-top: 20px;
  & > .label {
    line-height: 32px;
    white-space: nowrap;
  }
  .tip {
    margin: 5px 0 0 20px;
    font-size: 12px;
    color: #979ba5;
  }
  .last-selected {
    font-size: 12px;
    color: #c4c6cc;
  }
}

.image-tag-cls {
  /deep/ .bk-label::after {
    display: none;
  }
}

.dialog-header-wrapper {
  color: #313238;
  display: flex;
  align-items: center;
  .module-name-tag {
    margin-left: 8px;
    font-size: 12px;
    color: #63656e;
    background-color: #f0f1f5;
    padding: 3px 7px;
    border-radius: 2px;
  }
}

.dialog-footer-wrapper {
  text-align: right;
}

.mb12 {
  margin-bottom: 12px;
}

.customize-alert-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  color: #63656e;
  min-height: 32px;
  background: #ffeded;
  border: 1px solid #ffd2d2;
  border-radius: 2px;

  .text {
    word-break: break-all;
    display: flex;
    margin-right: 10px;

    .exclamation-cls {
      color: #ea3636;
      font-size: 14px;
      transform: translateY(2px);
      margin-right: 6px;
    }
  }

  .line {
    width: 1px;
    margin: 0 10px;
    height: 14px;
    background: #dcdee5;
  }

  .right-link {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    .link-text {
      font-size: 12px;
      color: #3a84ff;
      cursor: pointer;
    }
    i {
      font-size: 14px;
      transform: translateY(0px);
    }
  }
}
.round-loading-cls {
  width: 14px;
  height: 14px;
  transform: translateY(-1px);
}
.deploy-dialog-container :deep(.bk-sideslider-wrapper.right) {
  overflow: unset;
  .paas-deploy-log-wrapper {
    height: 100%;
    margin-bottom: 24px;
    min-height: 620px;
  }
}
.code-depot {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
