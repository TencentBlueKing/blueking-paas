<template>
  <section class="smart-logs-container flex-1">
    <section class="log-title">{{ $t('生成 smart 包') }}</section>
    <bk-multiple-log
      ref="multipleLog"
      search-id="multipleLog"
      class="bk-log"
      :log-list="logList"
      @open-log="openLog"
    >
      <template slot-scope="log">
        {{ log.data.name }}
      </template>
    </bk-multiple-log>
  </section>
</template>
<script>
import { bkMultipleLog } from '@blueking/log';
import { createSSE } from '@/common/tools';
import { calculateDeployTime, mapPhaseStatus } from '../utils/time-formatter';

export default {
  name: 'BuildLog',
  components: {
    bkMultipleLog,
  },
  props: {
    streamUrl: {
      type: String,
      default: '',
    },
    // 历史日志数据
    staticLogs: {
      type: String,
      default: '',
    },
  },
  // 自定义事件
  emits: ['phase-update', 'step-update', 'title-update', 'message-update'],
  data() {
    return {
      streamLogEvent: null,
      // 当前活动的阶段
      currentPhase: 'preparation',
      // smart 构建日志数据
      phaseLogData: {
        // 准备阶段日志
        preparation: [],
        // 构建阶段日志
        build: [],
      },
      // 日志节点列表
      logList: [
        { name: '准备阶段', id: 'preparation' },
        { name: '构建阶段', id: 'build' },
      ],
      // 跟踪已展开的阶段日志节点
      expandedPhases: new Set(),
    };
  },
  watch: {
    // 监听streamUrl变化，当新的URL传入时重新建立连接
    streamUrl: {
      handler(newUrl, oldUrl) {
        if (newUrl && newUrl !== oldUrl) {
          this.reconnectSSE();
        } else if (!newUrl && oldUrl) {
          this.closeStreamLogEvent();
          this.clearAllLogs();
        }
      },
      immediate: false,
    },
    // 监听静态日志数据变化
    staticLogs: {
      handler(newLogs) {
        if (newLogs && typeof newLogs === 'string') {
          this.loadBuildLogContent(newLogs);
        }
      },
      immediate: true,
    },
  },
  beforeDestroy() {
    this.closeStreamLogEvent();
  },
  methods: {
    /**
     * 加载构建日志内容
     * @param {string} logContent - 字符串格式的日志内容
     */
    loadBuildLogContent(logContent) {
      if (!logContent || typeof logContent !== 'string') return;

      // 清空现有日志数据
      this.clearAllLogs();

      // 按行分割日志内容
      const logLines = logContent.split('\n').map(line => line.replace(/\r/g, '').trim()).filter(line => line !== '');
      logLines.forEach((line) => {
        const logItem = {
          message: line,
          stream: 'STDOUT',
          timestamp: new Date().toISOString(),
        };
        // 将所有日志归到构建阶段
        this.addLogToPhase('build', logItem);
      });

      this.$nextTick(() => {
        this.autoExpandPhaseLog('build');
      });
    },

    // 获取 smart 构建日志（sse）
    async getLogs() {
      if (!this.streamUrl) return;
      if (this.streamLogEvent) {
        this.closeStreamLogEvent();
      }

      const url = `${BACKEND_URL}${this.streamUrl}`;

      // 初始化事件流
      this.streamLogEvent = createSSE(url, {
        withCredentials: true,
        onError: () => {
          // 服务异常重新连接
          this.addLogToCurrentPhase({ message: '正在尝试重新连接...' });
        },
        onEOF: () => {
          this.closeStreamLogEvent();
          // 流式日志结束，发送EOF事件通知父组件
          this.$emit('eof');
        },
      });

      this.phaseEventHandler = (event) => {
        const data = JSON.parse(event.data);

        // 更新当前活动阶段
        if (data.status === 'pending') {
          this.currentPhase = data.name;
          if (!this.phaseLogData[data.name]) {
            this.phaseLogData[data.name] = [];
          }

          // 当阶段开始时，自动展开对应的日志节点
          this.$nextTick(() => {
            this.autoExpandPhaseLog(data.name);
          });
        }

        const content = data.complete_time ? calculateDeployTime(data.start_time, data.complete_time) : '';

        // 向父组件发送阶段更新事件
        this.$emit('phase-update', {
          name: data.name, // 阶段名称 (preparation, build 等)
          status: mapPhaseStatus(data.status),
          content, // 耗时信息
          data,
        });
      };

      this.stepEventHandler = (event) => {
        const data = JSON.parse(event.data);

        // 更新当前活动阶段
        if (data.phase && data.status === 'pending') {
          this.currentPhase = data.phase;
        }

        const content = data.complete_time ? calculateDeployTime(data.start_time, data.complete_time) : '';

        // 向父组件发送步骤更新事件
        this.$emit('step-update', {
          name: data.name, // 步骤名称 (如: "校验应用描述文件")
          phase: data.phase, // 所属阶段 (preparation, build 等)
          status: mapPhaseStatus(data.status),
          content, // 耗时信息
          data,
        });
      };

      this.messageEventHandler = (event) => {
        const data = JSON.parse(event.data);
        if (!data.line) return;
        
        const cleanedLine = data.line.replace(/[\r\n]+/g, '').trim();
        
        // 如果清理后的内容为空，则跳过
        if (cleanedLine === '') return;
        
        const item = {
          message: cleanedLine,
          stream: data.stream, // STDOUT 或 STDERR
        };

        // 添加到当前活动阶段的日志中
        this.addLogToCurrentPhase(item);

        // 确保当前阶段的日志节点已展开
        this.$nextTick(() => {
          this.autoExpandPhaseLog(this.currentPhase);
        });
      };

      this.eofEventHandler = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.final_status) {
            this.$emit('phase-update', {
              name: 'build',
              status: mapPhaseStatus(data.final_status),
              content: '', // 耗时信息
              data: { name: 'build', status: data.final_status },
            });
          }
          this.$emit('eof', data);
        } catch (e) {
          this.$emit('eof', null);
        }
      };

      // 监听阶段切换事件
      this.streamLogEvent.addEventListener('phase', this.phaseEventHandler);

      // 监听到步骤变化
      this.streamLogEvent.addEventListener('step', this.stepEventHandler);

      // 监听消息事件
      this.streamLogEvent.addEventListener('message', this.messageEventHandler);

      // 监听EOF事件，用于更新最终状态
      this.streamLogEvent.addEventListener('EOF', this.eofEventHandler);
    },

    // 关闭事件源
    closeStreamLogEvent() {
      if (this.streamLogEvent) {
        if (this.phaseEventHandler) {
          this.streamLogEvent.removeEventListener('phase', this.phaseEventHandler);
        }
        if (this.stepEventHandler) {
          this.streamLogEvent.removeEventListener('step', this.stepEventHandler);
        }
        if (this.messageEventHandler) {
          this.streamLogEvent.removeEventListener('message', this.messageEventHandler);
        }
        if (this.eofEventHandler) {
          this.streamLogEvent.removeEventListener('EOF', this.eofEventHandler);
        }
        
        this.streamLogEvent.close();
        this.streamLogEvent = null; // 清空引用，避免重复使用
      }
    },

    expendAllLog() {
      this.logList.forEach((log) => {
        this.$refs.multipleLog?.expendLog(log);
      });
    },

    // 展开指定日志
    async openLog(plugin) {
      const phaseId = plugin.id; // 'preparation' 或 'build'
      // 如果已经展开过，不需要重复处理
      if (this.expandedPhases.has(phaseId)) return;
      
      let phaseLogs = this.phaseLogData[phaseId] || [];

      if (phaseId === 'preparation' && phaseLogs.length === 0) {
        phaseLogs = [
          {
            message: '暂无日志',
            stream: 'INFO',
            timestamp: new Date().toISOString(),
          },
        ];
      }

      // 标记该阶段为已展开
      this.expandedPhases.add(phaseId);

      // 先清空该阶段的日志数据，避免重复添加
      if (this.$refs.multipleLog) {
        try {
          await this.$refs.multipleLog.worker.postMessage({
            type: 'resetData',
            id: phaseId,
          });
          this.$refs.multipleLog.addLogData(phaseLogs, phaseId);
        } catch (error) {
          console.warn(`Failed to load logs for phase ${phaseId}:`, error);
        }
      }
    },

    /**
     * 将日志添加到指定阶段
     * @param {string} phase - 阶段名称
     * @param {Object} logItem - 日志项
     */
    addLogToPhase(phase, logItem) {
      if (!phase || !logItem) return;

      if (!this.phaseLogData[phase]) {
        this.phaseLogData[phase] = [];
      }

      // 添加到指定阶段
      this.phaseLogData[phase].push(logItem);
    },

    /**
     * 将日志添加到当前活动阶段
     * @param {Object} logItem - 日志项
     */
    addLogToCurrentPhase(logItem) {
      this.addLogToPhase(this.currentPhase, logItem);

      // 如果当前阶段的日志节点已展开，实时更新日志内容，避免重复
      if (this.expandedPhases.has(this.currentPhase)) {
        this.updateExpandedPhaseLog(this.currentPhase, logItem);
      }
    },

    /**
     * 清空所有日志数据
     */
    clearAllLogs() {
      // 清空阶段日志数据
      this.phaseLogData = {
        preparation: [],
        build: [],
      };
      this.currentPhase = 'preparation';
      // 重置展开状态
      this.expandedPhases.clear();

      // 清空多日志组件的数据
      if (this.$refs.multipleLog) {
        this.logList.forEach((log) => {
          this.$refs.multipleLog.worker.postMessage({
            type: 'resetData',
            id: log.id,
          });
        });
        this.$refs.multipleLog.foldAllPlugin();
      }
    },

    // 重新建立SSE连接
    reconnectSSE() {
      this.closeStreamLogEvent();
      this.clearAllLogs();
      setTimeout(() => {
        this.getLogs();
      }, 150);
    },

    /**
     * 自动展开指定阶段的日志节点
     * @param {string} phaseName - 阶段名称 (preparation, build 等)
     */
    autoExpandPhaseLog(phaseName) {
      if (!phaseName || !this.$refs.multipleLog) return;

      if (this.expandedPhases.has(phaseName)) return;

      // 查找对应的日志节点
      const targetLog = this.logList.find((log) => log.id === phaseName);
      if (!targetLog) return;
      this.$refs.multipleLog?.expendLog(targetLog);
    },

    /**
     * 更新已展开阶段的日志内容
     * @param {string} phaseName - 阶段名称
     * @param {Object} newLogItem - 新的日志项
     */
    updateExpandedPhaseLog(phaseName, newLogItem) {
      if (!phaseName || !newLogItem || !this.$refs.multipleLog) return;

      if (!this.expandedPhases.has(phaseName)) return;

      try {
        // 检查该阶段的日志节点是否已展开
        const targetLog = this.logList.find((log) => log.id === phaseName);
        if (!targetLog) return;
        // 将新的日志项添加到已展开的日志节点中
        this.$refs.multipleLog.addLogData([newLogItem], phaseName);
      } catch (error) {
        console.warn(`Failed to update expanded log for phase ${phaseName}:`, error);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.smart-logs-container {
  display: flex;
  flex-direction: column;
  .log-title {
    height: 40px;
    line-height: 40px;
    padding: 0 12px;
    font-size: 14px;
    color: #c4c6cc;
    background: #2e2e2e;
    border-radius: 2px 2px 0 0;
  }
  .bk-log {
    flex: 1;
    min-height: 0;
    margin-top: 0 !important;
    /deep/ .job-plugin-list-log {
      /* 自定义滚动条样式 - Webkit 浏览器 */
      &::-webkit-scrollbar {
        width: 8px;
      }

      &::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 4px;

        &:hover {
          background: rgba(255, 255, 255, 0.5);
        }
      }

      /* Firefox 滚动条样式 */
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.3) rgba(255, 255, 255, 0.1);
    }
  }
}
</style>
