<template>
  <div
    class="deploy-module-content"
    v-bkloading="{ isLoading: listLoading, opacity: 1 }"
  >
    <bk-alert
      type="info"
      :show-icon="false"
      class="mt20 mb20 alert-cls"
      v-if="isWatchOfflineing"
    >
      <div
        class="flex-row align-items-center"
        slot="title"
      >
        <div class="fl">
          <round-loading
            size="small"
            ext-cls="deploy-round-loading"
          />
        </div>
        <p class="deploy-pending-text pl20">
          {{ $t('模块') }} {{ curDeploymentInfoItem.module_name }} {{ $t('正在下架中...') }}
        </p>
      </div>
    </bk-alert>
    <div v-if="deploymentInfoData.length">
      <!-- 拖拽排序 -->
      <draggable
        v-model="deploymentInfoData"
        :handle="'.paasng-deploy-item-dot'"
        @end="draggableEnd"
      >
        <div
          class="deploy-module-list"
          v-for="(deploymentInfo, index) in deploymentInfoData"
          :key="deploymentInfo.name"
        >
          <div class="deploy-module-item">
            <!-- 预览模式 / 详情模式 / 未部署 -->
            <section class="top-info-wrapper">
              <!-- 已部署 -->
              <div class="left-info">
                <div class="module">
                  <i class="icon paasng-icon paasng-deploy-item-dot"></i>
                  <div
                    @click="handleOpenUrl(deploymentInfo.exposed_url)"
                    :class="['module-name-wrapper', { link: deploymentInfo.exposed_url }]"
                    v-bk-tooltips="{ content: $t('访问模块'), disabled: !deploymentInfo.exposed_url, distance: -3 }"
                  >
                    <span class="name">{{ deploymentInfo.module_name }}</span>
                    <div
                      v-if="deploymentInfo.exposed_url"
                      class="access-entrance"
                    >
                      <i class="paasng-icon paasng-jump-link ml10"></i>
                    </div>
                  </div>
                </div>
                <!-- 最后一次是部署成功状态则展示 -->
                <template v-if="deploymentInfo.state.deployment.latest_succeeded">
                  <!-- smart应用 -->
                  <div
                    class="flex-row"
                    v-if="isSmartApp"
                  >
                    <div class="version">
                      <span class="label">{{ $t('版本：') }}</span>
                      <span class="value">
                        {{ deploymentInfo.version_info.revision }}
                      </span>
                    </div>
                  </div>
                  <!-- 仅镜像 -->
                  <div
                    class="flex-row"
                    v-else-if="deploymentInfo.build_method === 'custom_image'"
                  >
                    <div class="version">
                      <span class="label">{{ $t('镜像Tag：') }}</span>
                      <span class="value">
                        {{
                          deploymentInfo.state.deployment.latest_succeeded.version_info.version_name.substring(0, 16)
                        }}
                      </span>
                    </div>
                  </div>
                  <!-- buildpack、dockerfile 展示版本/分支, smartApp 展示版本 -->
                  <div v-else>
                    <!-- 源码分支 -->
                    <div
                      class="flex-row"
                      v-if="deploymentInfo.version_info.version_type === 'branch'"
                    >
                      <div class="version">
                        <span class="label">{{ $t('版本：') }}</span>
                        <span class="value">
                          {{ deploymentInfo.version_info.revision.substring(0, 8) }}
                        </span>
                      </div>
                      <template v-if="!isSmartApp">
                        <div class="line"></div>
                        <div class="branch">
                          <span class="label">{{ $t('分支：') }}</span>
                          <span class="value">
                            {{ deploymentInfo.version_info.version_name }}
                          </span>
                        </div>
                      </template>
                    </div>
                  </div>
                </template>
                <template v-else-if="!deploymentInfo.state.deployment.latest">
                  <div class="not-deployed">{{ $t('暂未部署') }}</div>
                </template>
                <template v-else-if="isRemoved(deploymentInfo)">
                  <div class="not-deployed">{{ $t('已下架') }}</div>
                </template>
                <template v-else>
                  <div class="not-deployed">
                    <span v-bk-tooltips="{ content: 'Error: ' + deploymentInfo.state.deployment?.latest?.err_detail }">
                      <i class="paasng-icon paasng-info-line info-icon mr5" />
                      {{ $t('暂未成功部署') }}
                    </span>
                  </div>
                </template>
              </div>
              <div class="right-btn">
                <span v-if="!!deploymentInfo.state.deployment.pending">
                  <bk-button
                    v-if="deploymentInfo.state.deployment.pending.has_requested_in"
                    :theme="'primary'"
                    class="mr10"
                    size="small"
                    text
                  >
                    {{ $t('正在中断部署...') }}
                  </bk-button>
                  <bk-button
                    v-else
                    :theme="'primary'"
                    class="mr10"
                    size="small"
                    text
                    @click="handleShowDeploy(deploymentInfo)"
                  >
                    {{ $t('部署详情') }}
                  </bk-button>
                </span>
                <bk-button
                  :theme="'primary'"
                  class="mr10"
                  size="small"
                  @click="handleDeploy(deploymentInfo, index)"
                  :disabled="!!deploymentInfo.state.offline.pending || !!deploymentInfo.state.deployment.pending"
                  :loading="!!deploymentInfo.state.deployment.pending || (curDeployItemIndex === index && yamlLoading)"
                >
                  {{ $t('部署') }}
                </bk-button>
                <bk-button
                  :theme="'default'"
                  class="mr10"
                  size="small"
                  @click="handleOfflineApp(deploymentInfo)"
                  :disabled="
                    !!deploymentInfo.state.offline.pending ||
                    !!deploymentInfo.state.deployment.pending ||
                    !deploymentInfo.state.deployment.latest_succeeded
                  "
                  :loading="!!deploymentInfo.state.offline.pending"
                >
                  {{ $t('下架') }}
                </bk-button>
                <bk-button
                  :theme="'default'"
                  ext-cls="module-config-btn"
                  size="small"
                  v-bk-tooltips="$t('模块配置')"
                  @click="handleToModuleConfig(deploymentInfo.module_name)"
                >
                  <i class="paasng-icon paasng-configuration-line"></i>
                </bk-button>
              </div>
            </section>
            <!-- 内容 -->
            <section class="main">
              <!-- 详情表格 -->
              <deploy-detail
                v-if="deploymentInfo.isExpand"
                :rv-data="rvData"
                :index="index"
                :deployment-info="deploymentInfo"
                :environment="environment"
                :module-name="deploymentInfo.module_name"
                :is-dialog-show-sideslider="isDialogShowSideslider"
              />
              <!-- 预览 -->
              <deploy-preview
                :deployment-info="deploymentInfo"
                v-if="!deploymentInfo.isExpand"
              />
              <div
                class="operation-wrapper"
                v-if="deploymentInfo.processes.length || deploymentInfo.proc_specs.length"
              >
                <div
                  class="btn"
                  @click="handleChangePanel(deploymentInfo)"
                >
                  {{ deploymentInfo.isExpand ? $t('收起') : $t('展开详情') }}
                  <i
                    class="paasng-icon paasng-ps-arrow-down"
                    v-if="!deploymentInfo.isExpand"
                  ></i>
                  <i
                    class="paasng-icon paasng-ps-arrow-up"
                    v-else
                  ></i>
                </div>
              </div>
            </section>
          </div>
        </div>
      </draggable>
    </div>

    <bk-dialog
      v-model="offlineAppDialog.visiable"
      width="450"
      :title="disableModuleTitle"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="offlineAppDialog.isLoading"
      :ok-text="$t('下架')"
      :cancel-text="$t('取消')"
      @confirm="confirmOfflineApp"
      @cancel="cancelOfflineApp"
    >
      <div class="tl">
        {{ $t('将模块从') }}
        <em>{{ environment === 'stag' ? $t('预发布环境') : $t('生产环境') }}</em>
        {{ $t('下架，会停止当前模块下所有进程，增强服务等模块的资源仍然保留。') }}
      </div>
    </bk-dialog>
    <deploy-dialog
      :show.sync="isShowDialog"
      :environment="environment"
      :deployment-info="curDeploymentInfoItem"
      :rv-data="rvData"
      @refresh="handleListRefresh"
      @showSideslider="isDialogShowSideslider = true"
    ></deploy-dialog>

    <bk-sideslider
      :is-show.sync="isShowSideslider"
      :title="$t('部署日志')"
      :width="820"
      :quick-close="true"
      :before-close="handleCloseProcessWatch"
    >
      <div slot="content">
        <!-- :deployment-id="curDeploymentInfoItem.state.deployment.pending.id" -->
        <deploy-status-detail
          ref="deployStatusRef"
          :environment="environment"
          :deployment-id="curDeploymentInfoItem.state?.deployment?.pending?.id"
          :deployment-info="curDeploymentInfoItem"
          :rv-data="rvData"
          @close="handleCloseSideslider"
        ></deploy-status-detail>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import deployDetail from './deploy-detail';
import deployPreview from './deploy-preview';
import deployDialog from './deploy-dialog';
import deployStatusDetail from './deploy-status-detail';
import appBaseMixin from '@/mixins/app-base-mixin';
import draggable from 'vuedraggable';
import { cloneDeep, isEqual } from 'lodash';
import { bus } from '@/common/bus';

export default {
  components: {
    deployDetail,
    deployPreview,
    deployDialog,
    deployStatusDetail,
    draggable,
  },
  mixins: [appBaseMixin],
  props: {
    environment: {
      type: String,
      default: () => 'stag',
    },
    modelName: {
      type: String,
      default: () => '',
    },
  },

  data() {
    return {
      isExpand: false,
      offlineAppDialog: {
        visiable: false,
        isLoading: false,
      },
      isShowDialog: false,
      isFirstDeploy: false, // 是否是第一次部署
      listLoading: false,
      deploymentInfoData: [], // 部署信息列表
      deploymentInfoDataBackUp: [], //  部署信息列表备份
      curDeploymentInfoItem: {}, // 当前弹窗的部署信息
      isWatchOfflineing: false, // 下架中
      isWatctDeploying: false,
      isShowSideslider: false,
      initPage: false, // 第一次进入页面
      rvData: {},
      intervalTimer: null,
      yamlLoading: false,
      curDeployItemIndex: '',
      isDialogShowSideslider: false, // 部署的侧边栏
      currentAllExpandedItems: [],
      curModuleSequence: [],
      isDeployEnvVarChange: false,
    };
  },

  computed: {
    curModuleId() {
      // 当前模块的名称
      return this.curDeploymentInfoItem.module_name;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    disableModuleTitle() {
      return this.$t('是否下架 {n} 模块', { n: this.curModuleId });
    },
    // 进入页面是否直接显示部署弹窗
    isShowDeploymentDialog() {
      return this.$route.params?.isShowDeploy;
    },
  },

  watch: {
    modelName(value) {
      if (value === this.$t('全部模块') || value === '') {
        this.deploymentInfoData = this.deploymentInfoDataBackUp;
      } else {
        this.deploymentInfoData = this.deploymentInfoDataBackUp.filter((module) => module.module_name === value);
      }
      this.init();
    },
    isWatchOfflineing(newVal, oldVal) {
      if (oldVal && !newVal) {
        // 从true变为false，则代表下架完成
        this.$paasMessage({
          theme: 'success',
          message: this.$t('应用下架成功'),
        });
      }
    },
  },

  beforeDestroy() {
    bus.$off('get-release-info');
  },

  mounted() {
    this.initPage = true; // 进入页面
    bus.$on('get-release-info', () => {
      this.handleRefresh(); // 请求模块列表数据
    });
    this.init();
  },

  methods: {
    async init() {
      await this.getModuleOrder();
      await this.getModuleReleaseInfo();
    },

    /**
     * 处理模块面板展开/收起状态变更
     * @param {Object} payload - 包含模块状态信息的对象
     * @param {string} payload.module_name - 模块名称
     * @param {boolean} payload.isExpand - 当前展开状态
     */
    handleChangePanel(payload) {
      payload.isExpand = !payload.isExpand;
      // 更新当前展开项列表
      if (payload.isExpand) {
        this.currentAllExpandedItems.push(payload.module_name);
        this.handleRefresh();
      } else {
        this.currentAllExpandedItems = this.currentAllExpandedItems.filter((name) => name !== payload.module_name);
      }
      this.curDeploymentInfoItem = payload || {};

      // 模块列表展开/收起，同步外界状态
      const allCollapsed = this.deploymentInfoData.every((item) => !item.isExpand);
      this.$emit('expand', allCollapsed);
    },

    // 部署
    handleDeploy(payload, index) {
      this.curDeploymentInfoItem = payload;
      this.curDeployItemIndex = index;
      this.$nextTick(() => {
        this.isShowDialog = true;
      });
    },

    // 部署侧边栏
    handleShowDeploy(payload) {
      this.curDeploymentInfoItem = payload || {};
      // 将正在部署的信息赋值给模块版本信息
      this.curDeploymentInfoItem.version_info = { ...payload.state.deployment.pending.version_info };
      this.isShowSideslider = true;
    },

    // 下架
    handleOfflineApp(payload) {
      this.curDeploymentInfoItem = payload || {};
      this.offlineAppDialog.visiable = true;
    },

    // 确认应用下架
    async confirmOfflineApp() {
      this.offlineAppDialog.isLoading = true;
      try {
        await this.$store.dispatch('deploy/offlineApp', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        this.isWatchOfflineing = true;
        this.getModuleReleaseInfo(false); // 查询列表数据
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('下架失败，请稍候再试'),
        });
      } finally {
        this.offlineAppDialog.visiable = false;
        this.offlineAppDialog.isLoading = false;
      }
    },

    cancelOfflineApp() {
      this.offlineAppDialog.visiable = false;
      this.offlineAppDialog.isLoading = false;
    },

    // 获取部署版本信息
    async getModuleReleaseInfo(listLoading = true) {
      // 非云原生应用，不能请求当前list接口
      if (!this.isCloudNativeApp) return;
      // 如果已经有了timer则return 打开了侧边栏也不需要watch
      if (this.intervalTimer || this.isShowSideslider || this.isDialogShowSideslider) return;
      try {
        this.listLoading = listLoading;
        const res = await this.$store.dispatch('deploy/getModuleReleaseList', {
          appCode: this.appCode,
          env: this.environment,
        });
        // 是否需要排序
        if (this.curModuleSequence.length) {
          res.data = this.sortDataByModuleName(res.data, this.curModuleSequence);
        }
        const isModuleDeployedList = [];
        res.data = res.data.map((e) => {
          if (this.currentAllExpandedItems.length) {
            e.isExpand = this.currentAllExpandedItems.includes(e.module_name);
          } else {
            if (e.module_name === this.curDeploymentInfoItem.module_name) {
              e.isExpand = this.curDeploymentInfoItem.isExpand || false;
            } else {
              e.isExpand = false;
            }
          }
          isModuleDeployedList.push({
            name: e.module_name,
            isDeployed: !!e.state.deployment?.latest,
            versionInfo: e.version_info,
          });
          return e;
        });
        this.$emit('module-deployment-info', isModuleDeployedList);
        this.$nextTick(() => {
          this.$set(this, 'deploymentInfoData', res.data);
          if (this.modelName && this.modelName !== this.$t('全部模块')) {
            this.deploymentInfoData = this.deploymentInfoData.filter((module) => module.module_name === this.modelName);
          }
        });
        this.rvData = {
          rvInst: res.rv_inst,
          rvProc: res.rv_proc,
        };
        this.deploymentInfoDataBackUp = cloneDeep(res.data);
        const hasOfflinedData = res.data.filter((e) => e.state.offline.pending) || []; // 有正在下架的数据
        const hasDeployData = res.data.filter((e) => e.state.deployment.pending) || []; // 有正在部署的数据
        this.isWatchOfflineing = !!hasOfflinedData.length; // 如果还存在下架中的数据，这说明还有模块在下架中
        this.isWatctDeploying = !!hasDeployData.length;
        if (hasOfflinedData.length || hasDeployData.length) {
          this.intervalTimer = setTimeout(async () => {
            this.intervalTimer = null;
            this.getModuleReleaseInfo(false);
          }, 3000);
        } else {
          this.initPage = false;
          this.intervalTimer && clearInterval(this.intervalTimer);
          this.intervalTimer = null;
        }
      } catch (e) {
        this.deploymentInfoData = null;
        this.isFirstDeploy = true;
        this.exposedLink = '';
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.listLoading = false;
        this.$nextTick(() => {
          this.handleDeployEnvVarChange();
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

    // 刷新列表
    handleRefresh() {
      if (this.intervalTimer || this.isDialogShowSideslider) return;
      this.getModuleReleaseInfo(false);
    },

    // 关闭进程的事件流
    handleCloseProcessWatch() {
      this.isShowSideslider = false;
      this.handleRefresh();
    },

    // 关闭侧边栏
    handleCloseSideslider() {
      this.isShowSideslider = false;
      this.handleRefresh();
    },

    // 将模块的进程实例全部收起
    handleSetCloseExpand() {
      this.curDeploymentInfoItem.isExpand = false;
      this.deploymentInfoData.forEach((e) => {
        e.isExpand = false;
      });
      this.currentAllExpandedItems = [];
    },

    // 将模块的进程实例全部展开
    handleSetOpenExpand() {
      this.curDeploymentInfoItem.isExpand = true;
      this.deploymentInfoData.forEach((module) => {
        if (module.processes.length || module.proc_specs.length) {
          module.isExpand = true;
          // 记录当前模块展开项
          this.currentAllExpandedItems.push(module.module_name);
        }
      });
    },

    // 点击访问链接
    handleOpenUrl(url) {
      if (!url) return;
      window.open(url);
    },

    // 跳转模块配置
    handleToModuleConfig(moduleName) {
      this.$router.push({
        name: 'cloudAppDeployForProcess',
        params: { id: this.appCode, moduleId: moduleName },
      });
    },

    // dialog里的slider关闭
    handleListRefresh() {
      this.isDialogShowSideslider = false;
      this.handleRefresh();
    },

    // 判断当前模块是否已下架
    isRemoved(data) {
      const deploymentTime = data.state.deployment?.latest ? new Date(data.state.deployment.latest?.created) : 0;
      const offlineTime = data.state.offline?.latest ? new Date(data.state.offline.latest?.created) : 0;
      return offlineTime > deploymentTime;
    },

    // 拖拽结束后判断是否进行排序
    draggableEnd() {
      const dragDoduleSequence = this.getModuleSequence(this.deploymentInfoData);
      if (!isEqual(this.curModuleSequence, dragDoduleSequence)) {
        // 更新模块排序
        this.updateModuleOrder();
      }
    },

    // 模块列表按照指定数组进行排序
    sortDataByModuleName(data, sequence) {
      const sequenceMap = new Map(sequence.map((moduleName, index) => [moduleName, index]));

      // 对 data 数组进行排序
      data.sort((a, b) => {
        // 获取 a 和 b 的索引，如果不存在则使用 Infinity 作为默认值
        const indexA = sequenceMap.has(a.module_name) ? sequenceMap.get(a.module_name) : Infinity;
        const indexB = sequenceMap.has(b.module_name) ? sequenceMap.get(b.module_name) : Infinity;
        // 按照索引进行排序
        return indexA - indexB;
      });
      return data;
    },

    // 获取当前模块列表名称序列
    getModuleSequence(moduleList) {
      return moduleList.map((item) => item.module_name);
    },

    // 获取部署管理模块顺序
    async getModuleOrder() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleOrder', {
          appCode: this.appCode,
        });
        // 记录当前模块顺序
        this.curModuleSequence = this.getModuleSequence(res);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 更新模块顺序
    async updateModuleOrder() {
      try {
        this.curModuleSequence = this.getModuleSequence(this.deploymentInfoData);
        const data = {
          module_orders: this.curModuleSequence.map((n, index) => {
            return {
              module_name: n,
              order: index + 1,
            };
          }),
        };
        await this.$store.dispatch('deploy/updateModuleOrder', {
          appCode: this.appCode,
          data,
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },

    // 处理环境变量变更需要部署的情况
    handleDeployEnvVarChange() {
      if (!this.isShowDeploymentDialog || this.isDeployEnvVarChange) return;
      this.isDeployEnvVarChange = true;
      const deployModleId = this.$route.params.deployModuleId;
      const deployIndex = this.deploymentInfoData.findIndex((item) => item.module_name === deployModleId);
      if (deployIndex !== -1) {
        const additionalData = this.isSmartApp ? { activeImagePullPolicy: 'Always' } : { activeImageSource: 'image' };
        const deployData = {
          ...this.deploymentInfoData[deployIndex],
          ...additionalData,
        };
        this.handleDeploy(deployData, deployIndex);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-module-content {
  height: 100%;
  // min-height: 280px;
  .deploy-module-list.sortable-chosen {
    .main {
      background: #deeff9;
    }
  }
}
.deploy-module-item {
  margin-bottom: 16px;
  .top-info-wrapper {
    position: relative;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-right: 24px;
    background: #eaebf0;
    border-radius: 2px 2px 0 0;

    .left-info {
      height: 100%;
      flex: 1;
      display: flex;
      color: #63656e;
      align-items: center;

      .module {
        height: 100%;
        display: flex;
        align-items: center;
        margin-right: 30px;

        i {
          cursor: pointer;
          color: #c4c6cc;
        }

        .paasng-jump-link {
          font-size: 14px;
          color: #3a84ff;
          transform: translateY(1px);
        }

        .paasng-deploy-item-dot {
          padding: 5px 14px 5px 12px;
          cursor: move;
        }

        .name {
          font-weight: 700;
          font-size: 14px;
          color: #313238;
        }

        .icon-cls-link {
          color: #3a84ff;
        }
      }

      .line {
        width: 1px;
        margin: 0 24px;
        background: #dcdee5;
      }

      .access-entrance {
        height: 100%;
        display: flex;
        align-items: center;
        cursor: pointer;
        .module-default {
          padding: 0px 5px;
          border-radius: 30px;
          font-size: 12px;
          color: #3a84ff;
          margin-right: 5px;
          background: #ecf3ff;
          border: 1px solid #3a84ff;
        }
        &:hover {
          i,
          .module-default {
            color: #699df4;
            border-color: #699df4;
          }
        }
      }
      .deploy-icon {
        width: 38px;
        height: 22px;
        margin-right: 5px;
        transform: translateY(-1px);

        &.en {
          width: 54px;
        }
      }
    }
    .right-btn {
      .module-config-btn.bk-button {
        min-width: 26px;
        padding: 0 !important;
        width: 26px;
      }
      .paasng-configuration-line {
        font-size: 14px;
        color: #63656e;
        transform: translateY(0px);
      }
    }
  }
  .main {
    background: #fff;
    box-shadow: 0 2px 4px 0 #0000001a, 0 2px 4px 0 #1919290d;
    border-radius: 0 0 2px 2px;
  }
  .operation-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 40px;
    .btn {
      height: 100%;
      line-height: 40px;
      padding: 0 24px;
      font-size: 12px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
  .not-deployed {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    flex: 1;
    text-align: center;
    font-size: 12px;
    color: #979ba5;
    line-height: 26px;
  }
}
.deploy-pending-text {
  font-size: 14px;
  color: #313238;
  font-weight: 500;
  line-height: 32px;
}
.loading-cls {
  top: 30vh;
}
.alert-cls {
  border: none !important;
  /deep/ .bk-alert-wraper {
    padding: 5px 10px;
  }
}
.tl em {
  font-weight: bold;
}
.module-name-wrapper {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 5px;

  &.link {
    cursor: pointer;
    &:hover .name {
      color: #3a84ff !important;
    }
  }
}
</style>
