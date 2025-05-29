<template>
  <div class="app-overview-container">
    <!-- 基本信息 -->
    <section
      class="base-info-wrapper card-style"
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
              <bk-button
                style="padding: 0 6px"
                text
                @click="toAccessApp"
              >
                <i class="paasng-icon paasng-jump-link"></i>
                {{ $t('访问应用') }}
              </bk-button>
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
                v-if="platformFeature.MULTI_TENANT_MODE"
              ></bk-user-display-name>
              <span v-else>{{ baseInfo[key] }}</span>
            </template>
            <span v-else-if="key === 'is_active'">{{ baseInfo[key] ? $t('正常') : $t('下架') }}</span>
            <template v-else>
              {{ key === 'type' ? PAAS_APP_TYPE[baseInfo[key]] : baseInfo[key] || '--' }}
            </template>
          </div>
        </DetailsRow>
      </div>
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
                        v-if="platformFeature.MULTI_TENANT_MODE"
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
import { mapState } from 'vuex';
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
      editDeployCluster: {
        visible: false,
        loading: false,
        row: {},
        cluster: '',
      },
      // 部署集群
      deployClusterList: [],
      PAAS_APP_TYPE,
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    appCode() {
      return this.$route.params.code;
    },
    isEnginelessApp() {
      return this.baseInfo.type === 'engineless_app';
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
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    // 编辑
    handleEditAppName(appName) {
      this.editApp.isEdit = true;
      this.editApp.name = this.editApp.name || appName;
      this.$nextTick(() => {
        this.$refs.appNameInput[0]?.focus();
      });
    },
    // 取消
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
    // 取部署集群列表
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
    // 基本信息访问应用
    toAccessApp() {
      const routeName = this.baseInfo.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary';
      this.$router.push({
        name: routeName,
        params: { id: this.baseInfo.code },
      });
    },
    toLink(url) {
      window.open(url, '_blank');
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
    margin-top: 16px;
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
