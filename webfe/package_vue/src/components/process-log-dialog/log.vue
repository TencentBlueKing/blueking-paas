<template>
  <transition name="dialog-fade">
    <!--进程日志 -->
    <div
      v-if="internalVisible"
      class="paas-log dialog-backdrop"
      @click.self="handleClose"
    >
      <div
        class="log-wrapper"
        @click.stop
      >
        <div class="log-header">
          <slot name="header">
            <!-- 默认日志样式 -->
            <div class="top">
              <div class="title">{{ title }}</div>
              <div class="config">
                <div class="group">
                  <div
                    v-for="item in logTypeOption"
                    :class="['item', { active: item.id === logType }]"
                    :key="item.key"
                    @click="changeLogType(item.id)"
                  >
                    {{ item.text }}
                  </div>
                </div>
              </div>
              <div class="tools">
                <bk-select
                  v-model="logTime"
                  :clearable="false"
                  class="ml20"
                  ext-cls="log-time-select-cls"
                  :disabled="logType !== 'realtime'"
                  @change="refresh"
                >
                  <bk-option
                    v-for="(option, i) in timeSelection"
                    :id="option.id"
                    :key="i"
                    :name="option.name"
                  />
                  <bk-option
                    v-if="logType === 'restart'"
                    :id="'restart'"
                    :key="-1"
                    :name="$t('最近 400 条')"
                  />
                </bk-select>
                <!-- 刷新 -->
                <i
                  class="paasng-icon paasng-refresh ml20"
                  @click="refresh"
                ></i>
                <!-- 下载 -->
                <i
                  v-bk-tooltips="{ content: isRealTimeLog ? $t('暂不支持下载实时日志') : $t('下载完整日志') }"
                  class="paasng-icon paasng-download ml20"
                  :class="{ disabled: isRealTimeLog }"
                  @click="downloadPreviousLogs"
                ></i>
              </div>
            </div>
          </slot>
        </div>
        <div
          class="log-content"
          v-bkloading="{ isLoading: loading, opacity: 1, color: '#333030', zIndex: 10 }"
        >
          <slot name="content">
            <template v-if="logs.length">
              <ul>
                <li
                  v-for="(log, idx) of logs"
                  :key="idx"
                  class="log-item"
                >
                  <!-- 实时进程 -->
                  <template v-if="isRealTimeLog">
                    <span
                      class="mr10"
                      style="min-width: 140px"
                    >
                      {{ log.timestamp }}
                    </span>
                    <span class="pod-name">{{ log.podShortName }}</span>
                    <pre
                      class="message"
                      v-html="log.message || '--'"
                    />
                  </template>
                  <template v-else>
                    <pre
                      class="message"
                      v-html="log"
                    />
                  </template>
                </li>
              </ul>
            </template>
            <div
              v-else
              class="empty"
            >
              {{ $t('暂时没有日志记录') }}
            </div>
          </slot>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { downloadTxt } from '@/common/tools';

export default {
  name: 'PaasLog',
  props: {
    value: {
      type: Boolean,
      required: true,
    },
    params: {
      type: Object,
      default: () => {},
    },
    title: {
      type: String,
      default: '',
    },
    loading: {
      type: Boolean,
      default: true,
    },
    timeSelection: {
      type: Array,
      default: () => [],
    },
    logs: {
      type: Array | String,
      default: () => [],
    },
  },
  data() {
    return {
      internalVisible: this.value,
      logTime: '1h',
      logType: 'realtime',
      logTypeOption: [
        { id: 'realtime', text: this.$t('实时日志') },
        { id: 'restart', text: this.$t('最近一次重启日志') },
      ],
    };
  },
  computed: {
    isRealTimeLog() {
      return this.logType === 'realtime';
    },
  },
  watch: {
    value(newVal) {
      this.internalVisible = newVal;
      this.init();
    },
    internalVisible(newVal) {
      this.$emit('input', newVal);
      if (newVal) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    },
    'logs.length'() {
      this.scrollBottom();
    },
  },
  methods: {
    handleClose() {
      this.internalVisible = false;
    },
    init() {
      this.logTime = '1h';
      this.logType = 'realtime';
    },
    // 滚动到当前日志底部
    scrollBottom() {
      this.$nextTick(() => {
        const box = document.querySelector('.log-wrapper .log-content');
        box.scrollTo({
          top: box?.scrollHeight || 0,
          behavior: 'smooth',
        });
      });
    },
    changeLogType(type) {
      if (this.loading) return;
      this.logType = type;
      this.logTime = this.logType === 'restart' ? 'restart' : '1h';
    },
    // 刷新
    refresh() {
      this.$emit('refresh', {
        type: this.logType,
        time: this.logTime,
      });
    },
    // 下载重启日志
    async downloadPreviousLogs() {
      if (this.isRealTimeLog) return;
      try {
        const logTxt = await this.$store.dispatch('log/downloadPreviousLogs', this.params);
        if (!logTxt || !logTxt?.length) {
          this.$paasMessage({
            theme: 'warning',
            message: this.$t('暂时没有日志记录'),
          });
          return;
        }
        downloadTxt(logTxt, this.params.instanceName);
        // 404 处理
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  flex-direction: row-reverse;

  .log-wrapper {
    background-color: #1e1e1e;
    color: #fff;
    height: calc(100% - 32px);
    width: 80%;
    margin: 16px;
    border-radius: 6px;
    min-width: 300px;
    transition: all 0.2s ease-in-out; /* 对话框本身的过渡 */

    .log-header {
      background-color: #252935;
      border-bottom: 1px solid #2b2b2b;
      border-radius: 6px 6px 0 0;
      color: #d4d4d4;
      min-height: 48px;
      padding: 8px 20px;

      .top {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;

        .config .group {
          display: flex;
          align-items: center;
          .item {
            background: #2e3342;
            color: #999;
            height: 26px;
            line-height: 26px;
            padding: 0 12px;
            cursor: pointer;
            border-radius: 3px 0 0 3px;

            &:last-child {
              border-radius: 0 3px 3px 0;
            }

            &.active {
              background: #1a6df3;
              color: #fff;
            }
          }
        }

        .tools {
          display: flex;
          align-items: center;
          .log-time-select-cls {
            background: hsla(0, 0%, 100%, 0.125);
            border: none;
            color: #f6f8fa;
            width: 200px;
            flex-shrink: 0;
          }
          i {
            font-size: 16px;
            cursor: pointer;
            &.disabled {
              cursor: not-allowed;
            }
          }
        }
      }
    }

    .log-content {
      overflow-y: auto;
      height: calc(100% - 48px);
      padding: 10px 20px;

      .log-item {
        display: flex;
        margin-bottom: 8px;
        font-family: Consolas, 'source code pro', 'Bitstream Vera Sans Mono', Consolas, Courier, monospace, '微软雅黑',
          'Arial';

        .pod-name {
          min-width: 95px;
          text-align: right;
          margin-right: 15px;
          color: #979ba5;
          cursor: pointer;

          &:hover {
            color: #3a84ff;
          }
        }
        .message {
          flex: 1;
        }
      }

      /* 自定义滚动条样式 */
      ::-webkit-scrollbar {
        width: 8px;
      }
      ::-webkit-scrollbar-track {
        background: #1e1e1e;
      }
      ::-webkit-scrollbar-thumb {
        background-color: #4c4c4c; /* 滚动条颜色 */
        border: 2px solid #1e1e1e; /* 滚动条与轨道间隔 */
      }

      scrollbar-width: thin;
      scrollbar-color: #4c4c4c #1e1e1e;
    }
  }
}

/* 过渡动画 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s;
}

.dialog-fade-enter,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
