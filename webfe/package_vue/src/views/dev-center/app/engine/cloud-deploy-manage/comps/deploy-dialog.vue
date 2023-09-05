<template>
  <div>
    <bk-dialog
      v-model="isShowDialog"
      width="450"
      :title="$t('模块部署')"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="deployAppDialog.isLoading"
      @confirm="handleConfirm"
      @cancel="handleCancel"
    >
      <div class="code-depot">
        <span class="pr20">代码仓库</span>
        <bk-button :theme="'default'" text>
          mirrors.tencent.com/bkapp/some-appid-defalult
        </bk-button>
      </div>
      <div class="image-source mt20">
        <div class="mb10">镜像来源</div>
        <div class="bk-button-group">
          <bk-button
            v-for="item in imageSourceData"
            :key="item.value"
            :class="buttonActive === item.value ? 'is-selected' : ''"
            @click="handleSelected(item)"
          >
            {{ $t(item.label) }}
          </bk-button>
        </div>
      </div>

      <div class="image-source mt20">
        <div class="mb10">代码分支选择</div>
        <bk-select
          v-model="branchValue"
          :placeholder="$t('请选择')"
          style="width: 420px; display: inline-block; vertical-align: middle;"
          :popover-min-width="420"
          :clearable="false"
          :searchable="true"
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
    </bk-dialog>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
// :ok-text="$t('部署至')`${environment === 'stag' ? $t('预发布环境') : $t('生产环境')}`"
export default {
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
  },

  data() {
    return {
      deployAppDialog: {
        visiable: false,
        isLoading: false,
      },
      isShowDialog: false,
      imageSourceData: [{ value: 'source', label: '从源码构建' }, { value: 'image', label: '已构建镜像' }],
      buttonActive: 'source',
      branchList: [],
      branchValue: '',
      overview: '',
      isBranchesLoading: false,
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
  },
  watch: {
    show: {
      handler(value) {
        console.log('value', value);
        this.isShowDialog = true;
        this.deployAppDialog.visiable = !!value;
        if (this.isShowDialog) {
        //   this.fetchData();
        }
      },
      //   immediate: true,
      deep: true,
    },
  },
  methods: {
    handleConfirm() {},
    handleCancel() {},
    // 点击镜像来源
    handleSelected(item) {
      this.buttonActive = item.value;
    },


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
        const branchesData = res.results;
        const branchesList = [];
        branchesData.forEach((branch, index) => {
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

  },
};
</script>
