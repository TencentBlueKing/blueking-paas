<template>
  <section class="smart-logs-container flex-1">
    <section class="log-title">{{ $t('构建 S-mart 包') }}</section>
    <bk-log
      ref="bkLog"
      class="bk-log"
      @mousewheel.native="handleUserScroll"
    />
  </section>
</template>
<script>
import { bkLog } from '@blueking/log';
import { createSSE } from '@/common/tools';

export default {
  name: 'BuildLog',
  components: {
    bkLog,
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
  emits: ['eof', 'build-status-update'],
  data() {
    return {
      streamLogEvent: null,
      buildLogs: [],
      totalLogCount: 0, // 总日志行数
      logBuffer: [], // 日志缓冲区
      batchSize: 10, // 批量大小
      autoScroll: true, // 是否自动滚动
      userScrollTimer: null, // 用户滚动定时器
      flushTimer: null, // 缓冲区刷新定时器
      scrollCheckTimer: null, // 滚动位置检查定时器
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
    clearTimeout(this.flushTimer);
    clearTimeout(this.userScrollTimer);
    clearTimeout(this.scrollCheckTimer);
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
      const logLines = logContent
        .split('\n')
        .map((line) => line.replace(/\r/g, '').trim())
        .filter((line) => line !== '');

      const logs = logLines.map((line) => {
        return {
          message: line,
          stream: 'STDOUT',
        };
      });
      this.$refs.bkLog.addLogData(logs);

      // 更新总数量
      this.totalLogCount = logs.length;
      this.$nextTick(() => {
        this.scrollToBottom();
      });
    },

    handleUserScroll(event) {
      const deltaY = event.deltaY;

      if (deltaY < 0) {
        // 用户向上滚动，立即停止自动滚动
        this.autoScroll = false;
        clearTimeout(this.userScrollTimer);
        clearTimeout(this.scrollCheckTimer);
      } else if (deltaY > 0) {
        // 用户向下滚动，检查是否到达底部
        clearTimeout(this.scrollCheckTimer);
        this.scrollCheckTimer = setTimeout(() => {
          this.checkIfAtBottom();
        }, 200);
      }
    },

    scrollToBottom() {
      this.$refs.bkLog?.scrollPageByIndex(9999);
    },

    // 获取滚动容器元素
    getScrollContainer() {
      const bkLogEl = this.$refs.bkLog?.$el;
      const scrollContainer =
        bkLogEl.querySelector('.log-scroll-container') ||
        bkLogEl.querySelector('[style*="overflow"]') ||
        bkLogEl.querySelector('.bk-log-virtual-scroll') ||
        bkLogEl;
      return scrollContainer;
    },

    /**
     * 检查是否在底部
     */
    checkIfAtBottom() {
      const container = this.getScrollContainer();
      if (!container) return;

      // 获取滚动信息
      const { scrollTop, scrollHeight, clientHeight } = container;
      // 计算距离底部的距离
      const distanceToBottom = scrollHeight - scrollTop - clientHeight;
      // 恢复自动滚动
      if (distanceToBottom <= 5) {
        this.autoScroll = true;
      }
    },

    // 刷新日志缓冲区
    flushLogBuffer() {
      if (this.logBuffer.length === 0) return;

      // 批量添加日志
      this.$refs.bkLog?.addLogData([...this.logBuffer]);

      // 更新总数量
      this.totalLogCount += this.logBuffer.length;

      this.logBuffer = [];

      this.$nextTick(() => {
        if (this.autoScroll) {
          this.scrollToBottom();
        }
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
        onMessage: (event) => {
          try {
            const data = JSON.parse(event.data);
            const cleanedLine = data.line?.replace(/[\r\n]+/g, '').trim();
            if (cleanedLine === '') return;

            this.buildLogs.push({ message: cleanedLine, stream: 'STDOUT' });

            // 添加到缓冲区
            this.logBuffer.push({ message: cleanedLine, stream: 'STDOUT' });

            // 达到批量大小或者延迟后批量添加
            if (this.logBuffer.length >= this.batchSize) {
              this.flushLogBuffer();
            } else {
              // 防抖：100ms 内没有新日志则立即添加
              clearTimeout(this.flushTimer);
              this.flushTimer = setTimeout(() => {
                this.flushLogBuffer();
              }, 100);
            }
          } catch (e) {
            console.error('消息解析错误:', e);
          }
        },
        onError: () => {
          const errorLog = { message: '正在尝试重新连接...' };
          this.$refs.bkLog?.addLogData([errorLog]);
          this.totalLogCount += 1;
        },
        onEOF: () => {
          // 确保剩余日志也被添加
          this.flushLogBuffer();
          this.$emit('eof', null);
          this.closeStreamLogEvent();
        },
      });

      this.builderProcessEventHandler = (event) => {
        const data = JSON.parse(event.data);
        this.$emit('build-status-update', data);
      };

      // 监听Builder Process事件，用于更新构建状态
      this.streamLogEvent.addEventListener('Builder Process', this.builderProcessEventHandler);
    },

    // 关闭事件源
    closeStreamLogEvent() {
      if (this.streamLogEvent) {
        if (this.builderProcessEventHandler) {
          this.streamLogEvent.removeEventListener('Builder Process', this.builderProcessEventHandler);
        }
        this.streamLogEvent.close();
        this.streamLogEvent = null; // 清空引用，避免重复使用
      }
    },

    /**
     * 清空所有日志数据
     */
    clearAllLogs() {
      this.$refs.bkLog?.changeExecute();
      this.totalLogCount = 0;
      this.logBuffer = [];
      this.autoScroll = true;
      clearTimeout(this.flushTimer);
      clearTimeout(this.userScrollTimer);
      clearTimeout(this.scrollCheckTimer);
    },

    // 重新建立SSE连接
    reconnectSSE() {
      this.closeStreamLogEvent();
      this.clearAllLogs();
      setTimeout(() => {
        this.getLogs();
      }, 150);
    },
  },
};
</script>

<style lang="scss" scoped>
.smart-logs-container {
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  position: relative;

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
  }
}
</style>
