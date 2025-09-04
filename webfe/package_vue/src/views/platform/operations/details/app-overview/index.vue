<template>
  <div class="app-overview-container">
    <!-- 基本信息 -->
    <section
      class="base-info-wrapper card-style mb16"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <div class="view-title">{{ $t('基本信息') }}</div>
      <div class="info-wrapper">
        <DetailsRow
          v-for="(val, key) in baseInfoKeys"
          :label-width="150"
          :is-full="true"
          :align="'flex-start'"
          :key="val"
          :label="`${$t(val)}：`"
        >
          <div slot="value">
            <!-- 应用ID -->
            <div v-if="key === 'code'">
              <span>{{ baseInfo[key] }}</span>
            </div>
            <!-- 应用名称 -->
            <div v-else-if="key === 'name'">
              <template v-if="!editApp.isEdit">
                <span>{{ editApp.name || baseInfo[key] || '--' }}</span>
                <bk-button
                  style="padding: 0 6px"
                  text
                  :loading="editApp.loading"
                  @click="handleEditAppName(baseInfo[key])"
                >
                  <i class="paasng-icon paasng-edit-2" />
                  {{ $t('编辑') }}
                </bk-button>
              </template>
              <div
                class="name-edit-warpper"
                v-else
              >
                <bk-input
                  style="width: 160px"
                  ref="appNameInput"
                  v-model="editApp.name"
                  @enter="updataAppName"
                ></bk-input>
                <!-- 保存 -->
                <bk-button
                  class="save"
                  :icon="editApp.loading ? 'loading' : 'check-1'"
                  :disabled="editApp.loading"
                  @click="updataAppName"
                ></bk-button>
                <bk-button
                  icon="close"
                  class="cancel"
                  @click="handleCancel"
                ></bk-button>
              </div>
            </div>
            <span v-else-if="key === 'app_tenant_mode'">
              {{ baseInfo[key] ? (baseInfo[key] === 'single' ? $t('单租户') : $t('全租户')) : '--' }}
            </span>
            <template v-else-if="['creator'].includes(key)">
              <bk-user-display-name
                :user-id="baseInfo[key]"
                v-if="isMultiTenantDisplayMode"
              ></bk-user-display-name>
              <span v-else>{{ baseInfo[key] }}</span>
            </template>
            <template v-else-if="key === 'category'">
              <span>{{ baseInfo[key] || '--' }}</span>
              <bk-button
                style="padding: 0 6px"
                text
                :loading="editCategory.loading"
                @click="handleEditCategory"
              >
                <i class="paasng-icon paasng-edit-2" />
                {{ $t('编辑') }}
              </bk-button>
            </template>
            <span v-else-if="key === 'is_active'">{{ baseInfo[key] ? $t('正常') : $t('下架') }}</span>
            <template v-else>
              {{ key === 'type' ? PAAS_APP_TYPE[baseInfo[key]] : baseInfo[key] || '--' }}
            </template>
          </div>
        </DetailsRow>
      </div>
    </section>

    <section
      class="base-info-wrapper card-style mb16"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <div class="view-title">{{ $t('快捷操作') }}</div>
      <DetailsRow
        :label-width="150"
        :label="`${$t('应用权限')}：`"
        :align="'flex-start'"
        class="mb10"
      >
        <div slot="value">
          {{ isAppAdmin ? $t('你已经是该应用的管理员') : $t('你不具备管理员权限') }}
          <!-- 非管理员 -->
          <span
            v-if="!isAppAdmin"
            class="btn-wrapper ml10"
            v-bk-tooltips="{
              content: $t('应用所属租户为：{a}，您不是该租户下的用户，无法添加为管理员', { a: appTenantId }),
              disabled: !isBecomeAdminDisabled,
            }"
          >
            <!-- 跨租户不能操作 -->
            <bk-button
              theme="primary"
              :disabled="isBecomeAdminDisabled"
              :loading="adminConfig.appLoading"
              @click="becomeAppAdmin"
            >
              {{ $t('成为管理员') }}
            </bk-button>
          </span>
          <template v-else>
            <bk-button
              class="ml10"
              theme="danger"
              :loading="adminConfig.appLoading"
              @click="exitApp"
            >
              {{ $t('退出应用') }}
            </bk-button>
            <bk-button
              class="ml10"
              text
              @click="toAccessApp"
            >
              <i class="paasng-icon paasng-jump-link"></i>
              {{ $t('访问应用') }}
            </bk-button>
          </template>
        </div>
      </DetailsRow>
      <DetailsRow
        v-if="appAdmin?.show_plugin_admin_operations"
        :label-width="150"
        :label="`${$t('插件权限')}：`"
        :align="'flex-start'"
      >
        <div slot="value">
          {{ isPluginAdmin ? $t('你已经是该插件的管理员') : $t('你不具备管理员权限') }}
          <span
            v-if="!isPluginAdmin"
            class="btn-wrapper ml10"
            v-bk-tooltips="{
              content: $t('插件所属租户为：{a}，您不是该租户下的用户，无法添加为管理员', { a: appTenantId }),
              disabled: !isBecomeAdminDisabled,
            }"
          >
            <bk-button
              theme="primary"
              :disabled="isBecomeAdminDisabled"
              :loading="adminConfig.pluginLoading"
              @click="becomePluginAdmin"
            >
              {{ $t('成为管理员') }}
            </bk-button>
          </span>
          <template v-else>
            <bk-button
              class="ml10"
              theme="danger"
              :loading="adminConfig.pluginLoading"
              @click="exitPlugin"
            >
              {{ $t('退出插件管理员') }}
            </bk-button>
            <bk-button
              class="ml10"
              text
              @click="toAccessPlugin"
            >
              <i class="paasng-icon paasng-jump-link"></i>
              {{ $t('访问插件') }}
            </bk-button>
          </template>
        </div>
      </DetailsRow>
    </section>

    <!-- 模块信息-外链应用不展示 -->
    <section
      v-if="!isEnginelessApp && !isLoading"
      class="module-info-wrapper card-style"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <div class="view-title mb10">{{ $t('模块信息') }}</div>
      <bk-collapse
        v-model="activeNames"
        ext-cls="module-collapse-cls"
      >
        <bk-collapse-item
          v-for="(item, index) in moduleData"
          :name="item.name"
          :key="item.name"
          :hide-arrow="true"
          :class="[{ mb16: index !== moduleData.length - 1 }, { default: item.is_default }]"
        >
          <div class="module-tit">
            <div class="name-info">
              <i class="paasng-icon paasng-right-shape"></i>
              {{ item.name }}
              <span v-if="item.is_default">{{ $t('(主)') }}</span>
            </div>
            <div class="env-info">
              <div>{{ $t('预发布环境') }}：{{ getDeployInfo(item.environment, 'stag') }}</div>
              <div>{{ $t('生产环境') }}：{{ getDeployInfo(item.environment, 'prod') }}</div>
            </div>
          </div>
          <div
            slot="content"
            class="module-main-wrapper"
          >
            <div
              v-for="env in item.environment"
              :key="env.name"
              :class="['env', env.name]"
            >
              <div class="env-tit">{{ env.name === 'stag' ? $t('预发布环境') : $t('生产环境') }}</div>
              <DetailsRow
                v-for="(val, key) in moduleKeys"
                :label-width="150"
                :is-full="true"
                :align="'flex-start'"
                :key="val"
                :label="`${$t(val)}：`"
              >
                <div slot="value">
                  <div v-if="key === 'is_deployed'">
                    {{ env[key] ? $t('已部署') : $t('未部署') }}
                    <bk-button
                      v-if="env.exposed_url"
                      style="padding: 0 6px"
                      text
                      @click="toLink(env.exposed_url)"
                    >
                      <i class="paasng-icon paasng-jump-link"></i>
                      {{ $t('访问') }}
                    </bk-button>
                  </div>
                  <div v-else-if="key === 'deploy_cluster'">
                    <span>{{ env[key] || '--' }}</span>
                    <bk-button
                      style="padding: 0 6px"
                      text
                      @click="handleShowEditClusterDialog(item.name, env.name, env.deploy_cluster)"
                    >
                      <i class="paasng-icon paasng-edit-2" />
                      {{ $t('编辑') }}
                    </bk-button>
                  </div>
                  <template v-else-if="key === 'recent_operation'">
                    <template v-if="env[key]">
                      <div
                        v-if="isMultiTenantDisplayMode"
                        class="text-ellipsis"
                        v-bk-overflow-tips
                      >
                        <bk-user-display-name :user-id="env[key]?.operator"></bk-user-display-name>
                        <span>&nbsp;{{ env[key]?.message }}</span>
                      </div>
                      <span v-else>{{ `${env[key]?.operator} ${env[key]?.message}` }}</span>
                    </template>
                    <span v-else>--</span>
                  </template>
                  <template v-else>{{ env[key] ?? '--' }}</template>
                </div>
              </DetailsRow>
            </div>
          </div>
        </bk-collapse-item>
      </bk-collapse>
    </section>

    <!-- 修改应用分类弹窗 -->
    <bk-dialog
      v-model="editCategory.visible"
      header-position="left"
      theme="primary"
      width="560"
      :mask-close="false"
      :loading="editCategory.loading"
      @confirm="handleConfirmCategory"
    >
      <div
        slot="header"
        class="deploy-cluster-header-cls"
      >
        {{ $t('修改应用分类') }}
      </div>
      <div class="cluster-select-cls">
        <div class="label">{{ $t('应用分类') }}</div>
        <bk-select
          style="width: 100%"
          v-model="editCategory.selectedCategory"
          :clearable="false"
          :searchable="true"
        >
          <bk-option
            v-for="option in editCategory.categoryList"
            :key="option.id"
            :id="option.id"
            :name="option.name"
          ></bk-option>
        </bk-select>
      </div>
    </bk-dialog>

    <!-- 修改部署集群弹窗 -->
    <bk-dialog
      v-model="editDeployCluster.visible"
      header-position="left"
      theme="primary"
      width="560"
      :mask-close="false"
      :loading="editDeployCluster.loading"
      @confirm="handleConfirm"
    >
      <div
        slot="header"
        class="deploy-cluster-header-cls"
      >
        {{ $t('修改部署集群') }}
        <span class="sub-tit ml10">
          <span>{{ $t('模块') }}：{{ editDeployCluster.row.moduleName }}</span>
          <span class="ml10">
            {{ $t('环境') }}：{{ editDeployCluster.row.envName === 'stag' ? $t('预发布环境') : $t('生产环境') }}
          </span>
        </span>
      </div>
      <bk-alert
        type="warning"
        :title="$t('修改后需要重新部署才能生效，并且需要手动清理原有集群中的进程。')"
      ></bk-alert>
      <div class="cluster-select-cls">
        <div class="label">{{ $t('部署集群') }}</div>
        <bk-select
          style="width: 100%"
          v-model="editDeployCluster.cluster"
          :clearable="false"
          :searchable="true"
        >
          <bk-option
            v-for="option in deployClusterList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
        </bk-select>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import { mapState, mapGetters } from 'vuex';
import { PAAS_APP_TYPE } from '@/common/constants';

export default {
  name: 'appOverview',
  components: {
    DetailsRow,
  },
  data() {
    return {
      isLoading: true,
      baseInfoKeys: {
        code: '应用 ID',
        name: '应用名称',
        app_tenant_mode: '租户模式',
        app_tenant_id: '租户 ID',
        type: '应用类型',
        category: '应用分类',
        is_active: '状态',
        creator: '创建人',
        created_humanized: '创建时间',
      },
      moduleKeys: {
        is_deployed: '状态',
        deploy_cluster: '部署集群',
        recent_operation: '最近操作',
      },
      baseInfo: {},
      moduleData: [],
      // 模块信息展开项
      activeNames: [],
      editApp: {
        isEdit: false,
        name: '',
        loading: false,
        oldName: '',
      },
      editCategory: {
        visible: false,
        loading: false,
        categoryList: [],
        selectedCategory: null,
      },
      editDeployCluster: {
        visible: false,
        loading: false,
        row: {},
        cluster: '',
      },
      // 部署集群
      deployClusterList: [],
      PAAS_APP_TYPE,
      appAdmin: {},
      adminConfig: {
        appLoading: false,
        pluginLoading: false,
      },
    };
  },
  computed: {
    ...mapState(['platformFeature', 'curUserInfo']),
    ...mapGetters(['tenantId', 'isMultiTenantDisplayMode']),
    appCode() {
      return this.$route.params.code;
    },
    isEnginelessApp() {
      return this.baseInfo.type === 'engineless_app';
    },
    // 当前应用的租户id
    appTenantId() {
      return this.$route.query.tenant;
    },
    isBecomeAdminDisabled() {
      return this.platformFeature.MULTI_TENANT_MODE && this.appTenantId !== this.tenantId;
    },
    // 是否为应用的个管理员
    isAppAdmin() {
      return !!this.appAdmin?.user_is_admin_in_app;
    },
    isPluginAdmin() {
      return !!this.appAdmin?.user_is_admin_in_plugin;
    },
  },
  created() {
    this.getAppDetails();
  },
  methods: {
    // 获取应用详情
    async getAppDetails() {
      try {
        const ret = await this.$store.dispatch('tenantOperations/getAppDetails', {
          appCode: this.appCode,
        });
        this.baseInfo = ret.basic_info || {};
        // 主模块放在前面
        this.moduleData = ret.modules_info?.sort((a, b) => b.is_default - a.is_default) || [];
        if (this.moduleData.length) {
          this.activeNames.push(this.moduleData[0].name);
        }
        this.editApp.oldName = ret.basic_info?.name || '';
        this.appAdmin = ret.app_admin || {};
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    // 编辑应用名
    handleEditAppName(appName) {
      this.editApp.isEdit = true;
      this.editApp.name = this.editApp.name || appName;
      this.$nextTick(() => {
        this.$refs.appNameInput[0]?.focus();
      });
    },
    // 取消编辑应用名
    handleCancel() {
      this.editApp.isEdit = false;
      this.editApp.name = this.editApp.oldName;
    },
    // 更新应用名称
    async updataAppName() {
      const { name, oldName } = this.editApp;
      // 未变化
      if (name === oldName) {
        this.handleCancel();
        return;
      }
      this.$set(this.editApp, 'loading', true);
      try {
        await this.$store.dispatch('tenantOperations/updateAppInfo', {
          appCode: this.appCode,
          data: {
            name,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('应用名称修改成功'),
        });
        this.$set(this.editApp, 'oldName', name);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.editApp.isEdit = false;
        this.$set(this.editApp, 'loading', false);
      }
    },
    // 显示编辑分类对话框
    async handleEditCategory() {
      this.editCategory.visible = true;
      this.editCategory.loading = false;
      await this.getCategoryList();

      // 查找当前分类的ID
      const currentCategory = this.editCategory.categoryList.find((item) => item.name === this.baseInfo.category);
      this.editCategory.selectedCategory = currentCategory ? currentCategory.id : null;
    },
    // 获取分类列表
    async getCategoryList() {
      try {
        const res = await this.$store.dispatch('market/getTags');
        this.editCategory.categoryList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 更新应用分类
    async updateAppCategory() {
      try {
        await this.$store.dispatch('tenantOperations/updateAppCategory', {
          appCode: this.appCode,
          data: {
            category: this.editCategory.selectedCategory,
          },
        });
        this.editCategory.visible = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('应用分类修改成功'),
        });
        this.getAppDetails();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.editCategory.loading = false;
      }
    },
    // 确认修改分类
    handleConfirmCategory() {
      if (!this.editCategory.selectedCategory) return;

      this.editCategory.loading = true;
      this.updateAppCategory();
    },
    // 获取部署集群列表
    async getClusters() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterList');
        this.deployClusterList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleShowEditClusterDialog(moduleName, envName, cluster) {
      this.editDeployCluster.visible = true;
      this.editDeployCluster.cluster = cluster;
      this.getClusters();
      this.editDeployCluster.row = {
        moduleName,
        envName,
        cluster,
      };
    },
    handleConfirm() {
      const { cluster, row } = this.editDeployCluster;
      // 未发生变化
      if (cluster === row.cluster) return;
      this.editDeployCluster.loading = true;
      this.updateDeployCluster();
    },
    // 更新部署集群
    async updateDeployCluster() {
      const { row, cluster } = this.editDeployCluster;
      try {
        await this.$store.dispatch('tenantOperations/updateDeployCluster', {
          appCode: this.appCode,
          moduleId: row.moduleName,
          env: row.envName,
          data: {
            name: cluster,
          },
        });
        this.editDeployCluster.loading = false;
        this.editDeployCluster.visible = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('修改成功'),
        });
        this.getAppDetails();
      } catch (e) {
        this.catchErrorHandler(e);
        this.editDeployCluster.loading = false;
      }
    },
    // 获取部署信息
    getDeployInfo(envData, envKey) {
      const curEnv = envData.find((v) => v.name === envKey);
      return curEnv?.is_deployed ? this.$t('已部署') : this.$t('未部署');
    },
    // 访问应用
    toAccessApp() {
      const routeName = this.baseInfo.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary';
      const route = this.$router.resolve({
        name: routeName,
        params: { id: this.baseInfo.code, moduleId: 'default' },
      });
      this.toLink(route.href);
    },
    // 访问插件
    toAccessPlugin() {
      const route = this.$router.resolve({
        name: 'pluginSummary',
        params: { pluginTypeId: 'bk-saas', id: this.baseInfo.code },
      });
      this.toLink(route.href);
    },
    toLink(url) {
      window.open(url, '_blank');
    },
    setAdminLoading(key, loading) {
      this.$set(this.adminConfig, key, loading);
    },
    // 成为应用应用管理员
    async becomeAppAdmin() {
      this.setAdminLoading('appLoading', true);
      try {
        const params = [
          {
            roles: [{ id: 2 }],
            user: { username: this.curUserInfo.username },
          },
        ];
        await this.$store.dispatch('tenantOperations/addMember', {
          appCode: this.appCode,
          postParams: params,
        });
        await this.getAppDetails();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('您已成功成为应用管理员'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加用户角色失败：')} ${e.detail}`,
        });
      } finally {
        this.setAdminLoading('appLoading', false);
      }
    },
    // 退出应用
    async exitApp() {
      this.setAdminLoading('appLoading', true);
      try {
        await this.$store.dispatch('member/quitApplication', { appCode: this.appCode });
        await this.getAppDetails();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('您已退出应用管理员角色'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('退出应用失败：')} ${e.detail}`,
        });
      } finally {
        this.setAdminLoading('appLoading', false);
      }
    },
    // 成为插件管理员
    async becomePluginAdmin() {
      this.setAdminLoading('pluginLoading', true);
      try {
        await this.$store.dispatch('tenantOperations/becomePluginAdmin', { appCode: this.appCode });
        await this.getAppDetails();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('您已成功成为插件管理员'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.setAdminLoading('pluginLoading', false);
      }
    },
    // 退出插件
    async exitPlugin() {
      this.setAdminLoading('pluginLoading', true);
      try {
        await this.$store.dispatch('tenantOperations/exitPlugin', { appCode: this.appCode });
        await this.getAppDetails();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('您已退出插件管理员角色'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.setAdminLoading('pluginLoading', false);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.app-overview-container {
  i.paasng-jump-link {
    transform: translateY(0);
  }
  .mb16 {
    margin-bottom: 16px !important;
  }
  .btn-wrapper {
    display: inline-block;
  }
  /deep/ .details-row {
    margin-top: 0;
    .label,
    .value {
      font-size: 14px;
      height: 40px;
      line-height: 40px;
    }
    .value {
      padding-left: 10px;
    }
  }
  .base-info-wrapper {
    padding: 16px 24px;
  }
  .view-title {
    font-size: 14px;
    font-weight: 700;
    color: #313238;
    line-height: 22px;
    margin-bottom: 6px;
  }
  .info-wrapper {
    display: grid;
    grid-template-columns: repeat(2, 1fr); /* 创建两列等宽的网格 */
    gap: 0; /* 消除列与列之间的间距 */
    .name-edit-warpper {
      display: flex;
      align-items: center;
      gap: 8px;
      .save,
      .cancel {
        display: flex;
        justify-content: center;
        width: 32px;
      }
      .save {
        color: #3a84ff;
      }
    }
  }
  .module-info-wrapper {
    padding: 16px;
    .module-tit {
      height: 100%;
      display: flex;
      align-items: center;
      font-weight: 500;
      font-size: 14px;
      color: #313238;
      .name-info {
        height: 100%;
        width: 175px;
        font-weight: 700;
      }
      .env-info {
        height: 100%;
        flex: 1;
        display: flex;
        font-weight: 400;
        color: #4d4f56;
        div {
          width: 50%;
        }
      }
      i {
        font-size: 14px;
        color: #4d4f56;
        transition: all 0.2s;
        transform: translateY(-1px);
      }
    }
    .module-collapse-cls {
      .default /deep/ .bk-collapse-item-header {
        background: #f0f5ff;
      }
      /deep/ .bk-collapse-item-active {
        i.paasng-right-shape {
          transform: rotate(90deg) translateX(-1px);
        }
        .env-info {
          display: none;
        }
      }
      /deep/ .bk-collapse-item-header {
        height: 40px;
        background: #f5f7fa;
        border-radius: 2px 2px 0 0;
      }
      /deep/ .bk-collapse-item-content {
        padding-top: 16px;
      }
    }
    .module-main-wrapper {
      display: flex;
      flex-direction: row-reverse;
      .env {
        width: 50%;
      }
      .env-tit {
        width: 150px;
        padding-right: 14px;
        text-align: right;
        font-weight: 700;
        font-size: 14px;
        line-height: 20px;
        color: #4d4f56;
        margin-bottom: 6px;
      }
    }
  }
}
.deploy-cluster-header-cls {
  color: #313238;
  .sub-tit span {
    font-size: 14px;
    color: #979ba5;
  }
}
.cluster-select-cls {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  .label {
    flex-shrink: 0;
  }
}
</style>
