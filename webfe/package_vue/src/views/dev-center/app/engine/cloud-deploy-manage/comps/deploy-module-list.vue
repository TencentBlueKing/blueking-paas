<template>
  <div class="deploy-module-content">
    <div class="deploy-module-list" v-for="item in moduleData" :key="item.name">
      <div class="deploy-module-item">
        <!-- 预览模式 / 详情模式 / 未部署 -->
        <section class="top-info-wrapper">
          <!-- 已部署 -->
          <div class="left-info">
            <div class="module">
              <i class="paasng-icon paasng-restore-screen"></i>
              <span class="name">{{item.name}}</span>
              <i class="paasng-icon paasng-jump-link icon-cls-link" v-if="isDeploy" />
            </div>
            <template v-if="isDeploy">
              <div class="version">
                <span class="label">版本：</span>
                <span class="value">58239632</span>
              </div>
              <div class="line"></div>
              <div class="branch">
                <span class="label">分支：</span>
                <span class="value">xxxx</span>
              </div>
            </template>
            <template v-else>
              <div class="not-deployed">暂未部署</div>
            </template>
          </div>
          <div class="right-btn">
            <bk-button :theme="'primary'" class="mr10" size="small" @click="handleDeploy">
              部署
            </bk-button>
            <bk-button :theme="'default'" size="small" :disabled="!isDeploy" @click="handleOfflineApp">
              下架
            </bk-button>
          </div>
        </section>
        <!-- 内容 -->
        <section class="main" v-if="isDeploy">
          <!-- 详情表格 -->
          <deploy-detail v-show="isExpand" />
          <!-- 预览 -->
          <deploy-preview v-show="!isExpand" />
          <div class="operation-wrapper">
            <div
              class="btn"
              @click="handleChangePanel">
              {{ isExpand ? '收起' : '展开详情' }}
              <i class="paasng-icon paasng-ps-arrow-down" v-if="!isExpand"></i>
              <i class="paasng-icon paasng-ps-arrow-up" v-else></i>
            </div>
          </div>
        </section>
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
    <deploy-dialog :show="isShowDialog" :environment="environment"></deploy-dialog>
  </div>
</template>

<script>import deployDetail from './deploy-detail';
import deployPreview from './deploy-preview.vue';
import deployDialog from './deploy-dialog.vue';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  components: {
    deployDetail,
    deployPreview,
    deployDialog,
  },
  mixins: [appBaseMixin],
  props: {
    moduleData: {
      type: Array,
      default: () => [],
    },
    environment: {
      type: String,
      default: () => 'stag',
    },
  },

  data() {
    return {
      isExpand: true,
      offlineAppDialog: {
        visiable: false,
        isLoading: false,
      },
      isShowDialog: false,
    };
  },

  computed: {
    // 是否部署
    isDeploy() {
      console.log('this.moduleData', this.moduleData);
      return true;
    },
  },

  created() {
    this.init();
    // this.isExpand = this.isDeploy;
  },

  methods: {
    init() {
      this.getModuleReleaseInfo();
    },
    handleChangePanel() {
      this.isExpand = !this.isExpand;
    },

    // 部署
    handleDeploy() {
      this.isShowDialog = true;
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
        console.log('res', res);
        // this.watchOfflineOperation(res.offline_operation_id);

        // if (this.environment === 'prod') {
        //   this.appMarketPublished = false;
        //   this.$store.commit('updateCurAppMarketPublished', false);
        // }
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
    async getModuleReleaseInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleReleaseInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        console.log('res', res);
        // if (!res.code) {
        //   // 已下架
        //   if (res.is_offlined) {
        //     res.offline.repo.version = this.formatRevision(res.offline.repo.revision);
        //     this.deploymentInfo = res.offline;
        //     this.exposedLink = '';
        //     this.isAppOffline = true;
        //   } else if (res.deployment) {
        //     res.deployment.repo.version = this.formatRevision(res.deployment.repo.revision);
        //     this.deploymentInfo = res.deployment;
        //     this.exposedLink = res.exposed_link.url;
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
        this.deploymentInfo = null;
        this.isFirstDeploy = true;
        this.exposedLink = '';
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
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
</style>
