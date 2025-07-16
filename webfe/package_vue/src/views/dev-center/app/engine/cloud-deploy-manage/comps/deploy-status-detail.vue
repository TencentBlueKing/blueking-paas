<template>
  <div class="deploy-view pl10 pr10 pt20">
    <!-- 部署中、部署成功、部署失败 -->
    <div v-if="isWatchDeploying || isDeploySuccess || isDeployFail">
      <bk-alert
        type="info"
        :show-icon="false"
        class="mb20 alert-cls"
        v-if="isWatchDeploying"
      >
        <div
          class="flex-row align-items-center justify-content-between"
          slot="title"
        >
          <div class="flex-row align-items-center">
            <div class="fl">
              <round-loading
                size="small"
                ext-cls="deploy-round-loading"
              />
            </div>
            <p class="deploy-pending-text pl20">
              {{ $t('正在部署中...') }}
            </p>
            <p class="deploy-text-wrapper">
              <span v-if="deploymentInfo.build_method === 'dockerfile' && deploymentInfo.version_info">
                <!-- 分支 -->
                <span v-if="deploymentInfo.version_info.version_type === 'branch'">
                  <span class="version-text pl10">
                    {{ $t('版本：') }}
                    {{ deploymentInfo.version_info.revision ? deploymentInfo.version_info.revision.substring(0, 8) : '--' }}
                  </span>
                  <span class="branch-text pl30">
                    {{ $t('分支：') }}
                    {{ deploymentInfo.version_info.version_name }}
                  </span>
                </span>
                <!-- tag -->
                <span v-else>
                  <span class="branch-text">
                    {{ $t('镜像Tag：') }}
                    {{ deploymentInfo.version_info.version_name || '--' }}
                  </span>
                </span>
              </span>
              <span v-if="deploymentInfo.build_method === 'custom_image' && deploymentInfo.version_info">
                <span class="branch-text">
                  {{ $t('镜像Tag：') }}
                  {{ deploymentInfo.version_info.version_name || '--' }}
                </span>
              </span>
              <span
                v-if="deployTotalTime"
                class="time-text"
              >
                {{ $t('耗时：') }} {{ deployTotalTimeDisplay }}
              </span>
            </p>
          </div>
          <div
            v-if="appearDeployState.includes('build') || appearDeployState.includes('release')"
            class="action-wrapper"
          >
            <bk-button
              theme="primary"
              size="small"
              :outline="true"
              @click="stopDeploy"
            >
              {{ $t('停止部署') }}
            </bk-button>
          </div>
        </div>
      </bk-alert>
      <bk-alert
        type="error"
        :show-icon="false"
        class="mb20 alert-cls"
        v-if="isDeployFail"
      >
        <div
          class="flex-row align-items-center justify-content-between"
          slot="title"
        >
          <div class="flex-row align-items-center">
            <p class="deploy-pending-text pl10">
              {{ $t('部署失败') }}
            </p>
            <p class="pl20">
              <span>{{ curDeployResult.possible_reason }}</span>
              <span
                class="pl10"
                v-if="curDeployResult.result === 'failed'"
              >
                <span
                  v-for="(help, index) in curDeployResult.error_tips.helpers"
                  :key="index"
                >
                  <a
                    :href="help.link"
                    target="_blank"
                    class="mr10"
                  >
                    {{ help.text }}
                  </a>
                </span>
              </span>
            </p>
          </div>
          <bk-button
            theme="danger"
            ext-cls="paas-deploy-failed-btn ml10"
            outline
            size="small"
            @click="handleCallback"
          >
            {{ $t('返回') }}
          </bk-button>
        </div>
      </bk-alert>
      <bk-alert
        type="success"
        :show-icon="false"
        class="mb20 alert-cls"
        v-if="isDeploySuccess"
      >
        <div
          class="flex-row align-items-center justify-content-between"
          slot="title"
        >
          <p class="deploy-pending-text pl10">
            {{ $t('部署成功') }}
          </p>
          <section>
            <bk-button
              theme="success"
              ext-cls="paas-deploy-success-btn"
              outline
              size="small"
              @click="handleOpenLink"
            >
              {{ $t('访问') }}
            </bk-button>
            <bk-button
              style="margin-left: 6px"
              theme="success"
              ext-cls="paas-deploy-success-btn"
              outline
              size="small"
              @click="handleCallback"
            >
              {{ $t('返回') }}
            </bk-button>
          </section>
        </div>
      </bk-alert>
    </div>
    <div class="deploy-time-log flex-row">
      <div
        id="deploy-timeline-box"
        style="width: 230px"
      >
        <deploy-timeline
          ref="deployTimelineRef"
          :key="timelineComKey"
          :list="timeLineList"
          :stage="curDeployStage"
          disabled
        />
      </div>
      <deploy-log
        v-if="isWatchDeploying || isDeploySuccess || isDeployFail || isDeployInterrupted || isDeployInterrupting"
        ref="deployLogRef"
        :build-list="streamLogs"
        :ready-list="readyLogs"
        :release-list="releaseLogs"
        :process-list="allProcesses"
        :state-process="appearDeployState"
        :process-loading="processLoading"
        :environment="environment"
      />
    </div>

    <bk-dialog
      v-model="stopDeployConf.visiable"
      width="480"
      :title="stopDeployConf.title"
      :theme="'primary'"
      :mask-close="false"
      :draggable="false"
      header-position="left"
      @confirm="confirmStopDeploy"
      @cancel="cancelStopDeploy"
      @after-leave="afterLeaveStopDeploy"
    >
      <div v-if="stopDeployConf.stage === 'build'">
        {{ $t('数据库如有变更操作') }}，
        <span style="color: #f00">
          {{ $t('数据库变更可能会异常中断且无法回滚') }}
        </span>
        ，{{ $t('请留意表结构') }}。
      </div>
      <div v-else>
        {{ $t('部署命令已经下发') }}，
        <span style="color: #f00">{{ $t('仅停止检查部署结果') }}</span>
        ，{{ $t('请留意进程状态') }}。
      </div>
    </bk-dialog>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployTimeline from './deploy-timeline';
import deployLog from './deploy-log';
import moment from 'moment';
import _ from 'lodash';
export default {
  components: {
    deployTimeline,
    deployLog,
  },
  mixins: [appBaseMixin],
  props: {
    environment: {
      type: String,
      default: () => 'stag',
    },
    deploymentId: {
      // 部署id, stream流需要用到的参数
      type: String,
      default: () => '',
    },
    deploymentInfo: {
      type: Object,
      default: () => {},
    },
    rvData: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    const curDeployResult = {
      possible_reason: '',
      logs: '',
      exposedLink: '',
      title: '',
      result: '',
      resultMessage: this.$t('应用部署成功，已发布至蓝鲸应用市场。'),
      error_tips: null,
      getResultDisplay() {
        if (this.result === 'successful') {
          return this.$t('部署成功');
        }
        return this.$t('部署失败');
      },
      getTitleDisplay() {
        if (this.result) {
          return this.$t('项目部署结束');
        }
        return this.title;
      },
    };
    return {
      serverLogEvent: null,
      timelineComKey: -1,
      readyLogs: [], // 准备阶段日志流信息
      streamLogs: [], // 构建阶段日志流信息
      releaseLogs: [], // 部署阶段日志流信息
      eventSourceState: {
        CLOSED: 2,
      },
      isLogError: false, // 日志错误
      appearDeployState: [],
      deployStartTimeQueue: [],
      deployEndTimeQueue: [],
      isDeploySuccess: false,
      isDeployFail: false,
      isDeployInterrupted: false,
      isDeployInterrupting: false,
      isWatchDeploying: false,
      timeLineList: [], // 时间节点数据
      curDeployResult,
      deployTotalTime: 0, // 部署总耗时
      appMarketPublished: false, // 是否发布到应用市场
      allProcesses: [], // 全部进程
      processLoading: false,
      prevProcessVersion: 0,
      prevInstanceVersion: 0,
      releaseId: '', // 部署id
      isDeployReady: true,
      isBuildReady: false,
      curModuleInfo: {}, // 当前模块的信息
      serverProcessEvent: null,
      watchServerTimer: null,
      stopDeployConf: {
        // 停止部署
        title: '',
        visiable: false,
        isLoading: false,
        stage: '',
      },
      serverTimeout: 30,
      watchRvData: {},
      exposedLink: '',
    };
  },
  computed: {
    curDeployStage() {
      const flag =
        this.isWatchDeploying ||
        this.isDeploySuccess ||
        this.isDeployFail ||
        this.isDeployInterrupted ||
        this.isDeployInterrupting;
      return flag ? 'deploy' : 'noDeploy';
    },
    curModuleId() {
      // 当前模块的名称
      return this.deploymentInfo.module_name;
    },
    // 总时间
    deployTotalTimeDisplay() {
      return this.getDisplayTime(this.deployTotalTime);
    },
  },
  watch: {
    deploymentId: {
      handler(v) {
        this.$nextTick(() => {
          // 延迟一秒 等待getPreDeployDetail方法执行完
          setTimeout(() => {
            this.watchDeployStatus(v);
          }, 1000);
        });
      },
      immediate: true,
    },
    // 接受父组件传过来的rvData
    rvData: {
      handler(v) {
        this.watchRvData = _.cloneDeep(v);
      },
      immediate: true,
    },
  },
  created() {
    this.init();
  },
  mounted() {
    // 初始化日志彩色组件
    // eslint-disable-next-line
    const AU = require('ansi_up');
    // eslint-disable-next-line
    this.ansiUp = new AU.default();

    window.addEventListener('scroll', () => {
      this.isScrollFixed =
        (this.isWatchDeploying ||
          this.isWatchOfflineing ||
          this.isDeploySuccess ||
          this.isDeployFail ||
          this.isDeployInterrupted ||
          this.isDeployInterrupting) &&
        window.pageYOffset >= 260;
    });

    window.addEventListener('resize', () => {
      // this.computedBoxFixed();
    });
    // 部署处于准备阶段的判断标识，用于获取准备阶段的日志
    this.isDeployReady = true;
    // 部署处于构建阶段的判断标识，用于获取构建阶段的日志
    this.isBuildReady = false;
  },
  beforeDestroy() {
    // 页面销毁 关闭右边的部署进程watch事件
    this.closeServerPush();
    // 关闭左边的timeline时间轴watch事件
    this.serverLogEvent && this.serverLogEvent.close();
  },
  methods: {
    init() {
      this.getPreDeployDetail();
      // this.getModuleProcessList();
    },
    /**
     * 监听部署进度，打印日志
     */
    watchDeployStatus(deployId) {
      this.serverLogEvent = null;
      this.timelineComKey = +new Date();
      this.streamLogs = [];
      this.streamPanelShowed = true;
      this.isDeploySseEof = false;
      this.isWatchDeploying = true;

      clearInterval(this.watchTimer);
      if (this.serverLogEvent === null || this.serverLogEvent.readyState === this.eventSourceState.CLOSED) {
        this.serverLogEvent = new EventSource(`${BACKEND_URL}/streams/${deployId}?include_ansi_codes=true`, {
          withCredentials: true,
        });
        this.serverLogEvent.onmessage = (event) => {
          // 如果是error，会重新发起日志请求，在下次信息返回前清空上次信息
          if (this.isLogError) {
            this.streamLogs = [];
            this.isLogError = false;
            // streamLogItems = []
          }
          const item = JSON.parse(event.data);
          if (this.isDeployReady) {
            this.appearDeployState.push('preparation');
            this.$nextTick(() => {
              this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.editNodeStatus('preparation', 'pending', '');
            });
            this.readyLogs.push(this.ansiUp.ansi_to_html(item.line));
          } else if (this.isBuildReady) {
            this.streamLogs.push(this.ansiUp.ansi_to_html(item.line));
          } else {
            this.releaseLogs.push(this.ansiUp.ansi_to_html(item.line));
          }
        };

        this.serverLogEvent.addEventListener('phase', (event) => {
          const item = JSON.parse(event.data);
          if (item.name === 'build') {
            // 更改输出流到构建阶段 streamLogs
            this.isDeployReady = false;
            this.isBuildReady = true;
          }
          if (item.name === 'release') {
            // 更改输出流到部署阶段 releaseLogs
            this.isDeployReady = false;
            this.isBuildReady = false;
          }

          if (['build', 'preparation'].includes(item.name)) {
            this.appearDeployState.push(item.name);
          }
          let content = '';
          if (item.status === 'successful') {
            this.deployStartTimeQueue.push(item.start_time);
            this.deployEndTimeQueue.push(item.complete_time);
          }

          if ((item.name === 'release' || item.name === 'build') && ['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.name === 'release' && item.status === 'successful') {
            // 部署成功
            this.isDeploySuccess = true;
            this.isWatchDeploying = false;
            this.getExposedLink();
            // 更新当前模块信息
            // this.getModuleProcessList();
          } else if (item.status === 'failed') {
            // 部署失败
            this.isDeployFail = true;
            this.isWatchDeploying = false;
          } else if (item.status === 'interrupted') {
            // 停止部署成功
            this.isDeployInterrupted = true;
            this.isDeployInterrupting = false;
          }
          this.$nextTick(() => {
            this.$refs.deployTimelineRef &&
              this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
          });
        });

        this.serverLogEvent.addEventListener('step', (event) => {
          const item = JSON.parse(event.data);
          let content = '';

          if (item.name === this.$t('检测部署结果') && item.status === 'pending') {
            this.appearDeployState.push('release');
            // 更新日志输出流到 releaseLogs
            this.isDeployReady = false;
            this.isBuildReady = false;
            this.releaseId = item.bkapp_release_id;
            if (!this.processLoading) {
              this.getModuleProcessList(true).then(() => {
                // 发起服务监听
                this.watchServerPush();
                this.$nextTick(() => {
                  this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation('release');
                });
              });
            }
          }

          if (['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.status === 'successful' && item.name === this.$t('检测部署结果')) {
            this.serverProcessEvent && this.serverProcessEvent.close(); // 关闭进程的watch事件流
          }
          this.$nextTick(() => {
            // eslint-disable-next-line max-len
            this.$refs.deployTimelineRef &&
              this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
          });
          this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.$forceUpdate();
        });

        this.serverLogEvent.onerror = () => {
          this.isLogError = true;

          if (this.serverLogEvent.readyState === this.eventSourceState.CLOSED) {
            // 超过重试限制
            if (this.reConnectTimes >= this.reConnectLimit) {
              this.$paasMessage({
                theme: 'error',
                message: this.$t('日志输出流异常，建议您刷新页面重试!'),
              });
            }

            this.reConnectTimes += 1;
            // cancel debounced before we start new one
            // this.timeoutDebounced.cancel()
            setTimeout(() => {
              this.watchDeployStatus(deployId);
            }, 3000);
          }
        };

        // 监听到部署结束
        this.serverLogEvent.addEventListener(
          'EOF',
          () => {
            this.reConnectTimes = 0;
            this.serverLogEvent.close();
            this.serverProcessEvent && this.serverProcessEvent.close(); // 关闭进程的watch事件流
            this.isDeploySseEof = true;
            // this.allProcesses = JSON.parse(JSON.stringify(this.allProcesses))

            // 判断是否在准备阶段就失败
            const isReadyFailed = this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleGetIsInit();

            isReadyFailed && this.$refs.deployTimelineRef.editNodeStatus('preparation', 'failed', '');

            this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleSetFailed();

            if (this.isDeploySuccess) {
              this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.editNodeStatus('release', 'successful', '');
            }
            this.getDeployResult(deployId);
          },
          false
        );

        // 监听到部署slider title变化
        this.serverLogEvent.addEventListener(
          'title',
          (event) => {
            this.curDeployResult.title = event.data;
          },
          true
        );
      }
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
        if (this.watchServerTimer) {
          clearTimeout(this.watchServerTimer);
        }
      }
    },

    /**
     * 计算部署进程间的所花时间
     */
    computedDeployTime(startTime, endTime) {
      const start = new Date(startTime).getTime();
      const end = new Date(endTime).getTime();
      const interval = (end - start) / 1000;

      if (!interval) {
        return `< 1${this.$t('秒')}`;
      }

      return this.getDisplayTime(interval);
    },

    /**
     * 展示到页面的时间
     */
    getDisplayTime(payload) {
      let theTime = payload;
      if (theTime < 1) {
        return `< 1${this.$t('秒')}`;
      }
      let middle = 0;
      let hour = 0;

      if (theTime > 60) {
        middle = parseInt(theTime / 60, 10);
        theTime = parseInt(theTime % 60, 10);
        if (middle > 60) {
          hour = parseInt(middle / 60, 10);
          middle = parseInt(middle % 60, 10);
        }
      }

      let result = '';

      if (theTime > 0) {
        result = `${theTime}${this.$t('秒')}`;
      }
      if (middle > 0) {
        result = `${middle}${this.$t('分')}${result}`;
      }
      if (hour > 0) {
        result = `${hour}${this.$t('时')}${result}`;
      }

      return result;
    },

    /**
     * 获取部署前各阶段详情
     */
    async getPreDeployDetail() {
      try {
        const res = await this.$store.dispatch('deploy/getPreDeployDetail', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        const timeLineList = [];
        res.forEach((stageItem) => {
          timeLineList.push({
            // name: 部署阶段的名称
            name: stageItem.type,
            // tag: 部署阶段的展示名称
            tag: stageItem.display_name,
            // content: 完成时间
            content: '',
            // status: 部署阶段的状态
            status: 'default',
            displayBlocks: this.formatDisplayBlock(stageItem.display_blocks),
            // stage: 部署阶段类型, 仅主节点有该字段
            stage: stageItem.type,
            // sse没返回子进程的状态时强行改变当前的进程状态为 pending 的标识
            loading: false,
          });

          stageItem.steps.forEach((stepItem) => {
            timeLineList.push({
              // name: 部署阶段的名称
              name: stepItem.name,
              // tag: 部署阶段的展示名称
              tag: stepItem.display_name,
              // content: 完成时间
              content: '',
              // status: 部署阶段的状态
              status: 'default',
              parent: stageItem.display_name,
              parentStage: stageItem.type,
            });
          });
        });
        this.timeLineList = timeLineList;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      }
    },

    // 获取部署成功访问链接
    async getExposedLink() {
      const res = await this.$store.dispatch('entryConfig/getEntryDataList', {
        appCode: this.appCode,
      });
      const curModuleInfo = res.find((e) => e.name === this.curModuleId);
      const curDatabase = curModuleInfo?.envs[this.environment] || [];
      const exposedData = curDatabase.find((e) => e.address.type !== 'custom') || {}; // 访问链接
      this.exposedLink = exposedData?.address?.url || '';
    },

    /**
     * 获取部署结果
     */
    async getDeployResult(deployId) {
      try {
        const res = await this.$store.dispatch('deploy/getDeployResult', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          deployId,
        });
        this.curDeployResult.result = res.status;
        this.curDeployResult.logs = res.logs;
        if (res.status === 'successful') {
          this.computedTotalTime();
          this.curDeployResult.possible_reason = '';
          this.curDeployResult.error_tips = null;

          const appInfo = await this.$store.dispatch('getAppInfo', {
            appCode: this.appCode,
            moduleId: this.curModuleId,
          });
          this.appMarketPublished = appInfo.web_config.market_published;
        } else {
          this.curDeployResult.possible_reason = res.error_tips.possible_reason;
          this.curDeployResult.error_tips = res.error_tips;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('部署失败，请稍候再试'),
        });
      } finally {
        this.isWatchDeploying = false;
      }
    },

    // 成功计算部署总耗时
    computedTotalTime() {
      const startTime = new Date(this.deployStartTimeQueue[0]).getTime();
      const endTime = new Date(this.deployEndTimeQueue[this.deployEndTimeQueue.length - 1]).getTime();
      this.deployTotalTime = (endTime - startTime) / 1000;
    },

    // 展示时间节点数据
    formatDisplayBlock(displays) {
      const displayBlocks = [];
      const keys = Object.keys(displays);
      for (const key of keys) {
        const sourceInfo = [];
        if (displays[key].display_name) {
          sourceInfo.push({
            text: this.$t('类型'),
            value: displays[key].display_name,
          });
        }
        if (displays[key].repo_url) {
          sourceInfo.push({
            text: this.$t('地址'),
            value: displays[key].repo_url,
          });
        }
        if (displays[key].source_dir) {
          sourceInfo.push({
            text: this.$t('部署目录'),
            value: displays[key].source_dir,
          });
        }
        if (this.curAppInfo.application.is_plugin_app) {
          sourceInfo.push({
            text: this.$t('模块类型'),
            value: this.$t('蓝鲸插件'),
            href: this.GLOBAL.LINK.BK_PLUGIN,
            hrefText: this.$t('查看详情'),
          });
        }

        // 普通应用不展示
        if (
          this.curAppModule.web_config.templated_source_enabled &&
          this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.NORMAL_APP
        ) {
          sourceInfo.push(
            {
              text: this.$t('初始化模板类型'),
              value: this.initTemplateTypeDisplay || '--',
            },
            {
              text: this.$t('初始化模板说明'),
              value: this.initTemplateDesc || '--',
              downloadBtn: this.handleDownloadTemplate,
              downloadBtnText: this.initTemplateDesc === '--' ? '' : this.$t('下载模板代码'),
            }
          );
        }

        if (this.curAppModule.web_config.runtime_type !== 'custom_image') {
          const smartRoute = [
            {
              name: this.$t('查看包版本'),
              route: {
                name: 'appPackages',
              },
            },
          ];
          const value = this.isSmartApp
            ? smartRoute
            : this.curAppModule.source_origin === 1
            ? this.$t('代码库')
            : this.$t('蓝鲸运维开发平台提供源码包');
          // 普通应用不展示
          if (this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.NORMAL_APP) {
            sourceInfo.push({
              text: this.$t('源码管理'),
              value,
            });
          }
        }

        switch (key) {
          // 源码信息
          case 'source_info':
            displayBlocks.push({
              name:
                this.curAppModule.web_config.runtime_type === 'custom_image'
                  ? this.$t('镜像信息')
                  : this.$t('源码信息'),
              type: 'key-value',
              routerName: 'moduleManage',
              key,
              infos: sourceInfo,
            });
            break;

          // 增强服务
          case 'services_info':
            displayBlocks.push({
              name: this.$t('增强服务'),
              type: 'key-value',
              key,
              infos: [
                {
                  text: this.$t('启用未创建'),
                  value: displays[key]
                    .filter((item) => !item.is_provisioned)
                    .map((item) => item.display_name)
                    .join(', '),
                },
                {
                  text: this.$t('已创建实例'),
                  value: displays[key]
                    .filter((item) => item.is_provisioned)
                    .map((item) => ({
                      name: item.display_name,
                      route: {
                        name: 'appServiceInner',
                        params: {
                          id: this.appCode,
                          service: item.service_id,
                          category_id: item.category_id,
                        },
                      },
                    })),
                },
              ],
            });
            break;

          // 运行时的信息
          case 'runtime_info':
            displayBlocks.push({
              name: this.$t('运行时信息'),
              type: 'key-value',
              routerName: 'appEnvVariables',
              key,
              infos: [
                {
                  text: this.$t('基础镜像'),
                  value: displays[key].image,
                },
                {
                  text: this.$t('构建工具'),
                  value: displays[key].buildpacks.map((item) => item.display_name).join(', '),
                },
              ],
            });
            break;

          // 访问地址
          case 'access_info':
            displayBlocks.push({
              name: this.$t('访问地址'),
              type: 'key-value',
              routerName: 'appEntryConfig',
              key,
              infos: [
                {
                  text: this.$t('当前类型'),
                  value:
                    displays[key] && displays[key].type === 'default_subdomain' ? this.$t('子域名') : this.$t('子路径'),
                },
                {
                  text: this.$t('访问地址'),
                  value: displays[key].address,
                },
              ],
            });
            break;

          // 帮助文档
          case 'prepare_help_docs':
          case 'build_help_docs':
          case 'release_help_docs':
            displayBlocks.push({
              name: this.$t('帮助文档'),
              type: 'link',
              key,
              infos: displays[key].map((doc) => ({
                text: doc.name,
                value: doc.link,
              })),
            });
            break;
        }
      }
      return displayBlocks;
    },

    // 获取所有模块列表
    async getModuleProcessList(isLoading = false) {
      this.processLoading = isLoading;
      try {
        const res = await this.$store.dispatch('deploy/getModuleReleaseList', {
          appCode: this.appCode,
          env: this.environment,
          deployId: this.deploymentId,
        });
        this.curModuleInfo = res.data.find((e) => e.module_name === this.curModuleId);
        // 获取到新的rv_inst数据 重新赋值
        this.watchRvData = {
          rvInst: res.rv_inst,
          rvProc: res.rv_proc,
        };
        this.formatProcesses(this.curModuleInfo);
        return Promise.resolve(true);
      } catch (e) {
        // 无法获取进程目前状态
        console.error(e);
      } finally {
        this.processLoading = false;
      }
    },

    // 对数据进行处理
    formatProcesses(processesData) {
      const allProcesses = [];

      // 遍历进行数据组装
      const packages = processesData.proc_specs;
      const { instances } = processesData;

      processesData.processes.forEach((processItem) => {
        const { type } = processItem;
        const packageInfo = packages.find((item) => item.name === type);

        const processInfo = {
          ...processItem,
          ...packageInfo,
          instances: [],
        };

        instances.forEach((instance) => {
          if (instance.process_type === type) {
            processInfo.instances.push(instance);
          }
        });

        // 作数据转换，以兼容原逻辑
        const process = {
          name: processInfo.name,
          instance: processInfo.instances.length,
          instances: processInfo.instances,
          targetReplicas: processInfo.target_replicas,
          isStopTrigger: false,
          targetStatus: processInfo.target_status,
          isActionLoading: false, // 用于记录进程启动/停止接口是否已完成
          maxReplicas: processInfo.max_replicas,
          status: 'Stopped',
          cmd: processInfo.command,
          // operateIconTitle: operateIconTitle,
          // operateIconTitleCopy: operateIconTitle,
          // isShowTooltipConfirm: false,
          desired_replicas: processInfo.replicas,
          available_instance_count: processInfo.success,
          failed: processInfo.failed,
          resourceLimit: processInfo.resource_limit,
          clusterLink: processInfo.cluster_link,
        };

        this.$set(process, 'expanded', false);

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute').fromNow();
        });
        allProcesses.push(process);
      });
      // this.allProcesses = JSON.parse(JSON.stringify(allProcesses));
      this.$set(this, 'allProcesses', JSON.parse(JSON.stringify(allProcesses)));
    },

    // 监听进程事件流
    watchServerPush() {
      // 停止轮询的标志
      if (this.watchServerTimer) {
        clearTimeout(this.watchServerTimer);
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/envs/${this.environment}/processes/watch/?rv_proc=${this.watchRvData.rvProc}&rv_inst=${this.watchRvData.rvInst}&timeout_seconds=${this.serverTimeout}`;
      this.serverProcessEvent = new EventSource(url, {
        withCredentials: true,
      });

      // 收藏服务推送消息
      this.serverProcessEvent.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.warn(data);
        if (data.object_type === 'process') {
          if (data.object.module_name !== this.curModuleId) return; // 更新当前模块的进程
          this.updateProcessData(data);
        } else if (data.object_type === 'instance') {
          if (data.object.module_name !== this.curModuleId || data.object.version !== this.releaseId) return; // 更新当前模块的进程且是当前版本
          this.updateInstanceData(data);
          // if (data.type === 'ADDED') {
          //   if (data.object.module_name !== this.curModuleId) return;   // 更新当前模块的进程
          //   console.warn(this.$t('重新拉取进程...'));
          //   this.getModuleProcessList(false);
          // }
        } else if (data.type === 'ERROR') {
          // 判断 event.type 是否为 ERROR 即可，如果是 ERROR，就等待 2 秒钟后，重新发起 list/watch 流程
          clearTimeout(this.timer);
          this.timer = setTimeout(() => {
            // this.getProcessList(this.releaseId, false);
          }, 2000);
        }
      };

      // 服务异常
      this.serverProcessEvent.onerror = (event) => {
        // 异常后主动关闭，否则会继续重连
        console.error(this.$t('推送异常'), event);
        // this.serverProcessEvent.close();

        // 推迟调用，防止过于频繁导致服务性能问题
        // this.watchServerTimer = setTimeout(() => {
        //   this.watchServerPush();
        // }, 3000);
      };

      // 服务结束
      this.serverProcessEvent.addEventListener('EOF', () => {
        // 侧栏监听到EOF就不需要重新watch了 一般不会再侧栏看状态
        this.serverProcessEvent.close();

        // if (!this.isDeploySseEof) {
        //   // 推迟调用，防止过于频繁导致服务性能问题
        //   this.watchServerTimer = setTimeout(() => {
        //     this.watchServerPush();
        //   }, 3000);
        // }
      });
    },

    // 更新进程
    updateProcessData(data) {
      const processData = data.object || {};
      this.prevProcessVersion = data.resource_version || 0;

      if (data.type === 'ADDED') {
        this.getModuleProcessList(false);
      } else if (data.type === 'MODIFIED') {
        this.allProcesses.forEach((process) => {
          if (process.name === processData.type && process.version === this.releaseId) {
            process.available_instance_count = processData.success;
            process.desired_replicas = processData.replicas;
            process.failed = processData.failed;
            this.updateProcessStatus(process);
          }
        });
      } else if (data.type === 'DELETED') {
        this.allProcesses = this.allProcesses.filter((process) => process.name !== processData.type);
      }
    },

    // 更新实例
    updateInstanceData(data) {
      const instanceData = data.object || {};
      this.prevInstanceVersion = data.resource_version || 0;

      instanceData.date_time = moment(instanceData.start_time).startOf('minute').fromNow();
      this.allProcesses.forEach((process) => {
        if (process.name === instanceData.process_type) {
          // 新增
          if (data.type === 'ADDED') {
            // 防止在短时间内重复推送
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                process.instances.splice(index, 1);
              }
            });
            process.instances.push(instanceData);
          } else {
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                if (data.type === 'DELETED') {
                  // 删除
                  process.instances.splice(index, 1);
                } else {
                  // 更新
                  process.instances.splice(index, 1, instanceData);
                }
              }
            });
          }

          this.updateProcessStatus(process);
        }
      });
    },

    // 返回操作
    handleCallback() {
      this.$emit('close');
    },

    // 打开链接
    handleOpenLink() {
      window.open(this.exposedLink);
    },

    // 更新进程状态
    updateProcessStatus(process) {
      /*
       * 设置进程状态
       * targetStatus: 进行的操作，start\stop\scale
       * status: 操作状态，Running\stoped
       *
       * 如何判断进程当前是否为操作中（繁忙状态）？
       * 主要根据 process_packages 里面的 target_status 判断：
       * 如果 target_status 为 stop，仅当 processes 里面的 success 为 0 且实例为 0 时正常，否则为操作中
       * 如果 target_status 为 start，仅当 success 与 target_replicas 一致，而且 failed 为 0 时正常，否则为操作中
       */
      if (process.targetStatus === 'stop') {
        // process.operateIconTitle = '启动进程'
        // process.operateIconTitleCopy = '启动进程'
        if (process.available_instance_count === 0 && process.instances.length === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      } else if (process.targetStatus === 'start') {
        // process.operateIconTitle = '停止进程'
        // process.operateIconTitleCopy = '停止进程'
        if (process.available_instance_count === process.targetReplicas && process.failed === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      }
    },

    // 停止部署
    stopDeploy() {
      if (this.appearDeployState.includes('build')) {
        this.stopDeployConf.title = this.$t('确认停止【构建阶段】吗？');
        this.stopDeployConf.stage = 'build';
      }

      if (this.appearDeployState.includes('release')) {
        this.stopDeployConf.title = this.$t('确认停止【部署阶段】吗？');
        this.stopDeployConf.stage = 'release';
      }
      this.stopDeployConf.visiable = true;
    },

    // 确认停止部署
    async confirmStopDeploy() {
      try {
        await this.$store.dispatch('deploy/stopDeploy', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          deployId: this.deploymentId,
        });
        // 停止部署 返回
        // this.handleCallback();
        // this.cancelStopDeploy();  // 关闭弹窗
        // this.getDeployResult(this.deploymentId);
        this.closeServerPush();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('部署失败，请稍候再试'),
        });
      }
    },

    cancelStopDeploy() {
      this.stopDeployConf.visiable = false;
    },

    afterLeaveStopDeploy() {
      this.stopDeployConf.title = '';
      this.stopDeployConf.stage = '';
    },
  },
};
</script>
<style lang="scss" scoped>
.deploy-pending-text {
  color: #63656e;
  font-weight: 700;
  font-size: 14px;
}
.deploy-text-wrapper {
  padding-left: 30px;
}
.alert-cls {
  border: none !important;
  /deep/ .bk-alert-wraper {
    padding: 5px 10px;
  }
}
</style>
