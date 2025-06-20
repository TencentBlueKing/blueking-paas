<template>
  <div class="right-main">
    <module-top-bar
      :key="topBarIndex"
      :app-code="appCode"
      :title="$t('模块配置')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
      :first-module-name="firstTabActiveName"
      :active-route-name="active"
      @tab-change="handleTabChange"
    />
    <section :class="[{ 'enhanced-service-main-cls': !isTab }, { 'cloud-native-app': isCloudNativeApp }]">
      <paas-content-loader
        :placeholder="loaderPlaceholder"
        :offset-top="30"
        class="app-container middle overview"
        :class="{ 'enhanced-service': !isTab }"
      >
        <section :class="['deploy-panel', 'deploy-main', { 'instance-details-cls': !isTab }]">
          <!-- 增强服务实例详情隐藏tab -->
          <bk-tab
            v-show="isTab"
            ext-cls="deploy-tab-cls"
            :active.sync="active"
            @tab-change="handleGoPage"
          >
            <template slot="setting">
              <bk-button
                class="mr10"
                text
                @click="toDeploy"
              >
                <i class="paasng-icon paasng-bushu"></i>
                {{ $t('去部署') }}
              </bk-button>
              <bk-popover
                class="mr20"
                theme="light"
                ext-cls="more-operations"
                placement="bottom"
                ref="moreRef"
                :tippy-options="{ hideOnClick: false }"
              >
                <i class="paasng-icon paasng-icon-more"></i>
                <div slot="content">
                  <div
                    class="option"
                    @click="handleYamlView"
                  >
                    {{ $t('查看 YAML') }}
                  </div>
                </div>
              </bk-popover>
            </template>
            <bk-tab-panel
              v-for="(panel, index) in panels"
              v-bind="panel"
              :key="index"
            ></bk-tab-panel>
          </bk-tab>

          <div :class="['deploy-content', { 'details-router-cls': !isTab }]">
            <router-view
              :ref="routerRefs"
              :key="renderIndex"
              :save-loading="buttonLoading"
              :is-component-btn="!isFooterActionBtn"
              @cancel="handleCancel"
              @hide-tab="isTab = false"
              @show-tab="handleShowTab"
              @tab-change="handleGoPage"
              @route-back="handleGoBack"
            />
          </div>
        </section>
      </paas-content-loader>
    </section>

    <bk-dialog
      v-model="deployDialogConfig.visible"
      theme="primary"
      :width="deployDialogConfig.dialogWidth"
      ext-cls="deploy-dialog"
      title="YAML"
      header-position="left"
      :position="{ top: deployDialogConfig.top }"
      :show-footer="false"
    >
      <DeployYaml
        :key="isYamlLoading"
        :height="deployDialogConfig.height"
        :cloud-app-data="dialogCloudAppData"
        :loading="isYamlLoading"
      />
    </bk-dialog>
  </div>
</template>

<script>
import moduleTopBar from '@/components/paas-module-bar';
import appBaseMixin from '@/mixins/app-base-mixin.js';
import DeployYaml from './deploy-yaml';
import { throttle } from 'lodash';
import { traceIds } from '@/common/trace-ids';

export default {
  components: {
    moduleTopBar,
    DeployYaml,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      renderIndex: 0,
      buttonLoading: false,
      deployDialogConfig: {
        visible: false,
        dialogWidth: 1200,
        top: 120,
        height: 600,
      },
      manifestExt: {},
      panels: [
        { name: 'cloudAppDeployForBuild', label: this.$t('构建配置'), ref: 'build' },
        { name: 'cloudAppDeployForProcess', label: this.$t('进程配置'), ref: 'process' },
        { name: 'cloudAppDeployForEnv', label: this.$t('环境变量'), ref: 'env' },
        { name: 'cloudAppDeployForVolume', label: this.$t('挂载卷'), ref: 'volume' },
        { name: 'observabilityConfig', label: this.$t('可观测性'), ref: 'observability' },
        { name: 'appServices', label: this.$t('增强服务'), ref: 'services' },
        { name: 'moduleInfo', label: this.$t('更多配置'), ref: 'info' },
      ],
      active: 'cloudAppDeployForBuild',
      envValidate: true,
      isTab: true,
      dialogCloudAppData: [],
      topBarIndex: 0,
      isYamlLoading: false,
    };
  },
  computed: {
    routeName() {
      return this.$route.name;
    },

    userFeature() {
      return this.$store.state.userFeature;
    },

    loaderPlaceholder() {
      if (this.routeName === 'appDeployForStag' || this.routeName === 'appDeployForProd') {
        return 'deploy-loading';
      }
      if (this.routeName === 'appDeployForHistory') {
        return 'deploy-history-loading';
      }
      return 'deploy-top-loading';
    },

    routerRefs() {
      const curPenel = this.panels.find((e) => e.name === this.active);
      return curPenel ? curPenel.ref : 'process';
    },

    curAppModuleList() {
      // 根据name的英文字母排序
      return (this.$store.state.curAppModuleList || []).sort((a, b) => a.name.localeCompare(b.name));
    },

    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit;
    },

    firstTabActiveName() {
      return this.panels[0].name;
    },

    // 是否需要保存操作按钮
    isFooterActionBtn() {
      // 无需展示外部操作按钮组
      const hideTabItems = ['cloudAppDeployForProcess', 'cloudAppDeployForHook', 'cloudAppDeployForEnv'];
      return !hideTabItems.includes(this.active);
    },

    categoryText() {
      return this.isCloudNativeApp ? '云原生应用' : '普通应用';
    },
  },
  watch: {
    $route(newRoute) {
      if (this.active !== newRoute.name || newRoute.name === 'appServices') {
        this.handleGoPage(newRoute.name);
        this.isTab = newRoute.name === 'appServices'; // 显示tab
      }
      this.renderIndex += 1;
      this.$store.commit('cloudApi/updatePageEdit', false);
    },
    appCode() {
      this.topBarIndex += 1;
    },
  },
  created() {
    this.active = this.panels.find((e) => e.ref === this.$route.meta.module)?.name || this.firstTabActiveName;
    // 默认第一项
    if (this.$route.name !== this.firstTabActiveName) {
      this.$router.push({
        ...this.$route,
        name: this.active || this.firstTabActiveName,
      });
    }
  },
  mounted() {
    this.handleWindowResize();
    this.handleResizeFun();
  },
  methods: {
    handleGoPage(routeName) {
      const label = this.panels.find((item) => item.name === routeName).label;
      this.sendEventTracking({ id: traceIds[label], action: 'view', category: this.categoryText });
      this.$store.commit('cloudApi/updatePageEdit', false); // 切换tab 页面应为查看页面
      this.active = routeName;
      this.$router.push({
        name: routeName,
      });
    },

    // 取消改变页面状态
    handleCancel() {
      this.$store.commit('cloudApi/updatePageEdit', false);
      if (this.$refs[this.routerRefs]?.handleCancel) {
        this.$refs[this.routerRefs]?.handleCancel();
      }
    },

    // 查看yaml
    async handleYamlView() {
      this.isYamlLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/getAppYamlManiFests', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.deployDialogConfig.visible = true;
        this.dialogCloudAppData = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isYamlLoading = false;
      }
    },

    handleGoBack(routeName) {
      this.handleGoPage(routeName);
      this.isTab = true;
    },

    handleWindowResize() {
      window.addEventListener('resize', throttle(this.handleResizeFun, 100));
    },

    handleResizeFun() {
      if (window.innerWidth < 1366) {
        this.deployDialogConfig.dialogWidth = 800;
        this.deployDialogConfig.top = 80;
        this.deployDialogConfig.height = 400;
      } else {
        this.deployDialogConfig.dialogWidth = 1100;
        this.deployDialogConfig.top = 120;
        this.deployDialogConfig.height = 520;
      }
    },

    handleTabChange() {
      this.handleGoBack(this.active);
    },

    handleShowTab(callback) {
      this.isTab = true;
      callback(this);
    },

    // 跳转模块部署
    toDeploy() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.appCode,
          filterModule: this.curModuleId,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
@import '../../../../../assets/css/components/conf.scss';
@import './index.scss';
.enhanced-service-main-cls.cloud-native-app {
  height: 100%;
  display: flex;
  .enhanced-service {
    flex: 1;
    min-width: 0;
    padding: 0;
    margin: 0;
  }
}

.title {
  font-size: 16px;
  color: #313238;
  height: 50px;
  background: #fff;
  line-height: 50px;
  padding: 0 24px;
}
.deploy-btn-wrapper {
  // position: absolute;
  // top: 77vh;
  margin-top: 20px;
  height: 50px;
  line-height: 50px;
  padding: 0 20px;
}

.deploy-dialog .stage-info {
  width: 100%;
  background-color: #f5f6fa;
  overflow-y: auto;
  border-left: 10px solid #ccc;
  padding: 6px 0 30px 12px;
  margin-top: 8px;

  .info-title {
    font-weight: 700;
    margin-bottom: 8px;
  }

  .info-tips {
    margin-bottom: 8px;
  }

  .info-label {
    display: inline-block;
    min-width: 65px;
  }
}

.deploy-tab-cls {
  /deep/ .bk-tab-section {
    padding: 10px !important;
    border: none;
  }
}

.deploy-panel.deploy-main {
  box-shadow: 0 2px 4px 0 #1919290d;

  &.instance-details-cls {
    // 高度问题·
    height: 100%;
    min-height: auto;
    background: #f5f7fa;

    .details-router-cls {
      height: 100%;
    }
  }
  i.paasng-icon-more {
    padding: 3px;
    font-size: 16px;
    color: #63656e;
    cursor: pointer;
    border-radius: 50%;
    transform: translateY(0px);
    &:hover {
      background: #f0f1f5;
    }
  }
}
.instance-alert-cls {
  margin-bottom: 16px;
}
</style>
<style lang="scss">
.deploy-dropdown-menu .bk-dropdown-content {
  display: none !important;
}
.guide-link {
  color: #3a84ff;
  font-size: 12px;
  cursor: pointer;
}
.more-operations {
  .tippy-tooltip.light-theme {
    padding: 6px 0;
  }
  .option {
    height: 32px;
    line-height: 32px;
    padding: 0 12px;
    cursor: pointer;
    color: #63656e;
    &:hover {
      background-color: #eaf3ff;
      color: #3a84ff;
    }
  }
}
</style>
