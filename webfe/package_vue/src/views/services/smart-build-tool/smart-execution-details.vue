<template>
  <div class="smart-execution-details">
    <!-- 执行详情 -->
    <StatusBar
      :status="buildStatus.status"
      :time-taken="buildStatus.timeTaken"
      :action-text="buildStatus.actionText"
      :show-action="!isDetailView"
      @action="handleTerminate"
    />
    <div
      class="flex-row mt-16 flex-1"
      style="min-height: 0"
    >
      <!-- <div class="timeline-wrapper">
        <DeployTimeline
          ref="deployTimelineRef"
          :list="timeLineList"
        />
      </div> -->
      <!-- 步骤构建日志 -->
      <BuildLog
        ref="buildLogRef"
        :stream-url="streamUrl"
        :static-logs="historicalBuildLogs"
        @phase-update="handlePhaseUpdate"
        @step-update="handleStepUpdate"
        @eof="handleEOF"
      />
    </div>
  </div>
</template>

<script>
import BuildLog from './comps/build-log.vue';
import StatusBar from './comps/status-bar.vue';
// import DeployTimeline from '@/views/dev-center/app/engine/cloud-deploy-manage/comps/deploy-timeline';
import { calculateTimeDiff, calculateDeployTime, mapPhaseStatus } from './utils/time-formatter';
import dayjs from 'dayjs';

export default {
  components: {
    StatusBar,
    BuildLog,
  },
  props: {
    streamUrl: {
      type: String,
      default: '',
    },
    buildId: {
      type: String,
      default: '',
    },
    isDetailView: {
      type: Boolean,
      default: false,
    },
    // 行数据，用于获取 uuid 和 status
    rowData: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      timeLineList: [],
      // StatusBar 状态数据
      buildStatus: {
        status: 'running', // 'running' | 'success' | 'failed'
        timeTaken: '',
        actionText: '终止',
        startTime: null,
      },
      // 内部获取的日志数据
      historicalBuildLogs: '',
    };
  },
  async created() {
    // await this.getSmartBuildPhases();
    this.initBuildStatus();

    // 历史执行详情 & 非pending 状态，直接获取日志、阶段状态
    if (this.isDetailView && this.rowData.status !== 'pending') {
      // 第一版，先去掉步骤信息
      // await this.getSmartBuildPhaseStatus();
      const finalStatus = this.mapRowStatusToBuildStatus(this.rowData.status);
      this.updateBuildStatus(finalStatus);
      await this.handleLogData();
    }

    this.$nextTick(() => {
      // 初始化后获取日志
      this.$refs.buildLogRef?.getLogs();
    });
  },
  methods: {
    // 处理日志数据获取
    async handleLogData() {
      try {
        const res = await this.$store.dispatch('tool/getSmartBuildLogs', { id: this.rowData.uuid });
        this.historicalBuildLogs = res?.logs || '';
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },

    // 获取已构建步骤/状态
    async getSmartBuildPhaseStatus() {
      try {
        const res = await this.$store.dispatch('tool/getSmartBuildPhaseStatus', {
          id: this.rowData.uuid,
        });
        this.updateTimelinePhaseStatus(res || []);
        this.updateOverallBuildStatus(res || []);
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },

    /**
     * 更新时间轴的阶段状态
     * @param {Array} phaseStatusData - 阶段状态数据数组
     */
    updateTimelinePhaseStatus(phaseStatusData) {
      phaseStatusData.forEach((phase) => {
        this.updateNodeStatus(phase);

        // 更新该阶段下的所有步骤状态
        if (phase.steps?.length > 0) {
          phase.steps.forEach((step) => {
            this.updateNodeStatus(step);
          });
        }
      });
    },

    // 更新单个节点状态
    updateNodeStatus(node) {
      const status = mapPhaseStatus(node.status);
      const content = calculateDeployTime(node.start_time, node.complete_time);
      this.$refs.deployTimelineRef?.editNodeStatus(node.name, status, content);
    },

    /**
     * 根据阶段状态更新整体构建状态
     * @param {Array} phaseStatusData - 阶段状态数据数组
     */
    updateOverallBuildStatus(phaseStatusData) {
      if (phaseStatusData.length === 0) return;

      // 设置构建开始时间
      this.setStartTime(phaseStatusData);

      // 获取最新结束时间
      const latestEndTime = this.getLatestEndTime(phaseStatusData);

      // 根据阶段状态确定整体状态
      const buildResult = this.determineBuildResult(phaseStatusData);

      // 更新构建状态
      this.setBuildStatus(buildResult, latestEndTime);
    },

    /**
     * 设置构建开始时间
     * @param {Array} phaseStatusData - 阶段状态数据数组
     */
    setStartTime(phaseStatusData) {
      const firstPhase = phaseStatusData[0];
      if (firstPhase?.start_time) {
        this.buildStatus.startTime = dayjs(firstPhase.start_time).toDate();
      }
    },

    /**
     * 获取最新的结束时间
     * @param {Array} phaseStatusData - 阶段状态数据数组
     * @returns {string|null} 最新的结束时间
     */
    getLatestEndTime(phaseStatusData) {
      return phaseStatusData.reduce((latest, phase) => {
        const isCompleted = ['successful', 'failed'].includes(phase.status);
        if (!phase.complete_time || !isCompleted) return latest;

        return !latest || dayjs(phase.complete_time).isAfter(dayjs(latest)) ? phase.complete_time : latest;
      }, null);
    },

    /**
     * 根据阶段状态确定构建结果
     * @param {Array} phaseStatusData - 阶段状态数据数组
     * @returns {string} 构建结果状态
     */
    determineBuildResult(phaseStatusData) {
      const hasFailedPhase = phaseStatusData.some((phase) => phase.status === 'failed');
      if (hasFailedPhase) return 'failed';

      const allSuccessful = phaseStatusData.every((phase) => phase.status === 'successful');
      return allSuccessful ? 'success' : 'running';
    },

    /**
     * 设置构建状态
     * @param {string} status - 构建状态
     * @param {string|null} endTime - 结束时间
     */
    setBuildStatus(status, endTime) {
      if (status === 'running') {
        this.updateBuildStatus('running');
        this.calculateTotalTime();
      } else {
        // 已完成的构建
        if (endTime) {
          this.calculateTotalTime(endTime);
          this.updateBuildStatus(status, true); // 跳过重复计算时间
        } else {
          this.updateBuildStatus(status); // 没有结束时间，使用当前时间
        }
      }
    },

    handleTerminate() {
      // 根据当前状态决定是终止还是重新构建
      if (this.buildStatus.status === 'running') {
        this.terminateBuild();
      } else if (this.buildStatus.status === 'failed') {
        this.rebuildPackage();
      }
    },

    // 终止当前构建
    terminateBuild() {
      this.$bkInfo({
        title: '确认终止',
        subTitle: '确定要终止当前的构建任务吗？',
        confirmFn: () => {
          this.updateBuildStatus('failed');
        },
      });
    },

    // 重新构建
    async rebuildPackage() {
      this.$emit('rebuild');
      this.resetComponentState();
      this.clearCurrentLogs();
      // 重新初始化构建状态
      this.initBuildStatus();
      // await this.getSmartBuildPhases();
    },

    // 清空当前日志数据
    clearCurrentLogs() {
      this.$refs.buildLogRef?.clearAllLogs();
      // 关闭当前SSE连接
      this.$refs.buildLogRef?.closeStreamLogEvent();
    },

    // 重置组件状态
    resetComponentState() {
      this.timeLineList = this.timeLineList.map((item) => ({
        ...item,
        status: 'default',
        content: '',
        loading: false,
      }));

      // 重置构建状态
      this.buildStatus = {
        status: 'running',
        timeTaken: '',
        actionText: '终止',
        startTime: null,
      };

      // 重置时间线组件状态
      if (this.$refs.deployTimelineRef) {
        this.timeLineList.forEach((item) => {
          this.$refs.deployTimelineRef.editNodeStatus(item.name, 'default', '');
        });
      }
    },

    /**
     * 更新构建状态
     * @param {string} status - 状态: 'running' | 'success' | 'failed'
     * @param {boolean} skipTimeCalculation - 是否跳过时间计算（当外部已计算时）
     */
    updateBuildStatus(status, skipTimeCalculation = false) {
      this.buildStatus.status = status;

      switch (status) {
        case 'running':
          this.buildStatus.actionText = this.$t('终止');
          if (!this.buildStatus.startTime) {
            this.buildStatus.startTime = dayjs().toDate();
          }
          break;
        case 'success':
          this.buildStatus.actionText = '';
          if (!skipTimeCalculation) {
            this.calculateTotalTime();
          }
          break;
        case 'failed':
          this.buildStatus.actionText = this.$t('重试');
          if (!skipTimeCalculation) {
            this.calculateTotalTime();
          }
          break;
      }
    },

    // 将 rowData.status 映射为构建状态
    mapRowStatusToBuildStatus(rowStatus) {
      switch (rowStatus) {
        case 'successful':
          return 'success';
        case 'failed':
          return 'failed';
        default:
          return 'running';
      }
    },

    // 计算构建总耗时（使用共享的时间工具）
    calculateTotalTime(endTime = null) {
      if (!this.buildStatus.startTime) return;

      // 对于历史构建，使用传入的结束时间；对于进行中的构建，使用当前时间
      this.buildStatus.timeTaken = calculateTimeDiff(this.buildStatus.startTime, endTime);
    },

    // 获取构建步骤
    async getSmartBuildPhases() {
      try {
        const buildPhasesRes = await this.$store.dispatch('tool/getSmartBuildPhases');
        // 格式化数据
        const timeLineSteps = this.formatBuildPhasesToTimeLine(buildPhasesRes);
        this.timeLineList = timeLineSteps;
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },

    // 辅助方法：将接口返回的构建阶段数据格式化为时间线列表结构
    formatBuildPhasesToTimeLine(buildPhases) {
      if (!Array.isArray(buildPhases) || buildPhases.length === 0) return [];

      return buildPhases.flatMap((stageItem) => {
        // 1. 构建父节点
        const parentStep = {
          name: stageItem.type, // 部署阶段名称（原始标识）
          tag: stageItem.display_name, // 部署阶段展示名称（用户可见）
          content: '', // 完成时间（初始为空）
          status: 'default', // 初始状态
          stage: stageItem.type, // 主节点专属：部署阶段类型
          loading: false, // 加载中标识（sse未返回时用）
        };

        // 2. 构建子节点
        const childSteps = Array.isArray(stageItem.steps)
          ? stageItem.steps.map((stepItem) => ({
              name: stepItem.name, // 子步骤名称
              tag: stepItem.display_name, // 子步骤展示名称
              content: '', // 完成时间
              status: 'default', // 初始状态
              parent: stageItem.display_name, // 父节点展示名称
              parentStage: stageItem.type, // 父节点类型
            }))
          : [];

        return [parentStep, ...childSteps];
      });
    },

    /**
     * 处理来自BuildLog组件的阶段更新事件
     * @param {Object} phaseData - 阶段数据
     */
    handlePhaseUpdate(phaseData) {
      // 直接使用 DeployTimeline 的 editNodeStatus 方法更新阶段状态
      this.$refs.deployTimelineRef?.editNodeStatus(phaseData.name, phaseData.status, phaseData.content);

      // 如果阶段开始，也可以同时更新该阶段下所有步骤的状态
      if (phaseData.status === 'pending') {
        this.updatePhaseStepsStatus(phaseData.name, 'default');
      }

      // 更新StatusBar状态
      this.updateStatusBarFromPhase(phaseData);
    },

    /**
     * 处理来自BuildLog组件的步骤更新事件
     * @param {Object} stepData - 步骤数据
     */
    handleStepUpdate(stepData) {
      // 直接使用 DeployTimeline 的 editNodeStatus 方法更新步骤状态
      this.$refs.deployTimelineRef?.editNodeStatus(stepData.name, stepData.status, stepData.content);

      // 如果步骤开始执行 (pending状态)，可能需要确保其父阶段也是激活状态
      if (stepData.status === 'pending' && stepData.phase) {
        // 确保父阶段处于正确状态
        this.ensurePhaseActive(stepData.phase);
      }

      // 更新StatusBar状态
      this.updateStatusBarFromStep(stepData);
    },

    /**
     * 更新某个阶段下所有步骤的状态
     * @param {string} phaseName - 阶段名称
     * @param {string} status - 要设置的状态
     */
    updatePhaseStepsStatus(phaseName, status) {
      // 查找该阶段下的所有步骤并更新状态
      this.timeLineList.forEach((item) => {
        if (item.parentStage === phaseName && item.parent) {
          this.$refs.deployTimelineRef?.editNodeStatus(item.name, status, '');
        }
      });
    },

    /**
     * 确保指定阶段处于激活状态
     * @param {string} phaseName - 阶段名称
     */
    ensurePhaseActive(phaseName) {
      // 查找对应的阶段，如果不是pending状态，则设为pending
      const phaseItem = this.timeLineList.find((item) => item.stage === phaseName);
      if (phaseItem && phaseItem.status === 'default') {
        this.$refs.deployTimelineRef?.editNodeStatus(phaseName, 'pending', '');
      }
    },

    // 处理EOF事件
    handleEOF(data) {
      if (data && data.final_status) {
        if (data.final_status === 'failed') {
          this.updateBuildStatus('failed');
        } else if (data.final_status === 'successful') {
          this.updateBuildStatus('success');
        }
      }
    },

    // 根据阶段更新StatusBar状态
    updateStatusBarFromPhase(phaseData) {
      const { name, status } = phaseData;
      if (name === 'preparation' && status === 'pending') {
        // 准备阶段开始
        this.updateBuildStatus('running');
      } else if (name === 'build' && status === 'pending') {
        // 构建阶段开始
        this.updateBuildStatus('running');
      } else if (status === 'failed') {
        // 任何阶段失败
        this.updateBuildStatus('failed');
      } else if (name === 'build' && status === 'successful') {
        // 所有构建完成
        this.updateBuildStatus('success');
      }
    },

    /**
     * 根据步骤更新StatusBar状态
     * @param {Object} stepData - 步骤数据
     */
    updateStatusBarFromStep(stepData) {
      if (stepData.status === 'failed') {
        // 任何步骤失败都标记整体失败
        this.updateBuildStatus('failed');
      }
    },

    // 初始化构建状态
    initBuildStatus() {
      // 对于 pending 状态，设置为运行中
      if (this.rowData && this.rowData.status === 'pending') {
        this.buildStatus.startTime = dayjs().toDate();
        this.updateBuildStatus('running');
      } else {
        // 对于其他状态，等待从阶段状态中获取实际状态
        this.buildStatus.startTime = null;
        // 暂时不设置状态，等待 getSmartBuildPhaseStatus 的结果
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.smart-execution-details {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  .timeline-wrapper {
    width: 230px;
    margin-right: 16px;
  }
}
</style>
