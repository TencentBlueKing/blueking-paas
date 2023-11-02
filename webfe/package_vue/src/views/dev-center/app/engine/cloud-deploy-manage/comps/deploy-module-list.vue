<template>
  <div class="deploy-module-content" v-bkloading="{ isLoading: listLoading, opacity: 1}">
    <bk-alert type="info" :show-icon="false" class="mt20 mb20 alert-cls" v-if="isWatchOfflineing">
      <div class="flex-row align-items-center" slot="title">
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
      <div class="deploy-module-list" v-for="(deploymentInfo, index) in deploymentInfoData" :key="deploymentInfo.name">
        <div class="deploy-module-item">
          <!-- 预览模式 / 详情模式 / 未部署 -->
          <section class="top-info-wrapper">
            <!-- 已部署 -->
            <div class="left-info">
              <div class="module">
                <i class="icon paasng-icon paasng-deploy-item-dot"></i>
                <div
                  @click="handleOpenUrl(deploymentInfo.exposed_url)"
                  :class="['module-name-wrapper', { 'link': deploymentInfo.exposed_url }]"
                  v-bk-tooltips="{ content: $t('访问模块'), disabled: !deploymentInfo.exposed_url, distance: -3 }"
                >
                  <span class="name">{{deploymentInfo.module_name}}</span>
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
                <!-- 源码&镜像 -->
                <div v-if="deploymentInfo.build_method === 'dockerfile'">
                  <!-- 源码分支 -->
                  <div
                    class="flex-row"
                    v-if="deploymentInfo.state.deployment.latest_succeeded.version_info.version_type === 'branch'">
                    <div class="version">
                      <span class="label">{{$t('版本：')}}</span>
                      <span class="value">
                        {{ deploymentInfo.state.deployment.latest_succeeded.version_info.revision.substring(0,8) }}
                      </span>
                    </div>
                    <div class="line"></div>
                    <div class="branch">
                      <span class="label">{{$t('分支：')}}</span>
                      <span class="value">
                        {{ deploymentInfo.state.deployment.latest_succeeded.version_info.version_name }}
                      </span>
                    </div>
                  </div>
                  <!-- 镜像构建 -->
                  <div class="version" v-else>
                    <span class="label">{{$t('镜像Tag：')}}</span>
                    <span class="value">
                      {{ deploymentInfo.state.deployment.latest_succeeded.version_info.version_name.substring(0,16) }}
                    </span>
                  </div>
                </div>
                <!-- 仅镜像 -->
                <div class="flex-row" v-if="deploymentInfo.build_method === 'custom_image'">
                  <div class="version">
                    <span class="label">{{$t('镜像Tag：')}}</span>
                    <span class="value">
                      {{ deploymentInfo.state.deployment.latest_succeeded.version_info.version_name.substring(0,16) }}
                    </span>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="not-deployed">{{$t('暂未部署')}}</div>
              </template>
            </div>
            <div class="right-btn">
              <span v-if="!!deploymentInfo.state.deployment.pending">
                <bk-button
                  v-if="deploymentInfo.state.deployment.pending.has_requested_in"
                  :theme="'primary'"
                  class="mr10"
                  size="small"
                  text>
                  {{$t('正在中断部署...')}}
                </bk-button>
                <bk-button
                  v-else
                  :theme="'primary'"
                  class="mr10"
                  size="small"
                  text
                  @click="handleShowDeploy(deploymentInfo)">
                  {{$t('部署详情')}}
                </bk-button>
              </span>
              <bk-button
                :theme="'primary'"
                class="mr10"
                size="small"
                @click="handleDeploy(deploymentInfo, index)"
                :disabled="(!!deploymentInfo.state.offline.pending || !!deploymentInfo.state.deployment.pending)"
                :loading="!!deploymentInfo.state.deployment.pending || (curDeployItemIndex === index && yamlLoading)">
                {{$t('部署')}}
              </bk-button>
              <bk-button
                :theme="'default'"
                class="mr10"
                size="small"
                @click="handleOfflineApp(deploymentInfo)"
                :disabled="!!deploymentInfo.state.offline.pending || !!deploymentInfo.state.deployment.pending
                  || !deploymentInfo.state.deployment.latest_succeeded"
                :loading="!!deploymentInfo.state.offline.pending">
                {{$t('下架')}}
              </bk-button>
              <bk-button
                :theme="'default'"
                ext-cls="module-config-btn"
                size="small"
                v-bk-tooltips="$t('模块配置')"
                @click="handleToModuleConfig(deploymentInfo.module_name)">
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
              :module-name="deploymentInfo.module_name" />
            <!-- 预览 -->
            <deploy-preview
              :deployment-info="deploymentInfo"
              v-if="!deploymentInfo.isExpand" />
            <div
              class="operation-wrapper"
              @click="handleChangePanel(deploymentInfo)"
              v-if="deploymentInfo.processes.length || deploymentInfo.proc_specs.length">
              <div class="btn">
                {{ deploymentInfo.isExpand ? $t('收起') : $t('展开详情') }}
                <i class="paasng-icon paasng-ps-arrow-down" v-if="!deploymentInfo.isExpand"></i>
                <i class="paasng-icon paasng-ps-arrow-up" v-else></i>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <bk-dialog
      v-model="offlineAppDialog.visiable"
      width="450"
      :title="`${$t('是否')}${$t('下架')}${curModuleId}模块`"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="offlineAppDialog.isLoading"
      :ok-text="$t('下架')"
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
      @refresh="handleRefresh">
    </deploy-dialog>

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

<script>import deployDetail from './deploy-detail';
import deployPreview from './deploy-preview';
import deployDialog from './deploy-dialog';
import deployStatusDetail from './deploy-status-detail';
import appBaseMixin from '@/mixins/app-base-mixin';
import _ from 'lodash';
import { bus } from '@/common/bus';

export default {
  components: {
    deployDetail,
    deployPreview,
    deployDialog,
    deployStatusDetail,
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
      isAppOffline: false, // 是否下架
      isFirstDeploy: false,   // 是否是第一次部署
      listLoading: false,
      deploymentInfoData: [],    // 部署信息列表
      deploymentInfoDataBackUp: [],   //  部署信息列表备份
      curDeploymentInfoItem: {},      // 当前弹窗的部署信息
      isWatchOfflineing: false,   // 下架中
      isWatctDeploying: false,
      isShowSideslider: false,
      initPage: false,       // 第一次进入页面
      rvData: {},
      intervalTimer: null,
      yamlLoading: false,
      curDeployItemIndex: '',
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
  },

  watch: {
    modelName(value) {
      if (value === '全部模块' || value === '') {
        this.deploymentInfoData = this.deploymentInfoDataBackUp;
      } else {
        this.deploymentInfoData = this.deploymentInfoDataBackUp
          .filter(module => module.module_name === value);
      }
    },
    isWatchOfflineing(newVal, oldVal) {
      if (oldVal && !newVal) {    // 从true变为false，则代表下架完成
        this.$paasMessage({
          theme: 'success',
          message: this.$t('应用下架成功'),
        });
      }
    },

    isWatctDeploying(value) {
      if (value && this.initPage) {    // 第一次进入页面，如果正在部署中，提示
        this.$paasMessage({
          theme: 'primary',
          message: this.$t('检测到尚未结束的部署任务，已恢复部署进度'),
        });
      }
    },
  },

  created() {
    // this.isExpand = this.isDeploy;
  },

  mounted() {
    this.initPage = true;   // 进入页面
    bus.$on('get-release-info', () => {
      this.handleRefresh();   // 请求模块列表数据
    });
    this.init();
  },

  methods: {
    init() {
      this.getModuleReleaseInfo();
    },
    handleChangePanel(payload) {
      payload.isExpand = !payload.isExpand;
      // this.$set(this, 'deploymentInfoData', res.data);
      //   this.deploymentInfoDataBackUp = _.cloneDeep(res.data);
      this.curDeploymentInfoItem = payload || {};
      // this.isExpand = !this.isExpand;
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
      if (this.intervalTimer) true;  // 如果已经有了timer则return
      try {
        this.listLoading = listLoading;
        const res = await this.$store.dispatch('deploy/getModuleReleaseList', {
          appCode: this.appCode,
          env: this.environment,
        });
        // this.deploymentInfoData = res.data;
        res.data = res.data.map((e) => {
          if (e.module_name === this.curDeploymentInfoItem.module_name) {
            e.isExpand = this.curDeploymentInfoItem.isExpand || false;
          } else {
            e.isExpand = false;
          }
          return e;
        });
        this.$nextTick(() => {
          this.$set(this, 'deploymentInfoData', res.data);
          if (this.modelName && this.modelName !== '全部模块') {
            this.deploymentInfoData = this.deploymentInfoData
              .filter(module => module.module_name === this.modelName);
          }
        });
        this.rvData = {
          rvInst: res.rv_inst,
          rvProc: res.rv_proc,
        };
        this.deploymentInfoDataBackUp = _.cloneDeep(res.data);
        const hasOfflinedData = res.data.filter(e => e.state.offline.pending) || [];    // 有正在下架的数据
        const hasDeployData = res.data.filter(e => e.state.deployment.pending) || [];    // 有正在部署的数据
        this.isWatchOfflineing = !!(hasOfflinedData.length);   // 如果还存在下架中的数据，这说明还有模块在下架中
        this.isWatctDeploying = !!(hasDeployData.length);
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
      if (this.intervalTimer) return;
      this.getModuleReleaseInfo(false);
    },

    // 关闭进程的事件流
    handleCloseProcessWatch() {
      this.handleRefresh();
      this.isShowSideslider = false;
    },

    // 关闭侧边栏
    handleCloseSideslider() {
      this.isShowSideslider = false;
    },

    // 将模块的进程实例全部收起
    handleSetCloseExpand() {
      this.curDeploymentInfoItem.isExpand = false;
      this.deploymentInfoData.forEach((e) => {
        e.isExpand = false;
      });
    },

    // 将模块的进程实例全部展开
    handleSetOpenExpand() {
      this.curDeploymentInfoItem.isExpand = true;
      this.deploymentInfoData.forEach((instance) => {
        if (instance.processes.length || instance.proc_specs.length) {
          instance.isExpand = true;
        }
      });
    },

    // 点击访问链接
    handleOpenUrl(url) {
      window.open(url);
    },

    // 跳转模块配置
    handleToModuleConfig(moduleName) {
      this.$router.push({
        name: 'cloudAppDeployForProcess',
        params: { id: this.appCode, moduleId: moduleName },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.deploy-module-content{
  height: 100%;
  // min-height: 280px;
}
.deploy-module-item {
  margin-bottom: 16px;
  .top-info-wrapper {
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-left: 12px;
    padding-right: 24px;
    background: #EAEBF0;
    border-radius: 2px 2px 0 0;

    .left-info {
      height: 100%;
      flex: 1;
      display: flex;
      color: #63656E;
      align-items: center;

      .module {
        height: 100%;
        display: flex;
        align-items: center;
        margin-right: 30px;

        i {
          cursor: pointer;
          color: #C4C6CC;
        }

        .paasng-jump-link {
          font-size: 14px;
          color: #3A84FF;
          transform: translateY(1px);
        }

        .paasng-deploy-item-dot {
          margin-right: 14px;
        }

        .name {
          font-weight: 700;
          font-size: 14px;
          color: #313238;
        }

        .icon-cls-link {
          color: #3A84FF;
        }
      }

      .line {
        width: 1px;
        margin: 0 24px;
        background: #DCDEE5;
      }

      .access-entrance {
        height: 100%;
        display: flex;
        align-items: center;
        cursor: pointer;
        .module-default{
          padding: 0px 5px;
          border-radius: 30px;
          font-size: 12px;
          color: #3A84FF;
          margin-right: 5px;
          background: #ecf3ff;
          border: 1px solid #3A84FF;
        }
        &:hover {
          i,
          .module-default {
            color: #699df4;
            border-color: #699df4;
          }
        }
      }
      .deploy-icon{
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
        color: #979BA5;
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
    cursor: pointer;
    .btn {
      font-size: 12px;
      color: #3A84FF;
    }
  }
  .not-deployed {
    flex: 1;
    text-align: center;
    font-size: 12px;
    color: #979ba5;
    line-height: 26px;
  }
}
.deploy-pending-text{
  font-size: 14px;
  color: #313238;
  font-weight: 500;
  line-height: 32px;
}
.loading-cls{
  top: 30vh;
}
.alert-cls{
  border: none !important;
  /deep/ .bk-alert-wraper{
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
      color: #3A84FF !important;
    }
  }
}
</style>
