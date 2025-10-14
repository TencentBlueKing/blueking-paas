<template>
  <div class="bk-apps-wrapper sandbox-container">
    <section class="top-bar card-style">
      <div class="title">
        <div
          class="back"
          @click="back"
        >
          <i class="paasng-arrows-left paasng-icon icon-cls-back mr5"></i>
          <span class="title-text">{{ $t('沙箱开发') }}</span>
        </div>
        <span class="line"></span>
        <div class="flex-row info">
          <div>{{ $t('应用') }}：{{ this.code }}</div>
          <div>{{ $t('模块') }}：{{ this.module }}</div>
        </div>
      </div>
    </section>
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="sandbox-loading"
      :height="450"
    >
      <div class="sandbox-content">
        <div class="top-box">
          <bk-alert
            type="info"
            closable
            @close="alertClose"
            class="sandbox-alert-cls"
          >
            <div slot="title">
              <span>{{ $t('沙箱环境仅用于临时在线调试，如果沙箱环境在 2 小时内没有任何操作，将自动被销毁。') }}</span>
              <bk-popconfirm
                trigger="click"
                ext-cls="sandbox-destroy-cls"
                width="288"
                @confirm="handleSandboxDestruction"
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
                  size="small"
                >
                  {{ $t('立即销毁') }}
                </bk-button>
              </bk-popconfirm>
            </div>
          </bk-alert>
        </div>
        <section :class="['sandbox-editor', { collapse: !isCollapse }, { 'is-alert': isShowTopAlert }]">
          <bk-resize-layout
            placement="right"
            :min="360"
            :initial-divide="360"
            :border="false"
            ext-cls="sandbox-resize-layout"
          >
            <div
              slot="main"
              class="iframe-box"
            >
              <iframe
                v-if="isSandboxReady"
                ref="iframeRef"
                id="iframe-embed"
                :src="iframeUrl"
                scrolling="no"
                frameborder="0"
              />
              <div
                v-else
                class="iframe-loading"
              >
                <img src="/static/images/loading.gif" />
                <p>{{ $t('沙箱环境正在启动，预计需要约 30 秒，请稍候。') }}</p>
              </div>
            </div>
            <!-- 登录展示沙盒后，展示右侧的tab信息 -->
            <right-tab
              slot="aside"
              ref="rightTabRef"
              class="right-tab-cls"
              :data="sandboxData"
              :service-name="serviceName"
              :buildLog="buildLog"
              :runLog="runLog"
              :loading="isLogsLoading"
              :is-load-complete="isSandboxReady"
              :is-rerun="isProcessRunning || isBuildSuccess"
              :btn-loading="isRunNowLoading"
              :is-show-status="isShowRunningStatus"
              :is-build-success="isBuildSuccess"
              @rerun="handleRunNow"
              @run-now="showRunSandboxDialog"
              @submit-code="showSubmitCodeDialog"
              @jump="handleVisitNow"
              @tab-change="rightTabChange"
              @collapse-change="handleRightTabCollapseChange"
            />
          </bk-resize-layout>
        </section>
      </div>
    </paas-content-loader>
    <!-- 立即运行二次确认 -->
    <run-sandbox-dialog
      :show.sync="isRunSandboxVisible"
      :process-data="processData"
      @confirm="handleRunNow"
    />
    <!-- 提交代码 -->
    <submit-code-dialog
      ref="submitCodeDialog"
      :show.sync="isSubmitCodeVisible"
      :config="submitCode"
      @submit="submitCommit"
      @reset="submitCodeReset"
    />
  </div>
</template>

<script>
import RightTab from './comps/right-tab.vue';
import { bus } from '@/common/bus';
import axios from 'axios';
import RunSandboxDialog from './comps/run-sandbox-dialog.vue';
import SubmitCodeDialog from './comps/submit-code-dialog.vue';

export default {
  name: 'Sandbox',
  components: {
    RightTab,
    RunSandboxDialog,
    SubmitCodeDialog,
  },
  provide() {
    return {
      envData: this.envData,
      getSandboxEnvVars: this.getSandboxEnvVars,
    };
  },
  data() {
    return {
      sandboxData: {},
      sandboxAccessible: false,
      isLoading: true,
      deployId: '',
      buildLog: '',
      runLog: '',
      isRunNowLoading: false,
      serviceName: '',
      refreshTime: {
        build: 5,
        run: 5,
      },
      buildIntervalId: null,
      runIntervalId: null,
      sandboxIntervalId: null,
      curTabActive: 'config',
      // 构建日志状态
      buildStatus: '',
      isLogsLoading: true,
      isCollapse: true,
      processInfo: {},
      processData: [],
      isRunSandboxVisible: false,
      isSubmitCodeVisible: false,
      submitCode: {
        loading: false,
        isConfirm: false,
        fileTotal: 0,
        tree: {},
      },
      isShowTopAlert: true,
      envData: {
        sandboxEnvVars: [],
        isEnvLoading: false,
      },
      isVerifyPassword: false,
    };
  },
  computed: {
    code() {
      return this.$route.query.code;
    },
    module() {
      return this.$route.query.module;
    },
    devSandboxCode() {
      return this.$route.query.devSandboxCode;
    },
    isShowNotice() {
      return this.$store.state.isShowNotice;
    },
    iframeUrl() {
      const url = `${this.sandboxData.code_editor_url}?folder=${this.sandboxData.workspace}`;
      return this.ensureHttpProtocol(url);
    },
    // 沙箱加载完成（除状态 Ready 外，还需要检查是否可访问，即网络已通）
    isSandboxReady() {
      return this.sandboxData.status === 'ready' && this.sandboxAccessible && this.isVerifyPassword;
    },
    // 构建成功
    isBuildSuccess() {
      return this.buildStatus === 'Success';
    },
    // 是否存在进程信息
    isProcessRunning() {
      return !!Object.keys(this.processInfo).length;
    },
    // 是否显示运行状态
    isShowRunningStatus() {
      return !!(this.buildStatus && ['Failed', 'Success'].includes(this.buildStatus));
    },
  },
  created() {
    Promise.all([this.getSandboxData(), this.getEnhancedServices(), this.getSandboxEnvVars()]).finally(() => {
      setTimeout(() => {
        this.isLoading = false;
      }, 1000);
    });
    this.sandboxIntervalId = setInterval(() => {
      this.getSandboxData();
    }, 3000);
  },
  mounted() {
    // 当切换到日志tab，默认5s刷新一次日志
    bus.$on('change-refresh-time', (data) => {
      this.$set(this.refreshTime, data.key, data.value);
      this.automaticRefresh();
    });
    bus.$on('refresh-log', (type) => {
      if (this.deployId) {
        type === 'run' ? this.getRunLog() : this.getBuildLog();
      }
    });
  },
  beforeDestroy() {
    this.clearIntervals();
    clearInterval(this.sandboxIntervalId);
    bus.$off('change-refresh-time');
    bus.$off('refresh-log');
  },
  methods: {
    ensureHttpProtocol(url) {
      const protocol = window.location.protocol ?? 'http:';
      const protocolPattern = /^(https?:\/\/)/i;
      // 如果 URL 没有协议，则根据当前环境协议决定
      if (!protocolPattern.test(url)) {
        return `${protocol}//${url}`;
      }
      return url;
    },
    // 沙箱删除处理
    sandboxDeletionHandled() {
      clearInterval(this.sandboxIntervalId);
      this.back();
    },
    rightTabChange(name) {
      this.curTabActive = name;
    },
    // 清除现有的计时器
    clearIntervals() {
      if (this.buildIntervalId) {
        clearInterval(this.buildIntervalId);
        this.buildIntervalId = null;
      }
      if (this.runIntervalId) {
        clearInterval(this.runIntervalId);
        this.runIntervalId = null;
      }
    },
    // 自动刷新获取日志
    automaticRefresh() {
      if (this.curTabActive !== 'log' || !this.deployId) return;
      // 右侧tab高亮切换，当高亮为日志时，需要按照对应时间自动刷新(点击立即运行后，才允许自动刷新)
      this.clearIntervals();
      this.pollingBuildLog();
      this.pollingRunLog();
    },
    // 轮询构建日志
    pollingBuildLog() {
      // 如果构建不成功，则继续获取构建日志
      if (!this.isBuildSuccess) {
        this.buildIntervalId = setInterval(() => {
          this.getBuildLog(true);
        }, this.refreshTime.build * 1000);
      }
    },
    // 轮询运行日志
    pollingRunLog() {
      // 如果运行日志的刷新时间不是 'off'，则继续获取运行日志
      if (this.refreshTime.run !== 'off') {
        this.runIntervalId = setInterval(() => {
          this.getRunLog();
        }, this.refreshTime.run * 1000);
      }
    },
    // 获取界面数据
    async getSandboxData() {
      if (this.isSandboxReady && this.sandboxIntervalId) {
        clearInterval(this.sandboxIntervalId);
        return;
      }
      try {
        const res = await this.$store.dispatch('sandbox/getSandbox', {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
        });

        // 后台报告沙箱未就绪，提前返回，等下一次状态轮询
        if (res.status !== 'ready') {
          return;
        }

        // 后台报告沙箱就绪后，检查网络是否可达（后台 / Web端链路不同，不一定即时可达，以检测结果为准）
        this.sandboxData = res;
        this.sandboxAccessible = await this.getSandboxAccessible();

        // 检查到沙箱网络可达后，再获取沙箱中服务进程状态
        if (this.sandboxAccessible) {
          this.verifyPassword();
          this.getDevServerProcessesStatus();
        }
      } catch (e) {
        if (e.code === 'DEV_SANDBOX_NOT_FOUND') {
          this.sandboxDeletionHandled();
          return;
        }
        this.catchErrorHandler(e);
      }
    },
    // 获取增强服务
    async getEnhancedServices() {
      try {
        const res = await this.$store.dispatch('sandbox/getEnhancedServices', {
          appCode: this.code,
          moduleId: this.module,
        });
        this.serviceName = res.map((service) => service.service?.display_name)?.join(', ');
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 请求函数
    async executeRequest(url, method = 'get', data = null) {
      try {
        const response = await axios({
          method,
          url: this.ensureHttpProtocol(url),
          data,
          headers: {
            Authorization: `Bearer ${this.sandboxData.devserver_token}`,
          },
          timeout: 5000,
        });
        return response.data;
      } catch (e) {
        if (e.code === 'ERR_NETWORK') {
          this.isRunNowLoading = false;
        } else if (e.status === 500 && e.response?.data) {
          this.catchErrorHandler(e.response.data);
          return;
        }
        this.catchErrorHandler(e);
        await Promise.reject(e);
      }
    },
    // 检查沙箱是否已网络可达
    async getSandboxAccessible() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}healthz`);
        const headers = { Authorization: `Bearer ${this.sandboxData.devserver_token}` };

        const response = await axios({ method: 'get', url, headers, timeout: 1000 });
        return response.data.status === 'active';
      } catch (e) {
        console.error('dev sandbox status ready but inaccessible!', e);
      }

      return false;
    },
    // 获取当前沙箱进程状态
    async getDevServerProcessesStatus() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}processes/status`);
        const res = await this.executeRequest(url, 'get');
        this.processInfo = res.status || {};
        if (!!Object.keys(this.processInfo).length) {
          this.switchLogTab();
          // 轮询运行日志
          if (this.runIntervalId) {
            clearInterval(this.runIntervalId);
            this.runIntervalId = null;
          }
          this.pollingRunLog();
        }
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取沙箱进程列表
    async getDevServerProcesses() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}processes/list`);
        const res = await this.executeRequest(url, 'get');
        this.processData = res.processes;
      } catch (error) {
        this.processData = [];
      }
    },
    // 获取沙箱环境变量
    async getSandboxEnvVars() {
      this.$set(this.envData, 'isEnvLoading', true);
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxEnvVars', {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
        });
        // 对环境变量进行排序，确保自定义变量排在前面
        this.envData.sandboxEnvVars = (res || []).sort((a, b) => {
          return b.source === 'custom' ? 1 : a.source === 'custom' ? -1 : 0;
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.$set(this.envData, 'isEnvLoading', false);
      }
    },
    // 切换至日志tab
    switchLogTab() {
      this.$refs.rightTabRef.handleTabChange({ name: 'log', label: this.$t('日志') });
    },
    // 运行沙箱环境二次确认弹窗
    showRunSandboxDialog() {
      this.isRunSandboxVisible = true;
      this.getDevServerProcesses();
    },
    // 立即运行
    async handleRunNow() {
      this.isRunNowLoading = true;
      // 重置状态
      this.buildStatus = '';
      try {
        this.switchLogTab();
        const data = {
          env_vars: this.envData.sandboxEnvVars.reduce((acc, item) => {
            acc[item.key] = item.value;
            return acc;
          }, {}),
        };
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}deploys`);
        const res = await this.executeRequest(url, 'post', data);
        this.deployId = res.deployID;
        // 如果tab为折叠状态时，运行需打开
        if (!this.isCollapse) {
          this.$refs.rightTabRef.handleSwitchSide();
        }
        // 获取相关日志（构建/运行）
        this.getBuildLog();
        this.getRunLog();
        this.clearIntervals();
        this.automaticRefresh();
        this.isLogsLoading = true;
      } catch (e) {
        this.isRunNowLoading = false;
      } finally {
        setTimeout(() => {
          this.isLogsLoading = false;
        }, 300);
      }
    },
    // 获取构建日志
    async getBuildLog(isAutomaticRefresh = false) {
      if (this.isBuildSuccess && isAutomaticRefresh) return;
      try {
        const url = this.ensureHttpProtocol(
          `${this.sandboxData.devserver_url}deploys/${this.deployId}/results?log=true`
        );
        const res = await this.executeRequest(url);
        this.buildLog = res.log;
        // 构建日志成功，无需自动刷新
        this.buildStatus = res.status;
      } finally {
        this.isLogsLoading = false;
        if (this.isBuildSuccess || this.buildStatus === 'Failed') {
          this.isRunNowLoading = false;
        }
      }
    },
    // 运行日志
    async getRunLog() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}app_logs`);
        const res = await this.executeRequest(url);

        this.runLog = res.logs ?? '';
      } finally {
        setTimeout(() => {
          this.isLogsLoading = false;
        }, 300);
      }
    },
    handleVisitNow() {
      const url = this.ensureHttpProtocol(this.sandboxData.app_url);
      window.open(url, '_blank');
    },
    handleRightTabCollapseChange(data) {
      this.isCollapse = data;
    },
    back() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.code,
          moduleId: 'default',
        },
      });
    },
    // 立即销毁
    async handleSandboxDestruction() {
      try {
        await this.$store.dispatch('sandbox/destroySandbox', {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('销毁成功！'),
        });
        this.back();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    showSubmitCodeDialog() {
      this.isSubmitCodeVisible = true;
      this.getDiffs();
    },
    // 获取 diff 信息
    async getDiffs() {
      this.submitCode.loading = true;
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.devserver_url}codes/diffs?tree=true`);
        const res = await this.executeRequest(url);
        this.submitCode.isConfirm = !(res.total > 0);
        this.submitCode.fileTotal = res.total;
        this.submitCode.tree = res.tree;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitCode.loading = false;
      }
    },
    // 提交 commit 信息
    async submitCommit(message) {
      try {
        const res = await this.$store.dispatch('sandbox/sandboxSubmitCode', {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
          data: {
            message,
          },
        });
        this.showMessage(res.repo_url);
        this.isSubmitCodeVisible = false;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.$refs.submitCodeDialog?.closeLoading();
      }
    },
    // commit 成功弹窗
    showMessage(link) {
      const h = this.$createElement;
      const that = this;
      this.$bkMessage({
        message: h('p', [
          `${that.$t('代码提交成功')}，`,
          h(
            'a',
            {
              attrs: {
                href: link,
                target: '_blank',
              },
              style: {
                color: '#3A84FF',
              },
            },
            that.$t('点击跳转到仓库查看')
          ),
        ]),
        theme: 'success',
      });
    },
    submitCodeReset() {
      this.submitCode.loading = false;
      this.submitCode.isConfirm = false;
    },
    alertClose() {
      this.isShowTopAlert = false;
    },
    // 完成密码验证
    async verifyPassword() {
      try {
        const url = this.ensureHttpProtocol(`${this.sandboxData.code_editor_url}login?folder=/data/workspace&to=`);
        const formData = new URLSearchParams({
          base: '.',
          href: url,
          password: this.sandboxData.code_editor_password,
        });

        await axios.post(url, formData.toString(), {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          timeout: 1000,
          withCredentials: true,
        });
      } catch (e) {
        console.error('Password verification failed!', e);
      } finally {
        this.isVerifyPassword = true;
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.footer-tools-box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 24px;
  background: #e1ecff;
  box-shadow: 0 -2px 4px 0 #00000014;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;

  .run-tip {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    transform: translateY(-100%);
  }

  i {
    font-size: 14px;
  }
  .paasng-stop-shape {
    font-size: 18px;
    transform: translateY(0px);
    color: #ea3636;
  }
  .paasng-refresh-line {
    color: #2dcb56;
  }
}
.ml8 {
  margin-left: 8px;
}
.sandbox-container {
  overflow: hidden;
  height: 100%;
  background: #f5f7fa;
  .fadeout {
    height: calc(100% - 52px);
  }
  .fore {
    color: #313238;
  }
  .top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 52px;
    padding: 0 24px;
    .title {
      display: flex;
      align-items: center;
      .title-text {
        font-size: 16px;
        color: #313238;
      }
      .line {
        display: inline-block;
        width: 1px;
        height: 14px;
        background-color: #dcdee5;
        margin: 0 8px;
      }
      .info {
        gap: 16px;
        font-size: 14px;
        color: #979ba5;
      }
    }
    .back {
      cursor: pointer;
      color: #3a84ff;
      font-size: 18px;
      i {
        font-weight: 700;
      }
    }
  }
  .sandbox-alert-cls /deep/ .bk-alert-wraper {
    height: 32px;
    align-items: center;
  }
  .sandbox-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    .top-box {
      display: flex;
      /deep/ .bk-button {
        flex-shrink: 0;
        margin-right: 12px;
      }
      /deep/ .bk-alert {
        flex: 1;
      }
    }
    .sandbox-editor {
      min-height: 0;
      flex: 1;
      &.collapse {
        margin-right: 0;
        overflow-x: hidden;
        /deep/ .bk-resize-layout-aside {
          width: 0 !important;
        }
      }
      .sandbox-resize-layout {
        height: 100%;
        /deep/ .bk-resize-layout-main {
          margin-right: 24px;
        }
        /deep/ .bk-resize-layout-aside {
          border: none !important;
        }
      }
      .iframe-box {
        position: relative;
        height: 100%;
        iframe#iframe-embed {
          position: relative;
          width: 100%;
          height: 100%;
          /* resize seems to inherit in at least Firefox */
          -webkit-resize: none;
          -moz-resize: none;
          resize: none;
          z-index: 9;
        }
      }
      .iframe-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        width: 100%;
        height: 100%;
        img {
          width: 220px;
        }
      }
      .right-tab-cls {
        flex-shrink: 0;
      }
    }
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
