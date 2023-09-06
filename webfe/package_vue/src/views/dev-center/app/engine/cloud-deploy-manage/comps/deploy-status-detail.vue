<template>
  <div class="deploy-view pl10 pr10 pt20">
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
          :disabled="isWatchDeploying || isDeploySuccess || isDeployFail || isDeployInterrupted || isDeployInterrupting"
        />
      </div>
      <deploy-log
        v-if="isWatchDeploying || isDeploySuccess || isDeployFail || isDeployInterrupted || isDeployInterrupting"
        ref="deployLogRef"
        :build-list="streamLogs"
        :ready-list="readyLogs"
        :process-list="allProcesses"
        :state-process="appearDeployState"
        :process-loading="processLoading"
        :environment="environment"
      />
    </div>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployTimeline from './deploy-timeline';
import deployLog from './deploy-log';
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
    deploymentId: {     // 部署id, stream流需要用到的参数
      type: String,
      default: () => '',
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
      streamLogs: [],       // 日志流信息
      eventSourceState: {
        CLOSED: 2,
      },
      isLogError: false,        // 日志错误
      appearDeployState: [],
      readyLogs: [],        // 准备阶段日志
      deployStartTimeQueue: [],
      deployEndTimeQueue: [],
      isDeploySuccess: false,
      isDeployFail: false,
      isDeployInterrupted: false,
      isDeployInterrupting: false,
      isWatchDeploying: true,
      timeLineList: [],     // 时间节点数据
      curDeployResult,
      deployTotalTime: 0,       // 部署总耗时
      appMarketPublished: false,     // 是否发布到应用市场
      allProcesses: [],      // 全部进程
      processLoading: false,
    };
  },
  computed: {
    curDeployStage() {
      const flag = this.isWatchDeploying || this.isDeploySuccess
      || this.isDeployFail || this.isDeployInterrupted || this.isDeployInterrupting;
      return flag ? 'deploy' : 'noDeploy';
    },
  },
  watch: {
    deploymentId: {
      handler(v) {
        console.log('vvvv', v);
        this.watchDeployStatus(v);
      },
      immediate: true,
    },
  },
  mounted() {
    // 初始化日志彩色组件
    // eslint-disable-next-line
    const AU = require('ansi_up')
    // eslint-disable-next-line
    this.ansiUp = new AU.default

    window.addEventListener('scroll', () => {
      this.isScrollFixed = (this.isWatchDeploying || this.isWatchOfflineing
      || this.isDeploySuccess || this.isDeployFail
      || this.isDeployInterrupted || this.isDeployInterrupting)
      && (window.pageYOffset >= 260);
    });

    window.addEventListener('resize', () => {
      this.computedBoxFixed();
    });
    // 部署处于准备阶段的判断标识，用于获取准备阶段的日志
    this.isDeployReady = true;
    this.init();
  },
  methods: {
    init() {
      this.getPreDeployDetail();
    //   this.watchDeployStatus();
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

      clearInterval(this.watchTimer);
      if (this.serverLogEvent === null || this.serverLogEvent.readyState === this.eventSourceState.CLOSED) {
        this.serverLogEvent = new EventSource(`${BACKEND_URL}/streams/${deployId}`, {
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
          } else {
            this.streamLogs.push(this.ansiUp.ansi_to_html(item.line));
          }
        };

        this.serverLogEvent.addEventListener('phase', (event) => {
          const item = JSON.parse(event.data);
          if (item.name === 'build') {
            this.isDeployReady = false;
          }

          if (['build', 'preparation'].includes(item.name)) {
            this.appearDeployState.push(item.name);
          }
          let content = '';
          if (item.status === 'successful') {
            this.deployStartTimeQueue.push(item.start_time);
            this.deployEndTimeQueue.push(item.complete_time);
          }

          if (item.name === 'release' && ['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.name === 'release' && item.status === 'successful') {
            // 部署成功
            this.isDeploySuccess = true;
          } else if (item.status === 'failed') {
            // 部署失败
            this.isDeployFail = true;
          } else if (item.status === 'interrupted') {
            // 停止部署成功
            this.isDeployInterrupted = true;
            this.isDeployInterrupting = false;
          }
          this.$nextTick(() => {
            this.$refs.deployTimelineRef
            && this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
          });
        });

        this.serverLogEvent.addEventListener('step', (event) => {
          const item = JSON.parse(event.data);
          let content = '';

          if (item.name === this.$t('检测部署结果') && item.status === 'pending') {
            this.appearDeployState.push('release');
            this.releaseId = item.release_id;
            this.$nextTick(() => {
              this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation('release');
            });
          }

          if (['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.status === 'successful' && item.name === this.$t('检测部署结果')) {
            this.closeServerPush();
          }
          this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
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
        this.serverLogEvent.addEventListener('EOF', () => {
          this.reConnectTimes = 0;
          this.serverLogEvent.close();
          this.closeServerPush();
          this.isDeploySseEof = true;
          // this.allProcesses = JSON.parse(JSON.stringify(this.allProcesses))

          // 判断是否在准备阶段就失败
          const isReadyFailed = this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleGetIsInit();

          isReadyFailed && this.$refs.deployTimelineRef.editNodeStatus('preparation', 'failed', '');

          this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleSetFailed();

          if (this.isDeploySuccess) {
            this.$refs.deployTimelineRef.editNodeStatus('preparation', 'successful', '');
          }
          this.getDeployResult(deployId);
        }, false);

        // 监听到部署slider title变化
        this.serverLogEvent.addEventListener('title', (event) => {
          this.curDeployResult.title = event.data;
        }, true);
      }
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
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
        if (this.curAppInfo.application.type === 'bk_plugin') {
          sourceInfo.push({
            text: this.$t('模块类型'),
            value: this.$t('蓝鲸插件'),
            href: this.GLOBAL.LINK.BK_PLUGIN,
            hrefText: this.$t('查看详情'),
          });
        }

        // 普通应用不展示
        if (this.curAppModule.web_config.templated_source_enabled
        && this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.NORMAL_APP) {
          sourceInfo.push({
            text: this.$t('初始化模板类型'),
            value: this.initTemplateTypeDisplay || '--',
          }, {
            text: this.$t('初始化模板说明'),
            value: this.initTemplateDesc || '--',
            downloadBtn: this.handleDownloadTemplate,
            downloadBtnText: this.initTemplateDesc === '--' ? '' : this.$t('下载模板代码'),
          });
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
          const value = this.isSmartApp ? smartRoute : (this.curAppModule.source_origin === 1 ? this.$t('代码库') : this.$t('蓝鲸可视化开发平台提供源码包'));
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
              name: this.curAppModule.web_config.runtime_type === 'custom_image' ? this.$t('镜像信息') : this.$t('源码信息'),
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
                  value: displays[key].filter(item => !item.is_provisioned).map(item => item.display_name)
                    .join(', '),
                },
                {
                  text: this.$t('已创建实例'),
                  value: displays[key].filter(item => item.is_provisioned).map(item => ({
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
                  value: displays[key].buildpacks.map(item => item.display_name).join(', '),
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
                  value: displays[key] && displays[key].type === 'default_subdomain' ? this.$t('子域名') : this.$t('子路径'),
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
              infos: displays[key].map(doc => ({
                text: doc.name,
                value: doc.link,
              })),
            });
            break;
        }
      }
      return displayBlocks;
    },

  },
};
</script>
