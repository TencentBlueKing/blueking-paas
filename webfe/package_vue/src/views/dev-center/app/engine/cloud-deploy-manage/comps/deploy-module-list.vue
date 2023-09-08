<template>
  <div class="deploy-module-content" v-bkloading="{ isLoading: listLoading, opacity: 1 }">
    <bk-alert type="info" :show-icon="false" class="mt20" v-if="isWatchOfflineing">
      <div class="flex-row align-items-center" slot="title">
        <div class="fl">
          <round-loading
            size="small"
            ext-cls="deploy-round-loading"
          />
        </div>
        <p class="deploy-pending-text pl20">
          {{ $t('正在下架中...') }}
        </p>
      </div>
    </bk-alert>
    <div v-if="deploymentInfoData.length">
      <div class="deploy-module-list" v-for="deploymentInfo in deploymentInfoData" :key="deploymentInfo.name">
        <div class="deploy-module-item">
          <!-- 预览模式 / 详情模式 / 未部署 -->
          <section class="top-info-wrapper">
            <!-- 已部署 -->
            <div class="left-info">
              <div class="module">
                <i class="paasng-icon paasng-restore-screen"></i>
                <span class="name">{{deploymentInfo.module_name}}</span>
                <i class="paasng-icon paasng-jump-link icon-cls-link" />
              </div>
              <template v-if="deploymentInfo.is_deployed">
                <!-- 源码&镜像 -->
                <div class="flex-row" v-if="deploymentInfo.build_method === 'dockerfile'">
                  <div class="version">
                    <span class="label">版本：</span>
                    <span class="value">
                      {{ deploymentInfo.version_info.revision }}
                    </span>
                  </div>
                  <div class="line"></div>
                  <div class="branch">
                    <span class="label">分支：</span>
                    <span class="value">
                      {{ deploymentInfo.version_info.version_name }}
                    </span>
                  </div>
                </div>
                <!-- 仅镜像 -->
                <div class="flex-row" v-if="deploymentInfo.build_method === 'custom_image'">
                  <div class="version">
                    <span class="label">镜像Tag：</span>
                    <span class="value">
                      {{ deploymentInfo.version_info.version_name }}
                    </span>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="not-deployed">暂未部署</div>
              </template>
            </div>
            <div class="right-btn">
              <bk-button :theme="'primary'" class="mr10" size="small" @click="handleDeploy(deploymentInfo)">
                部署
              </bk-button>
              <bk-button :theme="'default'" size="small" @click="handleOfflineApp">
                下架
              </bk-button>
            </div>
          </section>
          <!-- 内容 -->
          <section class="main">
            <!-- 详情表格 -->
            <!-- <deploy-detail v-show="isExpand" /> -->
            <!-- 预览 -->
            <deploy-preview :deployment-info="deploymentInfo" />
            <!-- <div class="operation-wrapper">
              <div
                class="btn"
                @click="handleChangePanel">
                {{ isExpand ? '收起' : '展开详情' }}
                <i class="paasng-icon paasng-ps-arrow-down" v-if="!isExpand"></i>
                <i class="paasng-icon paasng-ps-arrow-up" v-else></i>
              </div>
            </div> -->
          </section>
        </div>
      </div>
    </div>

    <bk-dialog
      v-model="offlineAppDialog.visiable"
      width="450"
      :title="`${$t('是否')}${$t('下架')}${curAppModule.name}模块`"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="offlineAppDialog.isLoading"
      :ok-text="$t('下架')"
      @confirm="confirmOfflineApp"
      @cancel="cancelOfflineApp"
    >
      <div class="tl">
        {{ $t('将模块从') }}{{ environment === 'stag' ? $t('预发布环境') : $t('生产环境') }}
        {{ $t('下架，会停止当前模块下所有进程，增强服务等模块的资源仍然保留。') }}
      </div>
    </bk-dialog>
    <deploy-dialog
      :show.sync="isShowDialog"
      :environment="environment"
      :deployment-info="curDeploymentInfoItem"></deploy-dialog>
  </div>
</template>

<script>
// import deployDetail from './deploy-detail';
import deployPreview from './deploy-preview';
import deployDialog from './deploy-dialog.vue';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  components: {
    // deployDetail,
    deployPreview,
    deployDialog,
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
      curDeploymentInfoItem: {},      // 当前弹窗的部署信息
      isWatchOfflineing: false,   // 下架中
    };
  },

  watch: {
    modelName(value) {
      if (value === '全部模块') {
        this.showModuleList = this.moduleInfoList;
      } else {
        this.showModuleList = this.moduleInfoList.filter(module => module.name === this.moduleValue);
      }
    },
  },

  created() {
    // this.isExpand = this.isDeploy;
  },

  mounted() {
    this.init();
  },

  methods: {
    init() {
      this.getModuleReleaseInfo();
    },
    handleChangePanel() {
      this.isExpand = !this.isExpand;
    },

    // 部署
    handleDeploy(payload) {
      this.isShowDialog = true;
      this.curDeploymentInfoItem = payload;
      console.log('this.isShowDialog', this.isShowDialog);
    },

    // 下架
    handleOfflineApp() {
      this.offlineAppDialog.visiable = true;
    },


    // 确认应用下架
    async confirmOfflineApp() {
      this.offlineAppDialog.isLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/offlineApp', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        this.watchOfflineOperation(res.offline_operation_id);   // 轮询获取下架的进度
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


    /**
     * 轮询获取应用下架进度
     */
    watchOfflineOperation(offlineOperationId) {
      this.isWatchOfflineing = true;
      this.offlineTimer = setInterval(async () => {
        try {
          const res = await this.$store.dispatch('deploy/getOfflineResult', {
            appCode: this.appCode,
            moduleId: this.curModuleId,
            offlineOperationId,
          });

          // 下架进行中，三状态：pendding successful failed，pendding需要继续轮询
          if (res.status === 'successful') {
            this.isWatchOfflineing = false;
            this.getModuleReleaseInfo();
            this.$paasMessage({
              theme: 'success',
              message: this.$t('应用下架成功'),
            });
            clearInterval(this.offlineTimer);
          } else if (res.status === 'failed') {
            const message = res.err_detail;
            this.isWatchOfflineing = false;
            this.$paasMessage({
              theme: 'error',
              message,
            });
            clearInterval(this.offlineTimer);
          }
        } catch (e) {
          this.isWatchOfflineing = false;
          clearInterval(this.offlineTimer);
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('下架失败，请稍候再试'),
          });
        }
      }, 3000);
    },

    cancelOfflineApp() {
      this.offlineAppDialog.visiable = false;
      this.offlineAppDialog.isLoading = false;
    },

    // 获取部署版本信息
    async getModuleReleaseInfo() {
      try {
        this.listLoading = true;
        const res = await this.$store.dispatch('deploy/getModuleReleaseList', {
          appCode: this.appCode,
          env: this.environment,
        });
        this.deploymentInfoData = res.data;
        console.log('deploymentInfoData', this.deploymentInfoData);
        // if (!res.code) {
        //   // 已下架
        //   if (res.is_offlined) {
        //     res.offline.repo.version = this.formatRevision(res.offline.repo.revision);
        //     this.deploymentInfo = res.offline;
        //     this.isAppOffline = true;
        //   } else if (res.deployment) {
        //     res.deployment.repo.version = this.formatRevision(res.deployment.repo.revision);
        //     this.deploymentInfo = res.deployment;
        //     console.log('this.deploymentInfo', this.deploymentInfo);
        //     this.isAppOffline = false;
        //   } else {
        //     this.deploymentInfo = {
        //       repo: {},
        //     };
        //   }

        //   // 是否第一次部署
        //   this.isFirstDeploy = !res.deployment;
        // } else {
        //   this.isFirstDeploy = true;
        // }
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
  },
};
</script>

<style lang="scss" scoped>
.deploy-module-content{
  min-height: 280px;
}
.deploy-module-item {
  margin-top: 16px;
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
      flex: 1;
      display: flex;
      color: #63656E;

      .module {
        margin-right: 30px;

        i {
          cursor: pointer;
        }

        .name {
          font-weight: 700;
          font-size: 14px;
          color: #313238;
          margin-left: 12px;
          margin-right: 10px;
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

      .version {
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
    padding-bottom: 12px;
    .btn {
      font-size: 12px;
      color: #3A84FF;
      cursor: pointer;
    }
  }
  .not-deployed {
    flex: 1;
    text-align: center;
    font-size: 12px;
    color: #979ba5;
  }
}
.deploy-pending-text{
    font-size: 14px;
    color: #313238;
    font-weight: 500;
    line-height: 32px;
  }
</style>
