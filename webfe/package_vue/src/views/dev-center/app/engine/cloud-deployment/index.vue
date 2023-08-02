<template lang="html">
  <div class="right-main">
    <module-top-bar
      :title="$t('应用编排')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <paas-content-loader
      :is-loading="isLoading"
      :placeholder="loaderPlaceholder"
      :offset-top="30"
      class="app-container middle overview"
    >
      <section class="deploy-panel deploy-main mt5">
        <!-- <ul
          class="ps-tab"
          style="position: relative; z-index: 10;"
        >
          <li
            :class="['item', { 'active': deployModule === 'process' }]"
            @click="handleGoPage('cloudAppDeployForProcess')"
          >
            {{ $t('进程配置') }}
            <router-link :to="{ name: 'appDeployForStag' }" />
          </li>
          <li
            :class="['item', { 'active': deployModule === 'hook' }]"
            @click="handleGoPage('cloudAppDeployForHook')"
          >
            {{ $t('钩子命令') }}
          </li>
          <li
            :class="['item', { 'active': deployModule === 'env' }]"
            @click="handleGoPage('cloudAppDeployForEnv')"
          >
            {{ $t('环境变量') }}
          </li>
          <li
            :class="['item', { 'active': deployModule === 'resource' }]"
            @click="handleGoPage('cloudAppDeployForResource')"
          >
            {{ $t('依赖资源') }}
          </li>
          <li
            :class="['item', { 'active': deployModule === 'yaml' }]"
            @click="handleGoPage('cloudAppDeployForYaml')"
          >
            {{ $t('YAML') }}
          </li>
        </ul> -->

        <bk-tab ext-cls="deploy-tab-cls" :active.sync="active" @tab-change="handleGoPage">
          <template slot="setting">
            <bk-button class="pr20" text @click="handleYamlView">
              {{ $t('查看YAML') }}
            </bk-button>
          </template>
          <bk-tab-panel
            v-for="(panel, index) in panels"
            v-bind="panel"
            :key="index">
          </bk-tab-panel>
        </bk-tab>

        <div class="deploy-content">
          <router-view
            :ref="routerRefs"
            :key="renderIndex"
            :cloud-app-data="cloudAppData"
          />
        </div>
      </section>

      <div class="deploy-btn-wrapper" v-if="isPageEdit">
        <bk-button
          :loading="buttonLoading"
          class="pl20 pr20"
          :theme="'primary'"
          :disabled="isDisabled"
          @click="handleSave"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button class="pl20 pr20 ml20" @click="handleCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>

      <!-- <bk-dialog
        v-model="deployDialogConfig.visible"
        theme="primary"
        width="700"
        ext-cls="deploy-dialog"
        :mask-close="false"
        :ok-text="$t('确认发布')"
        :header-position="deployDialogConfig.headerPosition"
        :title="$t(`确认发布至${deployDialogConfig.stageTitle}`)"
        @confirm="sumbitCloudApp(deployDialogConfig.stage)"
        @after-leave="dialogAfterLeave"
      >
        <div>
          {{ $t('请关注以下问题：') }}
          <div class="stage-info">
            <p class="info-title">
              {{ $t('进程副本数变更') }}
            </p>
            <p>{{ $t('目标环境的部分进程的副本数量与当前模型不一致，将使用当前模型中的数据进行覆盖目标环境。') }}</p>
            <p class="info-tips">
              {{ $t('副本数将发生以下变化：') }}
            </p>
            <p
              v-for="(item, index) in replicasChanges"
              :key="index"
            >
              <span class="info-label">
                {{ item.proc_type }}：
              </span>
              {{ item.old }}（{{ deployDialogConfig.stageTitle }}） -> {{ item.new }} {{ $t('（当前模型）') }}
            </p>
          </div>
        </div>
      </bk-dialog> -->
      <bk-dialog
        v-model="deployDialogConfig.visible" theme="primary"
        width="1200"
        ext-cls="deploy-dialog"
        title="YAML"
        header-position="left"
        :show-footer="false">
        <deployYaml :cloud-app-data="dialogCloudAppData"></deployYaml>
      </bk-dialog>
    </paas-content-loader>
  </div>
</template>

<script>
import moduleTopBar from '@/components/paas-module-bar';
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployYaml from '@/views/dev-center/app/engine/cloud-deployment/deploy-yaml';
import { bus } from '@/common/bus';

export default {
  components: {
    moduleTopBar,
    deployYaml,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      renderIndex: 0,
      cloudAppData: {},
      isLargeDropdownShow: false,
      buttonLoading: false,
      deployDialogConfig: {
        visible: false,
        headerPosition: 'left',
        stageTitle: this.$t('预发布环境'),
        stage: 'stag',
      },
      replicasChanges: [],
      manifestExt: {},
      isDisabled: false,
      panels: [
        { name: 'cloudAppDeployForProcess', label: this.$t('进程配置'), ref: 'process' },
        { name: 'cloudAppDeployForHook', label: this.$t('钩子命令'), ref: 'hook'  },
        { name: 'cloudAppDeployForEnv', label: this.$t('环境变量'), ref: 'env'  },
      ],
      active: 'cloudAppDeployForProcess',
      envValidate: true,
    };
  },
  computed: {
    buildpacks() {
      if (this.overview.buildpacks && this.overview.buildpacks.length) {
        const buildpacks = this.overview.buildpacks.map(item => item.display_name);
        return buildpacks.join('，');
      }
      return '--';
    },
    deployModule() {
      return this.$route.meta.module || 'stag';
    },
    routeName() {
      return this.$route.name;
    },
    loaderPlaceholder() {
      if (this.routeName === 'appDeployForStag' || this.routeName === 'appDeployForProd') {
        return 'deploy-loading';
      } if (this.routeName === 'appDeployForHistory') {
        return 'deploy-history-loading';
      }
      return 'deploy-top-loading';
    },
    routerRefs() {
      const curPenel = this.panels.find(e => e.name === this.active);
      return curPenel ? curPenel.ref : 'process';
    },

    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit;
    },

    dialogCloudAppData() {
      return this.$store.state.cloudApi.cloudAppData;
    },
  },
  watch: {
    '$route'() {
      // eslint-disable-next-line no-plusplus
      this.renderIndex++;
      this.init();
    },
  },
  created() {
    this.init();
    this.active = this.panels.find(e => e.ref === this.$route.meta.module)?.name || 'cloudAppDeployForProcess';
    bus.$on('release-disabled', (value) => {
      this.isDisabled = value;
    });
  },
  methods: {
    async init() {
      try {
        const res = await this.$store.dispatch('deploy/getCloudAppYaml', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.cloudAppData = res.manifest;
        this.$store.commit('cloudApi/updateCloudAppData', this.cloudAppData);
        this.getManifestExt();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
      }
    },

    async getManifestExt() {
      try {
        const res = await this.$store.dispatch('deploy/getManifestExt', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          // 增强服务不分环境，目前指定为prod
          env: 'prod',
        });
        this.manifestExt = res;
        // 展示数据
        if (this.cloudAppData.metadata && this.cloudAppData.metadata.annotations) {
          const ext = Object.assign({}, this.cloudAppData.metadata.annotations, res.metadata.annotations);
          this.$set(this.cloudAppData.metadata, 'annotations', ext);
          this.$store.commit('cloudApi/updateCloudAppData', this.cloudAppData);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    handleGoPage(routeName) {
      this.cloudAppData = this.$store.state.cloudApi.cloudAppData;
      this.$store.commit('cloudApi/updatePageEdit', false); // 切换tab 页面应为查看页面
      this.$router.push({
        name: routeName,
      });
    },

    async deployDialog(env) {
      if (this.deployModule === 'process') { // 进程配置需要单独处理下
        try {
          const res = await this.$refs.square.formDataValidate();
          if (res) {
            this.buttonLoading = true;
            this.getCloudAppInfo(env);
          }
        } catch (error) {
          console.error(error);
        }
      } else {
        this.buttonLoading = true;
        this.getCloudAppInfo(env);
      }
    },

    showDeployDialog(env) {
      this.deployDialogConfig.visible = true;
      if (env === 'stag') {
        this.deployDialogConfig.stage = 'stag';
        this.deployDialogConfig.stageTitle = this.$t('预发布环境');
      } else {
        this.deployDialogConfig.stage = 'prod';
        this.deployDialogConfig.stageTitle = this.$t('生产环境');
      }
    },

    dialogAfterLeave() {
      this.buttonLoading = false;
    },

    // 发布二次确认信息
    async getCloudAppInfo(env) {
      try {
        const res = await this.$store.dispatch('deploy/getCloudAppInfo', {
          params: { manifest: this.$store.state.cloudApi.cloudAppData },
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env,
        });
        this.replicasChanges = res.proc_replicas_changes;
        // proc_replicas_changes没有数据时，不展示额外信息，只显示普通的二次确认框
        if (!res.proc_replicas_changes.length) {
          this.handleDeploy(env);
        } else {
          // 显示二次确认框，并展示数据
          this.showDeployDialog(env);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
        this.dialogAfterLeave();
      }
    },

    async handleDeploy(env) {
      const environment = env === 'stag' ? this.$t('预发布') : this.$t('生产');
      this.$bkInfo({
        title: this.$t('确认发布至{environment}环境', { environment }),
        subTitle: this.$t('确认要将应用（{code}）发布到{environment}环境', { code: this.appCode, environment }),
        width: 520,
        confirmLoading: true,
        cancelFn: () => {
          this.buttonLoading = false;
        },
        confirmFn: async () => {
          this.sumbitCloudApp(env);
        },
      });
    },

    async sumbitCloudApp(env) {
      // 表单校验, 弹出提示
      let flag = true;
      const data = this.$store.state.cloudApi.cloudAppData;
      const { processes } = data.spec;
      const imageReg = /^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$/;
      const portReg = /^[0-9]*$/;
      for (let i = 0; i < processes.length; i++) {
        // image 镜像地址
        console.log('!processes[i].image', !processes[i].image);
        if (!processes[i].image) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('请输入容器镜像地址!'),
          });
          flag = false;
          // 触发验证函数
          this.$refs.square.formDataValidate(i);
          break;
        }

        if (!imageReg.test(processes[i].image)) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('地址格式不正确'),
          });
          flag = false;
          this.$refs.square.formDataValidate(i);
          break;
        }

        // 不填 targetPort, 这个 key 需要传
        if (processes[i].targetPort === '' || processes[i].targetPort === null || processes[i].targetPort === undefined) {
          delete processes[i].targetPort;
        } else {
          if (processes[i].targetPort < 1 || processes[i].targetPort > 65535) {
            this.$bkMessage({
              theme: 'error',
              message: this.$t('端口有效范围1-65535'),
            });
            flag = false;
            this.$refs.square.formDataValidate(i);
            break;
          }
          if (!portReg.test(processes[i].targetPort)) {
            this.$bkMessage({
              theme: 'error',
              message: this.$t('只能输入数字'),
            });
            flag = false;
            this.$refs.square.formDataValidate(i);
            break;
          }
        }

        // replicas 副本数量
        if (!processes[i].replicas) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('请输入副本数量!'),
          });
          flag = false;
          this.$refs.square.formDataValidate(i);
          break;
        }
        if (!(processes[i].replicas >= 0 && processes[i].replicas <= 5)) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('副本数量有效值范围0-5'),
          });
          flag = false;
          this.$refs.square.formDataValidate(i);
          break;
        }
      }

      if (!flag) {
        return;
      }

      // 环境变量
      const envArr = data.spec.configuration.env;
      for (let i = 0; i < envArr.length; i++) {
        if (!envArr[i].name) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('NAME是必填项'),
          });
          flag = false;
          this.envProcessor(i);
          break;
        }
        if (!envArr[i].value) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('VALUE是必填项'),
          });
          flag = false;
          this.envProcessor(i);
          break;
        }
        if (envArr[i].value.length > 2048) {
          this.$bkMessage({
            theme: 'error',
            message: this.$t('VALUE不能超过2048个字符'),
          });
          flag = false;
          this.envProcessor(i);
          break;
        }
      }

      if (!flag) {
        return;
      }

      const paramsData = this.$store.state.cloudApi.cloudAppData;
      if (paramsData.spec.configuration.env.length) {
        paramsData.spec.configuration.env.forEach((element) => {
          if (element.envName) {
            delete element.envName;
          }
          if (element.isAdd) {
            delete element.isAdd;
          }
        });
      }
      // 去除 manifeat_ext 属性
      if (paramsData.metadata.annotations) {
        Object.keys(this.manifestExt.metadata.annotations).forEach((key) => {
          if (paramsData.metadata.annotations[key]) {
            delete paramsData.metadata.annotations[key];
          }
        });
      }
      try {
        this.buttonLoading = true;
        await this.$store.dispatch('deploy/sumbitCloudApp', {
          params: { manifest: paramsData },
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('操作成功'),
        });
        this.$router.push({
          name: 'appStatus',
          query: { env },
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.buttonLoading = false;
      }
    },

    async envProcessor(i) {
      this.handleGoPage('cloudAppDeployForEnv');
      await this.$nextTick();
      this.$refs.square.formDataValidate(i);
    },

    // 取消改变页面状态
    handleCancel() {
      this.$store.commit('cloudApi/updatePageEdit', false);
    },

    // 保存
    async handleSave() {
      try {
        // 处理进程配置数据
        this.$refs[this.routerRefs]?.handleProcessData && this.$refs[this.routerRefs]?.handleProcessData();
        // 处理环境变量校验
        this.envValidate = await (this.$refs[this.routerRefs]?.formDataValidate
        && this.$refs[this.routerRefs]?.formDataValidate());
        if (!this.envValidate) return;   // 没通过校验不提交
        console.log('this.envValidate', this.envValidate);
        debugger;
        const params = { ... this.$store.state.cloudApi.cloudAppData };
        await this.$store.dispatch('deploy/saveCloudAppInfo', {
          appCode: this.appCode,
          params,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('操作成功'),
        });
        this.$store.commit('cloudApi/updatePageEdit', false);
      } catch (e) {
        console.log(e);
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },


    // 查看yaml
    handleYamlView() {
      console.log('dialogCloudAppData', this.dialogCloudAppData);
      this.deployDialogConfig.visible = true;
    },
  },
};
</script>

<style lang="scss" scoped>
@import '../../../../../assets/css/components/conf.scss';
@import './index.scss';
    .title{
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

.deploy-tab-cls{
      /deep/ .bk-tab-section{
        padding: 10px !important;
        border: none
      }
    }
</style>
<style lang="scss">
.deploy-dropdown-menu .bk-dropdown-content{
    display: none !important;
}
</style>
