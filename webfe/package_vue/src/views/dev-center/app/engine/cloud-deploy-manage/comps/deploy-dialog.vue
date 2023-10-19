<template>
  <div class="deploy-dialog-container">
    <bk-dialog
      v-model="deployAppDialog.visiable"
      width="520"
      :title="$t('模块部署')"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="deployAppDialog.isLoading"
      :auto-close="false"
      :ok-text="`${$t('部署至')}${environment === 'stag' ? $t('预发布环境') : $t('生产环境') }`"
      @confirm="handleConfirmValidate"
      @cancel="handleCancel"
      @after-leave="handleAfterLeave"
    >
      <div v-if="isV1alpha2">
        <div class="code-depot mb15" v-if="deploymentInfoBackUp.repo_url">
          <span class="pr20">
            {{ deploymentInfoBackUp.build_method === 'dockerfile' ?
              $t('代码仓库') : $t('镜像仓库') }}
          </span>
          {{ deploymentInfoBackUp.repo_url }}
        </div>
        <!-- 仅镜像不需要选择镜像来源 -->
        <div v-if="deploymentInfoBackUp.build_method !== 'custom_image'">
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
          </div>
          <div class="image-source mt20" v-if="buttonActive === 'branch'">
            <div class="mb10 flex-row justify-content-between">
              <div>{{$t('代码分支选择')}}</div>
              <div class="version-code" @click="handleShowCommits">{{$t('查看代码版本差异')}}</div>
            </div>
            <bk-select
              v-model="branchValue"
              :placeholder="$t('请选择')"
              style="width: 470px; display: inline-block; vertical-align: middle;"
              :popover-min-width="420"
              :clearable="false"
              :searchable="true"
              @change="handleChangeBranch"
              :loading="isBranchesLoading"
              :empty-text="branchEmptyText"
            >
              <bk-option-group
                v-for="(branch, index) in branchList"
                :key="index"
                class="option-group"
                :name="branch.name"
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
              <div
                v-if="curAppModule.repo && curAppModule.repo.type === 'bk_svn'"
                slot="extension"
                style="cursor: pointer;"
                @click="handleCreateBranch"
              >
                <i class="bk-icon icon-plus-circle mr5" /> {{ $t('新建部署分支') }}
              </div>
            </bk-select>
            <p class="error-text mt5" v-if="branchErrorTips">
              {{ branchErrorTips }}
            </p>
          </div>

          <div class="image-source mt20" v-if="buttonActive === 'image'">
            <div class="mb10 mt10 flex-row justify-content-between">
              <div>{{$t('镜像Tag')}}</div>
            </div>
            <bk-select
              v-model="tagData.tagValue"
              :placeholder="$t('请选择')"
              style="width: 470px; display: inline-block; vertical-align: middle;"
              :popover-min-width="420"
              :clearable="false"
              :searchable="true"
              @change="handleChangeTags"
              :loading="isTagLoading"
            >
              <bk-option
                v-for="option in imageTagList"
                :id="option.id"
                :key="option.id"
                :name="option.tag"
              />
              <div slot="extension" @click="handleNext" style="cursor: pointer;" v-if="isShowNext">
                {{ $t('下一页') }}
              </div>
            </bk-select>
          </div>
        </div>
        <div v-else>
          <bk-form :model="tagData" ref="imageFormRef" form-type="vertical">
            <bk-form-item
              label="镜像Tag"
              :rules="rules.tag"
              :required="true"
              :property="'tagValue'"
              :error-display-type="'normal'"
            >
              <div
                v-if="tagUrl"
                class="image-list version-code"
                @click="handleOpenUrl(tagUrl)"
              >
                {{$t('查看镜像Tag列表')}}
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
                style="width: 470px; display: inline-block; vertical-align: middle;"
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
              <span v-if="errorTips" class="error-text">{{ errorTips }}</span>
            </bk-form-item>
          </bk-form>
        </div>
        <div style="margin-top: 16px;">
          <bk-form form-type="vertical">
            <bk-form-item
              :label="$t('镜像拉取策略')"
              :property="'tagValue'"
              :error-display-type="'normal'"
            >
              <bk-radio-group v-model="imagePullStrategy">
                <bk-radio :value="'IfNotPresent'" v-bk-tooltips="ifNotPresentTooltipsConfig">IfNotPresent</bk-radio>
                <bk-radio :value="'Always'" v-bk-tooltips="alwaysTooltipsConfig">Always</bk-radio>
              </bk-radio-group>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
      <div v-else class="v1-container">
        <div>{{$t('请确认模块下进程对应的镜像地址')}}</div>
        <div class="mt10" v-for="item in processesData" :key="item.name">
          <span class="name">{{ item.name }}：</span>
          <span class="value">{{ item.image }}</span>
        </div>
        <div class="image-pull-strategy">
          <label>{{ $t('镜像拉取策略') }}：</label>
          <bk-radio-group v-model="imagePullStrategy">
            <bk-radio :value="'IfNotPresent'" v-bk-tooltips="ifNotPresentTooltipsConfig">IfNotPresent</bk-radio>
            <bk-radio :value="'Always'" v-bk-tooltips="alwaysTooltipsConfig">Always</bk-radio>
          </bk-radio-group>
        </div>
      </div>
    </bk-dialog>
    <bk-sideslider
      :is-show.sync="isShowSideslider"
      :title="$t('部署日志')"
      :width="820"
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
  </div>
</template>
<script>import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployStatusDetail from './deploy-status-detail';
import _ from 'lodash';
// :ok-text="$t('部署至')`${environment === 'stag' ? $t('预发布环境') : $t('生产环境')}`"
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
    cloudAppData: {
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
      },
      imageSourceData: [{ value: 'branch', label: '从源码构建' }, { value: 'image', label: '已构建镜像' }],
      buttonActive: 'branch',
      branchList: [],
      branchesData: [],
      branchValue: '',
      overview: '',
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
      deploymentInfoBackUp: {},  // 模块信息备份
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
      alwaysTooltipsConfig: {
        content: this.$t('总在启动容器时拉取镜像，每个镜像 Tag 默认仅拉取一次，如镜像 Tag 内容有更新，请勾选该选项'),
        placements: ['bottom-start'],
      },
      ifNotPresentTooltipsConfig: {
        content: this.$t('如果本地不存在指定的镜像，才会从远程仓库拉取'),
        placements: ['bottom-start'],
      },
    };
  },
  computed: {
    curAppModule() {
      return this.curAppModuleList.find(e => e.name === (this.deploymentInfoBackUp.module_name || 'default'));
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

    // 是否是v2版本
    isV1alpha2() {
      return this.cloudAppData?.apiVersion?.includes('v1alpha2');
    },

    processesData() {
      return this.cloudAppData?.spec?.processes || [];
    },

    isShowNext() {
      return this.imageTagListCount > 10;
    },
  },
  watch: {
    show: {
      handler(value) {
        if (!value) return;
        this.deployAppDialog.visiable = !!value;
        this.buttonActive = 'branch';
        this.tagData.tagValue = '';
        // 初始化镜像taglist
        this.pagination.limit = 10;
        this.imageTagListCount = 0;
        // 仅镜像部署不需要获取分支数据
        if (this.deploymentInfoBackUp.build_method !== 'custom_image') {
          this.getModuleBranches();   // 获取分支数据
        } else {
          this.getCustomImageTagList();   // 获取仅镜像下镜像tag
        }
      },
      immediate: true,
    },
    deploymentInfo(v) {
      this.deploymentInfoBackUp = _.cloneDeep(v);
    },
  },
  methods: {
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

        //  Smart 应用(预发布/生产)显示最新分支
        if (this.isSmartApp) {
          const sortList = res.results.sort(this.sortData);
          this.branchSelection = `${sortList[0].type}:${sortList[0].name}`;
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
          if (!branchesList.map(item => item.id).includes(branch.type)) {
            branchesList.push({
              id: branch.type,
              name: branch.type,
              children: [obj],
            });
          } else {
            const curData = branchesList.find(item => item.id === branch.type);
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
        this.branchSelection = favBranchName;
        return;
      }

      if (this.branchList.length && !this.branchSelection) {
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
      this.$emit('update:show', false);
    },

    // 查看代码差异
    async handleShowCommits() {
      // console.log('this.curAppModule', this.curAppModule);
      // if (this.curAppModule.repo.diff_feature.method === 'external') {
      //   this.showCompare();
      // } else {
      //   this.showCommits();
      // }
      this.showCompare();
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
      const win = window.open();
      const res = await this.$store.dispatch('deploy/getGitCompareUrl', {
        appCode: this.appCode,
        moduleId: this.curModuleId,
        fromVersion,
        toVersion,
      });
      win.location.href = res.result;
    },

    async handleConfirmValidate() {
      try {
        if (this.$refs?.imageFormRef) {
          await this.$refs.imageFormRef?.validate();
        }
        this.handleConfirm();
      } catch (error) {
        console.error(error);
      }
    },

    // 弹窗确认
    async handleConfirm() {
      try {
        this.deployAppDialog.isLoading = true;
        let params = {};
        // V1alpha1与V1alpha2都添加镜像拉取策略
        const advancedOptions = {
          image_pull_policy: this.imagePullStrategy,
        };
        if (this.isV1alpha2) {
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
          if (!this.deploymentInfoBackUp.version_info) {
            this.deploymentInfoBackUp.version_info = {};
          }
          // 部署的分支或tag需要修改为选中的分支或者tag
          this.deploymentInfoBackUp.version_info.version_name = this.curSelectData.name;
          this.deploymentInfoBackUp.version_info.version_type = this.buttonActive;
          // 仅镜像部署
          if (this.deploymentInfoBackUp.build_method === 'custom_image') {
            params = {
              version_type: 'image',
              version_name: this.tagData.tagValue,
              advanced_options: advancedOptions,
            };
            this.deploymentInfoBackUp.version_info.version_name = this.tagData.tagValue;
          }
        } else {
          // v1alpha1部署
          params = {
            version_type: 'manifest',
            version_name: 'manifest',
            advanced_options: advancedOptions,
            manifest: this.cloudAppData,
          };
        }

        const res = await this.$store.dispatch('deploy/cloudDeployments', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: params,
        });
        this.deployAppDialog.visiable = false;
        this.deployAppDialog.isLoading = false;    // 成功之后关闭弹窗打开侧栏
        this.deploymentId = res.deployment_id;
        this.handleAfterLeave(); // 关闭弹窗
        this.isShowSideslider = true;  // 打开侧边栏
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
        const res =  await this.$store.dispatch('deploy/getImageTagData', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: {
            limit: this.pagination.limit,
            offset: 0,
          },
        });
        this.imageTagList.splice(0, this.imageTagList.length, ...(res.results || []));
        this.imageTagListCount = res.count;
        // 默认选中第一个
        this.tagData.tagValue = this.imageTagList[0]?.id || '';
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTagLoading = false;
      }
    },

    // 获取仅镜像镜像tag列表
    async getCustomImageTagList() {
      try {
        this.isTagLoading = true;
        this.tagUrl = '';
        this.errorTips = '';
        const res =  await this.$store.dispatch('deploy/getCustomImageTagData', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        console.log('res', res);
        this.customImageTagList.splice(0, this.customImageTagList.length, ...(res || []));
        // 默认选中第一个
        this.tagData.tagValue = this.customImageTagList[0]?.name || '';
      } catch (e) {
        this.tagUrl = e?.data?.url;
        this.errorTips = e.message;
      } finally {
        this.isTagLoading = false;
      }
    },

    // 选择分支
    handleChangeBranch() {
      this.curSelectData = this.branchesData.find((e) => {
        if (this.branchValue.includes(e.name)) {
          return e;
        }
      });
    },

    // 选择tag
    handleChangeTags() {
      this.curSelectData = this.imageTagList.find((e) => {
        if (e.id === this.tagData.tagValue) {
          e.revision = e.digest;
          e.type = 'image',
          e.name = e.tag;
          console.log('eeeeee', e);
          return e;
        }
      });
    },
    handleCancel() {
      this.$refs.imageFormRef?.clearError();
    },
    // 点击镜像来源
    handleSelected(item) {
      this.buttonActive = item.value;
      if (this.buttonActive === 'branch') {
        console.log('代码分支');
      } else {
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

    handleNext() {
      if (this.pagination.limit >= this.imageTagListCount || this.isTagLoading) return;
      this.pagination.limit += 10;
      this.getImageTagList();
    },

    handleOpenUrl(url) {
      window.open(url, '_blank');
    },
  },
};
</script>
<style lang="scss" scoped>
.version-code{
    cursor: pointer;
    color: #3A84FF;
    font-size: 12px;
  }
.option-group{
    position: relative;
  }
.paas-branch-btn{
    position: absolute;
    right: 30px;
    top: 0px;
    font-size: 12px;
  }
.btn-container{
  .btn-item{
    padding: 0 82px;
  }
}
.v1-container{
  .name{
    color: #76787f;
  }
  .value{
    color: #313238;
  }
}
.image-list{
  position: absolute;
  top: -30px;
  right: 0;
}
.error-text{
  font-size: 12px;
  color: #ea3636;
}
.image-pull-strategy {
  margin-top: 10px;
  display: flex;
  label {
    white-space: nowrap;
  }
}
</style>
