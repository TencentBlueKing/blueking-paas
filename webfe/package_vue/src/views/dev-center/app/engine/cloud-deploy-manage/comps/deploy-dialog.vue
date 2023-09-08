<template>
  <div class="deploy-dialog-container">
    <bk-dialog
      v-model="deployAppDialog.visiable"
      width="470"
      :title="$t('模块部署')"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="deployAppDialog.isLoading"
      @confirm="handleConfirm"
      @cancel="handleCancel"
      @after-leave="handleAfterLeave"
    >
      <div class="code-depot" v-if="deploymentInfo.exposed_url">
        <span class="pr20">
          {{ deploymentInfo.build_method === 'dockerfile' ?
            $t('代码仓库') : $t('镜像仓库') }}
        </span>
        <bk-button :theme="'default'" text>
          {{ deploymentInfo.exposed_url }}
        </bk-button>
      </div>
      <!-- 仅镜像不需要选择镜像来源 -->
      <div v-if="deploymentInfo.build_method !== 'custom_image'">
        <div class="image-source mt20">
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
            <div>代码分支选择</div>
            <div class="version-code" @click="handleShowCommits">查看代码版本差异</div>
          </div>
          <bk-select
            v-model="branchValue"
            :placeholder="$t('请选择')"
            style="width: 420px; display: inline-block; vertical-align: middle;"
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
        </div>

        <div class="image-source mt20" v-if="buttonActive === 'image'">
          <div class="mb10 flex-row justify-content-between">
            <div>镜像Tag</div>
            <div class="version-code" @click="handleShowCommits">查看代码版本差异</div>
          </div>
          <bk-select
            v-model="tagValue"
            :placeholder="$t('请选择')"
            style="width: 420px; display: inline-block; vertical-align: middle;"
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
          </bk-select>
        </div>
      </div>
      <div class="mt20" v-else>
        <div class="mb10 flex-row justify-content-between">
          <div>镜像Tag</div>
          <div class="version-code" @click="handleShowCommits">查看代码版本差异</div>
        </div>
        <bk-input
          v-model="tagValue"
          :placeholder="$t('请输入镜像Tag')"
          clearable
        />
      </div>

    </bk-dialog>
    <bk-sideslider
      :is-show.sync="isShowSideslider"
      :title="$t('部署日志')"
      :width="800"
      :quick-close="true"
    >
      <div slot="content">
        <deploy-status-detail
          :environment="environment"
          :deployment-id="deploymentId"
          :deployment-info="deploymentInfo"
        ></deploy-status-detail>
      </div>
    </bk-sideslider>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployStatusDetail from './deploy-status-detail';
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
      tagValue: '',
    };
  },
  computed: {
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
      return this.deploymentInfo.module_name;
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
  },
  watch: {
    show: {
      handler(value) {
        this.deployAppDialog.visiable = !!value;
        if (this.deployAppDialog.visiable) {
          this.getModuleBranches();   // 获取分支数据
        }
      },
      immediate: true,
    },
  },
  methods: {
    async getModuleBranches(favBranchName) {
      this.isBranchesLoading = true;
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
      if (this.curAppModule.repo.diff_feature.method === 'external') {
        this.showCompare();
      } else {
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

      const fromVersion = this.deploymentInfo?.repo?.revision;
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

    // 弹窗确认
    async handleConfirm() {
      try {
        this.deployAppDialog.isLoading = true;
        const advancedOptions = {
          image_pull_policy: 'IfNotPresent',
        };
        // 如果是镜像则需要传构建产物ID, 镜像列表接口里的 `id` 字段
        if (this.buttonActive === 'image') {
          advancedOptions.build_id = this.tagValue;
        }
        let params = {
          revision: this.curSelectData.revision,
          version_type: this.curSelectData.type,
          version_name: this.curSelectData.name,
          advanced_options: advancedOptions,
        };
        // 仅镜像部署
        if (this.deploymentInfo.build_method === 'custom_image') {
          params = {
            version_type: 'image',
            version_name: this.tagValue,
          };
        }

        const res = await this.$store.dispatch('deploy/cloudDeployments', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          data: params,
        });
        this.deployAppDialog.isLoading = false;    // 成功之后关闭弹窗打开侧栏
        this.deploymentId = res.deployment_id;
        this.handleAfterLeave(); // 关闭弹窗
        this.isShowSideslider = true;  // 打开侧边栏
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
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
            offset: this.pagination.limit * (this.pagination.current - 1),
          },
        });
        this.imageTagList = res.results;
        console.log('res', res);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
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
        return {};
      });
    },

    // 选择tag
    handleChangeTags() {
      this.curSelectData = this.imageTagList.find((e) => {
        if (e.id === this.tagValue) {
          e.revision = e.digest;
          e.type = 'image',
          e.name = e.tag;
          console.log('eeeeee', e);
          return e;
        }
        return {};
      });
    },
    handleCancel() {},
    // 点击镜像来源
    handleSelected(item) {
      this.buttonActive = item.value;
      if (this.buttonActive === 'branch') {

      } else {
        this.getImageTagList();
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.deploy-dialog-container{
}
.version-code{
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
  width: 420px;
  .btn-item{
    padding: 0 69px;
  }
}
</style>
