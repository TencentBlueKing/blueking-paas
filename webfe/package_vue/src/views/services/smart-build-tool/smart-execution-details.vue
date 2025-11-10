<template>
  <div class="smart-execution-details">
    <!-- 执行详情 -->
    <StatusBar
      :status="buildStatus.status"
      :time-taken="buildStatus.timeTaken"
      :show-action="!isDetailView"
      @action="handleTerminate"
    />
    <div
      class="flex-row mt-16 flex-1"
      style="min-height: 0"
    >
      <!-- 步骤构建日志 -->
      <BuildLog
        ref="buildLogRef"
        :stream-url="streamUrl"
        :static-logs="historicalBuildLogs"
        @build-status-update="handleBuildStatusUpdate"
        @eof="handleEOF"
      />
    </div>
  </div>
</template>

<script>
import BuildLog from './comps/build-log.vue';
import StatusBar from './comps/status-bar.vue';
import { calculateTimeDiff } from './utils/time-formatter';
import { fileDownload } from '@/common/utils';
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
      // StatusBar 状态数据
      buildStatus: {
        status: 'pending',
        timeTaken: '',
        startTime: null,
      },
      // 获取的日志数据
      historicalBuildLogs: '',
    };
  },
  async mounted() {
    this.initBuildStatus();

    // 历史执行详情 & 非pending 状态，直接获取日志、阶段状态
    if (this.isDetailView && this.rowData?.status !== 'pending') {
      const finalStatus = this.rowData.status;
      this.calculateHistoricalTime();
      this.updateBuildStatus(finalStatus);
      await this.handleLogData();
      return;
    }

    this.$nextTick(() => {
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

    // 更新构建状态
    updateBuildStatus(status) {
      this.buildStatus.status = status;
    },

    // 处理EOF事件
    handleEOF(data) {
      if (data?.final_status) {
        this.updateBuildStatus(data.final_status);
      }
    },

    handleBuildStatusUpdate(data) {
      if (data.start_time) {
        this.buildStatus.startTime = dayjs(data.start_time).toDate();
      }

      // 根据状态更新构建状态和计算时间
      if (data?.status === 'pending') {
        this.updateBuildStatus(data.status);
      } else if (['successful', 'failed', 'interrupted'].includes(data.status)) {
        if (data.end_time && data.start_time) {
          this.buildStatus.timeTaken = calculateTimeDiff(
            dayjs(data.start_time).toDate(),
            dayjs(data.end_time).toDate()
          );
        }
        this.updateBuildStatus(data.status);
      }
    },

    // 计算历史构建时间
    calculateHistoricalTime() {
      if (this.rowData.start_time && this.rowData.end_time) {
        this.buildStatus.timeTaken = calculateTimeDiff(this.rowData.start_time, this.rowData.end_time);
      }
    },

    // 初始化构建状态
    initBuildStatus() {
      if (this.rowData && this.rowData?.status === 'pending') {
        this.updateBuildStatus('pending');
      } else {
        this.buildStatus.startTime = null;
      }
    },
    handleTerminate(type) {
      if (type === 'back') {
        this.$emit('close-sideslider');
      } else if (type === 'download') {
        this.downloadBuildLog();
      }
    },
    // 下载构建日志
    async downloadBuildLog() {
      try {
        const id = this.buildId || this.rowData.uuid;
        const ret = await this.$store.dispatch('tool/getSmartDownload', { id });
        fileDownload(ret?.download_url, `${id}`);
      } catch {
        this.$bkMessage({
          message: this.$t('下载文件失败'),
          theme: 'error',
        });
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
}
</style>
