<template>
  <div class="right-main">
    <module-top-bar
      :app-code="appCode"
      :title="$t('模块配置')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
      :first-module-name="firstTabActiveName"
    />
    <paas-content-loader
      :placeholder="loaderPlaceholder"
      :offset-top="30"
      class="app-container middle overview"
    >
      <div
        v-if="!isTab"
        class="top-return-bar flex-row align-items-center"
        @click="handleGoBack"
      >
        <i
          class="paasng-icon paasng-arrows-left icon-cls-back mr5"
        />
        <h4>{{ $t('返回上一页') }}</h4>
      </div>
      <section class="deploy-panel deploy-main mt5">
        <!-- 增强服务实例详情隐藏tab -->
        <bk-tab
          v-show="isTab"
          ext-cls="deploy-tab-cls"
          :active.sync="active"
          @tab-change="handleGoPage"
        >
          <template slot="setting">
            <bk-button
              class="pr20"
              text
              @click="handleYamlView"
            >
              {{ $t('查看YAML') }}
            </bk-button>
          </template>
          <bk-tab-panel
            v-for="(panel, index) in curTabPanels"
            v-bind="panel"
            :key="index"
          ></bk-tab-panel>
        </bk-tab>

        <div class="deploy-content">
          <router-view
            :ref="routerRefs"
            :key="renderIndex"
            :save-loading="buttonLoading"
            :is-component-btn="!isFooterActionBtn"
            @cancel="handleCancel"
            @hide-tab="isTab = false"
            @tab-change="handleGoPage"
          />
        </div>
      </section>

      <!-- <div
        class="deploy-btn-wrapper"
        v-if="isPageEdit && isFooterActionBtn"
      >
        <bk-button
          :loading="buttonLoading"
          class="pl20 pr20"
          :theme="'primary'"
          @click="handleSave"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          class="pl20 pr20 ml20"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div> -->

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
        <deployYaml
          :height="deployDialogConfig.height"
          :cloud-app-data="dialogCloudAppData"
        />
      </bk-dialog>
    </paas-content-loader>
  </div>
</template>

<script>import moduleTopBar from '@/components/paas-module-bar';
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployYaml from './deploy-yaml';
import { throttle } from 'lodash';

export default {
  components: {
    moduleTopBar,
    deployYaml,
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
        { name: 'cloudAppDeployForHook', label: this.$t('钩子命令'), ref: 'hook' },
        { name: 'cloudAppDeployForEnv', label: this.$t('环境变量'), ref: 'env' },
        { name: 'cloudAppDeployForVolume', label: this.$t('挂载卷'), ref: 'volume' },
        { name: 'appServices', label: this.$t('增强服务'), ref: 'services' },
        { name: 'moduleInfo', label: this.$t('模块信息'), ref: 'module-info' },
      ],
      active: 'cloudAppDeployForProcess',
      envValidate: true,
      isTab: true,
      dialogCloudAppData: [],
    };
  },
  computed: {
    routeName() {
      return this.$route.name;
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
      const curPenel = this.curTabPanels.find(e => e.name === this.active);
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
      return this.curTabPanels[0].name;
    },

    curTabPanels() {
      if (this.curAppModule?.web_config?.runtime_type !== 'custom_image') {
        return this.panels;
      }
      return this.panels.filter(item => item.name !== 'cloudAppDeployForBuild');
    },

    // 是否需要保存操作按钮
    isFooterActionBtn() {
      // 无需展示外部操作按钮组
      const hideTabItems = ['cloudAppDeployForProcess', 'cloudAppDeployForHook', 'cloudAppDeployForEnv'];
      return !hideTabItems.includes(this.active);
    },
  },
  watch: {
    '$route'() {
      // eslint-disable-next-line no-plusplus
      this.renderIndex++;
      this.active = this.panels.find(e => e.ref === this.$route.meta.module)?.name || this.firstTabActiveName;
      this.$store.commit('cloudApi/updatePageEdit', false);
    },
  },
  created() {
    this.active = this.panels.find(e => e.ref === this.$route.meta.module)?.name || this.firstTabActiveName;
    // 默认第一项
    if (this.$route.name !== this.firstTabActiveName) {
      this.$router.push({
        ...this.$route,
        name: this.firstTabActiveName,
      });
    }
  },
  mounted() {
    this.handleWindowResize();
    this.handleResizeFun();
  },
  methods: {
    handleGoPage(routeName) {
      this.$store.commit('cloudApi/updatePageEdit', false); // 切换tab 页面应为查看页面
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
        this.isLoading = false;
      }
    },

    handleGoBack() {
      this.handleGoPage('appServices');
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
  },
};
</script>

<style lang="scss" scoped>
@import '../../../../../assets/css/components/conf.scss';
@import './index.scss';
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
}

.top-return-bar {
  background: #F5F7FA;
  cursor: pointer;
  h4 {
    font-size: 14px;
    color: #313238;
    font-weight: 400;
    padding: 0;
  }
  .icon-cls-back{
    color: #3A84FF;
    font-size: 14px;
    font-weight: bold;
  }
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
</style>
