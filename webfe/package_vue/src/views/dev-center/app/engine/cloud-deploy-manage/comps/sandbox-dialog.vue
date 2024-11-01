<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    :title="$t('创建沙箱开发环境')"
  >
    <div slot="footer">
      <bk-button
        theme="primary"
        :loading="dialogLoading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        type="submit"
        class="ml8"
        @click="dialogVisible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <div class="dialog-content">
      <bk-alert
        class="mb16"
        type="warning"
        :title="`${$t('沙箱环境将复用 “{n}” 的 Mysql 增强服务和环境变量', { n: envZh })}`"
        closable
      ></bk-alert>
      <bk-form
        form-type="vertical"
        :model="formData"
        ref="sandboxForm"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('模块')"
          :required="true"
          :property="'module'"
        >
          <bk-select
            :disabled="false"
            v-model="formData.module"
            searchable
          >
            <bk-option
              v-for="option in curAppModuleList"
              :key="option.name"
              :id="option.name"
              :name="option.name"
            ></bk-option>
          </bk-select>
          <p
            slot="tip"
            class="item-tips"
          >
            {{ $t('仅使用“蓝鲸 Buildpack”构建并部署到预发布环境的模块，才可使用沙箱开发功能') }}
          </p>
        </bk-form-item>
        <bk-form-item
          :label="`${$t('代码仓库')}：`"
          class="line-item"
        >
          <span :class="{ 'repo-url': curModuleInfo.repo?.repo_url }">{{ curModuleInfo.repo?.repo_url || '--' }}</span>
        </bk-form-item>
        <bk-form-item
          :label="$t('代码分支')"
          :required="true"
          :property="'branch'"
        >
          <bk-select
            :disabled="false"
            v-model="formData.branch"
            searchable
            :loading="isBranchLoading"
          >
            <bk-option
              v-for="option in branchList"
              :key="option.name"
              :id="option.name"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </bk-form-item>
      </bk-form>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'SandboxDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    env: {
      type: String,
      default: 'stag',
    },
  },
  data() {
    return {
      dialog: {
        visiable: false,
      },
      formData: {
        module: '',
        branch: '',
      },
      branchList: [],
      isBranchLoading: false,
      dialogLoading: false,
      rules: {
        module: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
        branch: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    dialogVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    curAppModuleList() {
      return this.$store.state.curAppModuleList || [];
    },
    curModuleInfo() {
      return this.curAppModuleList.find((v) => v.name === this.formData.module) ?? {};
    },
    envZh() {
      return this.env === 'stag' ? this.$t('预发布环境') : this.$t('生产环境');
    },
  },
  watch: {
    'formData.module'(newVal) {
      if (newVal) {
        this.getModuleBranches();
      }
    },
  },
  methods: {
    async getModuleBranches() {
      this.isBranchLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/getModuleBranches', {
          appCode: this.appCode,
          moduleId: this.formData.module,
        });
        this.branchList = res.results;
      } catch (e) {
        this.branchList = [];
        this.catchErrorHandler(e);
      } finally {
        this.isBranchLoading = false;
      }
    },
    // 创建沙箱
    handleConfirm() {
      this.$refs.sandboxForm.validate().then(
        () => {
          this.createSandbox();
        },
        (validator) => {
          console.error(validator);
        }
      );
    },
    toSandboxPage() {
      this.$router.push({
        name: 'sandbox',
        query: {
          code: this.appCode,
          module: this.formData.module,
        },
      });
    },
    async createSandbox() {
      this.dialogLoading = true;
      try {
        const curBranchData = this.branchList.find((v) => v.name === this.formData.branch);
        const data = {
          revision: curBranchData.revision,
          version_type: curBranchData.type,
          version_name: curBranchData.name,
        };
        await this.$store.dispatch('sandbox/createSandbox', {
          appCode: this.appCode,
          moduleId: this.formData.module,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('创建成功！'),
        });
        // 关闭dialog
        this.dialogVisible = false;
        // 跳转沙箱入口
        this.toSandboxPage();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .mb16 {
    margin-bottom: 16px;
  }
  .item-tips {
    color: #979ba5;
    font-size: 12px;
  }
  .line-item {
    display: flex;
    .repo-url {
      color: #3a84ff;
    }
    /deep/ .bk-label {
      width: auto !important;
      padding-right: 8px;
    }
  }
}
</style>
