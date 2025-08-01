<template>
  <div>
    <bk-sideslider
      :is-show.sync="sidesliderVisible"
      :quick-close="true"
      width="960"
      @shown="handleShown"
    >
      <div
        slot="header"
        class="header-box"
      >
        <div class="title-wrapper">
          <div class="title">{{ $t('沙箱开发') }}</div>
          <span
            class="sub-tit"
            v-bk-overflow-tips
          >
            {{ $t('沙箱提供云端开发环境，可以在线修改运行代码。') }}
          </span>
        </div>
        <bk-button
          :theme="'primary'"
          text
          @click="toSandboxGuide"
        >
          {{ $t('沙箱开发指引') }}
          <i class="paasng-jump-link paasng-icon"></i>
        </bk-button>
      </div>
      <div
        class="sideslider-content"
        slot="content"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      >
        <bk-alert
          type="info"
          :title="$t('沙箱会复用 “预发布环境” 的增强服务和环境变量。')"
        ></bk-alert>
        <template v-if="sandboxEnvList.length">
          <div class="table-title">{{ $t('已创建的沙箱的模块') }}</div>
          <bk-table
            :data="sandboxEnvList"
            :outer-border="false"
            size="small"
          >
            <bk-table-column
              :label="$t('模块')"
              prop="module_name"
            ></bk-table-column>
            <bk-table-column :label="$t('沙箱分支')">
              <template slot-scope="{ row }">
                {{ row.version_info?.version_name || '--' }}
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('创建时间')"
              prop="created_at"
            ></bk-table-column>
            <bk-table-column
              :label="$t('操作')"
              width="180"
            >
              <template slot-scope="{ row }">
                <bk-button
                  :theme="'primary'"
                  text
                  @click="toSandboxPage(row.module_name, row.code)"
                >
                  {{ $t('进入') }}
                </bk-button>
                <bk-popconfirm
                  trigger="click"
                  ext-cls="sandbox-destroy-cls"
                  width="288"
                  @confirm="handleDestroy(row)"
                >
                  <div slot="content">
                    <div class="custom">
                      <i class="content-icon bk-icon icon-info-circle-shape pr5"></i>
                      <div class="content-text">{{ $t('确认销毁沙箱开发环境吗？') }}</div>
                    </div>
                  </div>
                  <bk-button
                    :theme="'primary'"
                    text
                    class="ml10"
                  >
                    {{ $t('销毁') }}
                  </bk-button>
                </bk-popconfirm>
              </template>
            </bk-table-column>
          </bk-table>
        </template>
        <template v-if="nonCreatedSandboxModuleList.length">
          <div class="table-title">{{ $t('未创建的沙箱的模块') }}</div>
          <bk-table
            :data="nonCreatedSandboxModuleList"
            :outer-border="false"
            size="small"
          >
            <bk-table-column
              :label="$t('模块')"
              prop="name"
            ></bk-table-column>
            <bk-table-column :label="$t('构建目录')">
              <template slot-scope="{ row }">
                {{ row.repo?.source_dir || '--' }}
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('部署分支 / TAG')">
              <template slot-scope="{ row }">
                {{ row.versionInfo?.version_name || '--' }}
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('操作')"
              width="180"
            >
              <template slot-scope="{ row }">
                <span
                  v-bk-tooltips="{
                    content: disabledContent,
                    disabled: row.isCreationAllowed,
                    width: 310,
                    allowHTML: true,
                  }"
                >
                  <bk-button
                    :theme="'primary'"
                    text
                    :disabled="!row.isCreationAllowed"
                    @click="showCreateSandboxDialog(row)"
                  >
                    {{ $t('创建沙箱') }}
                  </bk-button>
                </span>
              </template>
            </bk-table-column>
          </bk-table>
        </template>
      </div>
    </bk-sideslider>
    <!-- 创建沙箱 -->
    <bk-dialog
      v-model="sandboxDialog.visible"
      theme="primary"
      header-position="left"
      :mask-close="false"
      :title="$t('创建沙箱')"
      ext-cls="create-sandbox-dialog-cls"
    >
      <div
        slot="header"
        class="dialog-title"
      >
        <div class="title">{{ $t('创建沙箱') }}</div>
        <div class="sub-title">{{ `${$t('模块')}：${sandboxDialog.name}` }}</div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :loading="sandboxDialog.btnLoading"
          bk-trace="{id: 'sandbox', action: 'new', category: '云原生应用'}"
          @click="handleConfirm"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          type="submit"
          class="ml8"
          @click="sandboxDialog.visible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
      <bk-form
        form-type="vertical"
        :model="sandboxDialog"
        ref="sandboxForm"
        :rules="rules"
      >
        <bk-form-item
          :label="$t('代码分支')"
          :required="true"
          :property="'branch'"
        >
          <bk-select
            :disabled="false"
            v-model="sandboxDialog.branch"
            searchable
            :loading="sandboxDialog.loading"
          >
            <bk-option
              v-for="option in branchList"
              :key="option.name"
              :id="option.name"
              :name="option.name"
            ></bk-option>
          </bk-select>
          <p
            class="dialog-tip"
            slot="tip"
          >
            {{ $t('仅支持通过代码分支创建沙箱，不支持选择 Tag') }}
          </p>
        </bk-form-item>
        <bk-form-item :label="$t('使用的增强服务')">
          <bk-select
            style="height: 100%"
            v-model="servicesConfig.list"
            :loading="servicesConfig.loading"
            searchable
            multiple
            display-tag
          >
            <bk-option
              v-for="option in servicesConfig.servicelist"
              :key="option?.service?.name"
              :id="option?.service?.name"
              :name="option?.service?.display_name"
            ></bk-option>
          </bk-select>
          <p
            class="dialog-tip"
            slot="tip"
          >
            {{ $t('沙箱会复用已选中增强服务 “预发布环境” 的环境变量') }}
          </p>
        </bk-form-item>
      </bk-form>
      <!-- 错误提示 -->
      <div
        class="customize-alert-wrapper"
        v-if="isShowErrorAlert"
      >
        <p class="text">
          <i class="paasng-icon paasng-remind exclamation-cls"></i>
          <span>{{ errorInfo?.message || errorInfo?.detail }}</span>
        </p>
        <div class="right-link">
          <template v-if="errorInfo.code === 'NEED_TO_BIND_OAUTH_INFO'">
            <bk-button
              class="link-text"
              :text="true"
              @click="hanndleToAuthorize"
            >
              {{ $t('去授权') }}
              <i class="paasng-icon paasng-jump-link" />
            </bk-button>
            <div class="line"></div>
          </template>
          <!-- 刷新代码分支 -->
          <bk-button
            class="link-text"
            :text="true"
            @click="getModuleBranches(sandboxDialog.name)"
          >
            {{ $t('刷新') }}
            <i
              class="paasng-icon paasng-refresh-line"
              v-if="!sandboxDialog.loading"
            />
            <round-loading
              class="round-loading-cls"
              v-else
            />
          </bk-button>
        </div>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
export default {
  name: 'SandboxSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    env: {
      type: String,
    },
    moduleDeployList: {
      type: Array,
      default: [],
    },
  },
  data() {
    return {
      sandboxEnvList: [],
      isTableLoading: false,
      // 代码分支
      branchList: [],
      // 创建沙箱
      sandboxDialog: {
        visible: false,
        loading: false,
        btnLoading: false,
        name: '',
        branch: '',
        versionInfo: {},
      },
      disabledContent: this.$t(
        '<p>同时满足下列条件的模块才能新建沙箱环境：</p><p>1. 使用“蓝鲸 Buildpack”构建且开发语言为 Python</p>2. 已经部署到预发布环境'
      ),
      errorInfo: {},
      isShowErrorAlert: false,
      dataReady: false,
      servicesConfig: {
        list: [],
        servicelist: [],
        loading: false,
      },
      rules: {
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
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    appCode() {
      return this.$route.params.id;
    },
    curAppModuleList() {
      return this.$store.state.curAppModuleList || [];
    },
    // 未创建的沙箱的模块
    nonCreatedSandboxModuleList() {
      if (!this.dataReady) return []; // 数据未就绪返回空
      // 过滤和合并模块信息
      const result = this.curAppModuleList.reduce((acc, module) => {
        const currentModuleDeploy = this.moduleDeployList.find((deploy) => deploy.name === module.name) || {};
        // 检查该模块是否不在沙箱环境列表中
        const isNotInSandbox = !this.sandboxEnvList.some((sandbox) => sandbox.module_name === module.name);
        if (isNotInSandbox) {
          const itemData = {
            ...module,
            ...currentModuleDeploy,
            isCreationAllowed:
              module.web_config?.build_method === 'buildpack' &&
              module.language?.toLowerCase() === 'python' &&
              currentModuleDeploy?.isDeployed,
          };
          acc.push(itemData);
        }
        return acc;
      }, []);
      // 不能启用的模块放在末尾
      return result.sort((a, b) => {
        if (a.isCreationAllowed === b.isCreationAllowed) return 0;
        return a.isCreationAllowed ? -1 : 1;
      });
    },
  },
  methods: {
    // 新建沙箱前置检查
    async createSandboxPreDeployCheck() {
      try {
        const res = await this.$store.dispatch('sandbox/createSandboxPreDeployCheck', {
          appCode: this.appCode,
        });
        return res.result ?? false;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    insufficientResourcesNotify() {
      const h = this.$createElement;
      this.$bkInfo({
        subHeader: h(
          'div',
          {
            class: 'sandbox-info-box',
          },
          [
            h('i', { class: 'paasng-icon paasng-paas-remind-fill' }, null),
            h('div', { class: 'title' }, [
              h('p', null, this.$t('沙箱资源不足')),
              h(
                'p',
                { class: 'tip-text' },
                this.$t('沙箱功能正在灰度开放，目前沙箱资源已申请完。如需体验，请联系 BK 助手。')
              ),
            ]),
          ]
        ),
        extCls: 'sandbox-info-cls',
        width: 360,
        showFooter: false,
      });
    },
    handleShown() {
      this.getSandboxList();
    },
    toSandboxPage(module, devSandboxCode) {
      this.$router.push({
        name: 'sandbox',
        query: {
          code: this.appCode,
          module,
          devSandboxCode,
        },
      });
    },
    // 获取沙箱列表
    async getSandboxList() {
      this.dataReady = false;
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxList', {
          appCode: this.appCode,
        });
        this.sandboxEnvList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
        this.dataReady = true;
      }
    },
    // 销毁沙箱
    async handleDestroy(row) {
      try {
        await this.$store.dispatch('sandbox/destroySandbox', {
          appCode: this.appCode,
          moduleId: row.module_name,
          devSandboxCode: row.code,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('销毁成功！'),
        });
        this.getSandboxList();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 沙箱开发指引
    toSandboxGuide() {
      window.open(this.GLOBAL.DOC.SANDBOX_DEVELOPMENT_GUIDE, '_blank');
    },
    // 获取对应模块代码分支
    async getModuleBranches(moduleId, versionName) {
      this.sandboxDialog.loading = true;
      this.branchList = [];
      try {
        const res = await this.$store.dispatch('deploy/getModuleBranches', {
          appCode: this.appCode,
          moduleId,
        });
        this.isShowErrorAlert = false;
        this.branchList = res.results.filter((item) => item.type === 'branch');
        // 代码分支默认值
        const branch = this.branchList.find((v) => v.name === versionName) || this.branchList[0];
        this.sandboxDialog.branch = branch.name;
      } catch (e) {
        this.branchList = [];
        this.isShowErrorAlert = true;
        this.errorInfo = e;
      } finally {
        this.sandboxDialog.loading = false;
      }
    },
    // 创建沙箱弹窗
    async showCreateSandboxDialog(row) {
      // 沙箱前置检查判断资源是否充足
      const result = await this.createSandboxPreDeployCheck();
      if (!result) {
        // 提示资源不足
        this.insufficientResourcesNotify();
        return;
      }
      this.getServices(row.name);
      this.sandboxDialog.visible = true;
      this.sandboxDialog.name = row.name;
      this.sandboxDialog.branch = '';
      this.getModuleBranches(row.name, row.versionInfo?.version_name);
    },
    handleConfirm() {
      this.$refs.sandboxForm.validate().then(
        () => {
          this.confirmSandboxCreation();
        },
        (validator) => {
          console.error(validator);
        }
      );
    },
    // 确认创建沙箱
    async confirmSandboxCreation() {
      this.sandboxDialog.btnLoading = true;
      try {
        const curBranchData = this.branchList.find((v) => v.name === this.sandboxDialog.branch);
        const data = {
          enable_code_editor: true,
          inject_staging_env_vars: true,
          source_code_version_info: {
            revision: curBranchData.revision,
            version_type: curBranchData.type,
            version_name: curBranchData.name,
          },
          enabled_addons_services: this.servicesConfig.list,
        };
        const ret = await this.$store.dispatch('sandbox/createSandbox', {
          appCode: this.appCode,
          moduleId: this.sandboxDialog.name,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('创建成功！'),
        });
        // 关闭弹窗
        this.sandboxDialog.visible = false;
        // 跳转沙箱入口
        this.toSandboxPage(this.sandboxDialog.name, ret.code);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.sandboxDialog.btnLoading = false;
      }
    },
    // 去授权
    hanndleToAuthorize() {
      const route = this.$router.resolve({ name: 'serviceCode' });
      window.open(route.href, '_blank');
    },
    // 获取增强服务
    async getServices(moduleId) {
      this.servicesConfig.loading = true;
      try {
        const { bound = [], shared = [] } = await this.$store.dispatch('service/getServicesList', {
          appCode: this.appCode,
          moduleId,
        });
        const enabledServices = [...bound, ...shared];
        this.servicesConfig = {
          ...this.servicesConfig,
          servicelist: enabledServices,
          list: enabledServices.map((item) => item.service?.name),
        };
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.servicesConfig.loading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.customize-alert-wrapper {
  margin-top: 12px;
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
.header-box {
  display: flex;
  justify-content: space-between;
  .bk-button-text {
    flex-shrink: 0;
    font-size: 12px;
  }
  .title-wrapper {
    width: 700px;
    display: flex;
    align-items: center;
    .title {
      flex-shrink: 0;
    }
    .sub-tit {
      position: relative;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      font-size: 14px;
      color: #979ba5;
      line-height: 22px;
      padding-left: 9px;
      margin-left: 9px;
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        width: 1px;
        height: 14px;
        background-color: #dcdee5;
        transform: translateY(-50%);
      }
    }
  }
}
.create-sandbox-dialog-cls {
  .dialog-title {
    display: flex;
    align-items: center;
    .title {
      font-size: 20px;
      color: #313238;
      line-height: 28px;
    }
    .sub-title {
      position: relative;
      margin-left: 20px;
      font-size: 14px;
      color: #979ba5;
      line-height: 22px;
      &::before {
        content: '';
        position: absolute;
        left: -10px;
        top: 50%;
        width: 1px;
        height: 14px;
        transform: translateY(-50%);
        background-color: #dcdee5;
      }
    }
  }
  .dialog-tip {
    margin-top: 3px;
    font-size: 12px;
    line-height: 20px;
    color: #979ba5;
  }
}
.sideslider-content {
  padding: 24px;
  .table-title {
    margin: 20px 0 8px 0;
    font-weight: 700;
    line-height: 22px;
    font-size: 14px;
    color: #313238;
  }
}
.sandbox-destroy-cls {
  .custom {
    font-size: 14px;
    line-height: 24px;
    color: #63656e;
    padding-bottom: 16px;
    .content-icon {
      color: #ea3636;
      position: absolute;
      top: 22px;
    }
    .content-text {
      display: inline-block;
      margin-left: 20px;
    }
  }
}
</style>
<style lang="scss">
.sandbox-info-cls {
  .bk-info-box .bk-dialog-sub-header {
    padding: 0 16px 30px !important;
  }
  .sandbox-info-box {
    display: flex;
    i {
      transform: translateY(2px);
      margin-right: 5px;
      color: #ff9c01;
    }
    color: #313238;
    .tip-text {
      margin-top: 8px;
      font-size: 12px;
      color: #63656e;
    }
  }
}
</style>
